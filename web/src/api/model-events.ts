import type { AgentEvent } from './client'
import type { ContextUsage, GatewayEvent, TokenUsage } from './events'

type EventBase = Pick<GatewayEvent, 'seq' | 'eventId' | 'sessionId' | 'turnId' | 'time'>
const counters = [
  'input_tokens',
  'output_tokens',
  'total_tokens',
  'cache_read_tokens',
  'cache_creation_tokens',
  'cache_miss_tokens',
  'reasoning_tokens',
] as const

// Missing telemetry stays missing: Number(null) would incorrectly claim zero.
function number(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value : undefined
}
function usage(value: unknown): TokenUsage | undefined {
  if (!value || typeof value !== 'object') return undefined
  const source = value as Record<string, unknown>
  const result: TokenUsage = {}
  for (const key of counters) {
    const count = number(source[key])
    if (count !== undefined && Number.isSafeInteger(count)) result[key] = count
  }
  return Object.keys(result).length ? result : undefined
}

/** Additive product telemetry, not LangGraph/SDK types in the public protocol. */
export function mapModelEvent(event: AgentEvent, base: EventBase): GatewayEvent | undefined {
  const p = event.payload
  if (event.type === 'context.updated') {
    const capacity = number(p.model_context_window)
    const context: ContextUsage = {
      seq: base.seq,
      callId: typeof p.call_id === 'string' ? p.call_id : '',
      modelName: typeof p.model_name === 'string' ? p.model_name : '',
      usedTokens: number(p.estimated_input_tokens) ?? null,
      windowTokens: capacity && Number.isSafeInteger(capacity) ? capacity : null,
      measurement: 'estimate',
    }
    return { ...base, type: 'context_update', context }
  }
  if (
    !['model.call.started', 'model.call.completed', 'model.call.failed', 'model.usage'].includes(
      event.type,
    )
  )
    return
  // Older receipts without call_id still have a durable identity; no invented count.
  const callId = typeof p.call_id === 'string' && p.call_id ? p.call_id : event.event_id
  if (!callId) return
  const common = {
    ...base,
    callId,
    purpose: typeof p.purpose === 'string' ? p.purpose : 'response',
  }
  if (event.type === 'model.call.started') return { ...common, type: 'model_start' }
  if (event.type === 'model.call.failed') return { ...common, type: 'model_failed' }
  return {
    ...common,
    type: 'model_end',
    usage: usage(p.usage),
    durationMs: number(p.duration_ms),
    firstTokenMs: number(p.first_token_ms),
    decodeMs: number(p.decode_ms),
  }
}
