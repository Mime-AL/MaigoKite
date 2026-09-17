import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('electronAPI', {
  runtimeStatus: () => ipcRenderer.invoke('runtime:status') as Promise<{ platform: string; packaged: boolean }>,
  onRuntimeError: (callback: (message: string) => void) => {
    const listener = (_event: Electron.IpcRendererEvent, message: string) => callback(message)
    ipcRenderer.on('runtime:error', listener)
    return () => ipcRenderer.removeListener('runtime:error', listener)
  }
})
