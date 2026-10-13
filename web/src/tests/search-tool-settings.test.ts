import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api } from '@/api/client'
import SearchToolSettingsPanel from '@/components/settings/SearchToolSettingsPanel.vue'
import { useSettingsStore } from '@/stores/settings'

describe('search tool settings', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    setActivePinia(createPinia())
  })

  it('saves Tavily through the credential reference API without echoing the secret', async () => {
    const save = vi.spyOn(api, 'saveCredential').mockResolvedValue()
    const store = useSettingsStore()
    const wrapper = mount(SearchToolSettingsPanel)

    await wrapper.find('input[type="password"]').setValue('tvly-secret-key')
    await wrapper.find('.credential-form .primary-button').trigger('click')
    await flushPromises()

    expect(save).toHaveBeenCalledWith('tavily', 'tvly-secret-key')
    expect(store.credentials.tavily.configured).toBe(true)
    expect((wrapper.find('input[type="password"]').element as HTMLInputElement).value).toBe('')
    expect(wrapper.html()).not.toContain('tvly-secret-key')
  })

  it('stores Google key and CX as one opaque credential', async () => {
    const save = vi.spyOn(api, 'saveCredential').mockResolvedValue()
    const wrapper = mount(SearchToolSettingsPanel)
    const fields = wrapper.findAll('.google-form input')

    await fields[0].setValue('google-secret-key')
    await fields[1].setValue('custom-search-id')
    await wrapper.get('.google-form .primary-button').trigger('click')
    await flushPromises()

    expect(save).toHaveBeenCalledWith('google', 'google-secret-key:custom-search-id')
  })

  it('does not expose credential-storage implementation details', () => {
    const wrapper = mount(SearchToolSettingsPanel)

    expect(wrapper.text()).not.toContain('操作系统密钥链')
    expect(wrapper.text()).not.toContain('Secret')
  })
})
