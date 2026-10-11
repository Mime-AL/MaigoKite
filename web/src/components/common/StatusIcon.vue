<script setup lang="ts">
import IconSymbol from './IconSymbol.vue'

const props = defineProps<{
  status: 'pending' | 'running' | 'completed' | 'failed' | 'paused' | 'todo'
}>()
function iconName() {
  if (props.status === 'completed') return 'check'
  if (props.status === 'failed') return 'alert'
  if (props.status === 'running') return 'activity'
  return 'clock'
}
</script>

<template>
  <span
    class="status-icon"
    :class="status"
  ><IconSymbol
    :name="iconName()"
    :size="14"
  /></span>
</template>

<style scoped lang="scss">
.status-icon {
  display: grid;
  width: var(--measure-22px);
  height: var(--measure-22px);
  place-items: center;
  border-radius: var(--radius-sm);
  color: var(--ink-2);
  background: var(--paper-3);
}
.status-icon.running {
  color: var(--accent);
  background: var(--accent-soft);
}
.status-icon.completed {
  color: var(--ink-2);
  background: var(--paper-2);
}
.status-icon.failed {
  color: var(--ink-2);
  background: var(--paper-2);
}
</style>
