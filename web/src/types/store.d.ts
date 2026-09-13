/**
 * Store 类型定义
 *
 * 定义 Pinia Store 的状态结构，包括布局、WebSocket 连接和 Inspector 状态。
 */

// Layout 状态
interface LayoutState {
  sidebarCollapsed: boolean
  sidebarWidth: number
  fileExplorerCollapsed: boolean
  fileExplorerWidth: number
}

// WebSocket 连接状态
interface WebSocketState {
  connected: boolean
  reconnecting: boolean
  lastError: string | null
}

// Inspector 状态
interface InspectorState {
  cards: InspectorCard[]
  selectedCard: string | null
  dimensions: {
    taskBreakdown: boolean
    toolChain: boolean
    modelInfo: boolean
    eventFlow: boolean
    exceptionHandling: boolean
    subAgentStatus: boolean
  }
}

export {}
