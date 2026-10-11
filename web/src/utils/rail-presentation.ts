import type { AwaitItem, RailNode, SupplementInput, Turn } from '@/api/events'
import { railNodes } from '@/stores/run-projection'
import { t } from '@/i18n'
// Display-only node: no new Gateway event or execution state.
export type PresentationNode = Omit<RailNode, 'kind'> & {
  kind: RailNode['kind'] | 'input'
  input?: SupplementInput
}
function timestamp(time?: string) {
  const value = Date.parse(time || '')
  return Number.isFinite(value) ? value : undefined
}
export function hasOrder(item: { seq?: number; time?: string }) {
  return Boolean(item.seq && item.seq > 0) || timestamp(item.time) !== undefined
}
/** Read-only presentation copy. Snapshot-only questions have no fabricated seq. */
export function presentationNodes(turn: Turn): PresentationNode[] {
  const timeline: (
    Turn['timeline'][number] | { id: string; kind: 'input'; seq?: number; time?: string }
  )[] = [
    ...turn.timeline,
    ...(turn.inputs || []).map((input) => ({
      id: input.id,
      kind: 'input' as const,
      seq: input.seq,
      time: input.created_at,
    })),
  ]
  const ordered = timeline.map((item, index) => ({ ...item, index }))
  const unordered = (item: (typeof ordered)[number]) =>
    ['await', 'input'].includes(item.kind) && !hasOrder(item)
  ordered.sort((a, b) => {
    if (unordered(a) !== unordered(b)) return unordered(a) ? 1 : -1
    // An input's seq can describe consumption, not submission. Prefer its real
    // creation time against timed operations; never invent an ordering number.
    const at = timestamp(a.time),
      bt = timestamp(b.time)
    if ((a.kind === 'input' || b.kind === 'input') && at !== undefined && bt !== undefined)
      return at - bt || a.index - b.index
    if (a.seq && b.seq) return a.seq - b.seq || a.index - b.index
    return at !== undefined && bt !== undefined ? at - bt || a.index - b.index : a.index - b.index
  })
  const projected: PresentationNode[] = []
  let segment: Turn['timeline'] = []
  const flush = () => {
    projected.push(...railNodes({ ...turn, timeline: segment }))
    segment = []
  }
  for (const item of ordered) {
    if (item.kind !== 'input') {
      segment.push(item)
      continue
    }
    flush()
    const input = turn.inputs?.find((value) => value.id === item.id)
    if (input)
      projected.push({
        id: `input-${input.id}`,
        kind: 'input',
        title: t('补充指令'),
        steps: [],
        input,
      })
  }
  flush()
  const approvals = turn.awaits.filter((item) => item.mode === 'approval' && item.toolCallId)
  const linkedIds = new Set(approvals.map((item) => item.toolCallId))
  const nodes = projected.flatMap((node) => {
    if (
      node.kind !== 'read' ||
      node.steps.length < 2 ||
      !node.steps.some((step) => linkedIds.has(step.id))
    )
      return [node]
    return node.steps.map((step) => ({
      ...node,
      id: step.id,
      title: step.title,
      steps: [step],
      running: turn.status === 'running' && ['running', 'pending'].includes(step.status),
    }))
  })
  // Identity, not tool name/argument similarity, associates an approval.
  for (const approval of approvals) {
    if (approval.sessionId !== turn.sessionId || approval.turnId !== turn.id) continue
    const owner = nodes.find(
      (node) => node.steps.some((step) => step.id === approval.toolCallId) && !node.await,
    )
    const index = nodes.findIndex((node) => node.await?.id === approval.id)
    if (owner && index >= 0) {
      owner.await = approval
      nodes.splice(index, 1)
    }
  }
  return nodes
}
export function pendingItem(item: { closed?: boolean; verdict?: string; answer?: string }) {
  return !item.closed && !item.verdict && item.answer === undefined
}
export function pendingOrder(a: AwaitItem, b: AwaitItem) {
  if (hasOrder(a) !== hasOrder(b)) return hasOrder(a) ? -1 : 1
  if (a.seq && a.seq > 0 && b.seq && b.seq > 0) return a.seq - b.seq
  const at = timestamp(a.time),
    bt = timestamp(b.time)
  return at !== undefined && bt !== undefined ? at - bt : 0
}
