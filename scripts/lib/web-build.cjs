// Vite owns compilation. Receipts prevent source-tree starts from using a failed
// or outdated build, including Electron bundles that still launch the Go gateway.
const { spawnSync } = require('node:child_process')
const { createHash } = require('node:crypto')
const { existsSync, readdirSync, readFileSync, statSync, unlinkSync, writeFileSync } = require('node:fs')
const path = require('node:path')

const web = path.resolve(__dirname, '../../web')
const parts = {
  web: { directory: 'dist', files: ['index.html'] },
  electron: { directory: 'dist-electron', files: ['main.cjs', 'preload.cjs'] },
}
const targets = { web: ['web'], electron: ['electron'], desktop: ['web', 'electron'] }

function sourceFingerprint() {
  const hash = createHash('sha256')
  function visit(relative) {
    // Local test fixtures are not build inputs; editing them must not invalidate the app.
    if (relative.startsWith('src/') && /(^|\/)(tests|__tests__)(\/|$)|\.(test|spec)\.[^/]+$/.test(relative)) return
    const file = path.join(web, relative)
    if (!existsSync(file)) return
    if (statSync(file).isDirectory()) {
      for (const name of readdirSync(file).sort()) visit(`${relative}/${name}`)
    } else {
      hash.update(relative).update('\0').update(createHash('sha256').update(readFileSync(file)).digest())
    }
  }
  for (const input of [
    'src', 'public', 'index.html', 'package.json', 'package-lock.json',
    'tsconfig.json', 'tsconfig.build.json', 'vite.config.ts', 'electron.vite.config.ts',
    ...readdirSync(web).filter((name) => name === '.env' || name.startsWith('.env.')).sort(),
  ]) visit(input)
  hash.update(readFileSync(__filename))
  return hash.digest('hex')
}

function receiptPath(part) {
  return path.join(web, parts[part].directory, '.maigokite-build.json')
}

function checkOutputs(part) {
  for (const file of parts[part].files) {
    const output = statSync(path.join(web, parts[part].directory, file))
    if (!output.isFile() || !output.size) throw new Error(`Incomplete ${part} output: ${file}`)
  }
}

function requireBuild(target) {
  const source = sourceFingerprint()
  for (const part of targets[target]) {
    try {
      const receipt = JSON.parse(readFileSync(receiptPath(part), 'utf8'))
      if (receipt.version !== 1 || receipt.source !== source) throw new Error('Outdated build')
      checkOutputs(part)
    } catch {
      const command = process.platform === 'win32'
        ? `.\\scripts\\build.ps1 ${target}` : `bash scripts/build.sh ${target}`
      throw new Error(`Missing, incomplete or outdated ${part} build. Run ${command} successfully before starting. No service was started.`)
    }
  }
}

function build(target) {
  const selected = targets[target]
  if (!selected) throw new Error('Usage: web-build.cjs web|desktop|electron')
  // Invalidate before type checking: a failed command must not leave an older
  // success receipt that would allow a subsequent, separately pasted start.
  for (const part of selected) {
    try { unlinkSync(receiptPath(part)) } catch (error) { if (error.code !== 'ENOENT') throw error }
  }
  const source = sourceFingerprint()
  function run(bin, args) {
    const result = spawnSync(process.execPath, [path.join(web, 'node_modules', bin), ...args], {
      cwd: web, stdio: 'inherit', windowsHide: true,
    })
    if (result.error) throw result.error
    if (result.status !== 0) throw new Error(`${bin} failed (${result.signal || result.status})`)
  }
  if (selected.includes('web')) {
    run('vue-tsc/bin/vue-tsc.js', ['--noEmit', '-p', 'tsconfig.build.json'])
    run('vite/bin/vite.js', ['build'])
  }
  if (selected.includes('electron')) {
    run('vite/bin/vite.js', ['build', '--config', 'electron.vite.config.ts'])
    run('vite/bin/vite.js', ['build', '--config', 'electron.vite.config.ts', '--mode', 'preload'])
  }
  if (source !== sourceFingerprint()) throw new Error('Build inputs changed during compilation. Rebuild before starting.')
  for (const part of selected) checkOutputs(part)
  for (const part of selected)
    writeFileSync(receiptPath(part), JSON.stringify({ version: 1, source }) + '\n', 'utf8')
}

module.exports = { requireBuild }
if (require.main === module) {
  try { build(process.argv[2]) } catch (error) {
    console.error(`[MaigoKite] ${error.message}`)
    process.exitCode = 1
  }
}
