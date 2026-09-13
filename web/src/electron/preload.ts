/**
 * Electron 预加载脚本
 *
 * 通过 contextBridge 向渲染进程暴露安全的 IPC 接口。
 * 避免直接暴露 Node.js API，保持 contextIsolation。
 */

import { contextBridge, ipcRenderer } from 'electron'

interface ElectronAPI {
  listSessions: () => Promise<any>
  createSession: (data: any) => Promise<any>
  searchMemories: (data: any) => Promise<any>
  listSkills: () => Promise<any>
  onAgentMessage: (callback: (data: any) => void) => void
  onGatewayError: (callback: (error: string) => void) => void
  connectWebSocket: (sessionId: string) => WebSocket
}

const electronAPI: ElectronAPI = {
  listSessions: () => ipcRenderer.invoke('session:list'),
  createSession: (data) => ipcRenderer.invoke('session:create', data),
  searchMemories: (data) => ipcRenderer.invoke('memory:search', data),
  listSkills: () => ipcRenderer.invoke('skill:list'),

  onAgentMessage: (callback) => {
    ipcRenderer.on('agent-message', (_, data) => callback(data))
  },

  onGatewayError: (callback) => {
    ipcRenderer.on('gateway-error', (_, error) => callback(error))
  },

  connectWebSocket: (sessionId) => {
    const ws = new WebSocket(`ws://localhost:8080/api/v1/sessions/${sessionId}/stream`)
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      ipcRenderer.send('websocket-message', data)
    }
    return ws
  }
}

contextBridge.exposeInMainWorld('electronAPI', electronAPI)
