import { t } from '@/i18n'
import { computed, onScopeDispose, ref } from 'vue'
import { defineStore } from 'pinia'
import { api, type ApprovalScope } from '@/api/client'
import type { AwaitItem, Verdict } from '@/api/events'
import { useRunStore } from './run'
import { useSessionStore } from './session'

export const useInboxStore = defineStore('inbox', () => {
  const run = useRunStore(),
    session = useSessionStore()
  const busy = ref<string[]>([]),
    error = ref('')
  const items = computed(() => run.awaits)
  let timer: ReturnType<typeof setInterval> | undefined
  let refreshing: Promise<void> | undefined
  let generation = 0
  function refresh(): Promise<void> {
    if (refreshing) return refreshing
    const pending = loadPending().finally(() => {
      if (refreshing === pending) refreshing = undefined
    })
    refreshing = pending
    return pending
  }
  async function loadPending() {
    const epoch = generation
    try {
      const [approvals, questions] = await Promise.all([api.listApprovals(), api.listQuestions()])
      if (epoch !== generation) return
      // Lists discover conversations only. Install pending items and task state
      // together from an atomic snapshot with a real sequence watermark.
      const ids = new Set([
        ...approvals.filter((a) => a.status === 'pending').map((a) => a.conversation_id),
        ...questions.filter((q) => q.status === 'pending').map((q) => q.conversation_id),
        ...items.value.map((item) => item.sessionId),
      ])
      await Promise.all([...ids].map((id) => session.refreshSnapshot(id)))
      if (epoch !== generation) return
      error.value = ''
    } catch (reason) {
      if (epoch === generation) error.value = reason instanceof Error ? reason.message : String(reason)
    }
  }
  async function decide(item: AwaitItem, verdict: Verdict, note?: string, scope: ApprovalScope = 'once') {
    if (item.mode !== 'approval') return
    if (verdict === 'allow_session') {
      error.value = t("请逐次确认本次操作。")
      return
    }
    // Submit the version the user actually reviewed, never a newer cached one.
    const version = item.version
    // Scope grants future permission only on allow; rejecting one operation
    // must work even after the user selected a reusable authorization scope.
    await submit(item, () => api.decideApproval(item.id, verdict, version, note, verdict === 'deny' ? 'once' : scope))
  }
  async function answer(item: AwaitItem, text: string) {
    if (item.mode !== 'question' || !text.trim()) return
    const version = item.version
    await submit(item, () => api.answerQuestion(item.id, text.trim(), version))
  }
  async function submit(item: AwaitItem, request: () => Promise<unknown>) {
    if (busy.value.includes(item.id) || item.closed || item.verdict || item.answer !== undefined) return
    const epoch = generation
    busy.value.push(item.id)
    error.value = ''
    let failure: unknown
    try {
      try { await request() } catch (reason) { failure = reason }
      if (epoch !== generation) return
      // A timeout can follow a committed decision. Reconcile success AND errors;
      // neither HTTP 202 nor a local click is an approval/question verdict.
      try { await session.refreshSnapshot(item.sessionId) } catch {
        failure ||= new Error(t("操作已提交，状态更新失败。请刷新，勿重复提交。"))
      }
      if (failure) {
        if (epoch === generation) error.value = failure instanceof Error ? failure.message : String(failure)
        throw failure
      }
    } finally {
      busy.value = busy.value.filter((id) => id !== item.id)
    }
  }
  function start() {
    if (timer) return
    void refresh()
    timer = setInterval(() => {
      void refresh()
    }, 15_000)
  }
  function stop() {
    generation++
    refreshing = undefined
    if (timer) clearInterval(timer)
    timer = undefined
  }
  onScopeDispose(stop)
  return { items, busy, error, refresh, decide, answer, start, stop }
})
