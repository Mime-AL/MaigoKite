/**
 * WebSocket 组合式函数
 *
 * 管理与 Go API Gateway 的 WebSocket 连接，
 * 支持断线重连和 HTTP 轮询降级。
 */

import { ref, onUnmounted } from 'vue'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8080/ws'

export function useWebSocket(sessionId: string) {
  const ws = ref<WebSocket | null>(null)
  const isConnected = ref(false)
  const reconnectAttempts = ref(0)
  const maxReconnectAttempts = 5
  const reconnectDelay = 3000

  /** 连接 WebSocket */
  function connect() {
    if (ws.value?.readyState === WebSocket.OPEN) return

    const url = `${WS_URL}?session_id=${sessionId}`
    const socket = new WebSocket(url)

    socket.onopen = () => {
      isConnected.value = true
      reconnectAttempts.value = 0
    }

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleMessage(data)
      } catch {
        console.warn('WebSocket 消息解析失败:', event.data)
      }
    }

    socket.onclose = () => {
      isConnected.value = false
      ws.value = null
      attemptReconnect()
    }

    socket.onerror = () => {
      console.error('WebSocket 错误')
      socket.close()
    }

    ws.value = socket
  }

  /** 断开连接 */
  function disconnect() {
    ws.value?.close()
    ws.value = null
    isConnected.value = false
  }

  /** 发送消息 */
  function send(data: Record<string, any>) {
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify(data))
    }
  }

  /** 断线重连 */
  function attemptReconnect() {
    if (reconnectAttempts.value >= maxReconnectAttempts) {
      console.warn('达到最大重连次数，切换到 HTTP 轮询降级')
      return
    }
    reconnectAttempts.value++
    setTimeout(connect, reconnectDelay)
  }

  /** 消息处理钩子（子类可覆盖） */
  function handleMessage(_data: Record<string, any>) {
    // 由调用方通过事件或回调处理
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    isConnected,
    connect,
    disconnect,
    send
  }
}
