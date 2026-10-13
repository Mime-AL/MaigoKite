import { t } from '@/i18n'
import { groupModelProfiles, normalizeEndpoint } from '@/config/model-groups'
import type { ModelOption, ModelServiceGroup } from '@/config/model-groups'
import type { TokenUsage } from '@/api/events'
import type { UsageMetrics, UsageModel, UsageProfile, UsageStatistics } from '@/api/usage'

export interface UsageRow { id: string; model: string; metrics: UsageMetrics }
export interface UsageGroup extends Omit<ModelServiceGroup<ModelOption>, 'models'> {
  models: UsageRow[]
  profiles: UsageProfile[]
  metrics: UsageMetrics
  historical: boolean
}
const formatters = new Map<string, Intl.NumberFormat>()
export function usageNumber(value: number | undefined, locale: string, compact = true): string {
  if (value === undefined) return '—'
  const key = `${locale}:${compact}`
  if (!formatters.has(key)) formatters.set(key, new Intl.NumberFormat(locale, {
    notation: compact ? 'compact' : 'standard', maximumFractionDigits: compact ? 1 : 0,
  }))
  return formatters.get(key)!.format(value)
}
export function sumUsage(items: readonly UsageMetrics[]): UsageMetrics {
  const result: UsageMetrics = {
    calls: 0, failed_calls: 0, reported_calls: 0, cache_reported_calls: 0,
    tokens: {}, token_reports: {}, cache_pct: null,
  }
  let validCache = true
  for (const item of items) {
    for (const field of ['calls', 'failed_calls', 'reported_calls', 'cache_reported_calls'] as const)
      result[field] += item[field]
    for (const field of Object.keys(item.tokens) as (keyof TokenUsage)[]) {
      const value = item.tokens[field]
      if (value !== undefined) result.tokens[field] = (result.tokens[field] || 0) + value
    }
    for (const field of Object.keys(item.token_reports) as (keyof TokenUsage)[])
      result.token_reports[field] = (result.token_reports[field] || 0) + (item.token_reports[field] || 0)
    if (item.calls && (item.tokens.input_tokens === undefined || item.tokens.cache_read_tokens === undefined ||
      item.tokens.cache_read_tokens > item.tokens.input_tokens)) validCache = false
  }
  if (result.calls && validCache && result.cache_reported_calls === result.calls &&
    result.token_reports.input_tokens === result.calls && result.tokens.input_tokens)
    result.cache_pct = (result.tokens.cache_read_tokens || 0) / result.tokens.input_tokens * 100
  return result
}

export function usageGroups(snapshot: UsageStatistics): UsageGroup[] {
  const empty = () => sumUsage([])
  const configured = groupModelProfiles(snapshot.profiles.map(profile => ({
    id: profile.id, name: profile.name, model: profile.model,
    provider: profile.provider, baseUrl: profile.base_url,
  })))
  const groups: UsageGroup[] = configured.map(group => ({ ...group,
    profiles: snapshot.profiles.filter(profile => group.models.some(model => model.id === profile.id)),
    models: group.models.map(profile => ({ id: profile.id, model: profile.model, metrics: empty() })),
    metrics: empty(), historical: false,
  }))
  const historical: (ModelOption & { metrics: UsageModel })[] = []
  for (const record of snapshot.models) {
    const profile = snapshot.profiles.find(item => item.id === record.model_id && item.model === record.model &&
      (!record.provider || item.provider === record.provider) &&
      (!record.base_url || normalizeEndpoint(item.base_url) === normalizeEndpoint(record.base_url)))
    const row = profile && groups.flatMap(group => group.models).find(item => item.id === profile.id)
    if (row) row.metrics = sumUsage([row.metrics, record])
    else historical.push({ id: JSON.stringify([record.model_id, record.provider, record.base_url, record.model]),
      name: t(record.model_id ? '历史配置' : '未归属的记录'),
      model: record.model || t('模型未记录'), provider: record.provider || undefined,
      baseUrl: record.base_url, metrics: record })
  }
  // Unknown routes belong in a clearly labelled historical bucket, not repeated supplier cards.
  const historyGroups = new Map<string, ModelServiceGroup<typeof historical[number]>>()
  for (const group of groupModelProfiles(historical)) {
    const key = group.models[0]?.provider ? group.id : `unrouted-${group.name}`
    const existing = historyGroups.get(key)
    if (existing) existing.models.push(...group.models)
    else historyGroups.set(key, { ...group, id: key })
  }
  for (const group of historyGroups.values()) groups.push({ ...group,
    id: `history-${group.id}`, profiles: [], historical: true,
    models: group.models.map(item => ({ id: item.id, model: item.model, metrics: item.metrics })),
    metrics: sumUsage(group.models.map(item => item.metrics)),
  })
  for (const group of groups) group.metrics = sumUsage(group.models.map(row => row.metrics))
  return groups.sort((a, b) => b.metrics.calls - a.metrics.calls)
}
