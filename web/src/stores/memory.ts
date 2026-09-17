/**
 * 记忆状态 Store
 *
 * 管理记忆系统的搜索与展示状态。
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { MemoryItem } from '@/types'

export const useMemoryStore = defineStore('memory', () => {
  const memories = ref<MemoryItem[]>([])
  const searchQuery = ref('')
  const isSearching = ref(false)

  const searchResults = computed(() =>
    memories.value.filter((m) =>
      m.content.toLowerCase().includes(searchQuery.value.toLowerCase())
    )
  )

  /** 搜索记忆 */
  async function searchMemories(query: string) {
    isSearching.value = true
    searchQuery.value = query
    try {
      // Memory search API is introduced in Phase 2; keep the Phase 1 store inert.
      memories.value = []
    } finally {
      isSearching.value = false
    }
  }

  return {
    memories,
    searchQuery,
    isSearching,
    searchResults,
    searchMemories
  }
})
