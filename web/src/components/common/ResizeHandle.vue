<script setup lang="ts">
import { computed, onDeactivated, onUnmounted, ref, watch } from 'vue'
import { useLayoutStore, panelWidths } from '@/stores/layout'
import { useLayout } from '@/composables/useLayout'
import { layoutPixels } from '@/utils/layout-media'
const props = withDefaults(
  defineProps<{
    side?: 'left' | 'right'
    orientation?: 'vertical' | 'horizontal'
    modelValue?: number
    minimum?: number
    maximum?: number
    defaultValue?: number
    label?: string
    hint?: string
  }>(),
  { side: 'left', orientation: 'vertical' },
)
const emit = defineEmits<{
  dragging: [active: boolean]
  'update:modelValue': [value: number]
  change: [value: number]
}>()
const layout = useLayoutStore()
const { isDragging: widthDragging, startDrag, stopDrag } = useLayout()
const horizontal = computed(() => props.orientation === 'horizontal')
const heightDragging = ref(false)
const isDragging = computed(() => widthDragging.value || heightDragging.value)
const minimum = computed(() =>
  horizontal.value ? (props.minimum ?? 0) : panelWidths[props.side].min,
)
const maximum = computed(() =>
  Math.max(
    minimum.value,
    horizontal.value
      ? (props.maximum ?? window.innerHeight)
      : Math.min(panelWidths[props.side].max, props.maximum ?? window.innerWidth),
  ),
)
const value = computed(() =>
  clamp(horizontal.value
    ? (props.modelValue ?? minimum.value)
    : props.side === 'left' ? layout.sidebarWidth : layout.fileExplorerWidth),
)
let captured: HTMLElement | null = null,
  capturedId = -1
let startY = 0,
  startHeight = 0,
  dragValue = 0,
  frame = 0
let pendingY: number | null = null
function clamp(next: number) {
  return Math.max(minimum.value, Math.min(maximum.value, next))
}
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
  if (horizontal.value) {
    startY = event.clientY
    startHeight = dragValue = value.value
    heightDragging.value = true
    window.addEventListener('blur', finish)
    return
  }
  const actual = target.parentElement?.getBoundingClientRect().width ?? value.value
  startDrag(props.side, event.clientX, actual, maximum.value, event.pointerId)
}
function flushHeight() {
  if (pendingY === null) return
  dragValue = clamp(startHeight + pendingY - startY)
  pendingY = null
  emit('update:modelValue', dragValue)
}
function move(event: PointerEvent) {
  if (!heightDragging.value || event.pointerId !== capturedId) return
  pendingY = event.clientY
  // Coalesce pointer movement; only persist once the gesture finishes.
  if (!frame) {
    frame = requestAnimationFrame(() => {
      frame = 0
      flushHeight()
    })
  }
}
function finish() {
  if (frame) cancelAnimationFrame(frame)
  frame = 0
  if (heightDragging.value) {
    flushHeight()
    heightDragging.value = false
    emit('change', clamp(dragValue))
  }
  window.removeEventListener('blur', finish)
  stopDrag()
  release()
}
function finishPointer(event: PointerEvent) {
  if (event.pointerId !== capturedId) return
  if (heightDragging.value && event.type === 'pointerup') pendingY = event.clientY
  finish()
}
function reset() {
  if (!horizontal.value) return layout.resetPanelWidth(props.side)
  const next = clamp(props.defaultValue ?? minimum.value)
  emit('update:modelValue', next)
  emit('change', next)
}
function onKey(event: KeyboardEvent) {
  const previous = horizontal.value ? 'ArrowUp' : 'ArrowLeft'
  const nextKey = horizontal.value ? 'ArrowDown' : 'ArrowRight'
  if (![previous, nextKey, 'Home', 'End', 'Enter'].includes(event.key)) return
  event.preventDefault()
  if (event.key === 'Enter') {
    reset()
    return
  }
  const direction =
    (event.key === nextKey ? 1 : -1) * (horizontal.value || props.side === 'left' ? 1 : -1)
  const next =
    event.key === 'Home'
      ? minimum.value
      : event.key === 'End'
        ? maximum.value
        : value.value + direction * layoutPixels(event.shiftKey ? '--resize-step-fast' : '--resize-step')
  const adjusted = clamp(next)
  if (horizontal.value) {
    emit('update:modelValue', adjusted)
    emit('change', adjusted)
    return
  }
  if (props.side === 'left') layout.setSidebarWidth(adjusted)
  else layout.setFileExplorerWidth(adjusted)
  layout.persistLayout()
}
watch(isDragging, (active) => {
  emit('dragging', active)
  if (!active) release()
})
onDeactivated(finish)
onUnmounted(finish)
</script>
<template>
  <div
    class="resize-handle"
    :class="[horizontal ? 'horizontal' : side, { dragging: isDragging }]"
    role="separator"
    tabindex="0"
    :aria-orientation="orientation"
    :aria-label="label || (horizontal ? $t('调整文件树与预览的高度') : side === 'left' ? $t('调整侧栏宽度') : $t('调整抽屉宽度'))"
    :aria-valuemin="minimum"
    :aria-valuemax="maximum"
    :aria-valuenow="Math.round(value)"
    :title="hint || (horizontal ? $t('拖动调整文件树和预览；双击还原') : $t('拖动调整宽度；双击还原'))"
    @pointerdown="begin"
    @pointermove="move"
    @pointerup="finishPointer"
    @pointercancel="finishPointer"
    @lostpointercapture="finishPointer"
    @keydown="onKey"
    @dblclick="reset"
  />
</template>
<style scoped lang="scss">
.resize-handle {
  position: absolute;
  inset-block: 0;
  width: var(--space-3);
  z-index: var(--z-resize);
  cursor: col-resize;
  touch-action: none;
  translate: none;
}
.left {
  right: calc(-1 * var(--space-2));
}
.right {
  left: calc(-1 * var(--space-2));
}
.resize-handle::after {
  content: '';
  position: absolute;
  inset-block: 0;
  left: var(--focus-offset);
  width: var(--space-1);
  background: var(--transparent);
  transition:
    transform var(--motion-fast) var(--ease),
    opacity var(--motion-fast) var(--ease);
}
.resize-handle:hover::after,
.resize-handle:focus-visible::after,
.resize-handle.dragging::after {
  background: var(--accent);
}
.horizontal {
  position: relative;
  inset: auto;
  flex: none;
  width: 100%;
  height: var(--explorer-split-handle-height);
  cursor: row-resize;
  background: var(--paper-3);
}
.horizontal::before {
  content: '';
  position: absolute;
  inset-inline: 0;
  top: 50%;
  height: var(--hairline);
  background: var(--rule);
}
.horizontal::after {
  inset: auto;
  top: 50%;
  left: 50%;
  width: var(--space-8);
  height: var(--space-1);
  transform: translate(-50%, -50%);
  border-radius: var(--radius-round);
  background: var(--ink-3);
}
</style>
