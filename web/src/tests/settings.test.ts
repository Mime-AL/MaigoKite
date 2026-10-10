import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createMemoryHistory, createRouter } from 'vue-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api, type ChatModelProfile, type ChatModelSettings } from '@/api/client'
import { useSettingsStore } from '@/stores/settings'
import Settings from '@/views/Settings.vue'

const localSettings: ChatModelSettings = {
  provider: 'openai_compatible',
  model: 'local-model',
  baseUrl: 'http://127.0.0.1:1234/v1',
  temperature: 0.7,
  maxTokens: 4096,
  timeoutSeconds: 60,
  credentialConfigured: false,
}

describe('settings store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
    localStorage.clear()
  })

  it('loads and saves the per-user assistant name', async () => {
    vi.spyOn(api, 'getUserPreferences').mockResolvedValue({ assistantName: '小七' })
    const update = vi.spyOn(api, 'updateUserPreferences').mockResolvedValue({ assistantName: '小七 Agent' })
    const store = useSettingsStore()

    await store.loadPreferences()
    expect(store.profile.assistantName).toBe('小七')

    const saved = await store.savePreferences('小七 Agent')
    expect(saved).toBe(true)
    expect(update).toHaveBeenCalledWith({ assistantName: '小七 Agent' })
    expect(store.profile.assistantName).toBe('小七 Agent')
    expect(localStorage.getItem('maigokite_user_preferences')).toContain('小七 Agent')
  })

  it('loads persisted model settings from the application service', async () => {
    const profile: ChatModelProfile = { ...localSettings, id: 'model_local', name: 'Local', isDefault: true }
    vi.spyOn(api, 'listChatModels').mockResolvedValue({ models: [profile], defaultModelId: profile.id })
    vi.spyOn(api, 'listCredentialReferences').mockResolvedValue([])
    const store = useSettingsStore()

    await store.loadSettings()

    expect(store.modelProfiles).toEqual([profile])
    expect(store.defaultModelId).toBe(profile.id)
    expect(store.loaded).toBe(true)
  })

  it('saves credentials in a model-profile-scoped request', async () => {
    const cloudSettings: ChatModelProfile = {
      ...localSettings,
      id: 'model_cloud',
      name: 'Cloud',
      provider: 'openai',
      model: 'gpt-test',
      baseUrl: '',
      isDefault: true,
    }
    const save = vi.spyOn(api, 'saveChatModel').mockResolvedValue({ ...cloudSettings, credentialConfigured: true })
    const store = useSettingsStore()

    const saved = await store.saveModelProfile(cloudSettings, 'secret-key')

    expect(saved?.id).toBe('model_cloud')
    expect(save).toHaveBeenCalledWith(cloudSettings, 'secret-key')
    expect(store.success).toContain('已保存')
  })

  it('presents settings without release phases or the internal project name', async () => {
    const pinia = createPinia()
    setActivePinia(pinia)
    vi.spyOn(api, 'listChatModels').mockResolvedValue({ models: [], defaultModelId: '' })
    vi.spyOn(api, 'listCredentialReferences').mockResolvedValue([])
    vi.spyOn(api, 'getUserPreferences').mockResolvedValue({ assistantName: '小七' })
    vi.spyOn(api, 'getPermissionSettings').mockResolvedValue({ default_mode: 'workspace' })
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [{ path: '/settings', component: Settings }],
    })
    await router.push('/settings')
    await router.isReady()

    const wrapper = mount(Settings, { global: { plugins: [pinia, router] } })
    await flushPromises()

    expect(wrapper.text()).toContain('管理助手称呼、模型、联网工具和执行权限')
    expect(wrapper.text()).not.toContain('Phase 1')
    expect(wrapper.text()).not.toContain('MaigoKite')
  })
})
