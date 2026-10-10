import type { AwaitItem, RailNode, Turn } from '@/api/events'
import { railNodes } from '@/stores/run-projection'
function timestamp(time?: string) { const value = Date.parse(time || ''); return Number.isFinite(value) ? value : undefined }
export function hasOrder(item: { seq?: number; time?: string }) {
  return Boolean(item.seq && item.seq > 0) || timestamp(item.time) !== undefined
}
/** Read-only presentation copy. Snapshot-only questions have no fabricated seq. */
export function presentationNodes(turn: Turn): RailNode[] {
  const timeline = turn.timeline.map((item, index) => ({ ...item, index }))
  const unordered = (item: typeof timeline[number]) => item.kind === 'await' && !hasOrder(item)
  timeline.sort((a, b) => {
    if (unordered(a) !== unordered(b)) return unordered(a) ? 1 : -1
    if (a.seq && b.seq) return a.seq - b.seq || a.index - b.index
    const at = timestamp(a.time), bt = timestamp(b.time)
    return at !== undefined && bt !== undefined ? at - bt || a.index - b.index : a.index - b.index
  })
  const approvals = turn.awaits.filter(item => item.mode === 'approval' && item.toolCallId)
  const linkedIds = new Set(approvals.map(item => item.toolCallId))
  const nodes = railNodes({ ...turn, timeline }).flatMap(node => {
    if (node.kind !== 'read' || node.steps.length < 2 || !node.steps.some(step => linkedIds.has(step.id))) return [node]
    return node.steps.map(step => ({ ...node, id: step.id, title: step.title, steps: [step],
      running: turn.status === 'running' && ['running', 'pending'].includes(step.status) }))
  })
  // Identity, not tool name/argument similarity, associates an approval.
  for (const approval of approvals) {
    if (approval.sessionId !== turn.sessionId || approval.turnId !== turn.id) continue
    const owner = nodes.find(node => node.steps.some(step => step.id === approval.toolCallId) && !node.await)
    const index = nodes.findIndex(node => node.await?.id === approval.id)
    if (owner && index >= 0) { owner.await = approval; nodes.splice(index, 1) }
  }
  return nodes
}
export function pendingItem(item: { closed?: boolean; verdict?: string; answer?: string }) {
  return !item.closed && !item.verdict && item.answer === undefined
}
export function pendingOrder(a: AwaitItem, b: AwaitItem) {
  if (hasOrder(a) !== hasOrder(b)) return hasOrder(a) ? -1 : 1
  if (a.seq && a.seq > 0 && b.seq && b.seq > 0) return a.seq - b.seq
  const at = timestamp(a.time), bt = timestamp(b.time)
  return at !== undefined && bt !== undefined ? at - bt : 0
}
