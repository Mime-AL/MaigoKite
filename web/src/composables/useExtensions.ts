import { onMounted, ref } from 'vue'
import { api, type ExtensionConfig, type ExtensionSettings } from '@/api/client'
import { t } from '@/i18n'

/** Server facts only: saving configuration never implies successful loading. */
export function useExtensions() {
  const snapshot = ref<ExtensionSettings | null>(null)
  const busy = ref(false)
  const error = ref('')
  const notice = ref('')
  async function perform(operation: () => Promise<void>) {
    if (busy.value) return false
    busy.value = true
    error.value = notice.value = ''
    try {
      await operation()
      return true
    } catch (reason) {
      error.value = reason instanceof Error ? reason.message : String(reason)
      // A timed-out apply may still be finishing. Query, never restart it.
      try { snapshot.value = await api.getExtensions() } catch { /* Keep original error. */ }
      return false
    } finally { busy.value = false }
  }
  const refresh = () => perform(async () => { snapshot.value = await api.getExtensions() })
  const save = (edit: (config: ExtensionConfig) => void) => perform(async () => {
    if (!snapshot.value) throw new Error(t('请先读取扩展配置。'))
    const config: ExtensionConfig = JSON.parse(JSON.stringify(snapshot.value.config))
    edit(config)
    snapshot.value = await api.saveExtensions(config)
    notice.value = t('配置已保存，应用后生效。')
  })
  const apply = () => perform(async () => {
    if (!snapshot.value) return
    snapshot.value = await api.applyExtensions(snapshot.value.config.revision)
    notice.value = t('扩展已重新加载，请检查各项运行状态。')
  })
  const restore = () => perform(async () => {
    if (!snapshot.value?.active_config) return
    snapshot.value = await api.applyExtensions(snapshot.value.active_config.revision, true)
    notice.value = t('已尝试恢复原有连接，未应用新配置；请检查各项状态。')
  })
  onMounted(() => { void refresh() })
  return { snapshot, busy, error, notice, perform, refresh, save, apply, restore }
}
