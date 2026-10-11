import { t } from '@/i18n'
export interface SettingsField {
  id: string
  tab: string
  label: string
  keywords?: string
}
export const settingsFields: SettingsField[] = [
  { id: 'language', tab: 'general', label: '语言', keywords: 'language locale English' },
  { id: 'assistant-name', tab: 'general', label: '助手名字', keywords: 'name assistant' },
  { id: 'greeting-name', tab: 'general', label: '怎么称呼你', keywords: 'greeting name' },
  { id: 'avatar', tab: 'general', label: '头像字', keywords: 'avatar' },
  { id: 'theme', tab: 'general', label: '纸页', keywords: 'theme dark light' },
  { id: 'accent', tab: 'general', label: '强调色', keywords: 'accent color' },
  { id: 'text-size', tab: 'general', label: '字号', keywords: 'font text size' },
  { id: 'texture', tab: 'general', label: '纸纹', keywords: 'texture paper' },
  {
    id: 'context-usage',
    tab: 'general',
    label: '显示模型上下文窗口用量',
    keywords: 'context tokens',
  },
  { id: 'capsule-shortcut', tab: 'general', label: '速记快捷键', keywords: 'capsule shortcut' },
  { id: 'models', tab: 'models', label: '模型', keywords: 'provider default model' },
  {
    id: 'model-base-url',
    tab: 'models',
    label: '服务地址',
    keywords: 'base URL endpoint relay 中转站',
  },
  { id: 'model-api-key', tab: 'models', label: 'API Key', keywords: 'credential secret 密钥' },
  {
    id: 'model-selection',
    tab: 'models',
    label: '模型（可多选）',
    keywords: 'models catalog discover',
  },
  { id: 'tool-selection', tab: 'tools', label: '助手可用工具', keywords: 'tools' },
  { id: 'search-tools', tab: 'tools', label: '联网搜索', keywords: 'Tavily Google DuckDuckGo' },
  {
    id: 'permission-mode',
    tab: 'permissions',
    label: '执行权限',
    keywords: 'permission approval risk',
  },
  {
    id: 'runtime-status',
    tab: 'workspace',
    label: '运行状态',
    keywords: 'gateway core version 工作区 路径',
  },
]
export function searchSettings(query: string, fields = settingsFields) {
  const words = query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean)
  if (!words.length) return []
  return fields.filter((field) => {
    const text = `${field.label} ${t(field.label)} ${field.keywords || ''}`.toLocaleLowerCase()
    return words.every((word) => text.includes(word))
  })
}
