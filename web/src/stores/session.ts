import { computed, onScopeDispose, ref } from 'vue'
import { defineStore } from 'pinia'
import {
  api,
  type AgentEvent,
  type Approval,
  type ChatMessage,
  type Conversation,
  type PermissionMode,
  type ResponseMode,
} from '@/api/client'
import { EventSocket } from '@/api/socket'
import { mapGatewayEvent } from '@/api/event-adapter'
import { useRunStore } from './run'
import { activityGroups, projectMessage } from './session-projection'
import { useWorkspaceStore } from './workspace'

export const useSessionStore = defineStore('session', () => {
  const workspace = useWorkspaceStore()
  const showArchived = ref(false)
  const sessions = ref<Conversation[]>([]),
    messages = ref<Record<string, ChatMessage[]>>({})
  const activeSessionId = ref<string | null>(null),
    isLoading = ref(false),
    error = ref<string | null>(null)
  const runningTaskIds = ref<Record<string, string[]>>({}),
    approvals = ref<Record<string, Approval[]>>({})
  const queuedMessages = ref<Record<string, string[]>>({})
  const queuedPaused = ref<Record<string, boolean>>({})
  const stoppingTaskIds = ref<string[]>([])
  const isStopping = computed(() =>
    (runningTaskIds.value[activeSessionId.value || ''] || []).some((id) =>
      stoppingTaskIds.value.includes(id),
    ),
  )
  const queuedAfterTask = new Map<string, string>(),
    draining = new Set<string>()
  const loadingSessions = new Map<string, Promise<void>>()
  const deletedSessions = new Set<string>()
  const bufferedEvents = new Map<string, Array<{ event: AgentEvent; replay: boolean }>>()
  const run = useRunStore(),
    streams = new Map<string, EventSocket>()
  const activeSession = computed(() =>
    sessions.value.find((item) => item.id === activeSessionId.value),
  )
  const visibleSessions = computed(() => sessions.value.filter((item) =>
    (item.folder_id || '') === workspace.selectedId && Boolean(item.archived) === showArchived.value,
  ))
  const activeMessages = computed(() =>
    activeSessionId.value ? messages.value[activeSessionId.value] || [] : [],
  )
  const activeApprovals = computed(() =>
    activeSessionId.value ? approvals.value[activeSessionId.value] || [] : [],
  )
  const isSending = computed(() =>
    Boolean(activeSessionId.value && runningTaskIds.value[activeSessionId.value]?.length),
  )
  const activeActivityGroups = computed(() =>
    activityGroups(run.turns[activeSessionId.value || ''] || []),
  )
  const activeActivities = computed(() =>
    activeActivityGroups.value.flatMap((group) => group.items),
  )
  const activities = computed(() =>
    Object.fromEntries(
      Object.entries(run.turns).map(([id, turns]) => [
        id,
        activityGroups(turns).flatMap((g) => g.items),
      ]),
    ),
  )
  const taskActivityStatuses = computed(() =>
    Object.fromEntries(
      Object.entries(run.turns).map(([id, turns]) => [
        id,
        Object.fromEntries(activityGroups(turns).map((g) => [g.task_id, g.status])),
      ]),
    ),
  )
  let generation = 0,
    frame = 0,
    lifecycle = 0
  const deltas: Array<{ id: string; event: AgentEvent; replay: boolean }> = []
  function flushDeltas() {
    if (frame) cancelAnimationFrame(frame)
    frame = 0
    for (const item of deltas.splice(0))
      projectMessage((messages.value[item.id] ||= []), item.event, item.replay)
  }
  function mark(id: string, task: string) {
    const list = (runningTaskIds.value[id] ||= [])
    if (task && !list.includes(task)) list.push(task)
  }
  function clear(id: string, task: string) {
    runningTaskIds.value[id] = (runningTaskIds.value[id] || []).filter((item) => item !== task)
  }
  function handleEvent(id: string, event: AgentEvent, replay = false) {
    if (deletedSessions.has(id)) return
    const buffer = bufferedEvents.get(id)
    if (buffer) {
      buffer.push({ event, replay })
      return
    }
    const task = event.task_id || ''
    if (event.type === 'task.started') {
      mark(id, task)
      run.markStarted(
        id,
        task,
        String(event.payload.input_text || '') || undefined,
        event.occurred_at,
      )
    }
    if (event.type === 'message.delta') {
      deltas.push({ id, event, replay })
      if (!frame) frame = requestAnimationFrame(flushDeltas)
    } else {
      flushDeltas()
      projectMessage((messages.value[id] ||= []), event, replay)
    }
    if (event.type === 'message.completed' && typeof event.payload.content === 'string')
      run.completeText(id, task, event.payload.content, String(event.payload.message_id || ''))
    for (const mapped of mapGatewayEvent(event)) run.apply(mapped)
    if (event.type === 'approval.requested') {
      const pending = (approvals.value[id] ||= [])
      const approval = {
        ...event.payload,
        id: String(event.payload.approval_id || event.payload.id || ''),
        conversation_id: id,
        task_id: task,
      } as unknown as Approval
      if (approval.id && !pending.some((a) => a.id === approval.id)) pending.push(approval)
      mark(id, task)
    }
    if (event.type === 'approval.decided')
      approvals.value[id] = (approvals.value[id] || []).filter(
        (a) => a.id !== String(event.payload.approval_id),
      )
    if (
      [
        'task.succeeded',
        'task.completed',
        'task.failed',
        'task.cancelled',
        'task.interrupted',
      ].includes(event.type)
    ) {
      clear(id, task)
      approvals.value[id] = (approvals.value[id] || []).filter((a) => a.task_id !== task)
      if (event.type === 'task.failed') error.value = String(event.payload.message || '执行失败')
      const succeeded = ['task.succeeded', 'task.completed'].includes(event.type)
      if (!succeeded && queuedAfterTask.get(id) === task) queuedPaused.value[id] = true
      if (!replay && succeeded) void sendNext(id, task)
    }
  }
  function watchSession(id: string) {
    if (streams.has(id) || deletedSessions.has(id)) return
    const stream = new EventSocket({
      connect: (receive) => api.connectEvents(id, receive),
      history: (after, signal) => api.listTaskEvents(id, after, signal),
      receive: (event, replay) => handleEvent(id, event, replay),
      connection: (online) => {
        run.setConnection(id, online)
        if (!online && queuedMessages.value[id]?.length) queuedPaused.value[id] = true
      },
    })
    streams.set(id, stream)
    stream.start()
  }
  async function loadSessions() {
    if (isLoading.value) return
    isLoading.value = true
    error.value = null
    try {
      await workspace.load()
      sessions.value = (await api.listConversations()).filter((item) => !deletedSessions.has(item.id))
      const current = activeSession.value
      if (current) { workspace.select(current.folder_id || ''); showArchived.value = Boolean(current.archived) }
    } catch (reason) {
      error.value =
        '无法连接应用服务：' + (reason instanceof Error ? reason.message : String(reason))
    } finally {
      isLoading.value = false
    }
  }
  async function createSession(title: string) {
    try {
      const item = await api.createConversation({ title, folder_id: workspace.selectedId })
      showArchived.value = false
      sessions.value.unshift(item)
      await switchSession(item.id)
      return item
    } catch (reason) {
      error.value = String(reason)
      throw reason
    }
  }
  async function switchSession(id: string, force = false) {
    if (!force && activeSessionId.value === id && messages.value[id] && streams.has(id)) return
    const current = ++generation
    activeSessionId.value = id
    error.value = null
    let conversation: Conversation
    try {
      conversation = await api.getConversation(id)
    } catch (reason) {
      if (current === generation) {
        activeSessionId.value = null
        error.value = '无法载入对话：' + (reason instanceof Error ? reason.message : String(reason))
      }
      return
    }
    if (current !== generation || deletedSessions.has(id)) return
    const index = sessions.value.findIndex((item) => item.id === id)
    if (index < 0) sessions.value.unshift(conversation)
    else sessions.value[index] = conversation
    workspace.select(conversation.folder_id || '')
    showArchived.value = Boolean(conversation.archived)
    let loading = loadingSessions.get(id)
    if (!loading) {
      const epoch = lifecycle
      // Buffer before subscribing/fetching. Snapshot installation must never
      // overwrite an event already consumed by EventSocket's dedupe set.
      const buffer: Array<{ event: AgentEvent; replay: boolean }> = []
      bufferedEvents.set(id, buffer)
      watchSession(id)
      loading = (async () => {
        try {
          const [loaded, pending, tasks] = await Promise.all([
            api.listMessages(id),
            api.listApprovals(id),
            api.listTasks(id),
          ])
          if (epoch !== lifecycle || deletedSessions.has(id)) return
          flushDeltas()
          const live = messages.value[id] || []
          messages.value[id] = [
            ...loaded,
            ...live.filter((m) => m.streaming && !loaded.some((item) => item.id === m.id)),
          ]
          approvals.value[id] = pending
          const sending = (runningTaskIds.value[id] || []).filter((task) =>
            task.startsWith('pending-'),
          )
          runningTaskIds.value[id] = [
            ...sending,
            ...tasks
              .filter((t) =>
                ['created', 'queued', 'running', 'waiting_approval', 'retry_wait'].includes(
                  t.status,
                ),
              )
              .map((t) => t.id),
          ]
          for (const task of tasks) run.hydrateTask(id, task)
        } finally {
          if (bufferedEvents.get(id) === buffer) bufferedEvents.delete(id)
          if (epoch === lifecycle && !deletedSessions.has(id))
            for (const item of buffer) handleEvent(id, item.event, item.replay)
        }
        if (epoch === lifecycle) await streams.get(id)?.recover()
      })().finally(() => {
        if (loadingSessions.get(id) === loading) loadingSessions.delete(id)
      })
      loadingSessions.set(id, loading)
    }
    try {
      await loading
    } catch (reason) {
      if (current === generation)
        error.value = '无法载入对话：' + (reason instanceof Error ? reason.message : String(reason))
    }
  }
  async function sendToSession(id: string, content: string) {
    if (sessions.value.find((item) => item.id === id)?.archived)
      throw new Error('请先恢复归档对话，再发送消息。')
    if (runningTaskIds.value[id]?.length) {
      if (!queuedMessages.value[id]?.length) {
        queuedAfterTask.set(id, runningTaskIds.value[id][0])
        queuedPaused.value[id] =
          runningTaskIds.value[id].length !== 1 || run.connected[id] === false
      }
      const queue = (queuedMessages.value[id] ||= [])
      queue.push(content)
      return
    }
    watchSession(id)
    const pending = 'pending-' + Date.now()
    mark(id, pending)
    error.value = null
    if (queuedMessages.value[id]?.length && !queuedPaused.value[id])
      queuedAfterTask.set(id, pending)
    const optimistic: ChatMessage = {
      id: 'local-' + Date.now(),
      conversation_id: id,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    }
    ;(messages.value[id] ||= []).push(optimistic)
    try {
      const result = await api.sendMessage(id, content)
      clear(id, pending)
      if (queuedAfterTask.get(id) === pending) queuedAfterTask.set(id, result.task_id)
      run.markStarted(id, result.task_id, content)
      const turn = run.getTurn(id, result.task_id)
      if (!['completed', 'failed', 'cancelled'].includes(turn.status)) mark(id, result.task_id)
      else if (turn.status === 'completed') void sendNext(id, result.task_id)
      else queuedPaused.value[id] = true
      const item = sessions.value.find((s) => s.id === id)
      if (item) {
        item.updated_at = new Date().toISOString()
        if (item.title === '新对话') item.title = content.slice(0, 28)
        sessions.value.sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at))
      }
    } catch (reason) {
      clear(id, pending)
      queuedPaused.value[id] = true
      messages.value[id] = messages.value[id].filter((m) => m.id !== optimistic.id)
      error.value = reason instanceof Error ? reason.message : String(reason)
      throw reason
    }
  }
  async function sendMessage(content: string) {
    if (activeSessionId.value) await sendToSession(activeSessionId.value, content)
  }
  async function sendNext(id: string, completedTask?: string, confirmed = false) {
    if (draining.has(id) || runningTaskIds.value[id]?.length || !queuedMessages.value[id]?.length)
      return
    if (
      !confirmed &&
      (queuedPaused.value[id] || !completedTask || queuedAfterTask.get(id) !== completedTask)
    )
      return
    draining.add(id)
    const epoch = lifecycle
    try {
      // HTTP 202 or an unrelated task's completion never authorizes a send.
      const tasks = await api.listTasks(id)
      if (epoch !== lifecycle) return
      if (
        tasks.some((t) =>
          ['created', 'queued', 'running', 'waiting_approval', 'retry_wait'].includes(t.status),
        )
      ) {
        queuedPaused.value[id] = true
        return
      }
      if (!confirmed && tasks.find((t) => t.id === completedTask)?.status !== 'succeeded') {
        queuedPaused.value[id] = true
        return
      }
      if (runningTaskIds.value[id]?.length || (!confirmed && queuedPaused.value[id])) return
      const next = queuedMessages.value[id]?.shift()
      if (!next) return
      queuedPaused.value[id] = false
      try {
        await sendToSession(id, next)
      } catch {
        const queue = (queuedMessages.value[id] ||= [])
        queue.unshift(next)
        queuedPaused.value[id] = true
      }
    } catch (reason) {
      queuedPaused.value[id] = true
      error.value = String(reason)
    } finally {
      draining.delete(id)
      const task = queuedAfterTask.get(id)
      // A very short run can finish before its POST response arrives.
      if (
        task &&
        !queuedPaused.value[id] &&
        run.turns[id]?.find((t) => t.id === task)?.status === 'completed' &&
        !runningTaskIds.value[id]?.length &&
        queuedMessages.value[id]?.length
      ) {
        // The next turn will rebind the queue; do not retry a stale completion.
        if (task !== completedTask) void sendNext(id, task)
      }
    }
  }
  async function resumeQueued(id: string) {
    await sendNext(id, undefined, true)
  }
  function removeQueued(id: string, index: number) {
    queuedMessages.value[id]?.splice(index, 1)
  }
  async function setPermissionMode(permissionMode: PermissionMode, id = activeSessionId.value) {
    if (!id) return
    const updated = await api.updateConversationPermission(id, permissionMode)
    const i = sessions.value.findIndex((s) => s.id === updated.id)
    if (i >= 0) sessions.value[i] = updated
  }
  async function setConversationRuntime(
    modelId: string,
    responseMode: ResponseMode,
    id = activeSessionId.value,
  ) {
    if (!id) return
    const updated = await api.updateConversationSettings(id, {
      model_id: modelId,
      response_mode: responseMode,
    })
    const i = sessions.value.findIndex((s) => s.id === updated.id)
    if (i >= 0) sessions.value[i] = updated
  }
  async function refreshEvents(id: string) {
    watchSession(id)
    await loadingSessions.get(id)
    await streams.get(id)?.recover()
  }
  async function decideApproval(approval: Approval, decision: 'allow' | 'deny') {
    await api.decideApproval(approval.id, decision, approval.version)
    await refreshEvents(approval.conversation_id)
  }
  async function cancelTask(task: string, conversationId: string) {
    queuedPaused.value[conversationId] = true
    if (stoppingTaskIds.value.includes(task)) return false
    stoppingTaskIds.value.push(task)
    try {
      await api.cancelTask(task)
      // HTTP acceptance is not a terminal task event.
      await refreshEvents(conversationId)
      return true
    } catch (reason) {
      error.value = '未能确认停止：' + (reason instanceof Error ? reason.message : String(reason))
      return false
    } finally {
      stoppingTaskIds.value = stoppingTaskIds.value.filter((id) => id !== task)
    }
  }
  async function cancelActiveTask() {
    const id = activeSessionId.value
    if (id) queuedPaused.value[id] = true
    const task = id ? runningTaskIds.value[id]?.find((t) => !t.startsWith('pending-')) : undefined
    if (id && task) await cancelTask(task, id)
    else if (id && runningTaskIds.value[id]?.length)
      error.value = '消息正在提交，任务建立后可停止。待发消息已暂停。'
  }
  function disconnect() {
    generation++
    lifecycle++
    bufferedEvents.clear()
    loadingSessions.clear()
    for (const id of Object.keys(queuedMessages.value)) queuedPaused.value[id] = true
    for (const stream of streams.values()) stream.stop()
    streams.clear()
    flushDeltas()
  }
  async function manageSession(id: string, patch: { title?: string; archived?: boolean; folder_id?: string }) {
    const item = await api.updateConversationSettings(id, patch)
    const index = sessions.value.findIndex((session) => session.id === id)
    if (index >= 0) sessions.value[index] = item
    if (activeSessionId.value === id) workspace.select(item.folder_id || '')
    return item
  }
  async function deleteSession(id: string) {
    await api.deleteConversation(id)
    // Late snapshots/events must not recreate a conversation after confirmed deletion.
    deletedSessions.add(id)
    loadingSessions.delete(id)
    streams.get(id)?.stop()
    streams.delete(id)
    bufferedEvents.delete(id)
    deltas.splice(0, deltas.length, ...deltas.filter((item) => item.id !== id))
    for (const map of [messages.value, approvals.value, runningTaskIds.value, queuedMessages.value, queuedPaused.value])
      delete map[id]
    queuedAfterTask.delete(id)
    sessions.value = sessions.value.filter((item) => item.id !== id)
    run.forgetSession(id)
    if (activeSessionId.value === id) activeSessionId.value = null
  }
  onScopeDispose(disconnect)
  return {
    sessions,
    visibleSessions,
    showArchived,
    messages,
    approvals,
    activities,
    taskActivityStatuses,
    runningTaskIds,
    queuedMessages,
    queuedPaused,
    activeSessionId,
    isLoading,
    isSending,
    isStopping,
    stoppingTaskIds,
    error,
    activeSession,
    activeMessages,
    activeApprovals,
    activeActivities,
    activeActivityGroups,
    loadSessions,
    createSession,
    manageSession,
    deleteSession,
    switchSession,
    watchSession,
    refreshEvents,
    sendMessage,
    sendToSession,
    setPermissionMode,
    setConversationRuntime,
    decideApproval,
    cancelActiveTask,
    cancelTask,
    removeQueued,
    resumeQueued,
    disconnect,
  }
})
