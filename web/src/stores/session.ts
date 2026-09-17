import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import {
  api,
  type AgentActivityGroup,
  type AgentActivityItem,
  type AgentEvent,
  type Approval,
  type ChatMessage,
  type Conversation,
  type PermissionMode,
  type ResponseMode,
} from '@/api/client'

export const useSessionStore = defineStore('session', () => {
  const sessions = ref<Conversation[]>([])
  const messages = ref<Record<string, ChatMessage[]>>({})
  const activeSessionId = ref<string | null>(null)
  const isLoading = ref(false)
  const isSending = ref(false)
  const error = ref<string | null>(null)
  const approvals = ref<Record<string, Approval[]>>({})
  const activities = ref<Record<string, AgentActivityItem[]>>({})
  const taskActivityStatuses = ref<Record<string, Record<string, AgentActivityGroup['status']>>>({})
  let socket: WebSocket | null = null
  let switchGeneration = 0
  const activeSession = computed(() =>
    sessions.value.find((item) => item.id === activeSessionId.value),
  )
  const activeMessages = computed(() =>
    activeSessionId.value ? messages.value[activeSessionId.value] || [] : [],
  )

  function setTaskActivityStatus(
    conversationId: string,
    taskId: string,
    status: AgentActivityGroup['status'],
  ) {
    if (!taskId) return
    const statuses =
      taskActivityStatuses.value[conversationId] ||
      (taskActivityStatuses.value[conversationId] = {})
    statuses[taskId] = status
  }

  function upsertActivity(conversationId: string, value: AgentActivityItem) {
    const list = activities.value[conversationId] || (activities.value[conversationId] = [])
    const existing = list.find((item) => item.id === value.id)
    if (existing) Object.assign(existing, value)
    else list.push(value)
  }

  function activityTimestamp(event: AgentEvent): string {
    return event.occurred_at || new Date().toISOString()
  }

  function handleReasoningActivity(id: string, event: AgentEvent) {
    if (!['reasoning.started', 'reasoning.delta', 'reasoning.completed'].includes(event.type))
      return
    const activityId = String(
      event.payload.activity_id || `reasoning-${event.task_id || event.event_id}`,
    )
    const existing = (activities.value[id] || []).find((item) => item.id === activityId)
    const nextText = String(event.payload.summary || event.payload.content || '')
    const summary =
      event.type === 'reasoning.delta'
        ? `${existing?.summary || ''}${nextText}`
        : nextText || existing?.summary || ''
    upsertActivity(id, {
      id: activityId,
      task_id: event.task_id || '',
      kind: 'reasoning',
      status: event.type === 'reasoning.completed' ? 'completed' : 'running',
      title: String(event.payload.title || '过程说明'),
      summary,
      sequence: existing?.sequence ?? event.sequence,
      created_at: existing?.created_at || activityTimestamp(event),
    })
  }

  function handleToolActivity(id: string, event: AgentEvent) {
    if (!['tool.proposed', 'tool.started', 'tool.completed', 'tool.failed'].includes(event.type))
      return
    const toolCallId = String(event.payload.tool_call_id || '')
    if (!toolCallId) return
    const activityId = `tool-${toolCallId}`
    const existing = (activities.value[id] || []).find((item) => item.id === activityId)
    const previousDetail =
      existing?.detail && typeof existing.detail === 'object'
        ? (existing.detail as Record<string, unknown>)
        : {}
    const status: AgentActivityItem['status'] =
      event.type === 'tool.proposed'
        ? 'pending'
        : event.type === 'tool.started'
          ? 'running'
          : event.type === 'tool.completed'
            ? 'completed'
            : event.payload.denied
              ? 'denied'
              : 'failed'
    upsertActivity(id, {
      id: activityId,
      task_id: event.task_id || existing?.task_id || '',
      kind: 'tool',
      status,
      title: String(event.payload.tool_name || existing?.title || '工具调用'),
      summary: String(event.payload.summary || event.payload.message || existing?.summary || ''),
      detail: {
        ...previousDetail,
        ...(event.payload.arguments ? { arguments: event.payload.arguments } : {}),
        ...(event.payload.data !== undefined ? { result: event.payload.data } : {}),
      },
      sequence: existing?.sequence ?? event.sequence,
      created_at: existing?.created_at || activityTimestamp(event),
    })
  }

  function handleSubagentActivity(id: string, event: AgentEvent) {
    const subagentTypes = [
      'subagent.started',
      'subagent.progress',
      'subagent.completed',
      'subagent.failed',
      'sub_agent_spawn',
      'sub_agent_complete',
    ]
    if (!subagentTypes.includes(event.type)) return
    const subagentId = String(event.payload.subagent_id || event.payload.agent_id || event.event_id)
    const activityId = `subagent-${subagentId}`
    const existing = (activities.value[id] || []).find((item) => item.id === activityId)
    const delta = String(
      event.payload.summary || event.payload.content || event.payload.message || '',
    )
    const isProgress = event.type === 'subagent.progress'
    const failed = event.type === 'subagent.failed'
    const completed = event.type === 'subagent.completed' || event.type === 'sub_agent_complete'
    upsertActivity(id, {
      id: activityId,
      task_id: event.task_id || existing?.task_id || '',
      kind: 'subagent',
      status: failed ? 'failed' : completed ? 'completed' : 'running',
      title: `子 Agent · ${String(event.payload.name || event.payload.role || subagentId)}`,
      summary: isProgress ? `${existing?.summary || ''}${delta}` : delta || existing?.summary || '',
      detail: event.payload,
      sequence: existing?.sequence ?? event.sequence,
      created_at: existing?.created_at || activityTimestamp(event),
    })
  }

  async function loadSessions() {
    if (isLoading.value) return
    isLoading.value = true
    error.value = null
    try {
      sessions.value = await api.listConversations()
    } catch (reason) {
      error.value = `无法连接 Gateway：${reason instanceof Error ? reason.message : String(reason)}`
    } finally {
      isLoading.value = false
    }
  }
  async function createSession(title: string) {
    error.value = null
    try {
      const item = await api.createConversation({ title })
      sessions.value.unshift(item)
      await switchSession(item.id)
      return item
    } catch (reason) {
      error.value = `无法创建对话：${reason instanceof Error ? reason.message : String(reason)}`
      throw reason
    }
  }
  async function switchSession(id: string) {
    if (activeSessionId.value === id && messages.value[id] && socket) return
    const generation = ++switchGeneration
    activeSessionId.value = id
    error.value = null
    try {
      const [loaded, pendingApprovals] = await Promise.all([
        api.listMessages(id),
        api.listApprovals(id),
      ])
      if (generation !== switchGeneration) return
      messages.value[id] = loaded
      approvals.value[id] = pendingApprovals
      socket?.close()
      socket = api.connectEvents(id, (event) => handleEvent(id, event))
    } catch (reason) {
      if (generation !== switchGeneration) return
      messages.value[id] = []
      error.value = `无法载入对话：${reason instanceof Error ? reason.message : String(reason)}`
    }
  }
  function handleEvent(id: string, event: AgentEvent) {
    const list = messages.value[id] || (messages.value[id] = [])
    const content = String(event.payload?.content || '')
    const taskId = event.task_id || ''
    if (event.type === 'task.started') setTaskActivityStatus(id, taskId, 'running')
    if (event.type === 'task.succeeded') setTaskActivityStatus(id, taskId, 'completed')
    if (event.type === 'task.failed') setTaskActivityStatus(id, taskId, 'failed')
    if (event.type === 'task.cancelled') setTaskActivityStatus(id, taskId, 'cancelled')
    handleReasoningActivity(id, event)
    handleToolActivity(id, event)
    handleSubagentActivity(id, event)
    if (event.type === 'message.delta' && content) {
      const streamId = `stream-${taskId}`
      const streamed = list.find((item) => item.id === streamId)
      if (streamed) streamed.content += content
      else
        list.push({
          id: streamId,
          conversation_id: id,
          role: 'assistant',
          content,
          created_at: activityTimestamp(event),
          streaming: true,
        })
    }
    if (event.type === 'message.completed') {
      const streamId = `stream-${taskId}`
      const streamed = list.find((item) => item.id === streamId)
      if (streamed) streamed.streaming = false
      else if (content)
        list.push({
          id: streamId,
          conversation_id: id,
          role: 'assistant',
          content,
          created_at: activityTimestamp(event),
          streaming: false,
        })
      setTaskActivityStatus(id, taskId, 'completed')
      isSending.value = false
    }
    if (event.type === 'approval.requested') {
      const approvalId = String(event.payload.approval_id || event.payload.id || '')
      const value = { ...event.payload, id: approvalId } as unknown as Approval
      const pending = approvals.value[id] || (approvals.value[id] = [])
      if (approvalId && !pending.some((item) => item.id === approvalId)) pending.push(value)
      isSending.value = false
    }
    if (event.type === 'approval.decided') {
      const approvalId = String(event.payload.approval_id || '')
      approvals.value[id] = (approvals.value[id] || []).filter((item) => item.id !== approvalId)
      isSending.value = event.payload.decision === 'allow'
    }
    if (event.type === 'error' || event.type === 'task.failed') {
      error.value = event.payload?.message || 'Agent 执行失败'
      setTaskActivityStatus(id, taskId, 'failed')
      isSending.value = false
    }
  }
  async function sendMessage(content: string) {
    const id = activeSessionId.value
    if (!id || isSending.value) return
    isSending.value = true
    error.value = null
    const optimistic: ChatMessage = {
      id: `local-${Date.now()}`,
      conversation_id: id,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    }
    ;(messages.value[id] || (messages.value[id] = [])).push(optimistic)
    try {
      await api.sendMessage(id, content)
    } catch (reason) {
      error.value = reason instanceof Error ? reason.message : String(reason)
      isSending.value = false
    }
  }
  async function setPermissionMode(permissionMode: PermissionMode) {
    const id = activeSessionId.value
    if (!id) return
    try {
      const updated = await api.updateConversationPermission(id, permissionMode)
      const index = sessions.value.findIndex((item) => item.id === id)
      if (index >= 0) sessions.value[index] = updated
    } catch (reason) {
      error.value = reason instanceof Error ? reason.message : String(reason)
      throw reason
    }
  }
  async function setConversationRuntime(modelId: string, responseMode: ResponseMode) {
    const id = activeSessionId.value
    if (!id) return
    try {
      const updated = await api.updateConversationSettings(id, {
        model_id: modelId,
        response_mode: responseMode,
      })
      const index = sessions.value.findIndex((item) => item.id === id)
      if (index >= 0) sessions.value[index] = updated
    } catch (reason) {
      error.value = reason instanceof Error ? reason.message : String(reason)
      throw reason
    }
  }
  async function decideApproval(approval: Approval, decision: 'allow' | 'deny') {
    error.value = null
    try {
      if (decision === 'allow') isSending.value = true
      await api.decideApproval(approval.id, decision, approval.version)
    } catch (reason) {
      isSending.value = false
      error.value = reason instanceof Error ? reason.message : String(reason)
      throw reason
    }
  }
  function disconnect() {
    switchGeneration++
    socket?.close()
    socket = null
  }
  const activeApprovals = computed(() =>
    activeSessionId.value ? approvals.value[activeSessionId.value] || [] : [],
  )
  const activeActivities = computed(() =>
    activeSessionId.value ? activities.value[activeSessionId.value] || [] : [],
  )
  const activeActivityGroups = computed<AgentActivityGroup[]>(() => {
    const conversationId = activeSessionId.value
    if (!conversationId) return []
    const grouped = new Map<string, AgentActivityItem[]>()
    for (const item of activities.value[conversationId] || []) {
      const list = grouped.get(item.task_id) || []
      list.push(item)
      grouped.set(item.task_id, list)
    }
    const statuses = taskActivityStatuses.value[conversationId] || {}
    const taskIds = new Set([...Object.keys(statuses), ...grouped.keys()])
    return [...taskIds]
      .map((task_id) => ({
        task_id,
        status: statuses[task_id] || 'running',
        items: (grouped.get(task_id) || []).slice().sort((a, b) => a.sequence - b.sequence),
      }))
      .filter((group) => group.status === 'running' || group.items.length > 0)
  })
  return {
    sessions,
    messages,
    approvals,
    activities,
    taskActivityStatuses,
    activeSessionId,
    isLoading,
    isSending,
    error,
    activeSession,
    activeMessages,
    activeApprovals,
    activeActivities,
    activeActivityGroups,
    loadSessions,
    createSession,
    switchSession,
    sendMessage,
    setPermissionMode,
    setConversationRuntime,
    decideApproval,
    disconnect,
  }
})
