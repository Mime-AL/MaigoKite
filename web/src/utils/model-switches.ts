import type { Turn } from '@/api/events'

/** Use durable task receipts, never the conversation's current model selection. */
export function modelSwitches(turns: readonly Turn[]): Map<string, string> {
  const switches = new Map<string, string>()
  let previous: { id: string; name: string } | undefined
  for (const turn of turns) {
    if (!turn.userText) continue
    const context = turn.context
    const name = context?.modelName.trim()
    if (!name || (context?.purpose && context.purpose !== 'response')) {
      // A gap without model history cannot prove when a switch took place.
      previous = undefined
      continue
    }
    const current = { id: context?.modelId?.trim() || '', name }
    if (previous && (previous.name !== current.name ||
      (previous.id && current.id && previous.id !== current.id)))
      switches.set(turn.id, name)
    previous = current
  }
  return switches
}
