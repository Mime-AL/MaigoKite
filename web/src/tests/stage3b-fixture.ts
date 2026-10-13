// Local visual fixture only. Never sends a task or modifies backend data.
import pinia from '@/stores'
import router from '@/router'
import { useRunStore } from '@/stores/run'
import { useSessionStore } from '@/stores/session'
import { useSettingsStore } from '@/stores/settings'
import { useUIStore } from '@/stores/ui'
import { useInboxStore } from '@/stores/inbox'
import type { Turn } from '@/api/events'

export async function install(scene = 'process', theme = 'light') {
  const session = useSessionStore(pinia), run = useRunStore(pinia)
  const settings = useSettingsStore(pinia), ui = useUIStore(pinia)
  useInboxStore(pinia).stop()
  session.disconnect()
  session.switchSession = async id => { session.activeSessionId = id }
  session.loadSessions = async () => {}
  settings.loaded = true
  settings.modelProfiles = [{ id: 'visual-model', name: '本地模型', model: 'Qwen 3.5', provider: 'openai_compatible', baseUrl: 'http://localhost:1234/v1', credentialConfigured: false, temperature: 0.7, maxTokens: 4096, timeoutSeconds: 60, isDefault: true }]
  settings.defaultModelId = 'visual-model'
  session.sessions = [{ id: 'visual', workspace_id: 'personal', message_count: 0, title: '整理工作区笔记', folder_id: '', archived: false, model_id: 'visual-model', response_mode: 'balanced', permission_mode: 'workspace', created_at: '2026-10-11T08:00:00Z', updated_at: '2026-10-11T08:01:00Z' }]
  const turn: Turn = {
    id: 'visual-task', sessionId: 'visual', status: 'completed', startedAt: Date.parse('2026-10-11T08:00:00Z'),
    userText: '检查工作区，把配置说明整理成一份可直接使用的笔记。',
    thinking: '先核对配置与使用方式，再确认改动范围。', thinkingStatus: 'completed',
    text: '## 配置笔记已整理\n\n启动方式、模型接入与工作区路径已经核对。原来的配置值没有改变。\n\n> 笔记只保留实际可用的选项。\n\n- 模型服务：本地 OpenAI-compatible\n- 工作区：保留当前路径\n- 变更：`notes/config.md`\n\n| 项目 | 结果 |\n| --- | --- |\n| 启动入口 | 已核对 |\n| 配置路径 | 无变化 |\n\n```ts\nconst workspace = {\n  name: "Personal",\n  model: "Qwen 3.5",\n  approval: "workspace",\n}\n```',
    steps: [], awaits: [], memories: [], timeline: [], changes: [], plan: [], jobs: [], inputs: [],
    summary: { files: 1, added: 12, removed: 2, commands: 1, failed: 0, awaits: 1, contextPct: null, durationMs: 12400 },
  }
  for (let index = 0; index < 3; index++) {
    const id = `read-${index}`
    turn.steps.push({ id, tool: 'file_read', kind: 'read', title: ['README.md', 'config.yaml', 'docs/usage.md'][index], input: { path: ['README.md', 'config.yaml', 'docs/usage.md'][index] }, output: 'workspace: personal\nmodel: local\napproval: workspace', status: 'completed', durationMs: 84 })
    turn.timeline.push({ id, kind: 'step', seq: index + 1, time: `2026-10-11T08:00:0${index}Z` })
  }
  turn.steps.push({ id: 'command', tool: 'shell', kind: 'act', title: '核对文件清单', input: { command: 'ls notes' }, output: Array.from({ length: 38 }, (_, n) => `notes/entry-${String(n + 1).padStart(2, '0')}.md`).join('\n'), status: 'completed', durationMs: 410, exitCode: 0 })
  turn.timeline.push({ id: 'command', kind: 'step', seq: 4 })
  turn.inputs = [{ id: 'input', task_id: turn.id, content: '保留原配置，只整理说明。', status: 'consumed', created_at: '2026-10-11T08:00:04Z', seq: 5 }]
  turn.steps.push({ id: 'write', tool: 'file_write', kind: 'act', title: '写入 notes/config.md', input: { path: 'notes/config.md', content: '# 配置笔记' }, output: 'notes/config.md written', status: 'completed', durationMs: 90 })
  turn.timeline.push({ id: 'write', kind: 'step', seq: 6 })
  turn.awaits.push({ id: 'approval', sessionId: 'visual', turnId: turn.id, mode: 'approval', title: '批准 file_write', detail: JSON.stringify({ path: 'notes/config.md', content: '# 配置笔记' }), version: 1, toolCallId: 'write', verdict: 'allow', seq: 7 })
  turn.timeline.push({ id: 'approval', kind: 'await', seq: 7 })
  turn.changes = [{ path: 'notes/config.md', diff: '--- a/notes/config.md\n+++ b/notes/config.md\n@@ -1,2 +1,3 @@\n # 配置\n-旧说明\n+工作区：Personal\n+模型：Qwen 3.5' }]
  if (scene === 'pure') {
    turn.steps = []; turn.awaits = []; turn.timeline = []; turn.inputs = []; turn.changes = []
    turn.userText = '晚上好。'; turn.text = '晚上好。今天想聊什么？'; turn.thinking = ''
    turn.summary = { ...turn.summary!, files: 0, added: 0, removed: 0, commands: 0, awaits: 0, durationMs: 1400 }
  }
  if (scene === 'failure') {
    turn.status = 'failed'; turn.steps[3].status = 'failed'; turn.steps[3].exitCode = 1
    turn.steps[3].output = 'Permission denied: notes/private.md'; turn.summary!.failed = 1
    turn.inputs![0].status = 'not_consumed'
  }
  if (scene === 'long') {
    turn.steps[3].output = Array.from({ length: 360 }, (_, n) => `note ${n + 1}: completed`).join('\n')
    for (let n = 0; n < 24; n++) {
      const id = `action-${n}`
      turn.steps.push({ id, tool: 'shell', kind: 'act', title: `核对记录 ${n + 1}`, input: { command: 'read note' }, output: `note ${n + 1}: OK`, status: 'completed', durationMs: 42, exitCode: 0 })
      turn.timeline.push({ id, kind: 'step', seq: 20 + n })
    }
  }
  if (scene === 'menus') settings.modelProfiles = [0, 1, 2].map(n => ({ ...settings.modelProfiles[0], id: n ? `visual-${n}` : 'visual-model', model: ['Qwen 3.5', 'Gemma 4', 'DeepSeek'][n], isDefault: n === 0 }))
  if (scene === 'running' || scene === 'queued' || scene === 'waiting') {
    turn.status = scene === 'waiting' ? 'waiting' : 'running'; turn.summary = undefined
    turn.text = ''; turn.thinkingStatus = 'completed'; turn.steps[4].status = 'running'
    session.runningTaskIds = { visual: [turn.id] }
    if (scene === 'waiting') { turn.awaits[0].verdict = undefined; turn.steps[4].status = 'pending' }
    if (scene === 'queued') session.queuedMessages = { visual: [{ id: 'queue', content: '下一条：整理安装说明。' }] }
    turn.inputs![0].status = scene === 'waiting' ? 'consumed' : 'queued'
  } else { session.runningTaskIds = {}; session.queuedMessages = {} }
  run.turns = { visual: [turn] }; run.connected = { visual: true }
  session.messages = { visual: [] }; session.activeSessionId = 'visual'
  ui.drawerOpen = false
  document.documentElement.dataset.theme = theme
  await router.replace('/chat/visual')
  return turn
}
