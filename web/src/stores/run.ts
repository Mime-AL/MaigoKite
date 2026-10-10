import { computed, onScopeDispose, shallowRef, triggerRef } from 'vue'
import { defineStore } from 'pinia'
import type { AwaitItem, GatewayEvent, PulseState, Turn } from '@/api/events'
import type { AgentTask } from '@/api/client'
import { summarize } from './run-projection'
export type { PulseState } from '@/api/events'

export const useRunStore = defineStore('run', () => {
  const turns = shallowRef<Record<string, Turn[]>>({})
  const connected = shallowRef<Record<string, boolean>>({})
  const seen = new Set<string>()
  const reasoningStreams = new Set<string>()
  let frame = 0
  function publish() {
    if (!frame)
      frame = requestAnimationFrame(() => {
        frame = 0
        triggerRef(turns)
      })
  }
  function getTurn(sessionId: string, turnId: string, time?: string): Turn {
    const list = (turns.value[sessionId] ||= [])
    let turn = list.find((t) => t.id === turnId)
    if (!turn) {
      turn = {
        id: turnId,
        sessionId,
        status: 'running',
        startedAt: time ? Date.parse(time) : Date.now(),
        text: '',
        thinking: '',
        steps: [],
        awaits: [],
        memories: [],
        timeline: [],
        changes: [],
        plan: [],
        jobs: [],
      }
      list.push(turn)
      list.sort((a, b) => a.startedAt - b.startedAt)
    }
    return turn
  }
  function markStarted(sessionId: string, turnId: string, userText?: string, time?: string) {
    const turn = getTurn(sessionId, turnId, time)
    turn.userText ||= userText
    publish()
  }
  function hydrateTask(sessionId: string, task: AgentTask) {
    const turn = getTurn(sessionId, task.id, task.created_at)
    turn.startedAt = Date.parse(task.created_at)
    turns.value[sessionId].sort((a, b) => a.startedAt - b.startedAt)
    turn.userText ||= task.input_text
    turn.status =
      task.status === 'succeeded'
        ? 'completed'
        : task.status === 'cancelled'
          ? 'cancelled'
          : ['failed', 'interrupted', 'timed_out'].includes(task.status)
            ? 'failed'
            : task.status === 'waiting_approval'
              ? 'waiting'
              : 'running'
    if (task.last_error) turn.error = task.last_error
    if (['completed', 'failed', 'cancelled'].includes(turn.status))
      for (const item of turn.awaits) if (!item.verdict) item.closed = true
    publish()
  }
  function completeText(sessionId: string, turnId: string, text: string, messageId?: string) {
    const turn = getTurn(sessionId, turnId)
    turn.text = text
    turn.messageId = messageId
    publish()
  }
  function forgetSession(id: string) {
    delete turns.value[id]
    delete connected.value[id]
    triggerRef(connected)
    publish()
  }
  function apply(event: GatewayEvent) {
    const itemId =
      'stepId' in event
        ? event.stepId
        : 'awaitId' in event
          ? event.awaitId
          : 'memoryId' in event
            ? event.memoryId
            : ''
    const identity = event.eventId
      ? `${event.eventId}:${event.type}`
      : `${event.sessionId}:${event.turnId}:${event.seq}:${event.type}:${itemId}`
    if (seen.has(identity)) return
    seen.add(identity)
    const turn = getTurn(event.sessionId, event.turnId, event.time)
    switch (event.type) {
      case 'text_delta':
        turn.text += event.text
        break
      case 'thinking_delta':
        reasoningStreams.add(`${event.sessionId}:${event.turnId}`)
        turn.thinking += event.text
        break
      case 'thinking_completed':
        if (!reasoningStreams.has(`${event.sessionId}:${event.turnId}`))
          turn.thinking += (turn.thinking ? '\n\n' : '') + event.text
        break
      case 'step_start': {
        let step = turn.steps.find((s) => s.id === event.stepId)
        if (step) {
          if (step.status === 'pending' && !event.pending) step.status = 'running'
          if (!event.pending) step.startedAt = event.time ? Date.parse(event.time) : Date.now()
          if (event.input) step.input = event.input
        } else {
          step = {
            id: event.stepId,
            tool: event.tool,
            kind: event.kind,
            title: event.title,
            input: event.input,
            status: event.pending ? 'pending' : 'running',
            output: '',
            durationMs: 0,
            startedAt: event.pending ? undefined : event.time ? Date.parse(event.time) : Date.now(),
          }
          turn.steps.push(step)
          turn.timeline.push({ id: step.id, kind: 'step' })
        }
        break
      }
      case 'step_end': {
        let step = turn.steps.find((s) => s.id === event.stepId)
        if (!step) {
          step = {
            id: event.stepId,
            tool: '工具',
            kind: 'act',
            title: '工具结果',
            input: {},
            status: 'running',
            output: '',
            durationMs: 0,
          }
          turn.steps.push(step)
          turn.timeline.push({ id: step.id, kind: 'step' })
        }
        if (step)
          Object.assign(step, {
            status: event.ok ? 'completed' : 'failed',
            output: event.output,
            durationMs:
              event.durationMs ||
              (step.startedAt
                ? Math.max(0, (event.time ? Date.parse(event.time) : Date.now()) - step.startedAt)
                : 0),
            exitCode: event.exitCode,
            hint: event.hint,
            errorCode: event.errorCode,
            action: event.action,
          })
        break
      }
      case 'await': {
        if (!turn.awaits.some((a) => a.id === event.awaitId)) {
          turn.awaits.push({
            id: event.awaitId,
            sessionId: event.sessionId,
            turnId: event.turnId,
            mode: event.mode,
            title: event.title,
            detail: event.detail,
            risk: event.risk,
            options: event.options,
            version: event.version || 1,
            closed: ['completed', 'failed', 'cancelled'].includes(turn.status),
          })
          turn.timeline.push({ id: event.awaitId, kind: 'await' })
        }
        if (!['completed', 'failed', 'cancelled'].includes(turn.status)) turn.status = 'waiting'
        break
      }
      case 'await_resolved': {
        const item = turn.awaits.find((a) => a.id === event.awaitId)
        if (item) {
          item.verdict = event.verdict
          item.note = event.note
        }
        if (turn.status === 'waiting' && turn.awaits.every((a) => a.verdict))
          turn.status = 'running'
        break
      }
      case 'file_change': {
        const item = turn.changes.find((c) => c.path === event.path)
        if (item) item.diff = event.diff
        else turn.changes.push({ path: event.path, diff: event.diff })
        break
      }
      case 'plan_update':
        turn.plan = event.items
        break
      case 'memory_added':
        if (!turn.memories.some((m) => m.id === event.memoryId)) {
          turn.memories.push({ id: event.memoryId, text: event.text })
          turn.timeline.push({ id: event.memoryId, kind: 'memory' })
        }
        break
      case 'job_update': {
        const job = turn.jobs.find((j) => j.id === event.jobId)
        if (job) Object.assign(job, event)
        else turn.jobs.push({ id: event.jobId, status: event.status, logTail: event.logTail })
        break
      }
      case 'error':
        turn.error = event.message
        turn.timeline.push({ id: `error-${event.seq}`, kind: 'error' })
        turn.status = 'failed'
        break
      case 'turn_end':
        turn.status = event.status || 'completed'
        turn.endedAt = event.time ? Date.parse(event.time) : Date.now()
        turn.summary = event.summary || summarize(turn)
        for (const item of turn.awaits) if (!item.verdict) item.closed = true
        break
    }
    // Streaming text is published once per frame, never once per token.
    publish()
  }
  function resolveAwait(id: string, verdict: AwaitItem['verdict'], note?: string) {
    for (const list of Object.values(turns.value))
      for (const turn of list) {
        const item = turn.awaits.find((a) => a.id === id)
        if (item) {
          item.verdict = verdict
          item.note = note
          if (turn.status === 'waiting' && turn.awaits.every((a) => a.verdict))
            turn.status = 'running'
        }
      }
    publish()
  }
  function removeMemory(id: string) {
    for (const list of Object.values(turns.value))
      for (const turn of list) {
        turn.memories = turn.memories.filter((m) => m.id !== id)
        turn.timeline = turn.timeline.filter((n) => n.kind !== 'memory' || n.id !== id)
      }
    publish()
  }
  function setConnection(id: string, value: boolean) {
    connected.value = { ...connected.value, [id]: value }
  }
  function pulse(id: string | null): PulseState {
    if (id && connected.value[id] === false) return 'offline'
    const turn = id ? turns.value[id]?.slice(-1)[0] : undefined
    if (!turn) return 'idle'
    if (turn.status === 'waiting') return 'waiting'
    if (turn.status === 'failed') return 'error'
    if (['completed', 'cancelled'].includes(turn.status)) return 'idle'
    return turn.steps.some((s) => s.status === 'running') ? 'acting' : 'thinking'
  }
  const awaits = computed(() =>
    Object.values(turns.value)
      .flatMap((list) => list.flatMap((t) => t.awaits))
      .filter((a) => !a.verdict && !a.closed),
  )
  onScopeDispose(() => {
    if (frame) cancelAnimationFrame(frame)
  })
  return {
    forgetSession,
    turns,
    connected,
    awaits,
    getTurn,
    markStarted,
    hydrateTask,
    completeText,
    apply,
    resolveAwait,
    removeMemory,
    setConnection,
    pulse,
  }
})
