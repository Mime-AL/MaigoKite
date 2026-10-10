import { app, BrowserWindow, globalShortcut, Menu, screen, shell, Tray } from 'electron'
import { spawn, type ChildProcess } from 'node:child_process'
import { existsSync, readFileSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createRuntimeEnvironment } from './runtime-env'
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
let quitting = false,
  appearance: Appearance | null = null,
  shortcut = ''
let pulseState: PulseState = 'idle'
const children: ChildProcess[] = []
const indexPath = path.resolve(__dirname, '../dist/index.html')
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
function workspaceRoot() {
  return process.env.MAIGOKITE_WORKSPACE_ROOT || (app.isPackaged ? process.cwd() : projectRoot())
}
function startProcess(command: string, args: string[], cwd: string) {
  const env = createRuntimeEnvironment()
  env.MAIGOKITE_WORKSPACE_ROOT = workspaceRoot()
  const child = spawn(command, args, { cwd, shell: false, stdio: ['ignore', 'pipe', 'pipe'], env })
  child.stdout?.on('data', () => undefined)
  child.stderr?.on('data', () => undefined)
  child.on('error', () =>
    mainWindow?.webContents.send('runtime:error', t('应用服务启动失败，请重新打开应用。')),
  )
  children.push(child)
}
function startRuntime() {
  if (process.env.MAIGOKITE_EXTERNAL_RUNTIME === '1' || process.env.VITE_MOCK === '1') return
  const root = projectRoot()
  if (app.isPackaged) {
    startProcess(
      path.join(process.resourcesPath, 'bin', 'agent-core'),
      ['run'],
      process.resourcesPath,
    )
    startProcess(path.join(process.resourcesPath, 'bin', 'gateway'), [], process.resourcesPath)
  } else {
    const projectPython = path.join(root, '.venv', 'bin', 'python')
    const python =
      process.env.MAIGOKITE_PYTHON || (existsSync(projectPython) ? projectPython : 'python3')
    startProcess(
      python,
      [
        path.join(root, 'python', 'main.py'),
        'run',
        '--config',
        path.join(root, 'config', 'config.dev.yaml'),
        '--port',
        '8081',
      ],
      root,
    )
    startProcess('go', ['run', './cmd/gateway'], path.join(root, 'gateway'))
  }
}
function stopRuntime() {
  for (const child of children.splice(0)) if (!child.killed) child.kill('SIGTERM')
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
    if (!isAllowedNavigation(url, !app.isPackaged)) event.preventDefault()
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
  if (!app.isPackaged) void window.loadURL('http://localhost:5173')
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
    if (app.isPackaged) void window.loadFile(indexPath, { hash: '/capsule' })
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
app.whenReady().then(() => {
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
    allowed: (url) => isAllowedNavigation(url, !app.isPackaged),
    workspace: (folderId = '') => registeredWorkspaceRoot(folderId),
    appearance: () => appearance,
    setAppearance,
    pulse: setPulse,
  })
  startRuntime()
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
})
app.on('before-quit', () => {
  quitting = true
  globalShortcut.unregisterAll()
  stopRuntime()
})
