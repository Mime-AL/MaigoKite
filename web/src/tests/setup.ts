import { config } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, vi } from 'vitest'
import { i18n } from '@/i18n'

// Mount with the same language plugin as main.ts; each test owns its store scope.
config.global.plugins.push(i18n)
beforeEach(() => {
  setActivePinia(createPinia())
  i18n.global.locale.value = 'zh-CN'
})

afterEach(() => {
  vi.restoreAllMocks()
})
