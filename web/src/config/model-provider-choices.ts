import type { ChatModelProvider } from '@/api/client'
import { COMPATIBLE_PROVIDER_PRESETS, MODEL_PROVIDERS, type ModelProviderGroup } from './model-providers'

type ChoiceGroup = '云端服务' | '聚合平台' | '本地服务' | '中转与自定义'

export interface ProviderChoice {
  id: string
  name: string
  description: string
  monogram: string
  provider: ChatModelProvider
  presetId?: string
  group: ChoiceGroup
  custom?: boolean
}

const groupLabels: Record<ModelProviderGroup, ChoiceGroup> = {
  cloud: '云端服务',
  aggregate: '聚合平台',
  local: '本地服务',
}

// Cards and editor presets share connection metadata, never a model catalog.
export const providerChoices: ProviderChoice[] = [
  ...MODEL_PROVIDERS.filter((item) => item.id !== 'openai_compatible').map((item) => ({
    id: item.id,
    name: item.name,
    description: item.summary,
    monogram: item.monogram,
    provider: item.id,
    group: groupLabels[item.group],
  })),
  ...COMPATIBLE_PROVIDER_PRESETS.map((item): ProviderChoice => ({
    id: item.id,
    name: item.name,
    description: item.description,
    monogram: item.monogram,
    provider: item.provider ?? 'openai_compatible',
    presetId: item.id,
    group: groupLabels[item.group],
  })),
  {
    id: 'custom',
    name: '中转站 / 自定义（OpenAI）',
    description: 'New API、One API、LiteLLM 或自建兼容网关',
    monogram: '+',
    provider: 'openai_compatible',
    group: '中转与自定义',
    custom: true,
  },
  {
    id: 'custom-anthropic',
    name: '中转站 / 自定义（Anthropic）',
    description: 'Anthropic Messages 兼容网关',
    monogram: 'A',
    provider: 'anthropic',
    group: '中转与自定义',
    custom: true,
  },
]

export const choiceGroups: ChoiceGroup[] = ['云端服务', '聚合平台', '本地服务', '中转与自定义']
