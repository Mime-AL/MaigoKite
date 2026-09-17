/**
 * 记忆类型定义
 *
 * 定义记忆系统的接口和数据结构，包括短期记忆、对话记忆和用户记忆。
 */

// 记忆系统接口
interface MemorySystem {
  short_term: ShortTermMemory
  conversation: ConversationMemory
  user: UserMemory
}

// 短期记忆
interface ShortTermMemory {
  get_context(session_id: string): Message[]
  save(session_id: string, messages: Message[]): void
  clear(session_id: string): void
}

// 用户记忆
interface UserMemory {
  get_preferences(user_id: string): Record<string, any>
  set_preference(user_id: string, key: string, value: any): void
  get_facts(user_id: string): string[]
}

export interface MemoryItem {
  id: string
  content: string
  type: string
  metadata?: Record<string, unknown>
}

export {}
