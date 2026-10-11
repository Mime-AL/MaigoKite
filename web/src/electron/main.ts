import { app, BrowserWindow, dialog, globalShortcut, Menu, screen, shell, Tray } from 'electron'
import { spawn, type ChildProcess } from 'node:child_process'
import { existsSync, readFileSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { createConnection, createServer } from 'node:net'
import { setTimeout as delay } from 'node:timers/promises'
import { fileURLToPath } from 'node:url'
import { createRuntimeEnvironment } from './runtime-env'
import { resolveCorePython } from './python-runtime'
import { registerIPC } from './ipc'
import { registeredWorkspaceRoot } from './workspace'
import { appearanceValue } from './contracts'
import { trayImage } from './tray-icons'
import { i18n, resolveLanguage, t } from '../i18n'
import type { Appearance } from '../stores/ui'
import type { PulseState } from '../api/events'
app.setName('MaigoKite')

let mainWindow: BrowserWindow | null = null,
  capsuleWindow: BrowserWindow | null = null,
  tray: Tray | null = null
let shutdownComplete = false
const singleInstance = app.requestSingleInstanceLock()
if (!singleInstance) app.quit()
let quitting = false,
  appearance: Appearance | null = null,
  shortcut = ''
let pulseState: PulseState = 'idle'
const children: ChildProcess[] = []
const runtimeStartup = new AbortController()
let runtimeFailure = '',
  runtimeShutdown: Promise<void> | null = null
const indexPath = path.resolve(__dirname, '../dist/index.html')
const builtUI = app.isPackaged || process.env.MAIGOKITE_DESKTOP_BUILT === '1'
const appIconPath = path.resolve(
  __dirname,
  app.isPackaged ? '../dist/brand/app-icon-cat-ribbon-v1.png' : '../public/brand/app-icon-cat-ribbon-v1.png',
)
export function secureWebPreferences() {
  return {
    preload: path.join(__dirname, 'preload.cjs'),
    contextIsolation: true,
    nodeIntegration: false,
    sandbox: true,
    webSecurity: true,
  }
}
function projectRoot() {
  return process.env.MAIGOKITE_PROJECT_ROOT || path.resolve(app.getAppPath(), '..')
}
function absoluteHostPath(value: string) {
  if (value === '~') return app.getPath('home')
  if (value.startsWith('~/') || value.startsWith('~\\'))
    return path.resolve(app.getPath('home'), value.slice(2))
  return path.resolve(value)
}
function installationRoot() {
  if (process.env.MAIGOKITE_INSTALL_DIR) return absoluteHostPath(process.env.MAIGOKITE_INSTALL_DIR)
  if (!app.isPackaged) return path.resolve(projectRoot())
  // AppImage's executable is mounted read-only; use the original image's directory.
  if (process.platform === 'linux' && process.env.APPIMAGE)
    return path.dirname(path.resolve(process.env.APPIMAGE))
  const executableDirectory = path.dirname(app.getPath('exe'))
  // Keep user files outside the signed .app bundle, not in Contents/MacOS or app.asar.
  return process.platform === 'darwin'
    ? path.resolve(executableDirectory, '../../..')
    : executableDirectory
}
function reportRuntimeFailure(message: string) {
  if (quitting || runtimeFailure) return
  runtimeFailure = message
  runtimeStartup.abort(new Error(message))
  console.error(`[MaigoKite] ${message}`)
  mainWindow?.webContents.send('runtime:error', message)
  // A failed backend ends this owned desktop suite too, rather than leaving
  // Electron/Vite alive against a stopped runtime.
  void stopRuntime().finally(() => app.exit(1))
  dialog.showErrorBox(t('应用服务无法启动'), message)
}
function startProcess(name: string, command: string, args: string[], cwd: string, configPath?: string) {
  runtimeStartup.signal.throwIfAborted()
  const env = createRuntimeEnvironment()
  env.MAIGOKITE_INSTALL_DIR = installationRoot()
  if (env.MAIGOKITE_WORKSPACE_ROOT)
    env.MAIGOKITE_WORKSPACE_ROOT = absoluteHostPath(env.MAIGOKITE_WORKSPACE_ROOT)
  if (configPath) env.MAIGOKITE_CONFIG = configPath
  env.MAIGOKITE_PARENT_PIPE = '1'
  console.info(`[MaigoKite] Starting ${name}`)
  // A process group also owns the executable spawned by `go run`.
  const child = spawn(command, args, {
    cwd,
    shell: false,
    detached: process.platform !== 'win32',
    stdio: ['pipe', 'pipe', 'pipe'],
    windowsHide: true,
    env,
  })
  // Forward logs; `close` waits for inherited pipes, including the Gateway child.
  child.stdout?.on('data', (chunk: Buffer) => process.stdout.write(chunk))
  child.stderr?.on('data', (chunk: Buffer) => process.stderr.write(chunk))
  child.stdin?.on('error', () => { /* The child may fail before its owner closes stdin. */ })
  child.on('error', (error) =>
    reportRuntimeFailure(t('{0} 启动失败：{1}', [name, error.message])),
  )
  child.on('exit', (code, signal) => {
    if (!quitting && !runtimeShutdown)
      reportRuntimeFailure(t('{0} 已退出（{1}）。请查看终端日志后重新启动。', [name, signal || String(code)]))
  })
  child.once('close', () => {
    const index = children.indexOf(child)
    if (index >= 0) children.splice(index, 1)
  })
  children.push(child)
}
async function waitForPort(port: number, name: string) {
  const signal = runtimeStartup.signal,
    deadline = Date.now() + 90_000
  while (Date.now() < deadline) {
    signal.throwIfAborted()
    const ready = await new Promise<boolean>((resolve) => {
      const socket = createConnection({ host: '127.0.0.1', port })
      function finish(connected: boolean) {
        signal.removeEventListener('abort', abort)
        socket.destroy()
        resolve(connected)
      }
      const abort = () => finish(false)
      signal.addEventListener('abort', abort, { once: true })
      socket.once('connect', () => finish(true))
      socket.once('error', () => finish(false))
      socket.setTimeout(1_000, () => finish(false))
      if (signal.aborted) abort()
    })
    signal.throwIfAborted()
    if (ready) return
    await delay(250, undefined, { signal })
  }
  throw new Error(t('{0} 启动超时（端口 {1}）。请查看终端日志。', [name, port]))
}
async function startRuntime() {
  if (process.env.MAIGOKITE_EXTERNAL_RUNTIME === '1' || process.env.VITE_MOCK === '1') return
  // Do not attach to a previous instance's open TCP port or mutate its database.
  for (const port of [8080, 8081]) await new Promise<void>((resolve, reject) => {
    const server = createServer()
    server.once('error', () => reject(new Error(t('端口 {0} 已被占用，请先退出已有应用服务。', [port]))))
    server.listen({ host: '127.0.0.1', port, exclusive: true }, () => server.close(() => resolve()))
  })
  const root = projectRoot()
  const bundledConfig = path.join(process.resourcesPath, 'config', 'config.prod.yaml')
  const configPath = process.env.MAIGOKITE_CONFIG
    ? absoluteHostPath(process.env.MAIGOKITE_CONFIG)
    : app.isPackaged
      ? (existsSync(bundledConfig) ? bundledConfig : undefined)
      : path.join(root, 'config', 'config.dev.yaml')
  if (app.isPackaged) {
    const executableSuffix = process.platform === 'win32' ? '.exe' : ''
    startProcess(
      'Core',
      path.join(process.resourcesPath, 'bin', `agent-core${executableSuffix}`),
      ['run'],
      process.resourcesPath,
      configPath,
    )
    await waitForPort(8081, 'Core')
    startProcess('Gateway', path.join(process.resourcesPath, 'bin', `gateway${executableSuffix}`), [], process.resourcesPath, configPath)
  } else {
    const python = await resolveCorePython(root, runtimeStartup.signal)
    runtimeStartup.signal.throwIfAborted()
    console.info(`[MaigoKite] Core Python: ${python}`)
    startProcess(
      'Core',
      python,
      [
        path.join(root, 'python', 'main.py'),
        'run',
        '--port',
        '8081',
      ],
      root,
      configPath,
    )
    await waitForPort(8081, 'Core')
    const gatewayExecutable = process.env.MAIGOKITE_GATEWAY_EXECUTABLE
    startProcess('Gateway', gatewayExecutable || 'go', gatewayExecutable ? [] : ['run', './cmd/gateway'],
      gatewayExecutable ? root : path.join(root, 'gateway'), configPath)
  }
  // The Gateway listens only after connecting to Core. Avoid failed initial UI requests.
  await waitForPort(8080, 'Gateway')
  console.info('[MaigoKite] Core and Gateway are ready')
}
function stopRuntime(): Promise<void> {
  if (runtimeShutdown) return runtimeShutdown
  runtimeStartup.abort()
  runtimeShutdown = Promise.all(children.splice(0).map((child) => new Promise<void>((resolve) => {
    const pid = child.pid
    if (!pid) {
      resolve()
      return
    }
    function terminate(processId: number, signal: NodeJS.Signals) {
      try {
        if (process.platform === 'win32') {
          const killer = spawn('taskkill', ['/PID', String(processId), '/T', '/F'], {
            shell: false, stdio: 'ignore', env: createRuntimeEnvironment(),
          })
          killer.once('error', () => child.kill(signal))
        } else process.kill(-processId, signal)
      } catch (error) {
        if ((error as NodeJS.ErrnoException).code !== 'ESRCH') console.error('[MaigoKite] Runtime shutdown:', error)
      }
    }
    const timeout = setTimeout(() => terminate(pid, 'SIGKILL'), 15_000)
    child.once('close', () => {
      clearTimeout(timeout)
      resolve()
    })
    // EOF works on Windows too; SIGTERM there would immediately terminate Python.
    child.stdin?.end()
    if (process.platform !== 'win32') terminate(pid, 'SIGTERM')
  }))).then(() => undefined)
  return runtimeShutdown
}
export function isAllowedNavigation(target: string, development: boolean) {
  try {
    const url = new URL(target)
    if (url.protocol === 'file:') return path.resolve(fileURLToPath(url)) === indexPath
    return development && url.origin === 'http://localhost:5173'
  } catch {
    return false
  }
}
function secureNavigation(window: BrowserWindow) {
  window.webContents.setWindowOpenHandler(({ url }) => {
    try {
      if (['https:', 'http:'].includes(new URL(url).protocol)) void shell.openExternal(url)
    } catch {
      /* Invalid links are ignored. */
    }
    return { action: 'deny' }
  })
  window.webContents.on('will-navigate', (event, url) => {
    if (!isAllowedNavigation(url, !builtUI)) event.preventDefault()
  })
}
export function createWindow() {
  const window = new BrowserWindow({
    title: 'MaigoKite',
    icon: appIconPath,
    width: 1320,
    height: 860,
    minWidth: 560,
    minHeight: 500,
    frame: false,
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'hidden',
    trafficLightPosition: { x: 12, y: 11 },
    webPreferences: secureWebPreferences(),
  })
  secureNavigation(window)
  if (!builtUI) void window.loadURL('http://localhost:5173')
  else void window.loadFile(indexPath)
  window.on('close', (event) => {
    if (!quitting) {
      event.preventDefault()
      window.hide()
    }
  })
  window.on('closed', () => {
    mainWindow = null
  })
  mainWindow = window
  return window
}
function showCapsule() {
  if (!capsuleWindow) {
    const window = new BrowserWindow({
      title: `MaigoKite · ${t('速记')}`,
      icon: appIconPath,
      width: 560,
      height: 56,
      frame: false,
      alwaysOnTop: true,
      resizable: false,
      skipTaskbar: true,
      show: false,
      webPreferences: secureWebPreferences(),
    })
    capsuleWindow = window
    secureNavigation(window)
    if (builtUI) void window.loadFile(indexPath, { hash: '/capsule' })
    else void window.loadURL('http://localhost:5173/capsule')
    window.once('ready-to-show', () => {
      window.show()
      window.focus()
    })
    window.on('blur', () => window.hide())
    window.on('closed', () => {
      capsuleWindow = null
    })
  }
  const bounds = screen.getDisplayNearestPoint(screen.getCursorScreenPoint()).workArea
  capsuleWindow.setPosition(
    Math.round(bounds.x + (bounds.width - 560) / 2),
    Math.round(bounds.y + bounds.height * 0.2),
  )
  capsuleWindow.show()
  capsuleWindow.focus()
}
function setShortcut(value: string) {
  if (shortcut === value) return
  if (!globalShortcut.register(value, showCapsule))
    throw new Error(t('快捷键已被占用，请换一个组合。'))
  if (shortcut) globalShortcut.unregister(shortcut)
  shortcut = value
}
function setAppearance(value: Appearance) {
  if (appearance && appearance.capsuleShortcut !== value.capsuleShortcut)
    setShortcut(value.capsuleShortcut)
  else if (!shortcut) {
    try {
      setShortcut(value.capsuleShortcut)
    } catch {
      /* A reserved default shortcut must not block theme sync. */
    }
  }
  if (JSON.stringify(value) === JSON.stringify(appearance)) return
  appearance = value
  i18n.global.locale.value = resolveLanguage(value.language, app.getLocale())
  updateTrayMenu()
  setPulse(pulseState)
  capsuleWindow?.setTitle(`MaigoKite · ${t('速记')}`)
  writeFileSync(
    path.join(app.getPath('userData'), 'inkline-ui.json'),
    JSON.stringify(value),
    'utf8',
  )
  for (const window of [mainWindow, capsuleWindow])
    window?.webContents.send('appearance:changed', value)
}
function setPulse(state: PulseState) {
  pulseState = state
  tray?.setImage(trayImage(state))
  tray?.setToolTip(
    'MaigoKite · ' +
      t({
        idle: '静息',
        thinking: '思考',
        acting: '行动',
        waiting: '等待确认',
        error: '出错',
        offline: '离线',
      }[state]),
  )
}
function createTray() {
  tray = new Tray(trayImage('idle'))
  tray.setToolTip('MaigoKite')
  tray.on('click', () => {
    mainWindow?.show()
    mainWindow?.focus()
  })
  updateTrayMenu()
  setPulse(pulseState)
}
function updateTrayMenu() {
  tray?.setContextMenu(
    Menu.buildFromTemplate([
      {
        label: t('显示窗口'),
        click: () => {
          mainWindow?.show()
          mainWindow?.focus()
        },
      },
      { label: t('速记'), click: showCapsule },
      { type: 'separator' },
      { label: t('退出'), click: () => app.quit() },
    ]),
  )
}
app.whenReady().then(async () => {
  if (!singleInstance || quitting) return
  if (process.platform === 'darwin') app.dock?.setIcon(appIconPath)
  try {
    const value: unknown = JSON.parse(
      readFileSync(path.join(app.getPath('userData'), 'inkline-ui.json'), 'utf8'),
    )
    if (appearanceValue(value)) appearance = value
  } catch {
    /* First launch uses saved renderer appearance. */
  }
  i18n.global.locale.value = resolveLanguage(appearance?.language, app.getLocale())
  registerIPC({
    main: () => mainWindow,
    capsule: () => capsuleWindow,
    allowed: (url) => isAllowedNavigation(url, !builtUI),
    workspace: (folderId = '') => registeredWorkspaceRoot(folderId),
    appearance: () => appearance,
    setAppearance,
    pulse: setPulse,
  })
  await startRuntime()
  if (!builtUI) await waitForPort(5173, 'Web')
  if (quitting) return
  createWindow()
  createTray()
  try {
    setShortcut(appearance?.capsuleShortcut || 'Alt+Space')
  } catch {
    /* Settings can choose a free shortcut. */
  }
  app.on('activate', () => {
    if (!mainWindow) createWindow()
    mainWindow?.show()
  })
}).catch(async (error: unknown) => {
  reportRuntimeFailure(error instanceof Error ? error.message : String(error))
  await stopRuntime()
  if (quitting) app.quit()
  else app.exit(1)
})
app.on('before-quit', (event) => {
  if (shutdownComplete || !singleInstance) return
  event.preventDefault()
  if (quitting) return
  quitting = true
  globalShortcut.unregisterAll()
  void stopRuntime().finally(() => {
    shutdownComplete = true
    app.quit()
  })
})
app.on('second-instance', () => { mainWindow?.show(); mainWindow?.focus() })
process.on('SIGINT', () => app.quit())
process.on('SIGTERM', () => app.quit())
process.on('SIGHUP', () => app.quit())
if (process.env.MAIGOKITE_PARENT_PIPE === '1') {
  process.stdin.on('end', () => app.quit())
  process.stdin.on('error', () => app.quit())
  process.stdin.resume()
}
