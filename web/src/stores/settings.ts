/**
 * Settings Store — 管理用户配置（模型、API Key、权限、搜索工具等）
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  AppConfig,
  ModelConfig,
  CredentialEntry,
  SearchEngineConfig,
} from '@/types/api'

interface SettingsState {
  app: AppConfig
  models: ModelConfig
  credentials: Record<string, CredentialEntry>
  searchEngines: SearchEngineConfig
  permissions: {
    defaultMode: string
    circuitBreakerEnabled: boolean
  }
  loaded: boolean
  saving: boolean
  error: string | null
}

export const useSettingsStore = defineStore('settings', () => {
  const app = ref<AppConfig>({
    name: 'NanamiGopher',
    version: '1.0.0',
    theme: 'dark',
    language: 'zh-CN',
  })

  const models = ref<ModelConfig>({
    preferLocal: true,
    localFallbackOrder: ['ollama', 'lm_studio', 'vllm'],
    chat: { default: '', fallback: '' },
    embedding: { provider: '', bge: { model: '', device: 'cpu' } },
  })

  const credentials = ref<Record<string, CredentialEntry>>({})
  const searchEngines = ref<SearchEngineConfig>({
    default: 'duckduckgo',
    providers: {
      tavily: { enabled: false, apiKey: '' },
      google: { enabled: false, apiKey: '', cx: '' },
      duckduckgo: { enabled: true },
    },
  })

  const permissions = ref({
    defaultMode: 'manual',
    circuitBreakerEnabled: true,
  })

  const loaded = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)

  const hasChatModel = computed(() => !!models.value.chat.default)
  const hasEmbeddingModel = computed(() => !!models.value.embedding.provider)
  const activeSearchEngine = computed(() => {
    for (const [name, cfg] of Object.entries(searchEngines.value.providers)) {
      if (cfg.enabled) return name
    }
    return searchEngines.value.default
  })

  /**
   * 从后端加载当前配置
   */
  async function loadSettings() {
    saving.value = true
    error.value = null
    try {
      const res = await fetch('/api/v1/settings')
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      app.value = data.app ?? app.value
      models.value = data.models ?? models.value
      credentials.value = data.credentials ?? credentials.value
      searchEngines.value = data.search_engines ?? searchEngines.value
      permissions.value = data.permissions ?? permissions.value
      loaded.value = true
    } catch (e: any) {
      error.value = e.message
    } finally {
      saving.value = false
    }
  }

  /**
   * 保存模型配置
   */
  async function saveModels(cfg: Partial<ModelConfig>) {
    saving.value = true
    error.value = null
    try {
      const res = await fetch('/api/v1/settings/models', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cfg),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      models.value = { ...models.value, ...cfg }
    } catch (e: any) {
      error.value = e.message
    } finally {
      saving.value = false
    }
  }

  /**
   * 保存凭证（API Key）
   */
  async function saveCredential(service: string, apiKey: string) {
    saving.value = true
    error.value = null
    try {
      const res = await fetch(`/api/v1/credentials/${service}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ service, api_key: apiKey }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      credentials.value[service] = {
        service,
        configured: true,
        validated: true,
        updated_at: new Date().toISOString(),
      }
    } catch (e: any) {
      error.value = e.message
    } finally {
      saving.value = false
    }
  }

  /**
   * 删除凭证
   */
  async function deleteCredential(service: string) {
    saving.value = true
    error.value = null
    try {
      const res = await fetch(`/api/v1/credentials/search/${service}`, {
        method: 'DELETE',
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      delete credentials.value[service]
    } catch (e: any) {
      error.value = e.message
    } finally {
      saving.value = false
    }
  }

  /**
   * 保存搜索引擎配置
   */
  async function saveSearchEngines(cfg: Partial<SearchEngineConfig>) {
    saving.value = true
    error.value = null
    try {
      const res = await fetch('/api/v1/settings/search-engines', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cfg),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      searchEngines.value = { ...searchEngines.value, ...cfg }
    } catch (e: any) {
      error.value = e.message
    } finally {
      saving.value = false
    }
  }

  /**
   * 保存权限配置
   */
  async function savePermissions(cfg: typeof permissions.value) {
    saving.value = true
    error.value = null
    try {
      const res = await fetch('/api/v1/permissions', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cfg),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      permissions.value = cfg
    } catch (e: any) {
      error.value = e.message
    } finally {
      saving.value = false
    }
  }

  return {
    app,
    models,
    credentials,
    searchEngines,
    permissions,
    loaded,
    saving,
    error,
    hasChatModel,
    hasEmbeddingModel,
    activeSearchEngine,
    loadSettings,
    saveModels,
    saveCredential,
    deleteCredential,
    saveSearchEngines,
    savePermissions,
  }
})
