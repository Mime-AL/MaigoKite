interface ElectronAPI {
  runtimeStatus: () => Promise<{ platform: string; packaged: boolean }>
  onRuntimeError: (callback: (message: string) => void) => () => void
}
declare global { interface Window { electronAPI?: ElectronAPI } }
export {}
