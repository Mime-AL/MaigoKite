import type { ContextUsage } from './events'
import { normalizeEndpoint, type ModelOption } from '@/config/model-groups'

export function modelContextKey(model: ModelOption): string {
  return JSON.stringify([
    model.id, model.provider, normalizeEndpoint(model.baseUrl || ''), model.model,
    model.contextWindow ?? null,
  ])
}

/** Accept old three-part keys only when no configured capacity changed. Never
 * associate an unidentified receipt by display name or borrow another chat's use. */
export function matchesModelContext(value: ContextUsage | undefined, model: ModelOption): boolean {
  if (!value || value.modelId !== model.id || value.modelName !== model.model || !value.modelKey)
    return false
  try {
    const key: unknown = JSON.parse(value.modelKey)
    if (!Array.isArray(key) || (key.length !== 3 && key.length !== 4)) return false
    return key[0] === model.provider && typeof key[1] === 'string' &&
      normalizeEndpoint(key[1]) === normalizeEndpoint(model.baseUrl || '') && key[2] === model.model &&
      (key.length === 4 ? key[3] === (model.contextWindow ?? null) : model.contextWindow === undefined)
  } catch { return false }
}

// Capacity policy changed: v1 could contain another vendor's window for a
// relay. Leave that cache unread rather than carrying its guesses forward.
const capacityCacheKey = 'maigokite:model-capacities:route-v1'

export function preferredModelCapacity(values: readonly (ContextUsage | undefined)[]): ContextUsage | undefined {
  const rank = (value: ContextUsage) =>
    ['lmstudio.loaded_instance', 'ollama.loaded_instance', 'provider_error'].includes(value.capacitySource || '')
      ? 2 : value.capacitySource === 'model_profile' ? 1 : 0
  return values.reduce<ContextUsage | undefined>((current, next) => {
    if (!next?.windowTokens) return current
    if (!current || rank(next) > rank(current)) return next
    return rank(next) === rank(current) &&
      (Date.parse(next.capacityCheckedAt || '') || 0) > (Date.parse(current.capacityCheckedAt || '') || 0)
      ? next : current
  }, undefined)
}

/** Persist capacity only. Never cache a conversation's usage with the model. */
export function cachedModelCapacity(model: ModelOption): ContextUsage | undefined {
  try {
    const cache: unknown = JSON.parse(localStorage.getItem(capacityCacheKey) || '{}')
    if (!cache || typeof cache !== 'object' || Array.isArray(cache)) return undefined
    const entry: unknown = (cache as Record<string, unknown>)[modelContextKey(model)]
    if (!entry || typeof entry !== 'object' || Array.isArray(entry)) return undefined
    const value = entry as Record<string, unknown>
    if (typeof value.windowTokens !== 'number' || !Number.isSafeInteger(value.windowTokens) || value.windowTokens <= 0)
      return undefined
    return {
      seq: 0, callId: '', modelId: model.id, modelName: model.model,
      modelKey: JSON.stringify([model.provider, model.baseUrl || '', model.model, model.contextWindow ?? null]),
      usedTokens: null, inputTokens: null, measurement: null,
      windowTokens: value.windowTokens,
      capacitySource: typeof value.capacitySource === 'string' ? value.capacitySource : null,
      capacityCheckedAt: typeof value.capacityCheckedAt === 'string' ? value.capacityCheckedAt : null,
      capacityStatus: 'cached',
    }
  } catch { return undefined }
}

export function rememberModelCapacity(value: ContextUsage, model: ModelOption): void {
  if (!matchesModelContext(value, model) || !value.windowTokens || value.windowTokens < 0 || !Number.isSafeInteger(value.windowTokens))
    return
  try {
    const previous: unknown = JSON.parse(localStorage.getItem(capacityCacheKey) || '{}')
    const entries = previous && typeof previous === 'object' && !Array.isArray(previous)
      ? Object.entries(previous).filter(([key]) => key !== modelContextKey(model)).slice(-63) : []
    const cache: Record<string, unknown> = Object.fromEntries(entries)
    cache[modelContextKey(model)] = {
      windowTokens: value.windowTokens, capacitySource: value.capacitySource,
      capacityCheckedAt: value.capacityCheckedAt,
    }
    localStorage.setItem(capacityCacheKey, JSON.stringify(cache))
  } catch { /* Storage denial must not affect capacity discovery or chat. */ }
}
