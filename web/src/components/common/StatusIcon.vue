<script setup lang="ts">
import IconSymbol from './IconSymbol.vue'

const props = defineProps<{ status: 'pending' | 'running' | 'completed' | 'failed' | 'paused' | 'todo' }>()
function iconName() {
  if (props.status === 'completed') return 'check'
  if (props.status === 'failed') return 'alert'
  if (props.status === 'running') return 'activity'
  return 'clock'
}
</script>

<template>
  <span class="status-icon" :class="status"><IconSymbol :name="iconName()" :size="14" /></span>
</template>

<style scoped lang="scss">
.status-icon {
  display: grid;
  width: 22px;
  height: 22px;
  place-items: center;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  background: var(--surface-strong);
}
.status-icon.running {
  color: var(--primary-color);
  background: var(--primary-soft);
}
.status-icon.completed {
  color: var(--success);
  background: var(--success-soft);
}
.status-icon.failed {
  color: var(--danger);
  background: var(--danger-soft);
}
</style>
