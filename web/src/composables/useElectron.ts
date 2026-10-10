import { onMounted, ref } from 'vue'

// Demo data must never reach real files, notifications or persisted desktop settings.
// Window chrome and platform detection remain available for the frameless demo window.
export const desktopEffects = import.meta.env.VITE_MOCK === '1' ? undefined : window.electronAPI

export function useElectron() {
  const isElectron = Boolean(window.electronAPI),
    platform = ref('web')
  onMounted(async () => {
    try {
      const status = await window.electronAPI?.runtimeStatus()
      if (status) platform.value = status.platform
    } catch {
      /* The web UI remains usable without desktop status. */
    }
  })
  function windowControl(action: 'minimize' | 'maximize' | 'close' | 'hide') {
    void window.electronAPI?.windowControl(action)
  }
  return { isElectron, platform, windowControl }
}
