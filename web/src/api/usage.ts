import { request, workspacePath } from './http'
import type { ChatModelProvider } from './client'
import type { TokenUsage } from './events'

export interface UsageMetrics {
  calls: number
  failed_calls: number
  reported_calls: number
  cache_reported_calls: number
  tokens: TokenUsage
  token_reports: Partial<Record<keyof TokenUsage, number>>
  cache_pct: number | null
}
export interface UsageModel extends UsageMetrics {
  model_id: string
  provider: ChatModelProvider | ''
  base_url: string
  model: string
}
export interface UsageProfile {
  id: string
  name: string
  model: string
  provider: ChatModelProvider
  base_url: string
  quota_service: 'deepseek' | 'openrouter' | null
}
export interface UsageStatistics {
  profiles: UsageProfile[]
  models: UsageModel[]
  totals: UsageMetrics
  daily: (UsageMetrics & { date: string })[]
  unattributed_calls: number
  since: string | null
  until: string
  start_date: string | null
  end_date: string
}
export interface ModelBalance {
  kind: 'balance' | 'key_limit'
  values: { currency: string; amount: string }[]
  checked_at: string
}
export function getUsageStatistics(days: number, signal?: AbortSignal): Promise<UsageStatistics> {
  return request(`${workspacePath}/usage?days=${days}`, { signal })
}
export function getModelBalance(id: string, signal?: AbortSignal): Promise<ModelBalance> {
  return request(`${workspacePath}/models/${encodeURIComponent(id)}/balance`, { signal })
}
