import { computed, onScopeDispose, ref, watch, type Ref } from 'vue'
import { api, type WorkspaceFileEntry } from '@/api/client'
import { useSessionStore } from '@/stores/session'
import { useMemoryStore } from '@/stores/memory'
import { useWorkspaceStore } from '@/stores/workspace'
import type { Mention } from '@/components/inkwell/MentionMenu.vue'

export function useMentions(input: Ref<string>) {
  const session = useSessionStore(),
    memory = useMemoryStore(),
    workspace = useWorkspaceStore()
  const files = ref<WorkspaceFileEntry[]>([]),
    loading = ref(false)
  const query = computed(() => input.value.match(/(?:^|\s)@([^\s]*)$/)?.[1])
  const items = computed<Mention[]>(() => {
    const needle = (query.value || '').toLocaleLowerCase()
    return [
      ...files.value
        .filter((f) => f.type === 'file')
        .map((f) => ({
          id: `file-${f.path}`,
          kind: '文件' as const,
          label: f.path,
          value: `文件：${f.path}`,
        })),
      ...session.sessions.filter((s) => !s.archived && (s.folder_id || '') === workspace.selectedId).map((s) => ({
        id: s.id,
        kind: '会话' as const,
        label: s.title,
        value: `会话：${s.title}（${s.id}）`,
      })),
      ...memory.items.map((m) => ({
        id: m.id,
        kind: '记忆' as const,
        label: m.content,
        value: `记忆：${m.content}`,
      })),
    ]
      .filter((item) => item.label.toLocaleLowerCase().includes(needle))
      .slice(0, 30)
  })
  let timer: ReturnType<typeof setTimeout> | undefined,
    generation = 0
  watch([query, () => workspace.selectedId], ([value, folderId]) => {
    if (timer) clearTimeout(timer)
    const current = ++generation
    files.value = []
    if (value === undefined) {
      loading.value = false
      return
    }
    timer = setTimeout(async () => {
      loading.value = true
      try {
        const path = value.includes('/') ? value.slice(0, value.lastIndexOf('/')) : ''
        const entries = await api.listWorkspaceFiles(path, folderId)
        if (current === generation) files.value = entries
        if (!memory.items.length) void memory.load()
      } catch {
        if (current === generation) files.value = []
      } finally {
        if (current === generation) loading.value = false
      }
    }, 180)
  })
  function select(item: Mention) {
    input.value = input.value.replace(/@[^\s]*$/, `[${item.value}] `)
  }
  onScopeDispose(() => {
    generation++
    if (timer) clearTimeout(timer)
  })
  return { query, items, loading, select }
}
