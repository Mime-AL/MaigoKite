import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useLayoutStore } from '@/stores/layout'

describe('layout store', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('does not synchronously persist every drag update', () => {
    const setItem = vi.spyOn(Storage.prototype, 'setItem')
    const store = useLayoutStore()

    store.setSidebarWidth(280)
    store.setSidebarWidth(300)
    expect(setItem).not.toHaveBeenCalled()

    store.persistLayout()
    expect(setItem).toHaveBeenCalledTimes(4)
    expect(store.sidebarWidth).toBe(300)
  })
})
