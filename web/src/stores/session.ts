/**
 * 会话状态 Store
 *
 * 管理会话列表、当前会话及消息。
 * 数据通过 Electron IPC 或 HTTP 与 Go API Gateway 同步。
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Session, Message } from '@/types'

export const useSessionStore = defineStore('session', () => {
  const sessions = ref<Session[]>([])
  const activeSessionId = ref<string | null>(null)
  const isLoading = ref(false)

  const activeSession = computed(() =>
    sessions.value.find((s) => s.id === activeSessionId.value)
  )

  /** 加载会话列表 */
  async function loadSessions() {
    isLoading.value = true
    try {
      const result = await window.electronAPI.listSessions()
      sessions.value = result.sessions ?? []
    } finally {
      isLoading.value = false
    }
  }

  /** 创建新会话 */
  async function createSession(title: string) {
    const result = await window.electronAPI.createSession({ title })
    sessions.value.unshift(result)
    activeSessionId.value = result.id
    return result
  }

  /** 切换到指定会话 */
  function switchSession(sessionId: string) {
    activeSessionId.value = sessionId
  }

  return {
    sessions,
    activeSessionId,
    isLoading,
    activeSession,
    loadSessions,
    createSession,
    switchSession
  }
})
