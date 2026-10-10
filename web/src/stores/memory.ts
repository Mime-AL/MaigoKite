import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api, type MemoryInput, type UserMemory } from '@/api/client'

export const useMemoryStore = defineStore('memory', () => {
  const items = ref<UserMemory[]>([])
  const query = ref('')
  const loading = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)
  let stored: unknown
  const storageKey =
    import.meta.env.VITE_MOCK === '1' ? 'maigokite_pinned_memories_demo' : 'maigokite_pinned_memories'
  try {
    stored = JSON.parse(localStorage.getItem(storageKey) || '[]')
  } catch {
    stored = []
  }
  const pinnedIds = ref<string[]>(
    Array.isArray(stored) ? stored.filter((id): id is string => typeof id === 'string') : [],
  )
  const orderedItems = computed(() =>
    items.value
      .slice()
      .sort(
        (a, b) => Number(pinnedIds.value.includes(b.id)) - Number(pinnedIds.value.includes(a.id)),
      ),
  )
  function togglePinned(id: string) {
    pinnedIds.value = pinnedIds.value.includes(id)
      ? pinnedIds.value.filter((value) => value !== id)
      : [...pinnedIds.value, id]
    try {
      localStorage.setItem(storageKey, JSON.stringify(pinnedIds.value))
    } catch {
      /* Pinning remains available in this window. */
    }
  }

  async function load(search = query.value) {
    if (loading.value) return
    query.value = search.trim()
    loading.value = true
    error.value = null
    try {
      items.value = await api.listMemories(query.value)
    } catch (reason) {
      error.value = reason instanceof Error ? reason.message : String(reason)
    } finally {
      loading.value = false
    }
  }

  async function save(input: MemoryInput & { id?: string }) {
    saving.value = true
    error.value = null
    try {
      const saved = await api.saveMemory(input)
      const index = items.value.findIndex((item) => item.id === saved.id)
      const visible =
        !query.value || saved.content.toLocaleLowerCase().includes(query.value.toLocaleLowerCase())
      if (index >= 0 && visible) items.value[index] = saved
      else if (index >= 0) items.value.splice(index, 1)
      else if (visible) items.value.unshift(saved)
      return saved
    } catch (reason) {
      error.value = reason instanceof Error ? reason.message : String(reason)
      return null
    } finally {
      saving.value = false
    }
  }

  async function remove(id: string) {
    saving.value = true
    error.value = null
    try {
      await api.deleteMemory(id)
      items.value = items.value.filter((item) => item.id !== id)
      return true
    } catch (reason) {
      error.value = reason instanceof Error ? reason.message : String(reason)
      return false
    } finally {
      saving.value = false
    }
  }

  return {
    items,
    orderedItems,
    pinnedIds,
    query,
    loading,
    saving,
    error,
    load,
    save,
    remove,
    togglePinned,
  }
})
