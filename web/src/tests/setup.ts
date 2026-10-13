import { config, enableAutoUnmount } from '@vue/test-utils'
import { createPinia, disposePinia, getActivePinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, onTestFinished, vi } from 'vitest'
import { i18n } from '@/i18n'
// jsdom lacks native dialog lifecycle. Keep a stable base polyfill so file-local
// fixtures can restore it before auto-unmount without breaking cleanup.
if (typeof HTMLDialogElement !== 'undefined') {
  if (!HTMLDialogElement.prototype.showModal) Object.defineProperty(HTMLDialogElement.prototype, 'showModal', { configurable: true, value: function (this: HTMLDialogElement) { this.open = true } })
  if (!HTMLDialogElement.prototype.close) Object.defineProperty(HTMLDialogElement.prototype, 'close', { configurable: true, value: function (this: HTMLDialogElement) { this.open = false } })
}

// Mount with the same language plugin as main.ts; each test owns its store scope.
config.global.plugins.push(i18n)
enableAutoUnmount(afterEach)
beforeEach(() => {
  setActivePinia(createPinia())
  i18n.global.locale.value = 'zh-CN'
  if (typeof localStorage !== 'undefined') localStorage.clear()
  if (typeof sessionStorage !== 'undefined') sessionStorage.clear()
  // File-local cleanup (disconnect, wrapper assertions) must run before disposal.
  onTestFinished(() => {
    const pinia = getActivePinia()
    if (pinia) disposePinia(pinia)
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })
})
