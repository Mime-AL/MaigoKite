import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { api, type WorkspaceFolder } from '@/api/client'

export const useWorkspaceStore = defineStore('workspace', () => {
  const folders = ref<WorkspaceFolder[]>([]),
    loading = ref(false),
    error = ref('')
  const storageKey =
    import.meta.env.VITE_MOCK === '1' ? 'maigokite_demo_workspace' : 'maigokite_workspace'
  const selectedId = ref('')
  try {
    selectedId.value = localStorage.getItem(storageKey) || ''
  } catch {
    /* Storage is optional. */
  }
  const current = computed(() => folders.value.find((folder) => folder.id === selectedId.value))
  let pending: Promise<void> | undefined
  function select(id: string) {
    selectedId.value = id
    try {
      localStorage.setItem(storageKey, id)
    } catch {
      /* Storage is optional. */
    }
  }
  function load(): Promise<void> {
    if (pending) return pending
    loading.value = true
    error.value = ''
    pending = (async () => {
      try {
        folders.value = await api.listWorkspaceFolders()
        if (!folders.value.some((folder) => folder.id === selectedId.value)) select('')
      } catch (reason) {
        error.value = reason instanceof Error ? reason.message : String(reason)
      } finally {
        loading.value = false
        pending = undefined
      }
    })()
    return pending
  }
  async function add(rootPath: string, name = '') {
    const folder = await api.createWorkspaceFolder(rootPath, name)
    if (!folders.value.some((item) => item.id === folder.id)) folders.value.push(folder)
    select(folder.id)
    return folder
  }
  return { folders, loading, error, selectedId, current, select, load, add }
})
