import { computed, watch } from 'vue'
import { useRunStore } from '@/stores/run'
import { useSessionStore } from '@/stores/session'
import { desktopEffects } from './useElectron'

export function usePulse() {
  const run = useRunStore(),
    session = useSessionStore()
  const state = computed(() => run.pulse(session.activeSessionId))
  const trayState = computed(() => {
    const states = Object.keys(run.turns).map((id) => run.pulse(id))
    if (run.awaits.length) return 'waiting'
    return (
      states.find((value) => value === 'acting') ||
      states.find((value) => value === 'thinking') ||
      state.value
    )
  })
  watch(
    trayState,
    (value) => {
      void desktopEffects?.setPulse(value).catch(() => undefined)
    },
    { immediate: true },
  )
  return { state }
}
