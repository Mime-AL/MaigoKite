/**
 * 渲染进程中对 electronAPI 的类型声明
 */

interface ElectronAPI {
  listSessions: () => Promise<any>
  createSession: (data: any) => Promise<any>
  searchMemories: (data: any) => Promise<any>
  listSkills: () => Promise<any>
  onAgentMessage: (callback: (data: any) => void) => void
  onGatewayError: (callback: (error: string) => void) => void
  connectWebSocket: (sessionId: string) => WebSocket
}

declare global {
  interface Window {
    electronAPI: ElectronAPI
  }
}
