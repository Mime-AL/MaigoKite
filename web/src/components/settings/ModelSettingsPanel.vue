<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import IconSymbol from '@/components/common/IconSymbol.vue'
import ModelCatalogPicker from '@/components/settings/ModelCatalogPicker.vue'
import {
  COMPATIBLE_PROVIDER_PRESETS,
  MODEL_PROVIDERS,
  getModelProvider,
  modelSettingsFingerprint,
} from '@/config/model-providers'
import { useSettingsStore } from '@/stores/settings'
import {
  api,
  type ChatModelProfile,
  type ChatModelProvider,
  type DiscoveredChatModel,
} from '@/api/client'

type PanelMode = 'list' | 'providers' | 'editor'
type ChoiceGroup = '云端服务' | '本地服务'

interface ProviderChoice {
  id: string
  name: string
  description: string
  monogram: string
  provider: ChatModelProvider
  presetId?: string
  group: ChoiceGroup
}

const settings = useSettingsStore()
const mode = ref<PanelMode>('list')
const selectedId = ref('')
const apiKey = ref('')
const revealKey = ref(false)
const discoveredModels = ref<DiscoveredChatModel[]>([])
const discovering = ref(false)
const discoveryMessage = ref('')
const catalogOpen = ref(false)

const providerChoices: ProviderChoice[] = [
  {
    id: 'deepseek',
    name: 'DeepSeek',
    description: '官方 API',
    monogram: 'DS',
    provider: 'openai_compatible',
    presetId: 'deepseek',
    group: '云端服务',
  },
  {
    id: 'openai',
    name: 'OpenAI',
    description: '官方 API',
    monogram: 'O',
    provider: 'openai',
    group: '云端服务',
  },
  {
    id: 'anthropic',
    name: 'Anthropic',
    description: 'Claude API',
    monogram: 'A',
    provider: 'anthropic',
    group: '云端服务',
  },
  {
    id: 'openrouter',
    name: 'OpenRouter',
    description: '多模型聚合服务',
    monogram: 'OR',
    provider: 'openai_compatible',
    presetId: 'openrouter',
    group: '云端服务',
  },
  {
    id: 'dashscope',
    name: '阿里云百炼',
    description: 'OpenAI 兼容 API',
    monogram: '百',
    provider: 'openai_compatible',
    presetId: 'dashscope',
    group: '云端服务',
  },
  {
    id: 'groq',
    name: 'Groq',
    description: 'GroqCloud API',
    monogram: 'G',
    provider: 'openai_compatible',
    presetId: 'groq',
    group: '云端服务',
  },
  {
    id: 'together',
    name: 'Together AI',
    description: '开源模型聚合服务',
    monogram: 'T',
    provider: 'openai_compatible',
    presetId: 'together',
    group: '云端服务',
  },
  {
    id: 'ollama',
    name: 'Ollama',
    description: '本机模型服务',
    monogram: 'OL',
    provider: 'ollama',
    group: '本地服务',
  },
  {
    id: 'lm-studio',
    name: 'LM Studio',
    description: '本机 OpenAI 兼容服务',
    monogram: 'LM',
    provider: 'openai_compatible',
    presetId: 'lm-studio',
    group: '本地服务',
  },
  {
    id: 'vllm',
    name: 'vLLM',
    description: '高吞吐本地推理',
    monogram: 'VL',
    provider: 'openai_compatible',
    presetId: 'vllm',
    group: '本地服务',
  },
  {
    id: 'llama-cpp',
    name: 'llama.cpp',
    description: '轻量本地服务器',
    monogram: 'LC',
    provider: 'openai_compatible',
    presetId: 'llama-cpp',
    group: '本地服务',
  },
  {
    id: 'custom',
    name: '自定义服务',
    description: '任意 OpenAI 兼容端点',
    monogram: '+',
    provider: 'openai_compatible',
    group: '本地服务',
  },
]

const choiceGroups: ChoiceGroup[] = ['云端服务', '本地服务']
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
  compatiblePreset.value?.models.length
    ? compatiblePreset.value.models
    : provider.value.recommendedModels,
)
const modelOptions = computed<DiscoveredChatModel[]>(() =>
  discoveredModels.value.length
    ? discoveredModels.value
    : recommendedModels.value.map((id) => ({ id, name: id })),
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
    (!keyRequired.value ||
      apiKey.value.trim() ||
      (draft.credentialConfigured && !endpointChanged.value)),
  ),
)
const canSave = computed(() =>
  Boolean(
    draft.name.trim() &&
    draft.model.trim() &&
    (draft.provider !== 'openai_compatible' || draft.baseUrl.trim()) &&
    (!keyRequired.value ||
      apiKey.value.trim() ||
      (draft.credentialConfigured && !endpointChanged.value)) &&
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
</script>

<template>
  <section class="model-settings glass-card">
    <header class="panel-heading">
      <div>
        <p>Model providers</p>
        <h2>模型</h2>
        <span>管理服务凭证、模型目录和 Workspace 默认模型。</span>
      </div>
      <button
        v-if="mode === 'list'"
        type="button"
        class="primary-button add-button"
        data-testid="add-model"
        @click="showProviderPicker"
      >
        <IconSymbol name="plus" :size="15" />添加模型
      </button>
    </header>

    <div v-if="mode === 'list'" class="profile-list">
      <article v-for="item in settings.modelProfiles" :key="item.id" class="profile-row">
        <button
          type="button"
          class="profile-main"
          :aria-label="`编辑 ${item.name}`"
          @click="selectProfile(item.id)"
        >
          <span class="provider-mark" :class="item.provider">{{
            findPreset(item.baseUrl)?.name.slice(0, 2) || getModelProvider(item.provider).monogram
          }}</span>
          <span class="profile-copy">
            <span
              ><strong>{{ item.name }}</strong
              ><i v-if="item.isDefault">默认</i></span
            >
            <small>{{ profileProviderName(item) }} · {{ item.model }}</small>
          </span>
          <span class="credential-state" :class="profileCredential(item).tone"
            ><i />{{ profileCredential(item).label }}</span
          >
        </button>
        <button
          v-if="!item.isDefault"
          type="button"
          class="default-action"
          @click="makeDefault(item.id)"
        >
          设为默认
        </button>
        <button
          type="button"
          class="edit-action"
          :aria-label="`编辑 ${item.name}`"
          @click="selectProfile(item.id)"
        >
          ›
        </button>
      </article>

      <div v-if="!settings.modelProfiles.length" class="empty-profile">
        <span class="empty-icon"><IconSymbol name="brain" :size="25" /></span>
        <h3>连接你的第一个模型</h3>
        <p>选择云端服务或本地运行时。凭证只会写入系统凭证库。</p>
        <button type="button" class="primary-button" @click="showProviderPicker">
          选择模型服务
        </button>
      </div>
    </div>

    <section v-else-if="mode === 'providers'" class="provider-picker" data-testid="provider-picker">
      <button type="button" class="back-button" @click="closeEditor">‹ 返回模型列表</button>
      <div class="picker-heading">
        <h3>添加模型服务</h3>
        <p>先选择服务，再填写密钥和模型。每次只处理一个配置。</p>
      </div>
      <div v-for="group in choiceGroups" :key="group" class="choice-group">
        <h4>{{ group }}</h4>
        <div class="choice-grid">
          <button
            v-for="choice in providerChoices.filter((item) => item.group === group)"
            :key="choice.id"
            type="button"
            class="provider-choice"
            :data-provider-choice="choice.id"
            @click="beginAdd(choice)"
          >
            <span class="provider-mark compatible">{{ choice.monogram }}</span>
            <span
              ><strong>{{ choice.name }}</strong
              ><small>{{ choice.description }}</small></span
            >
            <i>›</i>
          </button>
        </div>
      </div>
    </section>

    <form v-else class="profile-editor" @submit.prevent="save">
      <header class="editor-heading">
        <button type="button" class="back-button" @click="closeEditor">‹ 返回模型列表</button>
        <div class="editor-title">
          <span class="provider-mark" :class="draft.provider">{{
            compatiblePreset?.name.slice(0, 2) || provider.monogram
          }}</span>
          <span
            ><small>{{ draft.id ? '编辑模型配置' : '添加模型配置' }}</small>
            <h3>{{ displayProviderName }}</h3></span
          >
          <i v-if="draft.isDefault" class="default-pill">默认</i>
        </div>
      </header>

      <div class="editor-body">
        <label class="form-field">
          <span>配置名称 <b>必填</b></span>
          <input
            v-model.trim="draft.name"
            data-testid="profile-name"
            maxlength="80"
            placeholder="例如：工作区 DeepSeek"
          />
          <small>用于在聊天框和默认模型列表中辨认这个配置。</small>
        </label>

        <label v-if="provider.apiKeyMode !== 'none'" class="form-field">
          <span
            >API Key <b>{{ keyRequired ? '必填' : '按需' }}</b></span
          >
          <span class="secret">
            <input
              v-model="apiKey"
              data-testid="api-key"
              :type="revealKey ? 'text' : 'password'"
              autocomplete="new-password"
              :placeholder="draft.credentialConfigured ? '已配置；留空继续使用' : '粘贴 API Key'"
            />
            <button
              type="button"
              :aria-label="revealKey ? '隐藏 API Key' : '显示 API Key'"
              @click="revealKey = !revealKey"
            >
              <IconSymbol :name="revealKey ? 'eye-off' : 'eye'" :size="16" />
            </button>
          </span>
          <small v-if="endpointChanged" class="warning"
            >端点或接口类型已变化，请输入对应的新 Key；旧 Key 不会发送到新端点。</small
          >
          <small v-else-if="draft.credentialConfigured" class="credential-confirmed"
            ><i />密钥已保存在系统凭证库中；页面不会回显真实值。</small
          >
          <small v-else>密钥按模型配置隔离，并保存在系统凭证库中。</small>
        </label>

        <div class="form-field model-field">
          <span>模型 <b>必填</b></span>
          <div class="model-input-row">
            <input
              v-model.trim="draft.model"
              data-testid="model-id"
              :placeholder="provider.modelPlaceholder"
            />
            <button
              v-if="modelOptions.length"
              type="button"
              class="secondary-button"
              data-testid="browse-models"
              @click="openCatalog"
            >
              选择模型
            </button>
            <button
              type="button"
              class="secondary-button discover-button"
              :disabled="!canDiscover || discovering"
              data-testid="discover-models"
              @click="discoverModels"
            >
              <IconSymbol name="refresh" :size="14" />{{ discovering ? '正在获取…' : '从服务获取' }}
            </button>
          </div>
          <small v-if="selectedModelInfo" class="model-meta">{{ selectedModelInfo }}</small>
          <small v-else-if="discoveryMessage" :class="{ warning: !discoveredModels.length }">{{
            discoveryMessage
          }}</small>
          <small v-else>可自动读取服务端模型目录；目录不可用时也可以手工输入准确的模型 ID。</small>
        </div>

        <details class="custom-settings">
          <summary>
            <span><strong>自定义设置</strong><small>接口类型、服务预设与 Base URL</small></span>
            <i>›</i>
          </summary>
          <div class="custom-settings-body">
            <label class="form-field">
              <span>接口类型</span>
              <select
                data-testid="provider-type"
                :value="draft.provider"
                @change="handleProviderChange"
              >
                <option v-for="item in MODEL_PROVIDERS" :key="item.id" :value="item.id">
                  {{ item.name }}
                </option>
              </select>
            </label>
            <label v-if="draft.provider === 'openai_compatible'" class="form-field">
              <span>服务预设</span>
              <select
                data-testid="preset-select"
                :value="compatiblePreset?.id || ''"
                @change="handlePresetChange"
              >
                <option value="">自定义地址</option>
                <option v-for="item in COMPATIBLE_PROVIDER_PRESETS" :key="item.id" :value="item.id">
                  {{ item.name }}
                </option>
              </select>
            </label>
            <label class="form-field full">
              <span>{{ provider.baseUrlLabel }}</span>
              <input
                v-model.trim="draft.baseUrl"
                data-testid="base-url"
                type="url"
                :placeholder="provider.baseUrlPlaceholder"
              />
              <small>{{ provider.baseUrlHelp }}</small>
            </label>
          </div>
        </details>

        <p v-if="settings.validation" class="validation" :class="{ ok: settings.validation.ok }">
          <IconSymbol :name="settings.validation.ok ? 'check' : 'alert'" :size="15" />{{
            settings.validation.message
          }}
        </p>
      </div>

      <footer class="editor-footer">
        <div>
          <button v-if="draft.id" type="button" class="danger-button" @click="remove">
            删除配置
          </button>
          <button
            v-if="draft.id && !draft.isDefault"
            type="button"
            class="secondary-button"
            @click="makeDefault()"
          >
            设为默认
          </button>
        </div>
        <div class="save-actions">
          <span>{{ isDirty ? '有未保存的修改' : '已保存' }}</span>
          <button
            type="button"
            class="secondary-button"
            :disabled="!canSave || settings.validating"
            @click="settings.validateChatModel({ ...draft }, apiKey.trim())"
          >
            {{ settings.validating ? '测试中…' : '测试连接' }}
          </button>
          <button type="submit" class="primary-button" :disabled="!canSave || settings.saving">
            {{ settings.saving ? '保存中…' : '保存配置' }}
          </button>
        </div>
      </footer>
    </form>

    <ModelCatalogPicker
      v-if="catalogOpen"
      :models="modelOptions"
      :selected-model="draft.model"
      :loading="discovering"
      :can-refresh="canDiscover"
      :message="discoveryMessage"
      @close="catalogOpen = false"
      @refresh="discoverModels"
      @select="useCatalogModel"
    />
  </section>
</template>

<style scoped lang="scss">
.model-settings {
  min-height: 560px;
  overflow: hidden;
}
.panel-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 24px 26px 20px;
  border-bottom: 1px solid var(--border-color);
}
.panel-heading p {
  margin: 0 0 4px;
  color: var(--text-tertiary);
  font-size: 11px;
  font-weight: 750;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.panel-heading h2 {
  margin: 0;
  font-size: 22px;
}
.panel-heading span {
  display: block;
  margin-top: 5px;
  color: var(--text-secondary);
  font-size: 12px;
}
.add-button {
  display: inline-flex;
  min-height: 38px;
  align-items: center;
  gap: 6px;
}

.profile-list {
  padding: 12px 16px 20px;
}
.profile-row {
  display: flex;
  min-height: 72px;
  align-items: center;
  gap: 8px;
  padding: 7px 9px;
  border-bottom: 1px solid var(--border-color);
}
.profile-row:last-child {
  border-bottom: 0;
}
.profile-main {
  display: flex;
  min-width: 0;
  flex: 1;
  align-items: center;
  gap: 12px;
  padding: 6px;
  border: 0;
  border-radius: 12px;
  color: var(--text-primary);
  background: transparent;
  cursor: pointer;
  text-align: left;
}
.profile-main:hover {
  background: var(--surface-muted);
}
.provider-mark {
  display: grid;
  width: 38px;
  height: 38px;
  flex: none;
  place-items: center;
  border-radius: 11px;
  color: #fff;
  background: #202633;
  font-size: 11px;
  font-style: normal;
  font-weight: 780;
  letter-spacing: -0.02em;
}
.provider-mark.anthropic {
  background: #b2633b;
}
.provider-mark.ollama {
  background: #596477;
}
.provider-mark.openai_compatible,
.provider-mark.compatible {
  background: #6d5bd0;
}
.profile-copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 5px;
}
.profile-copy > span {
  display: flex;
  align-items: center;
  gap: 7px;
}
.profile-copy strong {
  overflow: hidden;
  font-size: 13px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.profile-copy small {
  overflow: hidden;
  color: var(--text-secondary);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.profile-copy i,
.default-pill {
  padding: 3px 7px;
  border-radius: 999px;
  color: var(--primary-color);
  background: var(--primary-soft);
  font-size: 10px;
  font-style: normal;
  font-weight: 750;
}
.credential-state {
  display: inline-flex;
  flex: none;
  align-items: center;
  gap: 6px;
  color: var(--text-tertiary);
  font-size: 11px;
}
.credential-state i,
.credential-confirmed i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--text-tertiary);
}
.credential-state.ready,
.credential-confirmed {
  color: var(--success) !important;
}
.credential-state.ready i,
.credential-confirmed i {
  background: var(--success);
}
.credential-state.missing {
  color: var(--danger);
}
.credential-state.missing i {
  background: var(--danger);
}
.default-action,
.edit-action {
  flex: none;
  border: 0;
  color: var(--text-secondary);
  background: transparent;
  cursor: pointer;
}
.default-action {
  padding: 7px 9px;
  border-radius: 9px;
  font-size: 11px;
}
.default-action:hover {
  color: var(--primary-color);
  background: var(--primary-soft);
}
.edit-action {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  font-size: 22px;
}
.edit-action:hover {
  background: var(--surface-muted);
}

.empty-profile {
  display: grid;
  min-height: 390px;
  place-content: center;
  justify-items: center;
  padding: 40px;
  text-align: center;
}
.empty-icon {
  display: grid;
  width: 54px;
  height: 54px;
  place-items: center;
  border-radius: 17px;
  color: var(--primary-color);
  background: var(--primary-soft);
}
.empty-profile h3 {
  margin: 16px 0 6px;
  font-size: 17px;
}
.empty-profile p {
  max-width: 390px;
  margin: 0 0 18px;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.55;
}

.provider-picker {
  padding: 20px 26px 30px;
}
.back-button {
  padding: 5px 0;
  border: 0;
  color: var(--primary-color);
  background: transparent;
  cursor: pointer;
  font-size: 12px;
}
.picker-heading {
  margin: 18px 0 22px;
}
.picker-heading h3 {
  margin: 0;
  font-size: 19px;
}
.picker-heading p {
  margin: 6px 0 0;
  color: var(--text-secondary);
  font-size: 12px;
}
.choice-group + .choice-group {
  margin-top: 24px;
}
.choice-group h4 {
  margin: 0 0 9px;
  color: var(--text-secondary);
  font-size: 12px;
}
.choice-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 9px;
}
.provider-choice {
  display: flex;
  min-width: 0;
  min-height: 68px;
  align-items: center;
  gap: 11px;
  padding: 11px;
  border: 1px solid var(--border-color);
  border-radius: 14px;
  color: var(--text-primary);
  background: var(--surface-muted);
  cursor: pointer;
  text-align: left;
  transition:
    border-color 0.15s ease,
    transform 0.15s ease,
    background 0.15s ease;
}
.provider-choice:hover {
  border-color: var(--primary-color);
  background: var(--surface-solid);
  transform: translateY(-1px);
}
.provider-choice > span:nth-child(2) {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 4px;
}
.provider-choice strong {
  overflow: hidden;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.provider-choice small {
  overflow: hidden;
  color: var(--text-tertiary);
  font-size: 10.5px;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.provider-choice > i {
  color: var(--text-tertiary);
  font-size: 18px;
  font-style: normal;
}

.profile-editor {
  display: flex;
  min-height: 470px;
  flex-direction: column;
}
.editor-heading {
  padding: 16px 26px 18px;
  border-bottom: 1px solid var(--border-color);
}
.editor-title {
  display: flex;
  align-items: center;
  gap: 11px;
  margin-top: 12px;
}
.editor-title > span:nth-child(2) {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.editor-title small {
  color: var(--text-tertiary);
  font-size: 10.5px;
}
.editor-title h3 {
  margin: 0;
  font-size: 18px;
}
.editor-body {
  display: grid;
  gap: 18px;
  padding: 22px 26px 26px;
}
.form-field {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.form-field > span:first-child {
  font-size: 12px;
  font-weight: 680;
}
.form-field b {
  color: var(--primary-color);
  font-size: 10px;
}
.form-field input,
.form-field select {
  width: 100%;
  height: 42px;
  padding: 0 12px;
  border: 1px solid var(--border-strong);
  border-radius: 11px;
  outline: 0;
  color: var(--text-primary);
  background: var(--surface-muted);
  font-size: 13px;
}
.form-field input:focus,
.form-field select:focus {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px var(--focus-ring);
}
.form-field small {
  color: var(--text-tertiary);
  font-size: 11px;
  line-height: 1.5;
}
.secret {
  display: flex;
  border: 1px solid var(--border-strong);
  border-radius: 11px;
  background: var(--surface-muted);
}
.secret:focus-within {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px var(--focus-ring);
}
.secret input {
  border: 0;
  background: transparent;
  box-shadow: none !important;
}
.secret button {
  width: 42px;
  flex: none;
  border: 0;
  color: var(--text-tertiary);
  background: transparent;
  cursor: pointer;
}
.credential-confirmed {
  display: flex;
  align-items: center;
  gap: 6px;
}
.model-input-row {
  display: flex;
  gap: 8px;
}
.model-input-row input {
  min-width: 120px;
  flex: 1;
}
.model-input-row button {
  display: inline-flex;
  min-height: 42px;
  flex: none;
  align-items: center;
  justify-content: center;
  gap: 6px;
  white-space: nowrap;
}
.model-meta {
  color: var(--text-secondary) !important;
}
.warning {
  color: var(--warning) !important;
}

.custom-settings {
  border: 1px solid var(--border-color);
  border-radius: 13px;
  background: var(--surface-muted);
}
.custom-settings summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 13px 14px;
  cursor: pointer;
  list-style: none;
}
.custom-settings summary::-webkit-details-marker {
  display: none;
}
.custom-settings summary > span {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.custom-settings summary strong {
  font-size: 12px;
}
.custom-settings summary small {
  color: var(--text-tertiary);
  font-size: 10.5px;
}
.custom-settings summary > i {
  color: var(--text-tertiary);
  font-size: 19px;
  font-style: normal;
  transition: transform 0.15s ease;
}
.custom-settings[open] summary > i {
  transform: rotate(90deg);
}
.custom-settings-body {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 15px;
  padding: 4px 14px 16px;
  border-top: 1px solid var(--border-color);
}
.custom-settings-body .form-field {
  padding-top: 14px;
}
.custom-settings-body .full {
  grid-column: 1 / -1;
}

.validation {
  display: flex;
  align-items: center;
  gap: 7px;
  margin: 0;
  padding: 10px 12px;
  border-radius: 10px;
  color: var(--danger);
  background: var(--danger-soft);
  font-size: 12px;
}
.validation.ok {
  color: var(--success);
  background: var(--success-soft);
}
.editor-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: auto;
  padding: 14px 20px;
  border-top: 1px solid var(--border-color);
  background: var(--surface-muted);
}
.editor-footer > div,
.save-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.save-actions > span {
  margin-right: 4px;
  color: var(--text-tertiary);
  font-size: 11px;
}
.danger-button {
  min-height: 36px;
  padding: 0 12px;
  border: 1px solid rgba(220, 60, 60, 0.25);
  border-radius: 10px;
  color: var(--danger);
  background: var(--danger-soft);
  cursor: pointer;
  font-size: 11px;
}

@media (max-width: 760px) {
  .choice-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .credential-state {
    display: none;
  }
  .model-input-row {
    align-items: stretch;
    flex-wrap: wrap;
  }
  .model-input-row input {
    flex-basis: 100%;
  }
  .model-input-row button {
    flex: 1;
  }
  .editor-footer {
    align-items: stretch;
    flex-direction: column;
  }
  .editor-footer > div {
    justify-content: flex-end;
  }
}

@media (max-width: 500px) {
  .panel-heading,
  .editor-heading,
  .editor-body,
  .provider-picker {
    padding-right: 16px;
    padding-left: 16px;
  }
  .panel-heading {
    align-items: stretch;
    flex-direction: column;
  }
  .add-button {
    justify-content: center;
  }
  .choice-grid,
  .custom-settings-body {
    grid-template-columns: 1fr;
  }
  .custom-settings-body .full {
    grid-column: auto;
  }
  .profile-row {
    gap: 3px;
  }
  .default-action {
    display: none;
  }
  .save-actions {
    align-items: stretch !important;
    flex-wrap: wrap;
  }
  .save-actions > span {
    width: 100%;
  }
  .save-actions button {
    flex: 1;
  }
}
</style>
