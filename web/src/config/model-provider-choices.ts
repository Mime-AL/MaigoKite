import type { ChatModelProvider } from '@/api/client'

type ChoiceGroup = '云端服务' | '本地服务'

export interface ProviderChoice {
  id: string
  name: string
  description: string
  monogram: string
  provider: ChatModelProvider
  presetId?: string
  group: ChoiceGroup
}

export const providerChoices: ProviderChoice[] = [
  {
    id: 'deepseek',
    name: 'DeepSeek',
    description: '官方 API',
    monogram: 'DS',
    provider: 'openai_compatible',
    presetId: 'deepseek',
    group: '云端服务',
  },
  {
    id: 'openai',
    name: 'OpenAI',
    description: '官方 API',
    monogram: 'O',
    provider: 'openai',
    group: '云端服务',
  },
  {
    id: 'anthropic',
    name: 'Anthropic',
    description: 'Claude API',
    monogram: 'A',
    provider: 'anthropic',
    group: '云端服务',
  },
  {
    id: 'openrouter',
    name: 'OpenRouter',
    description: '多模型聚合服务',
    monogram: 'OR',
    provider: 'openai_compatible',
    presetId: 'openrouter',
    group: '云端服务',
  },
  {
    id: 'dashscope',
    name: '阿里云百炼',
    description: 'OpenAI 兼容 API',
    monogram: '百',
    provider: 'openai_compatible',
    presetId: 'dashscope',
    group: '云端服务',
  },
  {
    id: 'groq',
    name: 'Groq',
    description: 'GroqCloud API',
    monogram: 'G',
    provider: 'openai_compatible',
    presetId: 'groq',
    group: '云端服务',
  },
  {
    id: 'together',
    name: 'Together AI',
    description: '开源模型聚合服务',
    monogram: 'T',
    provider: 'openai_compatible',
    presetId: 'together',
    group: '云端服务',
  },
  {
    id: 'ollama',
    name: 'Ollama',
    description: '本机模型服务',
    monogram: 'OL',
    provider: 'ollama',
    group: '本地服务',
  },
  {
    id: 'lm-studio',
    name: 'LM Studio',
    description: '本机 OpenAI 兼容服务',
    monogram: 'LM',
    provider: 'openai_compatible',
    presetId: 'lm-studio',
    group: '本地服务',
  },
  {
    id: 'vllm',
    name: 'vLLM',
    description: '高吞吐本地推理',
    monogram: 'VL',
    provider: 'openai_compatible',
    presetId: 'vllm',
    group: '本地服务',
  },
  {
    id: 'llama-cpp',
    name: 'llama.cpp',
    description: '轻量本地服务器',
    monogram: 'LC',
    provider: 'openai_compatible',
    presetId: 'llama-cpp',
    group: '本地服务',
  },
  {
    id: 'custom',
    name: '自定义服务',
    description: '任意 OpenAI 兼容端点',
    monogram: '+',
    provider: 'openai_compatible',
    group: '本地服务',
  },
]

export const choiceGroups: ChoiceGroup[] = ['云端服务', '本地服务']
