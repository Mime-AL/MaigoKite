import type { UserMemory } from '@/api/client'
import type { Turn } from '@/api/events'

export function knownSessionStatus(turns: Turn[], active: string[]): string | undefined {
  // A newly marked task may precede its first activity projection.
  if (active.some(id => !turns.some(turn => turn.id === id))) return 'running'
  const turn = turns.at(-1)
  if (turn) return turn.status
  return active.length ? 'running' : undefined
}

export function memoryGroup(item: UserMemory): 'persona' | 'preference' | 'memory' {
  if (item.content.startsWith('人设：')) return 'persona'
  return ['preference', 'constraint'].includes(item.category) ? 'preference' : 'memory'
}

export function confidencePercent(value: number): number {
  return Math.round(Math.max(0, Math.min(1, Number.isFinite(value) ? value : 0)) * 100)
}
