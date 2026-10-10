import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api, type AgentEvent } from '@/api/client'
import { useSessionStore } from '@/stores/session'

describe('session store', () => {
  let onEvent: ((event: AgentEvent) => void) | undefined

  beforeEach(() => {
    vi.restoreAllMocks()
    setActivePinia(createPinia())
    vi.spyOn(api, 'listMessages').mockResolvedValue([])
    vi.spyOn(api, 'listApprovals').mockResolvedValue([])
    vi.spyOn(api, 'listTasks').mockResolvedValue([])
    vi.spyOn(api, 'listTaskEvents').mockResolvedValue([])
    vi.spyOn(api, 'connectEvents').mockImplementation((_id, callback) => {
      onEvent = callback
      return { close: vi.fn() } as unknown as WebSocket
    })
  })

  it('tracks a durable approval and submits its versioned decision', async () => {
    vi.spyOn(api, 'decideApproval').mockResolvedValue({ task_id: 'task-approval' })
    const store = useSessionStore()
    await store.switchSession('conv-1')
    onEvent?.({
      schema_version: 1,
      event_id: 'a1',
      sequence: 1,
      type: 'approval.requested',
      conversation_id: 'conv-1',
      task_id: 'task-approval',
      payload: {
        approval_id: 'approval-1',
        workspace_id: 'personal',
        conversation_id: 'conv-1',
        task_id: 'task-approval',
        tool_call_id: 'call-1',
        tool_name: 'file_write',
        arguments: { path: '/workspace/a.txt' },
        resource_scope: '/workspace/a.txt',
        risk_level: 'L4',
        status: 'pending',
        version: 1,
        expires_at: '2099-01-01T00:00:00Z',
      },
    })
    expect(store.activeApprovals).toHaveLength(1)
    await store.decideApproval(store.activeApprovals[0], 'allow')
    expect(api.decideApproval).toHaveBeenCalledWith('approval-1', 'allow', 1)
  })

  it('shows a task as waiting until its approval is allowed', async () => {
    const store = useSessionStore()
    await store.switchSession('conv-1')
    onEvent?.({
      schema_version: 1,
      event_id: 'wait-1',
      sequence: 1,
      type: 'task.waiting_approval',
      conversation_id: 'conv-1',
      task_id: 'task-waiting',
      payload: { tool_call_id: 'call-1', approval_id: 'approval-1' },
    })
    expect(store.activeActivityGroups[0].status).toBe('waiting_approval')

    onEvent?.({
      schema_version: 1,
      event_id: 'wait-2',
      sequence: 2,
      type: 'approval.decided',
      conversation_id: 'conv-1',
      task_id: 'task-waiting',
      payload: { approval_id: 'approval-1', decision: 'allow' },
    })
    expect(store.activeActivityGroups[0].status).toBe('running')
  })

  it('keeps structured recovery guidance on failed tool activity', async () => {
    const store = useSessionStore()
    await store.switchSession('conv-1')
    onEvent?.({
      schema_version: 1,
      event_id: 'tool-failed-1',
      sequence: 1,
      type: 'tool.failed',
      conversation_id: 'conv-1',
      task_id: 'task-search',
      payload: {
        tool_call_id: 'call-search',
        tool_name: 'web_search',
        message: 'Web search provider request failed.',
        code: 'SEARCH_PROVIDER_UNAVAILABLE',
        user_hint: '请检查网络，或配置其他搜索服务。',
        action: { label: '配置联网工具', to: '/settings?tab=tools' },
        data: { results: [], error: 'search provider request failed' },
      },
    })

    expect(store.activeActivityGroups[0].items[0]).toMatchObject({
      status: 'failed',
      hint: '请检查网络，或配置其他搜索服务。',
      action: { label: '配置联网工具', to: '/settings?tab=tools' },
      detail: { result: { results: [], error: 'search provider request failed' } },
    })
  })

  it('adds an optimistic message and completes a streamed reply', async () => {
    vi.spyOn(api, 'sendMessage').mockResolvedValue({ task_id: 'task-1', status: 'processing' })
    const store = useSessionStore()
    store.sessions.push({
      id: 'conv-1',
      workspace_id: 'personal',
      title: 't',
      model_id: '',
      permission_mode: 'read_only',
      response_mode: 'balanced',
      created_at: '',
      updated_at: '',
      message_count: 0,
    })
    await store.switchSession('conv-1')
    await store.sendMessage('hello')
    expect(store.activeMessages[0].content).toBe('hello')
    onEvent?.({
      schema_version: 1,
      event_id: '1',
      sequence: 1,
      type: 'message.delta',
      conversation_id: 'conv-1',
      task_id: 'task-1',
      payload: { content: 'world' },
    })
    onEvent?.({
      schema_version: 1,
      event_id: '2',
      sequence: 2,
      type: 'message.completed',
      conversation_id: 'conv-1',
      task_id: 'task-1',
      payload: {},
    })
    expect(store.activeMessages[1]).toMatchObject({
      role: 'assistant',
      content: 'world',
      streaming: false,
    })
    expect(store.isSending).toBe(false)
  })

  it('restores activity from durable events and cancels the active task', async () => {
    vi.mocked(api.listTasks).mockResolvedValueOnce([
      {
        id: 'task-running', workspace_id: 'personal', conversation_id: 'conv-1',
        title: 'task', status: 'running', input_text: 'work', last_error: '', version: 1,
        created_at: '', updated_at: '',
      },
    ])
    vi.mocked(api.listTaskEvents).mockResolvedValueOnce([
      {
        schema_version: 1, event_id: 'persisted-1', sequence: 1,
        type: 'tool.started', conversation_id: 'conv-1', task_id: 'task-running',
        payload: { tool_call_id: 'call-1', tool_name: 'browser' },
      },
    ])
    vi.spyOn(api, 'cancelTask').mockResolvedValue({
      id: 'task-running', workspace_id: 'personal', conversation_id: 'conv-1',
      title: 'task', status: 'cancelled', input_text: 'work', last_error: 'Cancelled by user',
      version: 2, created_at: '', updated_at: '',
    })
    const store = useSessionStore()
    await store.switchSession('conv-1')
    expect(store.isSending).toBe(true)
    expect(store.activeActivityGroups[0].items[0].title).toBe('browser')

    await store.cancelActiveTask()
    expect(api.cancelTask).toHaveBeenCalledWith('task-running')
    expect(store.isSending).toBe(false)
  })

  it('restores a completed message by its durable message id without duplication', async () => {
    vi.mocked(api.listMessages).mockResolvedValueOnce([
      {
        id: 'message-1', conversation_id: 'conv-1', role: 'assistant',
        content: '已完成', created_at: '2026-09-18T00:00:00Z',
      },
    ])
    vi.mocked(api.listTaskEvents).mockResolvedValueOnce([
      {
        schema_version: 1, event_id: 'completed-1', sequence: 3,
        type: 'message.completed', conversation_id: 'conv-1', task_id: 'task-1',
        occurred_at: '2026-09-18T00:00:00Z',
        payload: { message_id: 'message-1', content: '已完成' },
      },
    ])
    const store = useSessionStore()
    await store.switchSession('conv-1')
    expect(store.activeMessages).toHaveLength(1)
    expect(store.activeMessages[0]).toMatchObject({ id: 'message-1', content: '已完成' })
  })

  it('keeps reasoning, tools and subagents out of the assistant reply', async () => {
    const store = useSessionStore()
    await store.switchSession('conv-1')

    onEvent?.({
      schema_version: 1,
      event_id: '1',
      sequence: 1,
      type: 'task.started',
      conversation_id: 'conv-1',
      task_id: 'task-1',
      payload: {},
    })
    onEvent?.({
      schema_version: 1,
      event_id: '2',
      sequence: 2,
      type: 'reasoning.completed',
      conversation_id: 'conv-1',
      task_id: 'task-1',
      payload: { activity_id: 'reasoning-1', summary: '先检查项目文件。' },
    })
    onEvent?.({
      schema_version: 1,
      event_id: '3',
      sequence: 3,
      type: 'tool.proposed',
      conversation_id: 'conv-1',
      task_id: 'task-1',
      payload: { tool_call_id: 'call-1', tool_name: 'file_read', arguments: { path: 'README.md' } },
    })
    onEvent?.({
      schema_version: 1,
      event_id: '4',
      sequence: 4,
      type: 'tool.completed',
      conversation_id: 'conv-1',
      task_id: 'task-1',
      payload: { tool_call_id: 'call-1', tool_name: 'file_read', summary: '读取完成' },
    })
    onEvent?.({
      schema_version: 1,
      event_id: '5',
      sequence: 5,
      type: 'subagent.started',
      conversation_id: 'conv-1',
      task_id: 'task-1',
      payload: { subagent_id: 'reviewer', name: 'Reviewer', summary: '检查实现' },
    })
    onEvent?.({
      schema_version: 1,
      event_id: '6',
      sequence: 6,
      type: 'subagent.completed',
      conversation_id: 'conv-1',
      task_id: 'task-1',
      payload: { subagent_id: 'reviewer', name: 'Reviewer', summary: '检查完成' },
    })

    expect(store.activeMessages).toEqual([])
    expect(store.activeActivityGroups[0].items.map((item) => item.kind)).toEqual([
      'reasoning',
      'tool',
      'subagent',
    ])

    onEvent?.({
      schema_version: 1,
      event_id: '7',
      sequence: 7,
      type: 'message.delta',
      conversation_id: 'conv-1',
      task_id: 'task-1',
      payload: { content: '这是最终回答。' },
    })
    onEvent?.({
      schema_version: 1,
      event_id: '8',
      sequence: 8,
      type: 'message.completed',
      conversation_id: 'conv-1',
      task_id: 'task-1',
      payload: {},
    })

    expect(store.activeMessages).toHaveLength(1)
    expect(store.activeMessages[0].content).toBe('这是最终回答。')
    expect(store.activeMessages[0].content).not.toContain('先检查项目文件')
    expect(store.activeActivityGroups[0].status).toBe('completed')
  })

  it('persists the conversation model and response speed together', async () => {
    vi.spyOn(api, 'updateConversationSettings').mockResolvedValue({
      id: 'conv-1',
      workspace_id: 'personal',
      title: 't',
      model_id: 'model_fast',
      permission_mode: 'read_only',
      response_mode: 'fast',
      created_at: '',
      updated_at: '',
      message_count: 0,
    })
    const store = useSessionStore()
    store.sessions.push({
      id: 'conv-1',
      workspace_id: 'personal',
      title: 't',
      model_id: 'model_default',
      permission_mode: 'read_only',
      response_mode: 'balanced',
      created_at: '',
      updated_at: '',
      message_count: 0,
    })
    store.activeSessionId = 'conv-1'
    await store.setConversationRuntime('model_fast', 'fast')
    expect(api.updateConversationSettings).toHaveBeenCalledWith('conv-1', {
      model_id: 'model_fast',
      response_mode: 'fast',
    })
    expect(store.activeSession?.model_id).toBe('model_fast')
  })

  it('does not refetch or reconnect an already active session', async () => {
    const listMessages = vi.mocked(api.listMessages)
    const connectEvents = vi.mocked(api.connectEvents)
    const store = useSessionStore()

    await store.switchSession('conv-1')
    await store.switchSession('conv-1')

    expect(listMessages).toHaveBeenCalledTimes(1)
    expect(connectEvents).toHaveBeenCalledTimes(1)
  })
})
