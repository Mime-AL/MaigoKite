#!/usr/bin/env node
// Shared source-tree entry point. Bash/PowerShell wrappers only forward arguments.
// Process fan-out and failure propagation use concurrently, not a custom supervisor.
const { spawn, spawnSync } = require('node:child_process')
const { existsSync, mkdirSync } = require('node:fs')
const { createRequire } = require('node:module')
const net = require('node:net')
const os = require('node:os')
const path = require('node:path')

const root = path.resolve(__dirname, '..')
const web = path.join(root, 'web')
const gateway = path.join(root, 'gateway')
const windows = process.platform === 'win32'
const requireWeb = createRequire(path.join(web, 'package.json'))
const gatewayBinary = path.join(root, 'dist', `maigokite-api${windows ? '.exe' : ''}`)
const [action, targetArg, modeArg, ...extra] = process.argv.slice(2)

function run(command, args, cwd = root, env = process.env) {
  const result = spawnSync(command, args, { cwd, env, stdio: 'inherit', windowsHide: true })
  if (result.error) throw result.error
  if (result.status !== 0) throw new Error(`${path.basename(command)} failed (${result.signal || result.status})`)
}

function output(command, args) {
  const result = spawnSync(command, args, {
    cwd: root, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'], timeout: 15_000, windowsHide: true,
  })
  return result.status === 0 ? result.stdout.trim() : ''
}

function needFile(file) {
  if (!existsSync(file)) throw new Error(`Missing ${file}. Run setup / build first.`)
  return file
}

function hostPath(value, base = root) {
  return path.resolve(base, value.replace(/^~(?=[/\\]|$)/, os.homedir()))
}

function environmentPython(directory) {
  return path.join(directory, windows ? 'Scripts/python.exe' : 'bin/python')
}

function projectEnvironment() {
  return hostPath(process.env.UV_PROJECT_ENVIRONMENT || '.venv')
}

function probePython(command, args = []) {
  return output(command, [...args, '-I', '-c',
    'import sys; sys.exit(1) if sys.version_info < (3, 11) else print(sys.executable)'])
}

function findPython() {
  const override = process.env.MAIGOKITE_PYTHON
  if (override) {
    const found = probePython(/[/\\]/.test(override) ? hostPath(override) : override)
    if (found) return found
    throw new Error('MAIGOKITE_PYTHON must identify a usable Python 3.11+ executable.')
  }
  const projectPython = environmentPython(projectEnvironment())
  if (existsSync(projectPython)) {
    const found = probePython(projectPython)
    if (found) return found
    throw new Error('Project Python environment is unusable. Run setup again.')
  }
  if (process.env.VIRTUAL_ENV) {
    const found = probePython(environmentPython(hostPath(process.env.VIRTUAL_ENV)))
    if (found) return found
  }
  const uvPython = output('uv', ['python', 'find', '--no-python-downloads'])
  if (uvPython) {
    const found = probePython(uvPython)
    if (found) return found
  }
  for (const command of ['python', 'python3']) {
    const found = probePython(command)
    if (found) return found
  }
  if (windows) {
    const found = probePython('py', ['-3'])
    if (found) return found
  }
  throw new Error('Python 3.11+ not found. Install Python/uv or set MAIGOKITE_PYTHON.')
}

function npm(args) {
  if (!windows) return run('npm', args, web)
  // npm.cmd cannot be execFile'd. Invoke its installed JS entry with Node instead
  // of interpolating a repository path into cmd.exe (spaces, &, Unicode paths).
  const directories = [path.dirname(process.execPath), ...(process.env.PATH || '').split(path.delimiter)]
  for (const directory of directories) {
    const cli = path.join(directory.replace(/^"|"$/g, ''), 'node_modules/npm/bin/npm-cli.js')
    if (existsSync(cli)) return run(process.execPath, [cli, ...args], web)
  }
  throw new Error('npm CLI not found beside Node/on PATH. Install Node.js with npm.')
}

function needWebDependencies() {
  needFile(path.join(web, 'node_modules/vite/bin/vite.js'))
  needFile(path.join(web, 'node_modules/concurrently/package.json'))
}

function buildGateway() {
  const goOS = { win32: 'windows', linux: 'linux', darwin: 'darwin' }[process.platform]
  const goArch = { x64: 'amd64', arm64: 'arm64', ia32: '386' }[process.arch]
  if ((process.env.GOOS && process.env.GOOS !== goOS) || (process.env.GOARCH && process.env.GOARCH !== goArch))
    throw new Error('Local suite builds must target this computer. Unset cross-compilation GOOS/GOARCH overrides.')
  mkdirSync(path.dirname(gatewayBinary), { recursive: true })
  run('go', ['build', '-ldflags=-s -w', '-o', gatewayBinary, './cmd/gateway'], gateway,
    { ...process.env, CGO_ENABLED: process.env.CGO_ENABLED || '0' })
}

function setup() {
  if (targetArg || modeArg || extra.length) throw new Error('Usage: setup (no arguments)')
  if (!output('go', ['version'])) throw new Error('Go 1.22+ is required.')
  run('go', ['mod', 'download'], gateway)
  if (output('uv', ['--version'])) {
    const args = ['sync', '--locked', '--extra', 'dev']
    if (process.env.MAIGOKITE_PYTHON) args.push('--python', findPython())
    run('uv', args)
  } else {
    const venvPython = environmentPython(projectEnvironment())
    if (!existsSync(venvPython)) run(findPython(), ['-m', 'venv', projectEnvironment()])
    if (!probePython(venvPython)) throw new Error('Project Python environment is unusable.')
    run(venvPython, ['-m', 'pip', 'install', '-e', '.[dev]'])
  }
  npm(['ci'])
  console.info('Dependencies installed. Browser tools additionally need: <Core Python> -m playwright install chromium')
}

function build(target) {
  if (modeArg || extra.length || !['web', 'desktop', 'all', 'go', 'python', 'vue'].includes(target))
    throw new Error('Usage: build [web|desktop|all|go|python|vue]')
  if (target === 'python') {
    const out = path.join(root, 'dist')
    if (output('uv', ['--version'])) {
      const args = ['build', '--out-dir', out]
      if (process.env.MAIGOKITE_PYTHON) args.push('--python', findPython())
      run('uv', args)
    } else run(findPython(), ['-m', 'build', '--outdir', out])
    return
  }
  if (target !== 'go') needWebDependencies()
  if (target !== 'vue') buildGateway()
  if (target !== 'go') npm(['run', ['desktop', 'all'].includes(target) ? 'build' : 'build:web'])
  console.info('Build complete. Source-tree output only; Python dependencies are still required (not an installer).')
}

async function freePorts(ports) {
  for (const port of ports) {
    await new Promise((resolve, reject) => {
      const server = net.createServer()
      server.once('error', () => reject(new Error(`Port ${port} unavailable. Exit the existing suite first; no process was killed.`)))
      server.listen({ host: '127.0.0.1', port, exclusive: true }, () => server.close(resolve))
    })
  }
}

async function start(target, mode) {
  if (extra.length || !['web', 'desktop'].includes(target) || !['dev', 'built'].includes(mode))
    throw new Error('Usage: start [web|desktop] [dev|built]')
  needWebDependencies()
  // These are real, owned suites; never silently attach to an old Core or use mock UI.
  if (process.env.MAIGOKITE_EXTERNAL_RUNTIME === '1' || process.env.VITE_MOCK === '1')
    throw new Error('Unset MAIGOKITE_EXTERNAL_RUNTIME / VITE_MOCK before starting a complete suite.')
  const python = findPython()
  const config = needFile(hostPath(process.env.MAIGOKITE_CONFIG || 'config/config.dev.yaml'))
  const env = {
    ...process.env, MAIGOKITE_PROJECT_ROOT: root, MAIGOKITE_CONFIG: config,
    MAIGOKITE_PYTHON: python, PYTHONUNBUFFERED: '1',
    MAIGOKITE_INSTALL_DIR: hostPath(process.env.MAIGOKITE_INSTALL_DIR || root),
    MAIGOKITE_GATEWAY_PROXY_TARGET: 'http://127.0.0.1:8080',
    MAIGOKITE_PARENT_PIPE: '1',
  }
  if (env.MAIGOKITE_WORKSPACE_ROOT) env.MAIGOKITE_WORKSPACE_ROOT = hostPath(env.MAIGOKITE_WORKSPACE_ROOT)
  const port = mode === 'dev' ? 5173 : 4173
  await freePorts([8080, 8081, ...(target === 'web' || mode === 'dev' ? [port] : [])])
  if (mode === 'dev') {
    // Launch the binary directly: there is no `go run` intermediary to orphan.
    buildGateway()
    if (target === 'desktop') npm(['run', 'electron:compile'])
  } else {
    needFile(gatewayBinary)
    needFile(path.join(web, 'dist/index.html'))
    if (target === 'desktop') needFile(path.join(web, 'dist-electron/main.cjs'))
  }
  env.MAIGOKITE_GATEWAY_EXECUTABLE = gatewayBinary
  env.MAIGOKITE_DESKTOP_BUILT = mode === 'built' ? '1' : '0'
  const vite = path.join(web, 'node_modules/vite/bin/vite.js')
  const specs = target === 'web'
    ? [
        { name: 'Core', executable: python, args: [path.join(root, 'python/main.py'), 'run', '--config', config, '--port', '8081'], cwd: root },
        { name: 'Gateway', executable: gatewayBinary, args: [], cwd: root },
      ]
    : [{ name: 'Desktop', executable: requireWeb('electron'), args: [web], cwd: root }]
  if (target === 'web' || mode === 'dev') specs.push({
    name: 'Web', executable: process.execPath,
    args: ['--require', path.join(__dirname, 'lib/web-owner.cjs'), vite,
      ...(mode === 'built' ? ['preview'] : []), '--host', '127.0.0.1', '--port', String(port), '--strictPort'], cwd: web,
  })

  const { concurrently, Logger, LogOutput, LogError, LogExit, KillOnSignal, KillOthers } = requireWeb('concurrently')
  const treeKill = requireWeb('tree-kill')
  const logger = new Logger({ prefixFormat: '[{name}]' })
  const owned = new Map()
  const { result } = concurrently(specs.map(({ name, cwd }) => ({ name, command: name, cwd, env })), {
    logger, outputStream: process.stdout, successCondition: 'first',
    controllers: [new LogOutput({ logger }), new LogError({ logger }), new LogExit({ logger }),
      new KillOnSignal({ process }), new KillOthers({ logger, conditions: ['success', 'failure'] })],
    spawn(name, options) {
      const spec = specs.find((item) => item.name === name)
      const child = spawn(spec.executable, spec.args, {
        ...options, shell: false, windowsHide: true, detached: !windows, stdio: ['pipe', 'pipe', 'pipe'],
      })
      const record = { child, name, timer: null }
      if (child.pid) owned.set(child.pid, record)
      child.stdin.on('error', () => {}) // EPIPE when a child fails before shutdown.
      child.once('close', () => { clearTimeout(record.timer); owned.delete(child.pid) })
      return child
    },
    kill(pid) {
      const record = owned.get(pid)
      if (!record || record.timer) return
      // Core/Gateway/Desktop treat EOF as graceful stop, including owner crashes.
      // Windows cannot use SIGTERM for graceful cleanup. Force only after the wait.
      record.child.stdin.end()
      const force = () => {
        if (windows) treeKill(pid, 'SIGKILL', (error) => {
          if (error && owned.has(pid)) console.error(`Unable to stop ${record.name}: ${error.message}`)
        })
        else {
          try { process.kill(-pid, 'SIGKILL') } catch (error) {
            if (error.code !== 'ESRCH') console.error(`Unable to stop ${record.name}: ${error.message}`)
          }
        }
      }
      record.timer = setTimeout(force, record.name === 'Desktop' ? 20_000 : 15_000)
    },
  })
  if (target === 'web') console.info(`Starting local Web suite: http://127.0.0.1:${port} (wait for services to report ready).`)
  console.info('Ctrl+C stops the whole suite. Desktop window close hides to tray; use tray Exit to quit.')
  try { await result } catch { throw new Error('Suite stopped after a component failed; see the component log above.') }
}

async function main() {
  if (Number(process.versions.node.split('.')[0]) < 18) throw new Error('Node.js 18+ is required.')
  if (action === 'setup') setup()
  else if (action === 'build') build(targetArg || 'all')
  else if (action === 'start') await start(targetArg || 'web', modeArg || 'dev')
  else throw new Error('Usage: node scripts/local.cjs setup | build [web|desktop|all] | start [web|desktop] [dev|built]')
}
main().catch((error) => { console.error(`[MaigoKite] ${error.message}`); process.exitCode = 1 })
