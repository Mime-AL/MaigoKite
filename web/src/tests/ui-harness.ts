import { createMemoryHistory, createRouter } from 'vue-router'
import { afterEach, vi } from 'vitest'

/** Use the real router so route-dependent components and RouterLink keep their contract. */
export async function testRouter(path = '/') {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: '/:pathMatch(.*)*', component: { template: '<div />' } }],
  })
  await router.push(path)
  await router.isReady()
  return router
}

/** Only polyfill APIs absent in jsdom; keep modal open/close observable. */
export function mockDialogs() {
  const targets = [
    [HTMLDialogElement.prototype, 'showModal', function (this: HTMLDialogElement) { this.open = true }],
    [HTMLDialogElement.prototype, 'close', function (this: HTMLDialogElement) { this.open = false }],
    [HTMLElement.prototype, 'scrollIntoView', vi.fn()],
  ] as const
  for (const [target, key, value] of targets) {
    const original = Object.getOwnPropertyDescriptor(target, key)
    Object.defineProperty(target, key, { configurable: true, value })
    restores.push(() => {
      if (original) Object.defineProperty(target, key, original)
      else Reflect.deleteProperty(target, key)
    })
  }
  // jsdom has no layout/scroll implementation.
  vi.stubGlobal('ResizeObserver', class { observe() {} unobserve() {} disconnect() {} })
}
const restores: (() => void)[] = []
afterEach(() => { for (const restore of restores.splice(0).reverse()) restore() })
