import type { ChatModelProvider, ChatModelSettings } from '@/api/client'

export type ModelProviderGroup = 'cloud' | 'aggregate' | 'local'
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
}

export interface CompatibleProviderPreset {
  id: string
  name: string
  description: string
  baseUrl: string
  monogram: string
  group: ModelProviderGroup
  apiKeyMode: ApiKeyMode
  provider?: ChatModelProvider
  docsUrl?: string
}

export const MODEL_PROVIDER_GROUPS: Array<{ id: ModelProviderGroup; label: string }> = [
  { id: 'cloud', label: '云端服务' },
  { id: 'aggregate', label: '聚合平台' },
  { id: 'local', label: '本地与兼容服务' },
]

export const MODEL_PROVIDERS: ModelProviderDefinition[] = [
  {
    id: 'openai',
    name: 'OpenAI',
    monogram: 'O',
    group: 'cloud',
    summary: '官方 API',
    description: 'OpenAI 官方服务',
    modelPlaceholder: '输入你的账号可用的模型 ID',
    baseUrlLabel: 'API Base URL（可选）',
    baseUrlPlaceholder: '留空使用 OpenAI 官方地址',
    baseUrlHelp: '使用官方 API 时留空；只有企业代理或私有网关需要填写。',
    defaultBaseUrl: '',
    apiKeyMode: 'required',
  },
  {
    id: 'anthropic',
    name: 'Anthropic',
    monogram: 'A',
    group: 'cloud',
    summary: 'Claude API',
    description: 'Anthropic 官方服务',
    modelPlaceholder: '输入你的账号可用的 Claude 模型 ID',
    baseUrlLabel: 'API Base URL（可选）',
    baseUrlPlaceholder: '留空使用 Anthropic 官方地址',
    baseUrlHelp: '使用官方 API 时留空；只有企业代理或私有网关需要填写。',
    defaultBaseUrl: '',
    apiKeyMode: 'required',
  },
  {
    id: 'openai_compatible',
    name: 'OpenAI Compatible',
    monogram: 'C',
    group: 'local',
    summary: '自定义服务',
    description: 'OpenAI 兼容服务或中转站',
    modelPlaceholder: '输入服务端提供的模型 ID',
    baseUrlLabel: 'API Base URL',
    baseUrlPlaceholder: 'https://example.com/v1',
    baseUrlHelp: '必须填写完整的 HTTP(S) 地址；通常以 /v1 结尾。',
    defaultBaseUrl: 'http://127.0.0.1:1234/v1',
    apiKeyMode: 'optional',
  },
  {
    id: 'ollama',
    name: 'Ollama',
    monogram: 'OL',
    group: 'local',
    summary: '本机运行',
    description: '本地或远程 Ollama',
    modelPlaceholder: '选择已安装的模型，或输入模型 ID',
    baseUrlLabel: 'Ollama 地址',
    baseUrlPlaceholder: 'http://127.0.0.1:11434',
    baseUrlHelp: '默认端口为 11434；远程 Ollama 也可以填写局域网地址。',
    defaultBaseUrl: 'http://127.0.0.1:11434',
    apiKeyMode: 'none',
  },
]

export const COMPATIBLE_PROVIDER_PRESETS: CompatibleProviderPreset[] = [
  {
    id: 'deepseek',
    name: 'DeepSeek',
    description: '官方 OpenAI 兼容 API',
    baseUrl: 'https://api.deepseek.com',
    monogram: 'DS', group: 'cloud', apiKeyMode: 'required',
  },
  {
    id: 'openrouter',
    name: 'OpenRouter',
    description: '多模型聚合服务',
    baseUrl: 'https://openrouter.ai/api/v1',
    monogram: 'OR', group: 'aggregate', apiKeyMode: 'required',
  },
  {
    id: 'dashscope',
    name: '阿里云百炼',
    description: '北京地域 OpenAI 兼容 API',
    baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    monogram: '百', group: 'cloud', apiKeyMode: 'required',
  },
  {
    id: 'groq',
    name: 'Groq',
    description: 'GroqCloud OpenAI 兼容 API',
    baseUrl: 'https://api.groq.com/openai/v1',
    monogram: 'G', group: 'aggregate', apiKeyMode: 'required',
  },
  {
    id: 'together',
    name: 'Together AI',
    description: '开源模型聚合服务',
    baseUrl: 'https://api.together.ai/v1',
    monogram: 'T', group: 'aggregate', apiKeyMode: 'required',
  },
  {
    id: 'moonshot', name: 'Kimi / Moonshot', description: '月之暗面官方 API',
    baseUrl: 'https://api.moonshot.cn/v1',
    monogram: 'K', group: 'cloud', apiKeyMode: 'required',
    docsUrl: 'https://platform.kimi.com/blog/posts/kimi-api-quick-start-guide',
  },
  {
    id: 'mimo', name: '小米 MiMo', description: '按量付费 OpenAI 兼容 API',
    baseUrl: 'https://api.xiaomimimo.com/v1',
    monogram: 'MI', group: 'cloud', apiKeyMode: 'required',
    docsUrl: 'https://github.com/XiaomiMiMo/awesome-mimo-agent/blob/main/docs/pi_mono.zh-CN.md',
  },
  {
    id: 'mimo-token-plan', name: '小米 MiMo · Token Plan', description: '中国集群订阅接口，使用套餐专属 Key',
    baseUrl: 'https://token-plan-cn.xiaomimimo.com/v1',
    monogram: 'MI', group: 'cloud', apiKeyMode: 'required',
    docsUrl: 'https://github.com/XiaomiMiMo/awesome-mimo-agent/blob/main/docs/pi_mono.zh-CN.md',
  },
  {
    id: 'zhipu', name: '智谱 GLM', description: '智谱开放平台标准 API',
    baseUrl: 'https://open.bigmodel.cn/api/paas/v4',
    monogram: '智', group: 'cloud', apiKeyMode: 'required',
    docsUrl: 'https://docs.bigmodel.cn/cn/guide/develop/openai/introduction',
  },
  {
    id: 'minimax', name: 'MiniMax', description: 'MiniMax 国内标准 API',
    baseUrl: 'https://api.minimax.cn/v1',
    monogram: 'MM', group: 'cloud', apiKeyMode: 'required',
    docsUrl: 'https://platform.minimax.cn/docs/api-reference/text-openai-api',
  },
  {
    id: 'volcengine', name: '火山方舟 / 豆包', description: '北京地域 OpenAI 兼容 API',
    baseUrl: 'https://ark.cn-beijing.volces.com/api/v3',
    monogram: '火', group: 'cloud', apiKeyMode: 'required',
    docsUrl: 'https://docs.volcengine.com/docs/ark/compatible-with-openai-sdk?lang=zh',
  },
  {
    id: 'qianfan', name: '百度千帆', description: '千帆 v2 API Key 接口',
    baseUrl: 'https://qianfan.baidubce.com/v2',
    monogram: '千', group: 'cloud', apiKeyMode: 'required',
    docsUrl: 'https://cloud.baidu.com/doc/qianfan-api/s/3m7of64lb',
  },
  {
    id: 'gemini', name: 'Google Gemini', description: 'Gemini 官方 OpenAI 兼容接口',
    baseUrl: 'https://generativelanguage.googleapis.com/v1beta/openai',
    monogram: 'GE', group: 'cloud', apiKeyMode: 'required',
    docsUrl: 'https://ai.google.dev/gemini-api/docs/openai',
  },
  {
    id: 'mistral', name: 'Mistral AI', description: 'Mistral 官方 API',
    baseUrl: 'https://api.mistral.ai/v1',
    monogram: 'M', group: 'cloud', apiKeyMode: 'required',
    docsUrl: 'https://docs.mistral.ai/resources/migration-guides',
  },
  {
    id: 'xai', name: 'xAI / Grok', description: 'Grok 官方 API',
    baseUrl: 'https://api.x.ai/v1',
    monogram: 'X', group: 'cloud', apiKeyMode: 'required',
    docsUrl: 'https://docs.x.ai/overview',
  },
  {
    id: 'siliconflow', name: '硅基流动', description: '国内多模型推理平台',
    baseUrl: 'https://api.siliconflow.cn/v1',
    monogram: '硅', group: 'aggregate', apiKeyMode: 'required',
    docsUrl: 'https://docs.siliconflow.cn/docs/userguide/quickstart',
  },
  {
    id: 'fireworks', name: 'Fireworks AI', description: '多模型推理平台',
    baseUrl: 'https://api.fireworks.ai/inference/v1',
    monogram: 'FW', group: 'aggregate', apiKeyMode: 'required',
    docsUrl: 'https://docs.fireworks.ai/tools-sdks/openai-compatibility',
  },
  {
    id: 'deepinfra', name: 'DeepInfra', description: '多模型 OpenAI 兼容推理',
    baseUrl: 'https://api.deepinfra.com/v1/openai',
    monogram: 'DI', group: 'aggregate', apiKeyMode: 'required',
    docsUrl: 'https://docs.deepinfra.com/chat/overview',
  },
  {
    id: 'nvidia', name: 'NVIDIA NIM', description: 'NVIDIA API Catalog 托管接口',
    baseUrl: 'https://integrate.api.nvidia.com/v1',
    monogram: 'NV', group: 'aggregate', apiKeyMode: 'required',
    docsUrl: 'https://docs.nvidia.com/openshell/dev/how-it-works/providers/overview',
  },
  {
    id: 'lm-studio',
    name: 'LM Studio',
    description: '默认本地端口',
    baseUrl: 'http://127.0.0.1:1234/v1',
    monogram: 'LM', group: 'local', apiKeyMode: 'optional',
  },
  {
    id: 'vllm',
    name: 'vLLM',
    description: '默认本地端口',
    baseUrl: 'http://127.0.0.1:8000/v1',
    monogram: 'VL', group: 'local', apiKeyMode: 'optional',
  },
  {
    id: 'llama-cpp',
    name: 'llama.cpp',
    description: 'OpenAI 兼容本地服务器',
    baseUrl: 'http://127.0.0.1:8080/v1',
    monogram: 'LC', group: 'local', apiKeyMode: 'optional',
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
