import { execFile } from 'node:child_process'
import { existsSync } from 'node:fs'
import path from 'node:path'
import { createRuntimeEnvironment } from './runtime-env'
import { t } from '../i18n'

function hostPath(value: string, base: string) {
  const home = process.env.HOME || process.env.USERPROFILE
  if (home && (value.startsWith('~/') || value.startsWith('~\\')))
    return path.resolve(home, value.slice(2))
  return path.resolve(base, value)
}

function environmentPython(directory: string) {
  return process.platform === 'win32'
    ? path.join(directory, 'Scripts', 'python.exe')
    : path.join(directory, 'bin', 'python')
}

function commandOutput(command: string, args: string[], cwd: string, signal: AbortSignal) {
  return new Promise<string>((resolve, reject) => {
    execFile(command, args, {
      cwd, signal, env: createRuntimeEnvironment(), encoding: 'utf8',
      timeout: 5_000, maxBuffer: 16_384, windowsHide: true,
    }, (error, stdout) => {
      if (error) reject(error)
      else resolve(stdout.trim())
    })
  })
}

async function usablePython(command: string, root: string, signal: AbortSignal, args: string[] = []) {
  try {
    // Matches pyproject.toml; sys.executable retains the selected virtual environment.
    return await commandOutput(command, [...args, '-I', '-c',
      'import sys; sys.exit("Python 3.14.x required") if sys.version_info[:2] != (3, 14) else print(sys.executable)',
    ], root, signal)
  } catch {
    signal.throwIfAborted()
    return undefined
  }
}

/** Resolve Core only. Never substitute this interpreter into user workspace or MCP commands. */
export async function resolveCorePython(root: string, signal: AbortSignal): Promise<string> {
  const override = process.env.MAIGOKITE_PYTHON
  if (override) {
    const command = /[/\\]/.test(override) ? hostPath(override, root) : override
    const python = await usablePython(command, root, signal)
    if (python) return python
    throw new Error(t('指定的 Python 不可用或不是 3.14.x：{0}', [override]))
  }
  // Match uv's project-root-relative environment path rather than shell expansion.
  const environment = path.resolve(root, process.env.UV_PROJECT_ENVIRONMENT || '.venv')
  const projectPython = environmentPython(environment)
  if (existsSync(projectPython)) {
    const python = await usablePython(projectPython, root, signal)
    if (python) return python
    throw new Error(t('项目环境需要 Python 3.14.x：{0}。请退出应用后使用 uv 重新运行 setup.sh / setup.ps1；没有 uv 时先重命名旧环境目录。', [environment]))
  }
  if (process.env.VIRTUAL_ENV) {
    const python = await usablePython(environmentPython(hostPath(process.env.VIRTUAL_ENV, root)), root, signal)
    if (python) return python
  }
  try {
    // uv owns managed Python / .python-version discovery. Starting the app never downloads Python.
    const candidate = await commandOutput('uv', ['python', 'find', '3.14', '--no-python-downloads'], root, signal)
    const python = await usablePython(candidate, root, signal)
    if (python) return python
  } catch {
    signal.throwIfAborted()
  }
  for (const command of ['python3.14', 'python', 'python3']) {
    const python = await usablePython(command, root, signal)
    if (python) return python
  }
  if (process.platform === 'win32') {
    const python = await usablePython('py', root, signal, ['-3.14'])
    if (python) return python
  }
  throw new Error(t('找不到 Python 3.14.x。请运行 setup.sh / setup.ps1，或设置 MAIGOKITE_PYTHON。'))
}
