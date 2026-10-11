import { computed, onActivated, onDeactivated, onMounted, onUnmounted, ref, watch } from 'vue'
import { layoutPixels } from '@/utils/layout-media'

/** Presentation-only sizing shared by file and diff previews. */
export function usePreviewSplit(preference: string, preferredHeight?: () => number) {
  const root = ref<HTMLElement | null>(null)
  const height = ref(0), dragging = ref(false)
  const defaultRatio = layoutPixels('--explorer-tree-share')
  const storageKey = `${import.meta.env.VITE_MOCK === '1' ? 'demo_' : ''}${preference}`
  function savedRatio(): number | null {
    try {
      const value = Number(localStorage.getItem(storageKey))
      if (Number.isFinite(value) && value > 0 && value < 1) return value
    } catch { /* Resizing does not require preference storage. */ }
    return null
  }
  const ratio = ref(savedRatio())
  const available = computed(() => Math.max(0, height.value - layoutPixels('--explorer-split-handle-height')))
  const preferred = computed(() => preferredHeight?.() ?? available.value * defaultRatio)
  const minimum = computed(() => Math.min(
    layoutPixels('--explorer-tree-min-height'), available.value * defaultRatio, preferred.value,
  ))
  const maximum = computed(() => Math.max(minimum.value, available.value - Math.min(
    layoutPixels('--explorer-preview-min-height'), available.value * (1 - defaultRatio),
  )))
  const clamp = (value: number) => Math.max(minimum.value, Math.min(maximum.value, value))
  const defaultSize = computed(() => clamp(Math.min(preferred.value, available.value * defaultRatio)))
  const size = computed(() => clamp(ratio.value === null ? defaultSize.value : available.value * ratio.value))
  function resize(value: number) {
    if (available.value > 0 && Number.isFinite(value)) ratio.value = clamp(value) / available.value
  }
  function remember(value: number) {
    if (available.value <= 0) return
    resize(value)
    try { localStorage.setItem(storageKey, String(ratio.value)) } catch { /* Optional preference. */ }
  }
  let observer: ResizeObserver | undefined
  let active = true
  function observe() {
    observer?.disconnect()
    if (!active) return
    height.value = root.value?.getBoundingClientRect().height ?? 0
    if (root.value) observer?.observe(root.value)
  }
  watch(root, observe, { flush: 'post' })
  onMounted(() => {
    observer = new ResizeObserver(([entry]) => {
      if (active && entry && entry.target === root.value) height.value = entry.contentRect.height
    })
    observe()
  })
  onActivated(() => {
    active = true
    observe()
  })
  onDeactivated(() => {
    active = false
    observer?.disconnect()
  })
  onUnmounted(() => {
    active = false
    observer?.disconnect()
  })
  return { root, dragging, size, minimum, maximum, defaultSize, resize, remember }
}
