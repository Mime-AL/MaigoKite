// One host process owns one SRT session. Isolation and ACL recovery belong to SRT.
import { spawn } from 'node:child_process'
import { readFileSync, writeFileSync, renameSync } from 'node:fs'
import { createInterface } from 'node:readline'

const [action, receiptPath] = process.argv.slice(2)
const expectedVersion = '0.0.79'
let sdk, srtWin
try {
  if (process.platform !== 'win32') throw new Error('windows_required')
  const pkg = JSON.parse(readFileSync(new URL('./node_modules/@anthropic-ai/sandbox-runtime/package.json', import.meta.url), 'utf8'))
  if (pkg.version !== expectedVersion) throw new Error('version_mismatch')
  sdk = await import('@anthropic-ai/sandbox-runtime')
  // The released SDK requires an explicit helper, never PATH or a workspace lookup.
  srtWin = sdk.resolveSrtWin({ path: sdk.VENDORED_SRT_WIN_EXE })
} catch {
  if (action === 'run' && receiptPath)
    report({ started: false, cleanup_complete: true, error: 'dependency_unavailable' })
  console.error('Windows sandbox dependency unavailable. Run scripts/setup.ps1 sandbox (Node >=22.12).')
  process.exit(78)
}

function report(value) {
  // Only the Python owner reads this file; command output cannot forge readiness/cleanup.
  const temporary = receiptPath + '.next'
  writeFileSync(temporary, JSON.stringify(value), { mode: 0o600 })
  renameSync(temporary, receiptPath)
}

async function status() {
  const state = await sdk.checkWindowsSandboxStatusAsync({ srtWin })
  if (!state.user.provisioned || !state.user.credPresent) return { ready: false, reason: 'not_provisioned' }
  // Status does not grant file access or launch a sandbox child. initialize()
  // must still verify the live WFP fence for every command, before execution.
  return { provisioned: true, ready: false, reason: 'verification_on_execute', version: expectedVersion }
}

async function run() {
  if (!receiptPath) throw new Error('receipt_required')
  let child, stopping = false, started = false, handling = false, sid
  let failure = '', exitCode = 1
  const lines = createInterface({ input: process.stdin, crlfDelay: Infinity })
  report({ started: false, cleanup_complete: true, error: 'initializing' })
  const stop = () => {
    stopping = true
    // SRT's broker owns the runner Job; killing it closes the Job, not just a PID walk.
    if (child && child.exitCode === null) child.kill()
  }
  lines.on('close', stop) // Core exit closes the control pipe even on a crash.
  process.on('SIGTERM', stop)
  process.on('SIGINT', stop)
  const outputError = () => { failure = 'output_closed'; stop() }
  process.stdout.on('error', outputError)
  process.stderr.on('error', outputError)
  const initial = await new Promise((resolve, reject) => {
    let received = false
    lines.on('line', line => {
      if (!received) { received = true; resolve(line) }
      else if (line === 'stop') stop()
      else { failure = 'invalid_control'; stop() }
    })
    lines.once('close', () => reject(new Error('parent_closed')))
  })
  try {
    if (initial.length > 1024 * 1024) throw new Error('request_too_large')
    const request = JSON.parse(initial)
    const { argv, cwd, config } = request
    if (!Array.isArray(argv) || !argv.length || argv.some(arg => typeof arg !== 'string' || arg.includes('\0')))
      throw new Error('invalid_argv')
    const checked = sdk.SandboxRuntimeConfigSchema.parse({ ...config, windows: { srtWin: { path: srtWin.exe } } })
    if (checked.filesystem.disabled) throw new Error('isolation_required')
    const installed = await sdk.checkWindowsSandboxStatusAsync({ srtWin })
    sid = installed.user.sid
    if (!sid || !installed.user.provisioned || !installed.user.credPresent)
      throw new sdk.WindowsSandboxError('not_provisioned', 'Sandbox installation is required')
    if (stopping) return
    handling = true
    report({ started: false, cleanup_complete: false })
    // WFP verification runs this same helper as the dedicated account before
    // initialize() grants the workspace. A per-user install needs this narrow
    // temporary read grant first; it is released with the other session grants.
    sdk.grantWindowsAcl({ sandboxUserSid: sid, read: [srtWin.exe], write: [], srtWin })
    await sdk.SandboxManager.initialize(checked)
    if (stopping) return
    // The public shell descriptor accepts an executable + preceding argv. The last
    // argument stays a single argument; no host shell, quoting or protocol patch.
    const command = argv.length > 1 ? argv.at(-1) : ''
    const inner = { exe: argv[0], args: argv.slice(1, -1) }
    if (argv.length === 1) throw new Error('argument_required')
    const wrapped = await sdk.SandboxManager.wrapWithSandboxArgv(command, inner, undefined, undefined, cwd)
    if (stopping) return
    child = spawn(wrapped.argv[0], wrapped.argv.slice(1), {
      cwd, env: wrapped.env, shell: false, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'],
    })
    child.stdout.pipe(process.stdout, { end: false })
    child.stderr.pipe(process.stderr, { end: false })
    exitCode = await new Promise((resolve, reject) => {
      child.once('error', reject)
      child.once('spawn', () => {
        started = true
        try { report({ started, cleanup_complete: false }) }
        catch { failure = 'receipt_write_failed'; stop() }
        if (stopping) child.kill()
      })
      // close, unlike exit, also waits for inherited output handles to close.
      child.once('close', code => resolve(code ?? 1))
    })
  } catch (error) {
    failure = /^[a-z_]+$/.test(error?.code ?? '') ? error.code : 'sandbox_execution_failed'
    stop()
    if (child && child.exitCode === null) await new Promise(resolve => child.once('close', resolve))
  } finally {
    let clean = true
    if (handling) {
      // reset() is best-effort upstream. Inspect public ACL results before reset
      // so cleanup failure cannot be reported as a successful product command.
      try {
        if (!sid) throw new Error('missing_sid')
        for (const release of [sdk.revokeWindowsAcl, sdk.restoreWindowsAcl]) {
          const result = release({ sandboxUserSid: sid, srtWin })
          if (!Array.isArray(result) || result.some(item =>
            !['revoked', 'stillHeld', 'restored', 'alreadyOriginal'].includes(item.status))) clean = false
        }
      } catch { clean = false }
      try { await sdk.SandboxManager.reset() } catch { clean = false }
    }
    report({ started, cleanup_complete: clean, error: clean ? failure : 'cleanup_failed' })
    lines.removeListener('close', stop)
    lines.close()
    process.stdin.destroy()
    process.exitCode = !clean || failure || stopping ? 1 : exitCode
  }
}

try {
  if (action === 'status') console.log(JSON.stringify(await status()))
  else if (action === 'run') await run()
  else if (['install', 'uninstall'].includes(action)) {
    if (receiptPath !== '--confirm-system-changes') throw new Error('confirmation_required')
    const result = action === 'install'
      ? await sdk.installWindowsSandboxAsync({ srtWin })
      : sdk.uninstallWindowsSandbox({ srtWin })
    if (result.cancelled) throw new sdk.WindowsSandboxError('installation_cancelled', 'UAC cancelled')
    console.log(`Windows sandbox ${action} complete.`)
  } else throw new Error('unknown_action')
} catch (error) {
  const reason = /^[a-z_]+$/.test(error?.code ?? '') ? error.code : 'sandbox_unavailable'
  if (action === 'status') console.log(JSON.stringify({ ready: false, reason }))
  else console.error(`Windows sandbox failed (${reason}); inspect installation and folder permissions.`)
  process.exitCode = 1
}
