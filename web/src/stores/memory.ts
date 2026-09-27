import { defineStore } from 'pinia'
import { ref } from 'vue'
import { api, type MemoryInput, type UserMemory } from '@/api/client'

export const useMemoryStore = defineStore('memory', () => {
  const items = ref<UserMemory[]>([])
  const query = ref('')
  const loading = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)

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
      const index = items.value.findIndex(item => item.id === saved.id)
      const visible = !query.value || saved.content.toLocaleLowerCase().includes(query.value.toLocaleLowerCase())
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
      items.value = items.value.filter(item => item.id !== id)
      return true
    } catch (reason) {
      error.value = reason instanceof Error ? reason.message : String(reason)
      return false
    } finally {
      saving.value = false
    }
  }

  return { items, query, loading, saving, error, load, save, remove }
})
