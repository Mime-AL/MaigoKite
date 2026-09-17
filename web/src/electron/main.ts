import { app, BrowserWindow, ipcMain, Menu, shell, Tray } from 'electron'
import { spawn, type ChildProcess } from 'node:child_process'
import { existsSync } from 'node:fs'
import path from 'node:path'
import { createRuntimeEnvironment } from './runtime-env'

let mainWindow: BrowserWindow | null = null
let tray: Tray | null = null
const children: ChildProcess[] = []

export function secureWebPreferences() {
  return { preload: path.join(__dirname, 'preload.cjs'), contextIsolation: true, nodeIntegration: false, sandbox: true, webSecurity: true }
}

function projectRoot() { return process.env.NANAMI_PROJECT_ROOT || path.resolve(app.getAppPath(), '..') }
function startProcess(command: string, args: string[], cwd: string, workspaceRoot: string) {
  const env = createRuntimeEnvironment()
  env.NANAMI_WORKSPACE_ROOT = workspaceRoot
  const child = spawn(command, args, { cwd, shell: false, stdio: ['ignore', 'pipe', 'pipe'], env })
  child.on('error', () => mainWindow?.webContents.send('runtime:error', `${command} failed to start`))
  children.push(child)
}
function startRuntime() {
  if (process.env.NANAMI_EXTERNAL_RUNTIME === '1') return
  const root = projectRoot()
  const workspaceRoot = process.env.NANAMI_WORKSPACE_ROOT || (app.isPackaged ? process.cwd() : root)
  if (app.isPackaged) {
    startProcess(path.join(process.resourcesPath, 'bin', 'agent-core'), ['run'], process.resourcesPath, workspaceRoot)
    startProcess(path.join(process.resourcesPath, 'bin', 'gateway'), [], process.resourcesPath, workspaceRoot)
  } else {
    const projectPython = path.join(root, '.venv', 'bin', 'python')
    const python = process.env.NANAMI_PYTHON || (existsSync(projectPython) ? projectPython : 'python3')
    startProcess(python, [path.join(root, 'python', 'main.py'), 'run', '--config', path.join(root, 'config', 'config.dev.yaml'), '--port', '8081'], root, workspaceRoot)
    startProcess('go', ['run', './cmd/gateway'], path.join(root, 'gateway'), workspaceRoot)
  }
}
function stopRuntime() { for (const child of children.splice(0)) if (!child.killed) child.kill('SIGTERM') }

export function isAllowedNavigation(target: string, development: boolean) {
  try {
    const url = new URL(target)
    if (url.protocol === 'file:') return true
    return development && url.protocol === 'http:' && url.hostname === 'localhost' && url.port === '5173'
  } catch {
    return false
  }
}

export function createWindow() {
  const window = new BrowserWindow({ width: 1400, height: 900, minWidth: 800, minHeight: 600, titleBarStyle: 'hiddenInset', webPreferences: secureWebPreferences() })
  window.webContents.setWindowOpenHandler(({ url }) => { if (url.startsWith('https://')) void shell.openExternal(url); return { action: 'deny' } })
  window.webContents.on('will-navigate', (event, url) => { if (!isAllowedNavigation(url, !app.isPackaged)) event.preventDefault() })
  if (!app.isPackaged) void window.loadURL('http://localhost:5173'); else void window.loadFile(path.join(__dirname, '../dist/index.html'))
  window.on('closed', () => { mainWindow = null }); mainWindow = window; return window
}
function createTray() { tray = new Tray(path.join(app.getAppPath(), 'public', 'favicon.ico')); tray.setToolTip('NanamiGopher'); tray.setContextMenu(Menu.buildFromTemplate([{ label: '显示窗口', click: () => mainWindow?.show() }, { label: '退出', click: () => app.quit() }])) }
function registerIPC() { ipcMain.handle('runtime:status', event => ({ platform: process.platform, packaged: app.isPackaged, sender: event.sender.id })) }

app.whenReady().then(() => { startRuntime(); createWindow(); createTray(); registerIPC(); app.on('activate', () => { if (BrowserWindow.getAllWindows().length === 0) createWindow() }) })
app.on('before-quit', stopRuntime)
app.on('window-all-closed', () => { if (process.platform !== 'darwin') app.quit() })
