import { t } from '@/i18n'
import { computed, onScopeDispose, ref } from 'vue'
import { defineStore } from 'pinia'
import {
  api,
  type AgentEvent,
  type AgentTask,
  type Approval,
  type ChatMessage,
  type Conversation,
  type MessageReceipt,
  type PermissionMode,
  type ResponseMode,
} from '@/api/client'
import { GatewayError } from '@/api/http'
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
  const tasks = ref<Record<string, AgentTask[]>>({})
  const capabilities = ref<Record<string, boolean>>({})
  const historyTruncated = ref<Record<string, boolean>>({})
  const resumingTaskIds = ref<string[]>([])
  // One key per logical submission, retained after an ambiguous transport error.
  // This is client request bookkeeping, not execution state or an automatic retry queue.
  const submissions = ref<Record<string, { key: string; content: string; uncertain: boolean }>>({})
  const snapshotFacts = new Map<string, {
    sequence: number; tasks: Map<string, AgentTask>; pendingIds?: Set<string>
  }>()
  const taskSequences = new Map<string, number>()
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
    const snapshot = snapshotFacts.get(id)
    const covered = Boolean(snapshot && event.sequence <= snapshot.sequence)
    const stateKey = `${id}:${task}`
    const stateEvent = ['task.', 'approval.', 'question.'].some((prefix) => event.type.startsWith(prefix))
    const staleState = stateEvent && event.sequence <= (taskSequences.get(stateKey) || 0)
    if (stateEvent && !staleState) taskSequences.set(stateKey, event.sequence)
    if (event.type === 'task.started') {
      if (!covered && !staleState) mark(id, task)
      run.markStarted(
        id,
        task,
        String(event.payload.input_text || '') || undefined,
        event.occurred_at,
      )
    }
    if (!covered && !staleState && event.type === 'task.resumed') mark(id, task)
    if (!covered && event.type === 'message.delta') {
      deltas.push({ id, event, replay })
      if (!frame) frame = requestAnimationFrame(flushDeltas)
    } else {
      flushDeltas()
      if (!covered) projectMessage((messages.value[id] ||= []), event, replay)
    }
    if (event.type === 'message.completed' && typeof event.payload.content === 'string')
      run.completeText(id, task, event.payload.content, String(event.payload.message_id || ''))
    for (const mapped of mapGatewayEvent(event)) run.apply(mapped)
    // Rebuild historical activity, but never let replay regress atomic product facts.
    if (covered) {
      const fact = snapshot?.tasks.get(task)
      if (fact && event.type !== 'message.delta' && event.type !== 'reasoning.delta')
        run.hydrateTask(id, fact, snapshot?.pendingIds, snapshot?.sequence)
      return
    }
    if (staleState) return
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
    if (['question.requested', 'question.answered'].includes(event.type)) mark(id, task)
    if (
      [
        'task.succeeded',
        'task.completed',
        'task.failed',
        'task.cancelled',
        'task.interrupted',
        'task.timed_out',
      ].includes(event.type)
    ) {
      clear(id, task)
      approvals.value[id] = (approvals.value[id] || []).filter((a) => a.task_id !== task)
      if (event.type === 'task.failed') error.value = String(event.payload.message || t("执行失败"))
      const succeeded = ['task.succeeded', 'task.completed'].includes(event.type)
      if (!succeeded && queuedAfterTask.get(id) === task) queuedPaused.value[id] = true
      if (!replay && succeeded) void sendNext(id, task)
      const epoch = lifecycle
      if (!replay) void (async () => {
        await loadingSessions.get(id)
        if (epoch === lifecycle && !deletedSessions.has(id)) await refreshSnapshot(id)
      })().catch(() => {
        error.value = t("任务状态更新失败，请重新打开对话。")
      })
    }
  }
  function watchSession(id: string) {
    if (streams.has(id) || deletedSessions.has(id)) return
    let connectedOnce = false
    const stream = new EventSocket({
      connect: (receive) => api.connectEvents(id, receive),
      history: (after, signal) => api.listTaskEvents(id, after, signal),
      receive: (event, replay) => handleEvent(id, event, replay),
      connection: (online) => {
        const reconnected = online && connectedOnce && run.connected[id] === false
        if (online) connectedOnce = true
        run.setConnection(id, online)
        if (!online && queuedMessages.value[id]?.length) queuedPaused.value[id] = true
        if (reconnected) void refreshSnapshot(id).catch(() => {
          error.value = t("已重新连接，但未能刷新会话状态。请重新打开对话。")
        })
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
        t("无法连接应用服务：") + (reason instanceof Error ? reason.message : String(reason))
    } finally {
      isLoading.value = false
    }
  }
  async function createSession(title: string, folderId = workspace.selectedId) {
    try {
      const item = await api.createConversation({ title, folder_id: folderId })
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
        error.value = t("无法载入对话：") + (reason instanceof Error ? reason.message : String(reason))
      }
      return
    }
    if (current !== generation || deletedSessions.has(id)) return
    const index = sessions.value.findIndex((item) => item.id === id)
    if (index < 0) sessions.value.unshift(conversation)
    else sessions.value[index] = conversation
    workspace.select(conversation.folder_id || '')
    showArchived.value = Boolean(conversation.archived)
    try {
      await refreshSnapshot(id)
    } catch (reason) {
      if (current === generation)
        error.value = t("无法载入对话：") + (reason instanceof Error ? reason.message : String(reason))
    }
  }
  function refreshSnapshot(id: string): Promise<void> {
    if (deletedSessions.has(id)) return Promise.resolve()
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
          const [snapshot, available] = await Promise.all([
            api.getConversationSnapshot(id),
            api.getCapabilities().catch(() => ({})),
          ])
          if (epoch !== lifecycle || deletedSessions.has(id)) return
          flushDeltas()
          // Text still streaming is projected in run.turns from event history.
          // Do not carry stale stream/local messages over persisted messages.
          messages.value[id] = snapshot.messages
          approvals.value[id] = snapshot.approvals
          if (snapshot.truncated) {
            const known = new Map((tasks.value[id] || []).map((task) => [task.id, task]))
            for (const task of snapshot.tasks) known.set(task.id, task)
            tasks.value[id] = [...known.values()].sort((a, b) => Date.parse(a.created_at) - Date.parse(b.created_at))
          } else tasks.value[id] = snapshot.tasks
          capabilities.value = available
          historyTruncated.value[id] = snapshot.truncated
          const pendingIds = snapshot.truncated ? undefined : new Set([
            ...snapshot.approvals.map((item) => item.id),
            ...snapshot.questions.map((item) => item.id),
          ])
          snapshotFacts.set(id, {
            sequence: snapshot.last_sequence,
            tasks: new Map(snapshot.tasks.map((task) => [task.id, task])), pendingIds,
          })
          const includedTasks = new Set(snapshot.tasks.map((task) => task.id))
          const sending = (runningTaskIds.value[id] || []).filter((task) =>
            task.startsWith('pending-') || (snapshot.truncated && !includedTasks.has(task)),
          )
          runningTaskIds.value[id] = [
            ...sending,
            ...snapshot.tasks
              .filter((t) =>
                ['created', 'queued', 'running', 'waiting_approval', 'retry_wait'].includes(
                  t.status,
                ),
              )
              .map((t) => t.id),
          ]
          for (const task of snapshot.tasks) run.hydrateTask(id, task, pendingIds, snapshot.last_sequence)
          run.hydratePending(id, snapshot)
          for (const task of snapshot.tasks)
            taskSequences.set(`${id}:${task.id}`, snapshot.last_sequence)
        } finally {
          if (bufferedEvents.get(id) === buffer) bufferedEvents.delete(id)
          if (epoch === lifecycle && !deletedSessions.has(id))
            for (const item of buffer.sort((a, b) => a.event.sequence - b.event.sequence))
              handleEvent(id, item.event, item.replay)
        }
        if (epoch === lifecycle) await streams.get(id)?.recover()
      })().finally(() => {
        if (loadingSessions.get(id) === loading) loadingSessions.delete(id)
      })
      loadingSessions.set(id, loading)
    }
    return loading
  }
  async function sendToSession(id: string, content: string) {
    const previous = submissions.value[id]
    if (!previous && sessions.value.find((item) => item.id === id)?.archived)
      throw new Error(t("对话已归档，恢复后可发送消息。"))
    if (previous && !previous.uncertain) throw new Error(t("消息正在提交，请稍候。"))
    if (previous && previous.content !== content)
      throw new Error(t("上一条消息提交结果未知，请点击“确认提交结果”。"))
    if (!previous && runningTaskIds.value[id]?.length) {
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
    // getRandomValues also works on a private-network HTTP origin (unlike randomUUID).
    const submission = previous || {
      key: Array.from(crypto.getRandomValues(new Uint8Array(16)), (b) => b.toString(16).padStart(2, '0')).join(''),
      content, uncertain: false,
    }
    submission.uncertain = false
    submissions.value[id] = submission
    const epoch = lifecycle
    const pending = 'pending-' + submission.key
    mark(id, pending)
    error.value = null
    if (queuedMessages.value[id]?.length && !queuedPaused.value[id])
      queuedAfterTask.set(id, pending)
    const optimistic: ChatMessage = {
      id: 'local-' + submission.key,
      conversation_id: id,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    }
    ;(messages.value[id] ||= []).push(optimistic)
    let result: MessageReceipt
    try {
      result = await api.sendMessage(id, content, submission.key)
    } catch (reason) {
      if (epoch !== lifecycle || deletedSessions.has(id)) throw reason
      clear(id, pending)
      queuedPaused.value[id] = true
      messages.value[id] = (messages.value[id] || []).filter((m) => m.id !== optimistic.id)
      const refused = reason instanceof GatewayError && reason.status >= 400 && reason.status < 500
      if (refused) delete submissions.value[id]
      else submissions.value[id].uncertain = true
      error.value = (reason instanceof Error ? reason.message : String(reason)) +
        (refused ? '' : t(" 提交结果未知，请点击“确认提交结果”。"))
      throw reason
    }
    // Once acknowledged, a later snapshot failure is NOT a failed submission.
    delete submissions.value[id]
    if (epoch !== lifecycle || deletedSessions.has(id)) return
    clear(id, pending)
    if (queuedAfterTask.get(id) === pending) queuedAfterTask.set(id, result.task_id)
    run.markStarted(id, result.task_id, content)
    const turn = run.getTurn(id, result.task_id)
    if (!['completed', 'failed', 'cancelled'].includes(turn.status) &&
      !['succeeded', 'failed', 'cancelled', 'interrupted', 'timed_out'].includes(result.status))
      mark(id, result.task_id)
    else if (turn.status === 'completed' && !result.replayed) void sendNext(id, result.task_id)
    else queuedPaused.value[id] = true
    const item = sessions.value.find((s) => s.id === id)
    if (item) {
      item.updated_at = new Date().toISOString()
      if (item.title === '新对话') item.title = content.slice(0, 28)
      sessions.value.sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at))
    }
    try {
      await loadingSessions.get(id)
      if (epoch !== lifecycle || deletedSessions.has(id)) return
      await refreshSnapshot(id)
    } catch {
      error.value = t("消息已提交，状态更新失败。请重新打开对话，勿重复发送。")
    }
  }
  async function confirmSubmission(id: string) {
    const submission = submissions.value[id]
    if (!submission?.uncertain) return
    try {
      await sendToSession(id, submission.content)
    } catch {
      // A definitive refusal releases the key but must not lose the user's text.
      if (!deletedSessions.has(id) && !submissions.value[id]) {
        ;(queuedMessages.value[id] ||= []).unshift(submission.content)
        queuedPaused.value[id] = true
      }
    }
  }
  async function sendMessage(content: string) {
    if (activeSessionId.value) await sendToSession(activeSessionId.value, content)
  }
  async function sendNext(id: string, completedTask?: string, confirmed = false) {
    if (draining.has(id) || submissions.value[id] || runningTaskIds.value[id]?.length || !queuedMessages.value[id]?.length)
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
        // An ambiguous send already has a confirmation entry with the original key.
        if (!submissions.value[id]) (queuedMessages.value[id] ||= []).unshift(next)
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
  async function setSubagentLimits(calls: number, concurrent: number, id = activeSessionId.value, modelIds?: string[]) {
    if (!id) return
    const updated = await api.updateConversationSettings(id, {
      max_subagent_calls: calls, max_concurrent_subagents: concurrent,
      ...(modelIds === undefined ? {} : { subagent_model_ids: modelIds }),
    })
    const i = sessions.value.findIndex((s) => s.id === updated.id)
    if (i >= 0) sessions.value[i] = updated
  }
  async function decideApproval(approval: Approval, decision: 'allow' | 'deny') {
    await api.decideApproval(approval.id, decision, approval.version)
    await refreshEvents(approval.conversation_id)
  }
  function interruptedTask(id: string): AgentTask | undefined {
    const list = tasks.value[id] || []
    const latest = list[list.length - 1]
    return latest?.status === 'interrupted' ? latest : undefined
  }
  function canResumeTask(id: string) {
    return Boolean(capabilities.value.task_resume && interruptedTask(id) &&
      !sessions.value.find((item) => item.id === id)?.archived &&
      !runningTaskIds.value[id]?.length && !submissions.value[id])
  }
  async function resumeInterruptedTask(id: string) {
    const task = interruptedTask(id)
    if (!task || !canResumeTask(id) || resumingTaskIds.value.includes(task.id)) return
    resumingTaskIds.value.push(task.id)
    queuedPaused.value[id] = true
    error.value = null
    const epoch = lifecycle
    try {
      await refreshSnapshot(id)
      if (epoch !== lifecycle || deletedSessions.has(id)) return
      const current = interruptedTask(id)
      if (!canResumeTask(id) || current?.id !== task.id)
        throw new Error(t("任务状态已变化，请查看最新进展。"))
      // Checkpoint eligibility and all permission checks remain on the server.
      await api.resumeTask(current.id, current.version)
      if (epoch !== lifecycle || deletedSessions.has(id)) return
      await refreshEvents(id)
      await refreshSnapshot(id)
    } catch (reason) {
      if (epoch === lifecycle && !deletedSessions.has(id)) {
        error.value = t("未能确认恢复：") + (reason instanceof Error ? reason.message : String(reason))
        // A timeout may have happened after acceptance. Reconcile, never re-submit.
        try { await refreshSnapshot(id) } catch { /* Keep the original error. */ }
      }
    } finally {
      resumingTaskIds.value = resumingTaskIds.value.filter((item) => item !== task.id)
    }
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
      error.value = t("未能确认停止：") + (reason instanceof Error ? reason.message : String(reason))
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
      error.value = t("消息正在提交，任务建立后可停止。待发消息已暂停。")
  }
  function disconnect() {
    generation++
    lifecycle++
    bufferedEvents.clear()
    snapshotFacts.clear()
    taskSequences.clear()
    loadingSessions.clear()
    for (const [id, submission] of Object.entries(submissions.value)) {
      submission.uncertain = true
      clear(id, 'pending-' + submission.key)
    }
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
    snapshotFacts.delete(id)
    for (const key of taskSequences.keys()) if (key.startsWith(`${id}:`)) taskSequences.delete(key)
    deltas.splice(0, deltas.length, ...deltas.filter((item) => item.id !== id))
    for (const map of [messages.value, approvals.value, runningTaskIds.value, queuedMessages.value, queuedPaused.value,
      tasks.value, submissions.value, historyTruncated.value])
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
    submissions,
    historyTruncated,
    capabilities,
    resumingTaskIds,
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
    refreshSnapshot,
    sendMessage,
    sendToSession,
    setPermissionMode,
    setConversationRuntime,
    setSubagentLimits,
    decideApproval,
    cancelActiveTask,
    cancelTask,
    removeQueued,
    resumeQueued,
    confirmSubmission,
    interruptedTask,
    canResumeTask,
    resumeInterruptedTask,
    disconnect,
  }
})
