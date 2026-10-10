import type { AgentEvent, AgentTask, Approval, ChatMessage, Conversation, UserMemory, WorkspaceFolder } from './client'
import { mockEnvelope, playTask } from './mock-playback'

const now = () => new Date().toISOString()
const folders: WorkspaceFolder[] = [{ id: '', name: '默认工作区', root_path: '/demo/workspace' }]
const conversations: Conversation[] = [
  {
    id: 'inkline-demo',
    workspace_id: 'personal',
    title: '把一个想法写成计划',
    model_id: 'demo',
    permission_mode: 'read_only',
    response_mode: 'balanced',
    created_at: now(),
    updated_at: now(),
    message_count: 0,
  },
]
const messages = new Map<string, ChatMessage[]>(),
  events = new Map<string, AgentEvent[]>()
const subscribers = new Map<string, Set<(event: AgentEvent) => void>>()
const tasks: AgentTask[] = [],
  approvals: Approval[] = [],
  memories: UserMemory[] = []
const resumes = new Map<string, () => void>(),
  timers = new Map<string, Set<ReturnType<typeof setTimeout>>>()
const model = {
  id: 'demo',
  name: '墨线演示',
  provider: 'openai_compatible',
  model: 'demo',
  base_url: 'http://localhost:1234/v1',
  temperature: 0.7,
  max_tokens: 4096,
  timeout_seconds: 60,
  credential_configured: false,
  is_default: true,
}
let assistantName = '小墨'
function emit(sessionId: string, taskId: string, type: string, payload: Record<string, unknown>) {
  const history = events.get(sessionId) || []
  const event = mockEnvelope(sessionId, taskId, history.length + 1, type, payload)
  history.push(event)
  events.set(sessionId, history)
  subscribers.get(sessionId)?.forEach((receive) => receive(event))
}
function stopTimers(taskId: string) {
  timers.get(taskId)?.forEach((timer) => clearTimeout(timer))
  timers.delete(taskId)
}
function start(sessionId: string, content: string) {
  const id = `demo-${Date.now()}`
  const task: AgentTask = {
    id,
    workspace_id: 'personal',
    conversation_id: sessionId,
    title: content.slice(0, 28),
    status: 'running',
    input_text: content,
    last_error: '',
    version: 1,
    created_at: now(),
    updated_at: now(),
  }
  tasks.push(task)
  const list = messages.get(sessionId) || []
  list.push({ id: `user-${id}`, conversation_id: sessionId, role: 'user', content, created_at: now() })
  messages.set(sessionId, list)
  emit(sessionId, id, 'task.started', { input_text: content })
  const wait = (delay: number, action: () => void) => {
    const set = timers.get(id) || new Set<ReturnType<typeof setTimeout>>()
    const timer = setTimeout(() => {
      set.delete(timer)
      if (task.status !== 'cancelled') action()
    }, delay)
    set.add(timer)
    timers.set(id, set)
  }
  playTask({
    wait,
    emit: (type, payload) => emit(sessionId, id, type, payload),
    approval: (resume) => {
      const approval: Approval = {
        id: `approval-${id}`,
        workspace_id: 'personal',
        conversation_id: sessionId,
        task_id: id,
        tool_call_id: 'write',
        tool_name: 'file_write',
        arguments: { path: 'notes/next-step.md' },
        resource_scope: 'notes/next-step.md',
        risk_level: 'L4',
        status: 'pending',
        version: 1,
        expires_at: '2099-01-01T00:00:00Z',
      }
      task.status = 'waiting_approval'
      approvals.push(approval)
      resumes.set(approval.id, resume)
      emit(sessionId, id, 'approval.requested', { ...approval, approval_id: approval.id })
    },
    remember: () => {
      const memory: UserMemory = {
        id: `memory-${id}`,
        workspace_id: 'personal',
        subject_user_id: 'local-user',
        category: 'preference',
        content: '喜欢把大目标拆成可以马上开始的小步骤。',
        source_type: 'agent',
        source_id: sessionId,
        confidence: 1,
        created_at: now(),
        updated_at: now(),
      }
      memories.push(memory)
      emit(sessionId, id, 'memory.added', { memory_id: memory.id, content: memory.content })
    },
    finish: (answer) => {
      list.push({
        id: `answer-${id}`,
        conversation_id: sessionId,
        role: 'assistant',
        content: answer,
        created_at: now(),
      })
      emit(sessionId, id, 'message.completed', { message_id: `answer-${id}`, content: answer })
      task.status = 'succeeded'
      task.updated_at = now()
      emit(sessionId, id, 'task.succeeded', {
        summary: {
          files: 1,
          added: 2,
          removed: 0,
          commands: 1,
          failed: 0,
          awaits: 1,
          contextPct: 18,
          durationMs: Date.now() - Date.parse(task.created_at),
        },
      })
    },
  })
  return { task_id: id }
}
export function mockConnect(id: string, receive: (event: AgentEvent) => void): WebSocket {
  const listeners = subscribers.get(id) || new Set<(event: AgentEvent) => void>()
  listeners.add(receive)
  subscribers.set(id, listeners)
  const socket = {
    readyState: 0,
    onopen: null as ((event: Event) => void) | null,
    onclose: null as ((event: Event) => void) | null,
    onerror: null,
    close() {
      socket.readyState = 3
      listeners.delete(receive)
      socket.onclose?.(new Event('close'))
    },
  }
  setTimeout(() => {
    if (socket.readyState !== 3) {
      socket.readyState = 1
      socket.onopen?.(new Event('open'))
    }
  }, 0)
  return socket as unknown as WebSocket
}
export async function mockRequest<T>(url: string, init?: RequestInit): Promise<T> {
  const parsed = new URL(url, 'http://mock.local'),
    parts = parsed.pathname.split('/'),
    id = decodeURIComponent(parts[parts.length - 1])
  const method = init?.method || 'GET',
    body = typeof init?.body === 'string' ? (JSON.parse(init.body) as Record<string, unknown>) : {}
  let result: unknown
  if (url === '/health') result = { status: 'ok', version: 'demo' }
  else if (parsed.pathname.endsWith('/preferences')) {
    if (method === 'PATCH') assistantName = String(body.assistant_name)
    result = { assistant_name: assistantName }
  } else if (parsed.pathname.endsWith('/runtime-status'))
    result = {
      workspace_id: 'personal',
      workspace_root: folders.find((folder) => folder.id === (parsed.searchParams.get('folder_id') || ''))?.root_path || '/demo/workspace',
      workspace_source: parsed.searchParams.get('folder_id') ? 'selection' : 'configuration',
      environment: 'demo',
      gateway: { status: 'serving' },
      agent_core: { status: 'serving' },
      restart: { pending: false, required_for: [], hot_applied: [], note: '' },
    }
  else if (parsed.pathname.endsWith('/folders')) {
    if (method === 'POST') {
      const root = String(body.root_path)
      const existing = folders.find((folder) => folder.root_path === root)
      const item = existing || { id: `folder-${Date.now()}`, root_path: root, name: String(body.name || root.split(/[\\/]/).filter(Boolean).pop() || '工作区') }
      if (!existing) folders.push(item)
      result = item
    } else result = { folders }
  }
  else if (parsed.pathname.endsWith('/permissions')) result = { default_mode: body.default_mode || 'workspace' }
  else if (parsed.pathname.includes('/models/actions/validate'))
    result = { ok: true, message: '演示连接', model: 'demo' }
  else if (parsed.pathname.includes('/models/actions/discover')) result = { models: [{ id: 'demo' }] }
  else if (parsed.pathname.endsWith('/models') || parsed.pathname.endsWith('/default'))
    result = { models: [model], default_model_id: 'demo' }
  else if (parsed.pathname.includes('/models/')) result = { ...model, ...body }
  else if (parsed.pathname.endsWith('/settings')) result = { models: { chat: model } }
  else if (parsed.pathname.includes('/credential-references')) result = { engines: [] }
  else if (parsed.pathname.endsWith('/tool-settings')) result = { tools: [] }
  else if (parsed.pathname.endsWith('/mcp-servers')) result = { servers: [] }
  else if (parsed.pathname.endsWith('/skills')) result = { skills: [] }
  else if (parsed.pathname.endsWith('/audit-events')) result = { events: [] }
  else if (parsed.pathname.endsWith('/data-summary'))
    result = {
      storage_backend: 'demo',
      conversation_count: conversations.length,
      message_count: [...messages.values()].flat().length,
      memory_count: memories.length,
      task_count: tasks.length,
      audit_event_count: 0,
    }
  else if (parsed.pathname.includes('/memories')) {
    if (method === 'GET')
      result = { memories: memories.filter((m) => m.content.includes(parsed.searchParams.get('q') || '')) }
    else if (method === 'DELETE') {
      const index = memories.findIndex((m) => m.id === id)
      if (index >= 0) memories.splice(index, 1)
    } else {
      const existing = memories.find((m) => m.id === id)
      const memory: UserMemory = {
        id: existing?.id || `memory-${Date.now()}`,
        workspace_id: 'personal',
        subject_user_id: 'local-user',
        category: String(body.category) as UserMemory['category'],
        content: String(body.content),
        source_type: existing?.source_type || 'user',
        source_id: existing?.source_id || '',
        confidence: Number(body.confidence),
        created_at: existing?.created_at || now(),
        updated_at: now(),
      }
      if (existing) Object.assign(existing, memory)
      else memories.push(memory)
      result = memory
    }
  } else if (parsed.pathname.endsWith('/approvals'))
    result = {
      approvals: approvals.filter(
        (a) =>
          a.status === 'pending' &&
          (!parsed.searchParams.has('conversation_id') ||
            a.conversation_id === parsed.searchParams.get('conversation_id')),
      ),
    }
  else if (parsed.pathname.endsWith('/decision')) {
    const approval = approvals.find((a) => a.id === parts[parts.length - 2])
    if (!approval || approval.status !== 'pending' || approval.version !== body.version)
      throw new Error('审批已处理或版本已变化。')
    approval.status = body.decision === 'allow' ? 'approved' : 'denied'
    const task = tasks.find((t) => t.id === approval.task_id)
    emit(approval.conversation_id, approval.task_id, 'approval.decided', {
      approval_id: approval.id,
      decision: body.decision,
    })
    if (task) task.status = body.decision === 'allow' ? 'running' : 'cancelled'
    if (body.decision === 'allow') resumes.get(approval.id)?.()
    else {
      stopTimers(approval.task_id)
      emit(approval.conversation_id, approval.task_id, 'task.cancelled', {})
    }
    resumes.delete(approval.id)
    result = { task_id: approval.task_id }
  } else if (parsed.pathname.endsWith('/cancel')) {
    const task = tasks.find((t) => t.id === parts[parts.length - 2])
    if (task) {
      task.status = 'cancelled'
      stopTimers(task.id)
      emit(task.conversation_id, task.id, 'task.cancelled', {})
      for (const a of approvals.filter((a) => a.task_id === task.id && a.status === 'pending')) {
        a.status = 'denied'
        emit(task.conversation_id, task.id, 'approval.decided', { approval_id: a.id, decision: 'deny' })
      }
    }
    result = task
  } else if (parsed.pathname.endsWith('/tasks'))
    result = {
      tasks: tasks.filter(
        (t) =>
          !parsed.searchParams.has('conversation_id') ||
          t.conversation_id === parsed.searchParams.get('conversation_id'),
      ),
    }
  else if (parsed.pathname.endsWith('/events/history'))
    result = {
      events: (events.get(parts[parts.length - 3]) || [])
        .filter((e) => e.sequence > Number(parsed.searchParams.get('after') || 0))
        .slice(0, 1000),
    }
  else if (parsed.pathname.endsWith('/messages')) {
    const sessionId = parts[parts.length - 2]
    if (method === 'POST' && conversations.find((item) => item.id === sessionId)?.archived)
      throw new Error('请先恢复归档对话，再发送消息。')
    result = method === 'POST' ? start(sessionId, String(body.content)) : { messages: messages.get(sessionId) || [] }
  } else if (parsed.pathname.endsWith('/conversations')) {
    if (method === 'POST') {
      const conversation: Conversation = {
        workspace_id: 'personal',
        model_id: 'demo',
        permission_mode: 'workspace',
        response_mode: 'balanced',
        id: `session-${Date.now()}`,
        folder_id: String(body.folder_id || ''),
        archived: false,
        title: String(body.title || '新对话'),
        created_at: now(),
        updated_at: now(),
        message_count: 0,
      }
      conversations.unshift(conversation)
      result = conversation
    } else result = { conversations }
  } else if (parsed.pathname.includes('/conversations/')) {
    const conversation = conversations.find((c) => c.id === id)
    if (!conversation) throw new Error('对话不存在。')
    if ((method === 'DELETE' || body.archived !== undefined || body.folder_id !== undefined) && tasks.some((task) => task.conversation_id === id && ['running', 'waiting_approval'].includes(task.status)))
      throw new Error('请先停止或完成此对话中的任务。')
    if (method === 'DELETE') {
      const owned = tasks.filter((task) => task.conversation_id === id)
      owned.forEach((task) => stopTimers(task.id))
      for (let index = tasks.length - 1; index >= 0; index--)
        if (tasks[index].conversation_id === id) tasks.splice(index, 1)
      for (let index = approvals.length - 1; index >= 0; index--)
        if (approvals[index].conversation_id === id) { resumes.delete(approvals[index].id); approvals.splice(index, 1) }
      conversations.splice(conversations.indexOf(conversation), 1)
      messages.delete(id)
      events.delete(id)
    } else {
      Object.assign(conversation, body, method === 'PATCH' ? { updated_at: now() } : {})
      result = conversation
    }
  } else if (parsed.pathname.endsWith('/files'))
    result = {
      entries: ['README.md', 'notes'].map((name) => ({
        name,
        path: name,
        type: name.includes('.') ? 'file' : 'directory',
        modified_at: now(),
      })),
    }
  else if (parsed.pathname.endsWith('/files/content'))
    result = {
      path: parsed.searchParams.get('path'),
      content: '# 个人手记\n把想法写下来，慢慢完成。',
      binary: false,
      truncated: false,
      size: 50,
      modified_at: now(),
    }
  else if (parsed.pathname.includes('/changes')) {
    const change = {
      path: 'notes/next-step.md',
      status: 'added',
      additions: 2,
      deletions: 0,
      diff: '+# 下一步\n+从一个小目标开始。',
      diff_truncated: false,
    }
    result = parsed.pathname.endsWith('/diff')
      ? change
      : { changes: tasks.some((t) => t.status === 'succeeded') ? [change] : [], git: true, truncated: false }
  } else throw new Error(`演示未提供此操作：${parsed.pathname}`)
  return structuredClone(result) as T
}
