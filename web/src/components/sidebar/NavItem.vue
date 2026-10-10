<script setup lang="ts">
import { useLayoutStore } from '@/stores/layout'
import IconSymbol from '@/components/common/IconSymbol.vue'

defineProps<{ icon: string; to: string; label: string }>()
const layoutStore = useLayoutStore()
</script>

<template>
  <router-link :to="to" class="nav-item" :title="layoutStore.sidebarCollapsed ? $t(label) : undefined">
    <IconSymbol :name="icon" :size="17" />
    <span v-show="!layoutStore.sidebarCollapsed" class="nav-label">{{ $t(label) }}</span>
  </router-link>
</template>

<style scoped lang="scss">
.nav-item {
  display: flex;
  height: 34px;
  align-items: center;
  gap: 10px;
  padding: 0 10px;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
  transition:
    color var(--motion-pulse) var(--ease),
    background var(--motion-pulse) var(--ease),
    transform var(--motion-pulse) var(--ease);
}
.nav-item:hover {
  color: var(--text-primary);
  background: var(--surface-strong);
}
.nav-item:active {
  transform: scale(0.98);
}
.nav-item.router-link-exact-active {
  color: var(--text-primary);
  background: var(--paper-3);
  box-shadow: var(--shadow-card);
}
.nav-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
@media (prefers-color-scheme: dark) {
  .nav-item.router-link-exact-active {
    background: var(--paper-3);
  }
}
</style>
