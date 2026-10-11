import type { AgentEvent } from './client'
import type { ContextCompaction, ContextUsage, GatewayEvent, TokenUsage } from './events'

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
function measurement(value: unknown): ContextUsage['measurement'] {
  return value === 'estimate' || value === 'provider' ? value : null
}
const compactionStates: Record<string, ContextCompaction['status']> = {
  'context.compaction.started': 'running',
  'context.compaction.failed': 'failed',
  'context.compaction.skipped': 'skipped',
  'context.compacted': 'completed',
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
      modelId: typeof p.model_id === 'string' ? p.model_id : undefined,
      modelKey: typeof p.model_key === 'string' ? p.model_key : undefined,
      usedTokens: number(p.estimated_input_tokens) ?? null,
      windowTokens: capacity && Number.isSafeInteger(capacity) ? capacity : null,
      measurement: measurement(p.measurement),
      purpose: typeof p.purpose === 'string' ? p.purpose : 'response',
      capacitySource: typeof p.capacity_source === 'string' ? p.capacity_source : null,
      capacityStatus: typeof p.capacity_status === 'string' ? p.capacity_status : undefined,
      capacityCheckedAt: typeof p.capacity_checked_at === 'string' ? p.capacity_checked_at : null,
    }
    return { ...base, type: 'context_update', context }
  }
  const status = Object.prototype.hasOwnProperty.call(compactionStates, event.type)
    ? compactionStates[event.type]
    : undefined
  if (status && event.task_id) {
    const capacity = number(p.model_context_window)
    return {
      ...base,
      type: 'context_compaction',
      compaction: {
        seq: base.seq,
        status,
        measurement: measurement(p.measurement),
        beforeTokens: number(p.before_tokens) ?? null,
        afterTokens: number(p.after_tokens) ?? null,
        windowTokens: capacity && Number.isSafeInteger(capacity) ? capacity : null,
        message: typeof p.message === 'string' ? p.message : undefined,
        errorType: typeof p.error_type === 'string' ? p.error_type : undefined,
        reason: typeof p.reason === 'string' ? p.reason : undefined,
      },
    }
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
