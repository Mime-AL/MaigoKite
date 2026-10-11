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
