import type { ChatModelProvider, ChatModelSettings } from '@/api/client'

export type ModelProviderGroup = 'cloud' | 'local'
export type ApiKeyMode = 'required' | 'optional' | 'none'

export interface ModelProviderDefinition {
  id: ChatModelProvider
  name: string
  monogram: string
  group: ModelProviderGroup
  summary: string
  description: string
  modelPlaceholder: string
  baseUrlLabel: string
  baseUrlPlaceholder: string
  baseUrlHelp: string
  defaultBaseUrl: string
  apiKeyMode: ApiKeyMode
  recommendedModels: string[]
}

export interface CompatibleProviderPreset {
  id: string
  name: string
  description: string
  baseUrl: string
  model: string
  models: string[]
}

export const MODEL_PROVIDER_GROUPS: Array<{ id: ModelProviderGroup; label: string }> = [
  { id: 'cloud', label: '云端服务' },
  { id: 'local', label: '本地与兼容服务' },
]

export const MODEL_PROVIDERS: ModelProviderDefinition[] = [
  {
    id: 'openai',
    name: 'OpenAI',
    monogram: 'O',
    group: 'cloud',
    summary: '官方 API',
    description: '使用 OpenAI 官方接口，或通过可选 Base URL 接入企业代理。',
    modelPlaceholder: '输入你的账号可用的模型 ID',
    baseUrlLabel: 'API Base URL（可选）',
    baseUrlPlaceholder: '留空使用 OpenAI 官方地址',
    baseUrlHelp: '使用官方 API 时留空；只有企业代理或私有网关需要填写。',
    defaultBaseUrl: '',
    apiKeyMode: 'required',
    recommendedModels: ['gpt-5.6-sol', 'gpt-5.6-terra', 'gpt-5.6-luna', 'gpt-5.2', 'gpt-5-mini'],
  },
  {
    id: 'anthropic',
    name: 'Anthropic',
    monogram: 'A',
    group: 'cloud',
    summary: 'Claude API',
    description: '连接 Anthropic Claude API，也支持通过 Base URL 使用企业代理。',
    modelPlaceholder: '输入你的账号可用的 Claude 模型 ID',
    baseUrlLabel: 'API Base URL（可选）',
    baseUrlPlaceholder: '留空使用 Anthropic 官方地址',
    baseUrlHelp: '使用官方 API 时留空；只有企业代理或私有网关需要填写。',
    defaultBaseUrl: '',
    apiKeyMode: 'required',
    recommendedModels: [
      'claude-sonnet-5',
      'claude-opus-5',
      'claude-fable-5',
      'claude-sonnet-4-6',
      'claude-haiku-4-5-20251001',
    ],
  },
  {
    id: 'openai_compatible',
    name: 'OpenAI Compatible',
    monogram: 'C',
    group: 'local',
    summary: '自定义服务',
    description: '连接 DeepSeek、OpenRouter、LM Studio、vLLM 或其他 OpenAI 兼容端点。',
    modelPlaceholder: '输入服务端提供的模型 ID',
    baseUrlLabel: 'API Base URL',
    baseUrlPlaceholder: 'https://example.com/v1',
    baseUrlHelp: '必须填写完整的 HTTP(S) 地址；通常以 /v1 结尾。',
    defaultBaseUrl: 'http://127.0.0.1:1234/v1',
    apiKeyMode: 'optional',
    recommendedModels: [],
  },
  {
    id: 'ollama',
    name: 'Ollama',
    monogram: 'OL',
    group: 'local',
    summary: '本机运行',
    description: '连接当前设备上的 Ollama 服务，模型与数据无需离开本机。',
    modelPlaceholder: '例如 qwen3.5、gpt-oss:20b',
    baseUrlLabel: 'Ollama 地址',
    baseUrlPlaceholder: 'http://127.0.0.1:11434',
    baseUrlHelp: '默认端口为 11434；远程 Ollama 也可以填写局域网地址。',
    defaultBaseUrl: 'http://127.0.0.1:11434',
    apiKeyMode: 'none',
    recommendedModels: ['qwen3.5', 'gemma3', 'gpt-oss:20b', 'deepseek-r1', 'qwen3-coder', 'devstral'],
  },
]

export const COMPATIBLE_PROVIDER_PRESETS: CompatibleProviderPreset[] = [
  {
    id: 'deepseek',
    name: 'DeepSeek',
    description: '官方 OpenAI 兼容 API',
    baseUrl: 'https://api.deepseek.com',
    model: '',
    models: [],
  },
  {
    id: 'openrouter',
    name: 'OpenRouter',
    description: '多模型聚合服务',
    baseUrl: 'https://openrouter.ai/api/v1',
    model: '',
    models: [],
  },
  {
    id: 'dashscope',
    name: '阿里云百炼',
    description: '北京地域 OpenAI 兼容 API',
    baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    model: '',
    models: [],
  },
  {
    id: 'groq',
    name: 'Groq',
    description: 'GroqCloud OpenAI 兼容 API',
    baseUrl: 'https://api.groq.com/openai/v1',
    model: '',
    models: [],
  },
  {
    id: 'together',
    name: 'Together AI',
    description: '开源模型聚合服务',
    baseUrl: 'https://api.together.ai/v1',
    model: '',
    models: [],
  },
  {
    id: 'lm-studio',
    name: 'LM Studio',
    description: '默认本地端口',
    baseUrl: 'http://127.0.0.1:1234/v1',
    model: '',
    models: [],
  },
  {
    id: 'vllm',
    name: 'vLLM',
    description: '默认本地端口',
    baseUrl: 'http://127.0.0.1:8000/v1',
    model: '',
    models: [],
  },
  {
    id: 'llama-cpp',
    name: 'llama.cpp',
    description: 'OpenAI 兼容本地服务器',
    baseUrl: 'http://127.0.0.1:8080/v1',
    model: '',
    models: [],
  },
]

export function getModelProvider(provider: ChatModelProvider): ModelProviderDefinition {
  return MODEL_PROVIDERS.find(item => item.id === provider) ?? MODEL_PROVIDERS[0]
}

export function createProviderDraft(
  provider: ChatModelProvider,
  current?: ChatModelSettings,
): ChatModelSettings {
  if (current?.provider === provider) return { ...current }
  const definition = getModelProvider(provider)
  return {
    provider,
    model: '',
    baseUrl: definition.defaultBaseUrl,
    temperature: current?.temperature ?? 0.7,
    maxTokens: current?.maxTokens ?? 4096,
    timeoutSeconds: current?.timeoutSeconds ?? 60,
    credentialConfigured: false,
  }
}

export function modelSettingsFingerprint(settings: ChatModelSettings): string {
  return JSON.stringify({
    provider: settings.provider,
    model: settings.model.trim(),
    baseUrl: settings.baseUrl.trim().replace(/\/$/, ''),
    temperature: settings.temperature,
    maxTokens: settings.maxTokens,
    timeoutSeconds: settings.timeoutSeconds,
  })
}
