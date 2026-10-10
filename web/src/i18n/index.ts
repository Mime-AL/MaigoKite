import { createI18n } from 'vue-i18n'
import en from './locales/en'

export type Language = 'zh-CN' | 'en' | 'system'
export type Locale = Exclude<Language, 'system'>

export function resolveLanguage(language: Language | undefined, systemLanguage: string): Locale {
  if (language === 'system') return systemLanguage.toLowerCase().startsWith('zh') ? 'zh-CN' : 'en'
  return language || 'zh-CN'
}

// Source-keyed messages keep the existing Chinese copy and both catalogs in sync.
const zhCN = Object.fromEntries(Object.keys(en).map((key) => [key, key]))
export const i18n = createI18n({
  legacy: false,
  globalInjection: true,
  locale: 'zh-CN',
  fallbackLocale: 'zh-CN',
  messages: { 'zh-CN': zhCN, en },
})
export const t = i18n.global.t
