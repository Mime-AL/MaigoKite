import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api, type ChatModelProfile } from '@/api/client'
import ModelSettingsPanel from '@/components/settings/ModelSettingsPanel.vue'
import { createProviderDraft, modelSettingsFingerprint } from '@/config/model-providers'
import { useSettingsStore } from '@/stores/settings'

const cloudProfile: ChatModelProfile = {
  id: 'model_cloud',
  name: 'Cloud',
  provider: 'openai',
  model: 'cloud-model',
  baseUrl: '',
  temperature: 0.4,
  maxTokens: 2048,
  timeoutSeconds: 45,
  credentialConfigured: true,
  isDefault: true,
}

describe('model settings', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
    localStorage.clear()
  })

  it('keeps several profiles and starts a new provider with an isolated endpoint', async () => {
    const store = useSettingsStore()
    store.modelProfiles = [cloudProfile]
    store.defaultModelId = cloudProfile.id
    const wrapper = mount(ModelSettingsPanel)

    expect(wrapper.find('form').exists()).toBe(false)
    expect(wrapper.text()).toContain('Cloud')

    await wrapper.get('[data-testid="add-model"]').trigger('click')
    expect(wrapper.get('[data-testid="provider-picker"]').text()).toContain('DeepSeek')
    await wrapper.get('[data-provider-choice="custom"]').trigger('click')

    expect((wrapper.get('[data-testid="model-id"]').element as HTMLInputElement).value).toBe('')
    expect((wrapper.get('[data-testid="base-url"]').element as HTMLInputElement).value).toBe(
      'http://127.0.0.1:1234/v1',
    )
    expect(store.modelProfiles).toHaveLength(1)
  })

  it('clears an obsolete connection result when the draft changes', async () => {
    const store = useSettingsStore()
    store.validation = { ok: true, message: '连接成功' }
    const wrapper = mount(ModelSettingsPanel)

    await wrapper.get('[data-testid="add-model"]').trigger('click')
    await wrapper.get('[data-provider-choice="ollama"]').trigger('click')
    await wrapper.get('[data-testid="model-id"]').setValue('another-model')

    expect(store.validation).toBeNull()
  })

  it('requires a new key before moving a credentialed profile to another endpoint', async () => {
    const store = useSettingsStore()
    store.modelProfiles = [
      {
        id: 'model_compatible',
        name: 'Compatible',
        provider: 'openai_compatible',
        model: 'old-model',
        baseUrl: 'https://old-gateway.example/v1',
        temperature: 0.7,
        maxTokens: 4096,
        timeoutSeconds: 60,
        credentialConfigured: true,
        isDefault: true,
      },
    ]
    store.defaultModelId = 'model_compatible'
    const wrapper = mount(ModelSettingsPanel)

    await wrapper.get('.profile-main').trigger('click')
    await wrapper.get('[data-testid="base-url"]').setValue('https://api.deepseek.com')

    expect(wrapper.text()).toContain('旧 Key 不会发送到新端点')
    expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeDefined()
  })

  it('creates a named profile and keeps the save confirmation', async () => {
    const store = useSettingsStore()
    vi.spyOn(api, 'saveChatModel').mockImplementation(async (profile) => ({
      ...profile,
      id: 'model_local',
      isDefault: true,
    }))
    const wrapper = mount(ModelSettingsPanel)

    await wrapper.get('[data-testid="add-model"]').trigger('click')
    await wrapper.get('[data-provider-choice="ollama"]').trigger('click')
    await wrapper.get('[data-testid="profile-name"]').setValue('Local Qwen')
    await wrapper.get('[data-testid="model-id"]').setValue('local-model')
    await wrapper.get('form').trigger('submit')

    expect(store.success).toContain('Local Qwen')
    expect(store.modelProfiles).toHaveLength(1)
  })

  it('creates isolated defaults and normalizes a trailing slash in dirty checks', () => {
    const local = createProviderDraft('ollama', cloudProfile)
    expect(local.model).toBe('')
    expect(local.baseUrl).toBe('http://127.0.0.1:11434')
    expect(local.credentialConfigured).toBe(false)
    expect(modelSettingsFingerprint({ ...local, baseUrl: 'http://127.0.0.1:11434/' })).toBe(
      modelSettingsFingerprint(local),
    )
  })

  it('offers model recommendations without preventing a custom model id', async () => {
    const wrapper = mount(ModelSettingsPanel)
    await wrapper.get('[data-testid="add-model"]').trigger('click')
    await wrapper.get('[data-provider-choice="ollama"]').trigger('click')
    await wrapper.get('[data-testid="browse-models"]').trigger('click')
    expect(wrapper.text()).toContain('qwen3.5')
    await wrapper.get('button[aria-label="关闭模型目录"]').trigger('click')
    await wrapper.get('[data-testid="model-id"]').setValue('my-private-model')
    expect((wrapper.get('[data-testid="model-id"]').element as HTMLInputElement).value).toBe(
      'my-private-model',
    )
  })

  it('discovers models from the configured Base URL without exposing generation tuning', async () => {
    vi.spyOn(api, 'discoverChatModels').mockResolvedValue([
      { id: 'qwen3:8b', name: 'Qwen 3', context_window: 32768, details: 'qwen3 · 8B' },
    ])
    const wrapper = mount(ModelSettingsPanel)

    await wrapper.get('[data-testid="add-model"]').trigger('click')
    await wrapper.get('[data-provider-choice="ollama"]').trigger('click')
    await wrapper.get('[data-testid="discover-models"]').trigger('click')
    await flushPromises()

    expect(api.discoverChatModels).toHaveBeenCalledWith(
      expect.objectContaining({
        provider: 'ollama',
        baseUrl: 'http://127.0.0.1:11434',
      }),
      '',
    )
    expect((wrapper.get('[data-testid="model-id"]').element as HTMLInputElement).value).toBe('')
    expect(wrapper.get('[data-testid="model-catalog"]').isVisible()).toBe(true)
    expect(wrapper.text()).toContain('已从服务端获取 1 个模型')
    expect(wrapper.text()).toContain('32,768 Token 上下文')
    await wrapper.get('[data-model-id="qwen3:8b"]').trigger('click')
    await wrapper.get('[data-testid="catalog-apply"]').trigger('click')
    expect((wrapper.get('[data-testid="model-id"]').element as HTMLInputElement).value).toBe(
      'qwen3:8b',
    )
    expect(wrapper.text()).not.toContain('高级生成参数')
  })

  it('searches the fetched catalog and applies the choice only after confirmation', async () => {
    vi.spyOn(api, 'discoverChatModels').mockResolvedValue([
      { id: 'alpha-chat', name: 'Alpha Chat' },
      { id: 'beta-code', name: 'Beta Code' },
    ])
    const wrapper = mount(ModelSettingsPanel)

    await wrapper.get('[data-testid="add-model"]').trigger('click')
    await wrapper.get('[data-provider-choice="ollama"]').trigger('click')
    await wrapper.get('[data-testid="discover-models"]').trigger('click')
    await flushPromises()
    await wrapper.get('[data-testid="catalog-search"]').setValue('beta')

    expect(wrapper.find('[data-model-id="alpha-chat"]').exists()).toBe(false)
    expect(wrapper.find('[data-model-id="beta-code"]').exists()).toBe(true)
    expect((wrapper.get('[data-testid="model-id"]').element as HTMLInputElement).value).toBe('')

    await wrapper.get('[data-model-id="beta-code"]').trigger('click')
    await wrapper.get('[data-testid="catalog-apply"]').trigger('click')
    expect((wrapper.get('[data-testid="model-id"]').element as HTMLInputElement).value).toBe(
      'beta-code',
    )
  })
})
