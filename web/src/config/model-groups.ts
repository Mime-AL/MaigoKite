import type { ChatModelProfile, ChatModelProvider } from '@/api/client'
import { COMPATIBLE_PROVIDER_PRESETS, getModelProvider } from './model-providers'

export type ModelOption = Pick<ChatModelProfile, 'id' | 'name' | 'model'> &
  Partial<Pick<ChatModelProfile, 'provider' | 'baseUrl' | 'isDefault'>>

export interface ModelServiceGroup<T extends ModelOption> {
  id: string
  name: string
  providerName: string
  monogram: string
  location: string
  models: T[]
}

export function normalizeEndpoint(value: string): string {
  return value.trim().replace(/\/+$/, '')
}

export function findModelPreset(baseUrl: string, protocol?: ChatModelProvider) {
  return COMPATIBLE_PROVIDER_PRESETS.find(item =>
    normalizeEndpoint(item.baseUrl) === normalizeEndpoint(baseUrl) &&
    (!protocol || (item.provider ?? 'openai_compatible') === protocol))
}

export function modelServiceName(profile: ModelOption): string {
  // Earlier multi-model saves appended the model ID to each service name.
  const suffix = ` · ${profile.model}`
  const name = profile.name.trim()
  if (name.endsWith(suffix)) return name.slice(0, -suffix.length) || name
  // Previous saves truncated the combined label to 80 characters.
  const separator = name.lastIndexOf(' · ')
  if (name.length === 80 && separator > 0 &&
      `${name.slice(0, separator)}${suffix}`.slice(0, 80) === name) {
    return name.slice(0, separator)
  }
  return name || profile.model
}

function serviceLocation(baseUrl: string): string {
  if (!baseUrl) return ''
  try {
    const url = new URL(baseUrl)
    // A label must never reveal URL credentials, query parameters or fragments.
    return `${url.host}${url.pathname.replace(/\/+$/, '')}`
  } catch { return '' }
}

/** UI projection only: profile IDs and per-profile credentials remain independent. */
export function groupModelProfiles<T extends ModelOption>(profiles: readonly T[]): ModelServiceGroup<T>[] {
  const groups = new Map<string, ModelServiceGroup<T>>()
  for (const profile of profiles) {
    const name = modelServiceName(profile)
    const endpoint = normalizeEndpoint(profile.baseUrl || '')
    // Do not combine differently named accounts or different protocols/endpoints.
    const id = profile.provider ? JSON.stringify([profile.provider, endpoint, name]) : profile.id
    let group = groups.get(id)
    if (!group) {
      const definition = profile.provider ? getModelProvider(profile.provider) : null
      const preset = findModelPreset(endpoint, profile.provider)
      group = {
        id, name,
        providerName: preset?.name || definition?.name || name,
        monogram: preset?.monogram || definition?.monogram || 'M',
        location: serviceLocation(endpoint),
        models: [],
      }
      groups.set(id, group)
    }
    group.models.push(profile)
  }
  return [...groups.values()]
}
