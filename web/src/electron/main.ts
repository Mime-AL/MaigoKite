/**
 * Electron 主进程入口
 *
 * 负责创建浏览器窗口、启动 Go API Gateway、
 * 注册 IPC 处理器、管理系统托盘。
 */

import { app, BrowserWindow, ipcMain, Tray, Menu } from 'electron'
import path from 'path'

let mainWindow: BrowserWindow | null = null
let tray: Tray | null = null

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 800,
    minHeight: 600,
    titleBarStyle: 'hiddenInset',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true
    }
  })

  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

function createTray() {
  tray = new Tray(path.join(__dirname, '../public/icon.png'))
  const contextMenu = Menu.buildFromTemplate([
    { label: '显示窗口', click: () => mainWindow?.show() },
    { label: '退出', click: () => app.quit() }
  ])
  tray.setToolTip('NanamiGopher')
  tray.setContextMenu(contextMenu)
}

// 注册 IPC 处理器
function registerIPCHandlers() {
  // 会话管理
  ipcMain.handle('session:list', async () => {
    const res = await fetch('http://localhost:8080/api/v1/sessions')
    return res.json()
  })

  ipcMain.handle('session:create', async (_, data) => {
    const res = await fetch('http://localhost:8080/api/v1/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    return res.json()
  })

  // 记忆管理
  ipcMain.handle('memory:search', async (_, data) => {
    const res = await fetch('http://localhost:8080/api/v1/memories/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    return res.json()
  })

  // Skill 管理
  ipcMain.handle('skill:list', async () => {
    const res = await fetch('http://localhost:8080/api/v1/skills')
    return res.json()
  })
}

app.whenReady().then(() => {
  createWindow()
  createTray()
  registerIPCHandlers()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
