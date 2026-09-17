import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api } from '@/api/client'
import PermissionSettingsPanel from '@/components/settings/PermissionSettingsPanel.vue'
import { useSettingsStore } from '@/stores/settings'

describe('permission settings', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    setActivePinia(createPinia())
  })

  it('shows three clear profiles and keeps internal risk baselines out of the UI', async () => {
    const store = useSettingsStore()
    store.permissions = { default_mode: 'workspace' }
    vi.spyOn(api, 'updatePermissionSettings').mockImplementation(async value => value)
    const wrapper = mount(PermissionSettingsPanel)

    for (const label of ['只读', '工作区', '完全访问', '推荐']) {
      expect(wrapper.text()).toContain(label)
    }
    expect(wrapper.text()).not.toContain('L1')
    await wrapper.findAll('.mode-grid button')[0].trigger('click')
    await wrapper.get('footer button').trigger('click')

    expect(api.updatePermissionSettings).toHaveBeenCalledWith({ default_mode: 'read_only' })
  })
})
