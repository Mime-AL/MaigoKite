<script setup lang="ts">
import { computed, onUnmounted, watch } from 'vue'
import { useLayoutStore, panelWidths } from '@/stores/layout'
import { useLayout } from '@/composables/useLayout'
const props = defineProps<{ side: 'left' | 'right'; maximum?: number }>()
const emit = defineEmits<{ dragging: [active: boolean] }>()
const layout = useLayoutStore()
const { isDragging, startDrag, stopDrag } = useLayout()
const bounds = computed(() => panelWidths[props.side])
const maximum = computed(() =>
  Math.max(bounds.value.min, Math.min(bounds.value.max, props.maximum ?? window.innerWidth)),
)
const width = computed(() =>
  Math.min(maximum.value, props.side === 'left' ? layout.sidebarWidth : layout.fileExplorerWidth),
)
let captured: HTMLElement | null = null,
  capturedId = -1
function release() {
  if (captured?.hasPointerCapture(capturedId)) captured.releasePointerCapture(capturedId)
  captured = null
}
function begin(event: PointerEvent) {
  if (event.button !== 0 || !event.isPrimary) return
  const target = event.currentTarget
  if (!(target instanceof HTMLElement)) return
  event.preventDefault()
  target.focus()
  captured = target
  capturedId = event.pointerId
  target.setPointerCapture(event.pointerId)
  const actual = target.parentElement?.getBoundingClientRect().width ?? width.value
  startDrag(props.side, event.clientX, actual, maximum.value, event.pointerId)
}
function onKey(event: KeyboardEvent) {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End', 'Enter'].includes(event.key)) return
  event.preventDefault()
  if (event.key === 'Enter') {
    layout.resetPanelWidth(props.side)
    return
  }
  const direction = (event.key === 'ArrowRight' ? 1 : -1) * (props.side === 'left' ? 1 : -1)
  const next =
    event.key === 'Home'
      ? bounds.value.min
      : event.key === 'End'
        ? maximum.value
        : width.value + direction * (event.shiftKey ? 32 : 8)
  const value = Math.max(bounds.value.min, Math.min(maximum.value, next))
  if (props.side === 'left') layout.setSidebarWidth(value)
  else layout.setFileExplorerWidth(value)
  layout.persistLayout()
}
watch(isDragging, (active) => {
  emit('dragging', active)
  if (!active) release()
})
onUnmounted(release)
</script>
<template>
  <div
    class="resize-handle"
    :class="[side, { dragging: isDragging }]"
    role="separator"
    tabindex="0"
    aria-orientation="vertical"
    :aria-label="side === 'left' ? $t('调整侧栏宽度') : $t('调整抽屉宽度')"
    :aria-valuemin="bounds.min"
    :aria-valuemax="maximum"
    :aria-valuenow="Math.round(width)"
    :title="$t('拖动调整宽度；双击还原')"
    @pointerdown="begin"
    @lostpointercapture="stopDrag"
    @keydown="onKey"
    @dblclick="layout.resetPanelWidth(side)"
  />
</template>
<style scoped lang="scss">
.resize-handle {
  position: absolute;
  inset-block: 0;
  width: 8px;
  z-index: 4;
  cursor: col-resize;
  touch-action: none;
  translate: none;
}
.left {
  right: -4px;
}
.right {
  left: -4px;
}
.resize-handle::after {
  content: '';
  position: absolute;
  inset-block: 0;
  left: 3px;
  width: 2px;
  background: var(--transparent);
  transition: background-color var(--motion-fast) var(--ease);
}
.resize-handle:hover::after,
.resize-handle:focus-visible::after,
.resize-handle.dragging::after {
  background: var(--accent);
}
</style>
