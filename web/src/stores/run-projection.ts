import type { RailNode, Turn, TurnSummary } from '@/api/events'

export function summarize(turn: Turn): TurnSummary {
  const changed = new Set(turn.changes.map((change) => change.path))
  for (const step of turn.steps) {
    if (step.status !== 'completed' || !['file_write', 'file_edit', 'write', 'edit'].includes(step.tool)) continue
    const input = step.input && typeof step.input === 'object' ? (step.input as Record<string, unknown>) : {}
    if (input.path) changed.add(String(input.path))
  }
  const lines = turn.changes.flatMap((change) => change.diff.split('\n'))
  return {
    files: changed.size,
    added: lines.filter((line) => line.startsWith('+') && !line.startsWith('+++')).length,
    removed: lines.filter((line) => line.startsWith('-') && !line.startsWith('---')).length,
    commands: turn.steps.filter((step) => ['bash', 'exec_command', 'shell', 'powershell'].includes(step.tool)).length,
    failed: turn.steps.filter((step) => step.status === 'failed').length,
    awaits: turn.awaits.length,
    contextPct: null,
    durationMs: Math.max(0, (turn.endedAt || Date.now()) - turn.startedAt),
  }
}

export function railNodes(turn: Turn): RailNode[] {
  const nodes: RailNode[] = []
  const steps = new Map(turn.steps.map((step) => [step.id, step]))
  const awaits = new Map(turn.awaits.map((item) => [item.id, item]))
  const memories = new Map(turn.memories.map((item) => [item.id, item]))
  for (const item of turn.timeline) {
    if (item.kind === 'step') {
      const step = steps.get(item.id)
      if (!step) continue
      const kind = step.status === 'failed' ? 'failed' : step.kind
      const previous = nodes[nodes.length - 1]
      if (kind === 'read' && previous?.kind === 'read') {
        previous.steps.push(step)
        previous.title = previous.steps.every((s) => ['read', 'file_read'].includes(s.tool))
          ? `翻了 ${previous.steps.length} 个文件`
          : `查看了 ${previous.steps.length} 项资料`
        previous.running ||= turn.status === 'running' && (step.status === 'running' || step.status === 'pending')
      } else
        nodes.push({
          id: step.id,
          kind,
          title: step.title,
          steps: [step],
          running: turn.status === 'running' && (step.status === 'running' || step.status === 'pending'),
        })
    }
    if (item.kind === 'await') {
      const value = awaits.get(item.id)
      if (value) nodes.push({ id: value.id, kind: 'await', title: value.title, steps: [], await: value })
    }
    if (item.kind === 'memory') {
      const value = memories.get(item.id)
      if (value)
        nodes.push({ id: value.id, kind: 'memory', title: `记下了：${value.text}`, steps: [], memoryId: value.id })
    }
    if (item.kind === 'error') nodes.push({ id: item.id, kind: 'failed', title: turn.error || '执行失败', steps: [] })
  }
  return nodes
}
