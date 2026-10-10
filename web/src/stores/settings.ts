/**
 * Settings Store — 管理用户配置（模型、API Key、权限、搜索工具等）
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  api,
  type ChatModelProfile,
  type ChatModelSettings,
  type CredentialEntry,
  type PermissionSettings,
  type WorkspaceRuntimeStatus,
} from '@/api/client'

const PREFERENCES_CACHE_KEY = import.meta.env.VITE_MOCK === '1' ? 'maigokite_user_preferences_demo' : 'maigokite_user_preferences'

function cachedAssistantName(): string {
  try {
    const value = JSON.parse(localStorage.getItem(PREFERENCES_CACHE_KEY) || '{}') as { assistantName?: unknown }
    return typeof value.assistantName === 'string' && value.assistantName.trim() ? value.assistantName.trim() : '助手'
  } catch {
    return '助手'
  }
}

function cacheAssistantName(assistantName: string) {
  try { localStorage.setItem(PREFERENCES_CACHE_KEY, JSON.stringify({ assistantName })) }
  catch { /* The server remains the source of truth when storage is unavailable. */ }
}

export const useSettingsStore = defineStore('settings', () => {
  const credentials = ref<Record<string, CredentialEntry>>({})
  const modelProfiles = ref<ChatModelProfile[]>([])
  const defaultModelId = ref('')
  const profile = ref({ assistantName: cachedAssistantName() })
  const permissions = ref<PermissionSettings>({ default_mode: 'workspace' })
  const runtimeStatus = ref<WorkspaceRuntimeStatus | null>(null)
  const runtimeLoading = ref(false)
  const runtimeError = ref<string | null>(null)

  const loaded = ref(false)
  const profileLoaded = ref(false)
  const saving = ref(false)
  const error = ref<string | null>(null)
  const success = ref<string | null>(null)
  const validating = ref(false)
  const validation = ref<{ ok: boolean; message: string } | null>(null)

  let profileRequest: Promise<void> | null = null
  let runtimeRequest = 0

  async function loadPreferences() {
    if (profileLoaded.value) return
    if (profileRequest) return profileRequest
    profileRequest = (async () => {
      try {
        profile.value = await api.getUserPreferences()
        cacheAssistantName(profile.value.assistantName)
        profileLoaded.value = true
      } catch (reason) {
        error.value = reason instanceof Error ? reason.message : String(reason)
      } finally {
        profileRequest = null
      }
    })()
    return profileRequest
  }

  async function savePreferences(assistantName: string) {
    saving.value = true
    error.value = null
    success.value = null
    try {
      profile.value = await api.updateUserPreferences({ assistantName })
      cacheAssistantName(profile.value.assistantName)
      profileLoaded.value = true
      success.value = '界面称呼已更新。'
      return true
    } catch (reason) {
      error.value = reason instanceof Error ? reason.message : String(reason)
      return false
    } finally {
      saving.value = false
    }
  }

  async function loadPermissionSettings() {
    try { permissions.value = await api.getPermissionSettings() }
    catch (reason) { error.value = reason instanceof Error ? reason.message : String(reason) }
  }

  async function savePermissionSettings(value: PermissionSettings) {
    saving.value = true
    error.value = null
    success.value = null
    try {
      permissions.value = await api.updatePermissionSettings(value)
      success.value = '权限策略已保存，新任务将立即使用。'
      return true
    } catch (reason) {
      error.value = reason instanceof Error ? reason.message : String(reason)
      return false
    } finally { saving.value = false }
  }

  async function loadRuntimeStatus(folderId = '') {
    const request = ++runtimeRequest
    runtimeLoading.value = true
    runtimeStatus.value = null
    runtimeError.value = null
    try {
      const result = await api.getWorkspaceRuntimeStatus(folderId)
      if (request === runtimeRequest) runtimeStatus.value = result
    } catch (reason) {
      if (request === runtimeRequest)
        runtimeError.value = reason instanceof Error ? reason.message : String(reason)
    } finally {
      if (request === runtimeRequest) runtimeLoading.value = false
    }
  }

  /**
   * 从后端加载当前配置
   */
  async function loadSettings() {
    saving.value = true
    error.value = null
    success.value = null
    try {
      const [catalog, statuses] = await Promise.all([
        api.listChatModels(),
        api.listCredentialReferences(),
      ])
      modelProfiles.value = catalog.models
      defaultModelId.value = catalog.defaultModelId
      credentials.value = Object.fromEntries(statuses.map(item => [item.name, { service: item.name, configured: item.configured, validated: item.validated }]))
      loaded.value = true
    } catch (reason) {
      error.value = reason instanceof Error ? reason.message : String(reason)
    } finally {
      saving.value = false
    }
  }

  async function loadModelProfiles() {
    const catalog = await api.listChatModels()
    modelProfiles.value = catalog.models
    defaultModelId.value = catalog.defaultModelId
  }

  async function saveModelProfile(profile: ChatModelProfile, apiKey = '') {
    saving.value = true
    error.value = null
    success.value = null
    validation.value = null
    try {
      const saved = await api.saveChatModel(profile, apiKey)
      const index = modelProfiles.value.findIndex(item => item.id === saved.id)
      if (index >= 0) modelProfiles.value[index] = saved
      else modelProfiles.value.push(saved)
      if (saved.isDefault || !defaultModelId.value) {
        defaultModelId.value = saved.id
      }
      success.value = `模型配置“${saved.name}”已保存。`
      return saved
    } catch (reason) {
      error.value = reason instanceof Error ? reason.message : String(reason)
      return null
    } finally {
      saving.value = false
    }
  }

  async function setDefaultModel(modelId: string) {
    saving.value = true
    error.value = null
    try {
      const catalog = await api.setDefaultChatModel(modelId)
      modelProfiles.value = catalog.models
      defaultModelId.value = catalog.defaultModelId
      success.value = '默认模型已更新，新对话将自动使用它。'
      return true
    } catch (reason) {
      error.value = reason instanceof Error ? reason.message : String(reason)
      return false
    } finally { saving.value = false }
  }

  async function removeModelProfile(modelId: string) {
    saving.value = true
    error.value = null
    try {
      await api.deleteChatModel(modelId)
      await loadModelProfiles()
      success.value = '模型配置已删除。'
      return true
    } catch (reason) {
      error.value = reason instanceof Error ? reason.message : String(reason)
      return false
    } finally { saving.value = false }
  }

  async function validateChatModel(cfg: ChatModelSettings, apiKey = '') {
    validating.value = true
    error.value = null
    success.value = null
    validation.value = null
    try {
      const result = await api.validateChatModel(cfg, apiKey)
      validation.value = { ok: result.ok, message: result.ok ? `连接成功：${result.model}` : result.message }
      return result.ok
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : String(reason)
      validation.value = { ok: false, message }
      return false
    } finally {
      validating.value = false
    }
  }

  function clearModelFeedback() {
    validation.value = null
    error.value = null
    success.value = null
  }

  /**
   * 保存凭证（API Key）
   */
  async function saveCredential(service: string, apiKey: string) {
    saving.value = true
    error.value = null
    success.value = null
    try {
      await api.saveCredential(service, apiKey)
      credentials.value[service] = {
        service,
        configured: true,
        validated: false,
        updated_at: new Date().toISOString(),
      }
      success.value = '联网工具凭证已保存并立即生效。'
      return true
    } catch (reason) {
      error.value = reason instanceof Error ? reason.message : String(reason)
      return false
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
    success.value = null
    try {
      await api.deleteCredential(service)
      delete credentials.value[service]
      success.value = '联网工具凭证已移除。'
      return true
    } catch (reason) {
      error.value = reason instanceof Error ? reason.message : String(reason)
      return false
    } finally {
      saving.value = false
    }
  }

  return {
    modelProfiles,
    defaultModelId,
    credentials,
    profile,
    permissions,
    runtimeStatus,
    runtimeLoading,
    runtimeError,
    loaded,
    profileLoaded,
    saving,
    error,
    success,
    validating,
    validation,
    loadPreferences,
    savePreferences,
    loadPermissionSettings,
    savePermissionSettings,
    loadRuntimeStatus,
    loadSettings,
    loadModelProfiles,
    saveModelProfile,
    setDefaultModel,
    removeModelProfile,
    validateChatModel,
    clearModelFeedback,
    saveCredential,
    deleteCredential,
  }
})
