import type { ContextUsage, GatewayEvent, ModelCall, TokenUsage, Turn } from '@/api/events'

type MetricEvent = Extract<
  GatewayEvent,
  { type: 'model_start' | 'model_end' | 'model_failed' | 'context_update' }
>
export function projectModelEvent(turn: Turn, event: MetricEvent) {
  if (event.type === 'context_update') {
    if (!turn.context || event.seq > turn.context.seq) turn.context = { ...event.context }
    return
  }
  const calls = (turn.modelCalls ||= Object.create(null) as Record<string, ModelCall>)
  const previous = calls[event.callId]
  if (previous && event.seq <= previous.seq) return
  const call = { ...previous, id: event.callId, purpose: event.purpose, seq: event.seq }
  if (event.type === 'model_failed') call.failed = true
  if (event.type === 'model_end') {
    if (event.usage) call.usage = event.usage
    for (const key of ['durationMs', 'firstTokenMs', 'decodeMs'] as const)
      if (event[key] !== undefined) call[key] = event[key]
    // The last request plus its output is more accurate than a character estimate.
    // Keep this tied to the same call; replay must not overwrite a later prompt.
    if (
      turn.context?.callId === event.callId &&
      event.seq > turn.context.seq &&
      event.usage?.input_tokens !== undefined &&
      event.usage.output_tokens !== undefined
    )
      turn.context = {
        ...turn.context,
        seq: event.seq,
        measurement: 'provider',
        usedTokens: event.usage.input_tokens + event.usage.output_tokens,
      }
  }
  calls[event.callId] = call
}

export interface UsageStats {
  calls: number
  summaryCalls: number
  subagentCalls: number
  reportedCalls: number
  partial: boolean
  tokens: TokenUsage
  totalTokens: number | null
  cachePct: number | null
  tokensPerSecond: number | null
  firstTokenMs: number | null
  modelMs: number | null
  toolMs: number | null
}

/** Fold durable call receipts once, independent of the visible/paged transcript. */
export function sessionUsage(turns: Turn[]): UsageStats {
  const calls = turns.flatMap((turn) => Object.values(turn.modelCalls || {}))
  const reported = calls.filter((call) => call.usage !== undefined)
  const tokens: TokenUsage = {}
  for (const call of reported)
    for (const key of Object.keys(call.usage || {}) as Array<keyof TokenUsage>)
      tokens[key] = (tokens[key] ?? 0) + (call.usage?.[key] ?? 0)
  const totals = reported.map(({ usage }) => {
    if (usage?.total_tokens !== undefined) return usage.total_tokens
    if (usage?.input_tokens !== undefined && usage.output_tokens !== undefined)
      return usage.input_tokens + usage.output_tokens
    return null
  })
  const inputs = reported.filter((call) => call.usage?.input_tokens !== undefined)
  const cacheKnown =
    inputs.length > 0 &&
    inputs.length === reported.length &&
    inputs.every((call) => call.usage?.cache_read_tokens !== undefined)
  const response = calls.filter((call) => call.purpose === 'response')
  const decoded = response.filter(
    (call) =>
      !call.failed &&
      call.decodeMs !== undefined &&
      call.decodeMs > 0 &&
      call.usage?.output_tokens !== undefined,
  )
  const decodeMs = decoded.reduce((sum, call) => sum + (call.decodeMs ?? 0), 0)
  const output = decoded.reduce((sum, call) => sum + (call.usage?.output_tokens ?? 0), 0)
  const first = response.flatMap((call) =>
    call.firstTokenMs === undefined ? [] : [call.firstTokenMs],
  )
  const times = response.flatMap((call) => (call.durationMs === undefined ? [] : [call.durationMs]))
  const tools = turns.flatMap((turn) =>
    turn.steps.filter((step) => step.status === 'completed' || step.status === 'failed'),
  )
  const input = tokens.input_tokens ?? 0,
    cached = tokens.cache_read_tokens ?? 0
  return {
    calls: response.length,
    summaryCalls: calls.filter((call) => call.purpose === 'summary').length,
    subagentCalls: calls.filter((call) => call.purpose === 'subagent').length,
    reportedCalls: reported.length,
    partial: reported.length < calls.length || totals.some((total) => total === null),
    tokens,
    // Cache/reasoning counters are subsets. Never add them again to total usage.
    totalTokens: totals.some((total) => total !== null)
      ? totals.reduce<number>((sum, total) => sum + (total ?? 0), 0)
      : null,
    cachePct: cacheKnown && input > 0 && cached <= input ? (cached / input) * 100 : null,
    tokensPerSecond: decodeMs > 0 ? output / (decodeMs / 1000) : null,
    firstTokenMs: first.length ? first.reduce((sum, value) => sum + value, 0) / first.length : null,
    modelMs: times.length ? times.reduce((sum, value) => sum + value, 0) : null,
    toolMs: tools.length ? tools.reduce((sum, step) => sum + step.durationMs, 0) : null,
  }
}

export function latestContext(turns: Turn[], modelName?: string): ContextUsage | undefined {
  const contexts = turns.flatMap((turn) => (turn.context ? [turn.context] : []))
  const latest = contexts.reduce<ContextUsage | undefined>(
    (current, next) => (!current || next.seq > current.seq ? next : current),
    undefined,
  )
  // Changing models cannot carry the previous model's capacity/percentage over.
  return latest && (modelName === undefined || latest.modelName === modelName) ? latest : undefined
}
