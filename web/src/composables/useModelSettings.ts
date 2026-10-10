import { computed, reactive, ref, watch } from 'vue'
import { COMPATIBLE_PROVIDER_PRESETS, getModelProvider, modelSettingsFingerprint } from '@/config/model-providers'
import { useSettingsStore } from '@/stores/settings'
import { api, type ChatModelProfile, type ChatModelProvider, type DiscoveredChatModel } from '@/api/client'

import { type ProviderChoice } from '@/config/model-provider-choices'

type PanelMode = 'list' | 'providers' | 'editor'

// The existing model editor keeps the same Gateway requests and credential rules.
export function useModelSettings() {
  const settings = useSettingsStore()
  const mode = ref<PanelMode>('list')
  const selectedId = ref('')
  const apiKey = ref('')
  const revealKey = ref(false)
  const discoveredModels = ref<DiscoveredChatModel[]>([])
  const discovering = ref(false)
  const discoveryMessage = ref('')
  const catalogOpen = ref(false)

  const cloudPresetIds = new Set(['deepseek', 'openrouter', 'dashscope', 'groq', 'together'])

  function blankProfile(): ChatModelProfile {
    return {
      id: '',
      name: '',
      provider: 'ollama',
      model: '',
      baseUrl: 'http://127.0.0.1:11434',
      temperature: 0.7,
      maxTokens: 4096,
      timeoutSeconds: 60,
      credentialConfigured: false,
      isDefault: false,
    }
  }

  const draft = reactive<ChatModelProfile>(blankProfile())
  const original = ref<ChatModelProfile | null>(null)
  const provider = computed(() => getModelProvider(draft.provider))
  const compatiblePreset = computed(() => findPreset(draft.baseUrl))
  const displayProviderName = computed(() => compatiblePreset.value?.name ?? provider.value.name)
  const recommendedModels = computed(() =>
    compatiblePreset.value?.models.length ? compatiblePreset.value.models : provider.value.recommendedModels,
  )
  const modelOptions = computed<DiscoveredChatModel[]>(() =>
    discoveredModels.value.length ? discoveredModels.value : recommendedModels.value.map((id) => ({ id, name: id })),
  )
  const selectedModelInfo = computed(() => {
    const item = discoveredModels.value.find((model) => model.id === draft.model)
    if (!item) return ''
    return [
      item.owned_by,
      item.context_window ? `${item.context_window.toLocaleString('en-US')} Token 上下文` : '',
      item.details,
    ]
      .filter(Boolean)
      .join(' · ')
  })
  const endpointChanged = computed(() =>
    Boolean(
      original.value &&
      original.value.credentialConfigured &&
      (original.value.provider !== draft.provider ||
        normalizeEndpoint(original.value.baseUrl) !== normalizeEndpoint(draft.baseUrl)),
    ),
  )
  const keyRequired = computed(
    () =>
      provider.value.apiKeyMode === 'required' ||
      (draft.provider === 'openai_compatible' &&
        Boolean(compatiblePreset.value && cloudPresetIds.has(compatiblePreset.value.id))),
  )
  const canDiscover = computed(() =>
    Boolean(
      (draft.provider !== 'openai_compatible' || draft.baseUrl.trim()) &&
      (!keyRequired.value || apiKey.value.trim() || (draft.credentialConfigured && !endpointChanged.value)),
    ),
  )
  const canSave = computed(() =>
    Boolean(
      draft.name.trim() &&
      draft.model.trim() &&
      (draft.provider !== 'openai_compatible' || draft.baseUrl.trim()) &&
      (!keyRequired.value || apiKey.value.trim() || (draft.credentialConfigured && !endpointChanged.value)) &&
      (!endpointChanged.value || apiKey.value.trim()),
    ),
  )
  const isDirty = computed(
    () =>
      !original.value ||
      modelSettingsFingerprint(draft) !== modelSettingsFingerprint(original.value) ||
      draft.name !== original.value.name ||
      Boolean(apiKey.value.trim()),
  )

  watch(
    () => [modelSettingsFingerprint(draft), draft.name, apiKey.value],
    () => {
      settings.validation = null
      settings.error = null
    },
  )

  watch(
    () => [draft.provider, draft.baseUrl, apiKey.value],
    () => {
      discoveredModels.value = []
      discoveryMessage.value = ''
    },
  )

  watch(
    () => settings.modelProfiles.map((profile) => profile.id),
    (ids) => {
      if (selectedId.value && !ids.includes(selectedId.value)) closeEditor()
    },
  )

  function normalizeEndpoint(value: string): string {
    return value.trim().replace(/\/$/, '')
  }

  function findPreset(baseUrl: string) {
    const endpoint = normalizeEndpoint(baseUrl)
    return COMPATIBLE_PROVIDER_PRESETS.find((item) => normalizeEndpoint(item.baseUrl) === endpoint)
  }

  function profileProviderName(profile: ChatModelProfile): string {
    return findPreset(profile.baseUrl)?.name ?? getModelProvider(profile.provider).name
  }

  function profileCredential(profile: ChatModelProfile): { label: string; tone: string } {
    const definition = getModelProvider(profile.provider)
    const preset = findPreset(profile.baseUrl)
    if (definition.apiKeyMode === 'none') return { label: '无需密钥', tone: 'neutral' }
    if (profile.credentialConfigured) return { label: '密钥已配置', tone: 'ready' }
    if (definition.apiKeyMode === 'required' || (preset && cloudPresetIds.has(preset.id))) {
      return { label: '需要密钥', tone: 'missing' }
    }
    return { label: '密钥可选', tone: 'neutral' }
  }

  function resetEditor() {
    selectedId.value = ''
    original.value = null
    Object.assign(draft, blankProfile())
    apiKey.value = ''
    revealKey.value = false
    discoveredModels.value = []
    discoveryMessage.value = ''
    catalogOpen.value = false
    settings.clearModelFeedback()
  }

  function showProviderPicker() {
    resetEditor()
    mode.value = 'providers'
  }

  function beginAdd(choice: ProviderChoice) {
    resetEditor()
    selectProvider(choice.provider)
    draft.name = choice.name
    if (choice.presetId) applyPreset(choice.presetId)
    mode.value = 'editor'
  }

  function selectProfile(id: string) {
    const item = settings.modelProfiles.find((profile) => profile.id === id)
    if (!item) return
    selectedId.value = item.id
    original.value = { ...item }
    Object.assign(draft, item)
    apiKey.value = ''
    revealKey.value = false
    discoveredModels.value = []
    discoveryMessage.value = ''
    catalogOpen.value = false
    settings.clearModelFeedback()
    mode.value = 'editor'
  }

  function closeEditor() {
    resetEditor()
    mode.value = 'list'
  }

  function selectProvider(value: ChatModelProvider) {
    draft.provider = value
    draft.baseUrl = getModelProvider(value).defaultBaseUrl
    draft.model = ''
    draft.credentialConfigured = false
    apiKey.value = ''
  }

  function applyPreset(id: string) {
    const preset = COMPATIBLE_PROVIDER_PRESETS.find((item) => item.id === id)
    if (!preset) return
    draft.provider = 'openai_compatible'
    draft.baseUrl = preset.baseUrl
    draft.model = preset.model
    draft.credentialConfigured = false
    apiKey.value = ''
  }

  function handleProviderChange(event: Event) {
    selectProvider((event.target as HTMLSelectElement).value as ChatModelProvider)
  }

  function handlePresetChange(event: Event) {
    const presetId = (event.target as HTMLSelectElement).value
    if (presetId) applyPreset(presetId)
  }

  async function save() {
    const saved = await settings.saveModelProfile({ ...draft }, apiKey.value.trim())
    if (!saved) return
    selectedId.value = saved.id
    original.value = { ...saved }
    Object.assign(draft, saved)
    apiKey.value = ''
  }

  function openCatalog() {
    catalogOpen.value = true
  }

  function useCatalogModel(modelId: string) {
    draft.model = modelId
    catalogOpen.value = false
  }

  async function discoverModels() {
    if (!canDiscover.value || discovering.value) return
    discovering.value = true
    discoveryMessage.value = ''
    settings.clearModelFeedback()
    try {
      const models = await api.discoverChatModels(draft, apiKey.value.trim())
      discoveredModels.value = models
      discoveryMessage.value = `已从服务端获取 ${models.length} 个模型。`
      catalogOpen.value = true
    } catch (reason) {
      discoveryMessage.value = reason instanceof Error ? reason.message : String(reason)
    } finally {
      discovering.value = false
    }
  }

  async function makeDefault(id = draft.id) {
    if (!id) return
    const item = settings.modelProfiles.find((profile) => profile.id === id)
    if (!item || item.isDefault) return
    if (await settings.setDefaultModel(id)) {
      if (draft.id === id) {
        draft.isDefault = true
        if (original.value) original.value.isDefault = true
      }
    }
  }

  async function remove() {
    if (!draft.id || !window.confirm(`删除模型配置“${draft.name}”？`)) return
    if (await settings.removeModelProfile(draft.id)) closeEditor()
  }
  return {
    settings,
    mode,
    selectedId,
    apiKey,
    revealKey,
    discoveredModels,
    discovering,
    discoveryMessage,
    catalogOpen,
    draft,
    provider,
    compatiblePreset,
    displayProviderName,
    modelOptions,
    selectedModelInfo,
    endpointChanged,
    keyRequired,
    canDiscover,
    canSave,
    isDirty,
    findPreset,
    profileProviderName,
    profileCredential,
    showProviderPicker,
    beginAdd,
    selectProfile,
    closeEditor,
    handleProviderChange,
    handlePresetChange,
    save,
    openCatalog,
    useCatalogModel,
    discoverModels,
    makeDefault,
    remove,
  }
}
