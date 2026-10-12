import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { api, type MemoryInput, type UserMemory } from '@/api/client'

export const useMemoryStore = defineStore('memory', () => {
  const items = ref<UserMemory[]>([])
  const query = ref('')
  const loading = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)
  const folderId = ref<string | null>(null)
  const enabled = ref(false)
  const settingsReady = ref(false)
  const settingsError = ref<string | null>(null)
  const savingSettings = ref(false)
  let loadVersion = 0
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

  async function load(search = query.value, folder = folderId.value) {
    const version = ++loadVersion
    if (folderId.value !== folder) items.value = []
    folderId.value = folder
    enabled.value = false
    settingsReady.value = false
    settingsError.value = null
    query.value = search.trim()
    loading.value = true
    error.value = null
    try {
      const [rows, config] = await Promise.all([
        api.listMemories(query.value, folder),
        folder === null ? null : api.getMemorySettings(folder),
      ])
      if (version !== loadVersion) return
      items.value = rows
      enabled.value = config?.enabled === true
      settingsReady.value = folder !== null
    } catch (reason) {
      if (version === loadVersion) error.value = reason instanceof Error ? reason.message : String(reason)
    } finally {
      if (version === loadVersion) loading.value = false
    }
  }

  async function setEnabled(value: boolean) {
    const folder = folderId.value
    if (folder === null || !settingsReady.value || savingSettings.value) return
    savingSettings.value = true
    settingsError.value = null
    try {
      const result = await api.setMemorySettings(folder, value)
      if (folder === folderId.value) {
        enabled.value = result.enabled
        await load(query.value, folder)
      }
    } catch (reason) {
      if (folder === folderId.value) {
        settingsError.value = reason instanceof Error ? reason.message : String(reason)
        // A lost response is not proof that the write failed. Re-read, never
        // retry the mutation automatically or show an optimistic permission.
        settingsReady.value = false
        try {
          const actual = await api.getMemorySettings(folder)
          if (folder === folderId.value) {
            enabled.value = actual.enabled
            settingsReady.value = true
          }
        } catch { /* The control remains unavailable until a successful reload. */ }
      }
    } finally {
      savingSettings.value = false
    }
  }

  async function save(input: MemoryInput & { id?: string }) {
    if (saving.value) return null
    const folder = folderId.value
    saving.value = true
    error.value = null
    try {
      const saved = await api.saveMemory({ ...input, folder_id: folder ?? undefined })
      if (folder !== folderId.value) return saved
      ++loadVersion
      loading.value = false
      const index = items.value.findIndex((item) => item.id === saved.id)
      const visible =
        !query.value || saved.content.toLocaleLowerCase().includes(query.value.toLocaleLowerCase())
      if (index >= 0 && visible) items.value[index] = saved
      else if (index >= 0) items.value.splice(index, 1)
      else if (visible) items.value.unshift(saved)
      await load(query.value, folder)
      return saved
    } catch (reason) {
      error.value = reason instanceof Error ? reason.message : String(reason)
      return null
    } finally {
      saving.value = false
    }
  }

  async function remove(id: string) {
    if (saving.value) return false
    const folder = folderId.value
    saving.value = true
    error.value = null
    try {
      await api.deleteMemory(id)
      if (folder !== folderId.value) return true
      ++loadVersion
      loading.value = false
      items.value = items.value.filter((item) => item.id !== id)
      await load(query.value, folder)
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
    folderId,
    enabled,
    settingsReady,
    settingsError,
    savingSettings,
    setEnabled,
    load,
    save,
    remove,
    togglePinned,
  }
})
