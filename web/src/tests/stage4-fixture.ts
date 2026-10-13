// Browser-local evidence only: never creates tasks or changes backend data.
import pinia from '@/stores'
import router from '@/router'
import { useSessionStore } from '@/stores/session'
import { useRunStore } from '@/stores/run'
import { useUIStore } from '@/stores/ui'
import { useSettingsStore } from '@/stores/settings'
import { useInboxStore } from '@/stores/inbox'
import { useWorkspaceStore } from '@/stores/workspace'
import type { Turn } from '@/api/events'
export async function install(scene: string, theme: 'light' | 'dark') {
  const session = useSessionStore(pinia), run = useRunStore(pinia), ui = useUIStore(pinia)
  const settings = useSettingsStore(pinia), workspace = useWorkspaceStore(pinia)
  useInboxStore(pinia).stop(); session.disconnect()
  settings.loaded = true; settings.profileLoaded = true; settings.profile.assistantName = 'sakiko'
  settings.modelProfiles = [{ id: 'local', name: '本地模型', model: 'Qwen 3.5', provider: 'openai_compatible', baseUrl: '', credentialConfigured: false, maxTokens: 4096, temperature: .7, timeoutSeconds: 60, isDefault: true }]
  settings.defaultModelId = 'local'
  session.switchSession = async id => { session.activeSessionId = id }
  session.loadSessions = async () => {}
  ui.setAppearance({ theme, accent: 'stone', greetingName: 'nanami', texture: true })
  ui.layout.sidebarWidth = 240; ui.layout.sidebarCollapsed = window.innerWidth < 720
  ui.drawerOpen = false; ui.commandOpen = false
  workspace.folders = scene.includes('no-workspace') ? [] : [{ id: '', name: 'MaigoKite', root_path: '/workspace/MaigoKite' }]
  workspace.selectedId = ''
  session.sessions = scene === 'records-empty' ? [] : [
    { id: 'notes', title: '整理旅行资料', workspace_id: 'personal', folder_id: '', message_count: 8, model_id: 'local', permission_mode: 'workspace', response_mode: 'balanced', created_at: '2026-10-10T05:00:00Z', updated_at: '2026-10-11T02:24:00Z' },
    { id: 'research', title: '比较下个月的旅行路线', workspace_id: 'personal', folder_id: '', message_count: 12, model_id: 'local', permission_mode: 'workspace', response_mode: 'balanced', created_at: '2026-10-09T05:00:00Z', updated_at: '2026-10-10T08:16:00Z' },
    { id: 'unloaded', title: '想买的书和待读清单', workspace_id: 'personal', folder_id: '', message_count: 2, model_id: 'local', permission_mode: 'workspace', response_mode: 'balanced', created_at: '2026-10-09T05:00:00Z', updated_at: '2026-10-09T08:16:00Z' },
  ]
  run.turns = {}; run.connected = {}; session.runningTaskIds = {}; session.activeSessionId = null
  if (scene === 'records') {
    const turn: Turn = { id: 't-notes', sessionId: 'notes', status: 'waiting', startedAt: Date.parse('2026-10-11T02:00:00Z'), text: '', thinking: '', steps: [], timeline: [], memories: [], changes: [], jobs: [], plan: [], awaits: [{ id: 'approval-note', sessionId: 'notes', turnId: 't-notes', mode: 'approval', title: '批准 file_write', detail: JSON.stringify({ path: '旅行/路线.md' }), version: 2 }] }
    run.turns = { notes: [turn], research: [{ ...turn, id: 't-research', sessionId: 'research', status: 'running', awaits: [], steps: [{ id: 'read', title: '读取目的地与预算资料', kind: 'read', tool: 'file_read', input: {}, output: '', status: 'running', durationMs: 0 }] }] }
    session.runningTaskIds = { notes: ['t-notes'], research: ['t-research'] }
    run.connected = { notes: true, research: true }
  }
  const path = scene.startsWith('records') ? '/overview' : scene.startsWith('memory') ? '/memory' : '/chat'
  await router.replace(path)
}
export async function navigate(path: string) { await router.replace(path) }
