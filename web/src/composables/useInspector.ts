/**
 * Inspector 数据组合式函数
 *
 * 管理 Inspector 监控页面的数据加载和实时更新。
 */

import { ref, onUnmounted } from 'vue'
import type { InspectorCard, TimelineNode } from '@/types'
import { useInspectorStore } from '@/stores/inspector'

const INSPECTOR_WS_URL = 'ws://localhost:8080/api/v1/inspector/ws'

export function useInspector() {
  const inspectorStore = useInspectorStore()
  const ws = ref<WebSocket | null>(null)
  const isLoading = ref(false)

  /** 连接 Inspector WebSocket */
  function connect() {
    const socket = new WebSocket(INSPECTOR_WS_URL)

    socket.onopen = () => {
      console.log('Inspector WebSocket 已连接')
    }

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleInspectorMessage(data)
      } catch {
        console.warn('Inspector 消息解析失败:', event.data)
      }
    }

    socket.onclose = () => {
      // 3 秒后重连
      setTimeout(connect, 3000)
    }

    ws.value = socket
  }

  /** 处理 Inspector 消息 */
  function handleInspectorMessage(data: Record<string, any>) {
    switch (data.type) {
      case 'card_update':
        inspectorStore.updateCard(data.data as InspectorCard)
        break
      case 'timeline_node':
        inspectorStore.addTimelineNode(data.data as TimelineNode)
        break
    }
  }

  /** 加载卡片数据 */
  async function loadCards() {
    isLoading.value = true
    try {
      const res = await fetch('/api/v1/inspector/cards')
      const json = await res.json()
      inspectorStore.cards = json.cards ?? []
    } finally {
      isLoading.value = false
    }
  }

  onUnmounted(() => {
    ws.value?.close()
  })

  return {
    cards: inspectorStore.cards,
    activeCards: inspectorStore.activeCards,
    completedCards: inspectorStore.completedCards,
    failedCards: inspectorStore.failedCards,
    isLoading,
    connect,
    loadCards
  }
}
