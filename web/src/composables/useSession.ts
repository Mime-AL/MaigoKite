/**
 * 会话管理组合式函数
 *
 * 封装会话的创建、切换和消息发送逻辑。
 */

import { ref } from 'vue'
import { useSessionStore } from '@/stores/session'

export function useSession() {
  const sessionStore = useSessionStore()
  const isSending = ref(false)

  /** 创建新会话 */
  async function createNewSession(title = '') {
    return sessionStore.createSession(title)
  }

  /** 切换会话 */
  function switchToSession(sessionId: string) {
    sessionStore.switchSession(sessionId)
  }

  /** 获取会话列表 */
  async function refreshSessions() {
    await sessionStore.loadSessions()
  }

  return {
    activeSession: sessionStore.activeSession,
    sessions: sessionStore.sessions,
    isSending,
    createNewSession,
    switchToSession,
    refreshSessions
  }
}
