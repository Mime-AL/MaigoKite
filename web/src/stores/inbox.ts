import { computed, onScopeDispose, ref } from 'vue'
import { defineStore } from 'pinia'
import { api, type Approval } from '@/api/client'
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
  let loading = false
  const versions = new Map<string, Approval>()
  async function refresh() {
    if (loading) return
    loading = true
    try {
      const pending = await api.listApprovals()
      error.value = ''
      for (const approval of pending.filter((a) => a.status === 'pending')) {
        versions.set(approval.id, approval)
        session.watchSession(approval.conversation_id)
        if (!items.value.some((a) => a.id === approval.id))
          run.apply({
            type: 'await',
            seq: -Date.now(),
            sessionId: approval.conversation_id,
            turnId: approval.task_id,
            awaitId: approval.id,
            mode: 'approval',
            title: `批准 ${approval.tool_name}`,
            detail: JSON.stringify(approval.arguments, null, 2),
            risk: approval.risk_level,
            version: approval.version,
          })
      }
    } catch (reason) {
      error.value = reason instanceof Error ? reason.message : String(reason)
    } finally {
      loading = false
    }
  }
  async function decide(item: AwaitItem, verdict: Verdict, note?: string) {
    if (busy.value.includes(item.id)) return
    if (verdict === 'allow_session') {
      error.value = '当前服务只支持单次批准。'
      return
    }
    busy.value.push(item.id)
    error.value = ''
    try {
      const approval = versions.get(item.id)
      await api.decideApproval(item.id, verdict, approval?.version || item.version)
      // 202 only accepts the request; the persisted decision drives the UI.
      await session.refreshEvents(item.sessionId)
      const confirmed = run.turns[item.sessionId]
        ?.find((t) => t.id === item.turnId)
        ?.awaits.find((a) => a.id === item.id)
      if (confirmed?.verdict && note) run.resolveAwait(item.id, confirmed.verdict, note)
      versions.delete(item.id)
    } catch (reason) {
      error.value = reason instanceof Error ? reason.message : String(reason)
      throw reason
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
    if (timer) clearInterval(timer)
    timer = undefined
  }
  onScopeDispose(stop)
  return { items, busy, error, refresh, decide, start, stop }
})
