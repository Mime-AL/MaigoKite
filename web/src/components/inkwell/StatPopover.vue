<script setup lang="ts">
import { nextTick, onMounted, onScopeDispose, ref } from 'vue'
defineProps<{ label: string; title?: string }>()
const trigger = ref<HTMLButtonElement | null>(null),
  panel = ref<HTMLElement | null>(null)
const open = ref(false),
  position = ref({ left: '0px', top: '0px' })
async function toggle() {
  open.value = !open.value
  if (!open.value) return
  await nextTick()
  const anchor = trigger.value?.getBoundingClientRect(),
    bounds = panel.value?.getBoundingClientRect()
  if (!anchor || !bounds) return
  position.value = {
    left: `${Math.max(8, Math.min(window.innerWidth - bounds.width - 8, anchor.left + anchor.width / 2 - bounds.width / 2))}px`,
    top: `${Math.max(44, anchor.top - bounds.height - 8)}px`,
  }
}
function outside(event: PointerEvent) {
  if (
    event.target instanceof Node &&
    !trigger.value?.contains(event.target) &&
    !panel.value?.contains(event.target)
  )
    open.value = false
}
function escape(event: KeyboardEvent) {
  if (open.value && event.key === 'Escape') {
    event.preventDefault()
    event.stopImmediatePropagation()
    open.value = false
    trigger.value?.focus()
  }
}
function close() {
  open.value = false
}
onMounted(() => {
  document.addEventListener('pointerdown', outside)
  document.addEventListener('keydown', escape, true)
  window.addEventListener('resize', close)
})
onScopeDispose(() => {
  document.removeEventListener('pointerdown', outside)
  document.removeEventListener('keydown', escape, true)
  window.removeEventListener('resize', close)
})
</script>
<template>
  <button
    ref="trigger"
    class="stat-pill"
    :title="title || label"
    :aria-label="label"
    :aria-expanded="open"
    aria-haspopup="dialog"
    @click="toggle"
  >
    <slot name="trigger" />
  </button>
  <Teleport to="body">
    <section
      v-if="open"
      ref="panel"
      class="stat-panel"
      :style="position"
      role="dialog"
      :aria-label="label"
    >
      <h3>{{ label }}</h3>
      <slot />
    </section>
  </Teleport>
</template>
<style scoped lang="scss">
@use '@/styles/mixins' as mixins;
.stat-pill {
  @include mixins.interactive-row;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 0;
  border-radius: var(--radius-pill);
  padding: 2px 8px;
  background: var(--transparent);
  color: var(--ink-2);
  font-size: var(--text-xs);
  line-height: var(--leading-small);
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
.stat-pill[aria-expanded='true'] {
  background: var(--paper-2);
  color: var(--ink);
}
.stat-panel {
  position: fixed;
  z-index: 100;
  width: min(304px, calc(100vw - 16px));
  max-height: calc(100vh - 60px);
  overflow-y: auto;
  padding: 16px;
  border: 1px solid var(--rule);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-float);
  background: var(--paper);
  color: var(--ink-2);
  font-size: var(--text-xs);
  line-height: var(--leading-small);
}
h3 {
  margin: 0 0 12px;
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  color: var(--ink);
}
</style>
