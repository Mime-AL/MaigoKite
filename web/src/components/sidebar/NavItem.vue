<script setup lang="ts">
import { useLayoutStore } from '@/stores/layout'
import IconSymbol from '@/components/common/IconSymbol.vue'

defineProps<{ icon: string; to: string; label: string }>()
const layoutStore = useLayoutStore()
</script>

<template>
  <router-link :to="to" class="nav-item" :title="layoutStore.sidebarCollapsed ? label : undefined">
    <IconSymbol :name="icon" :size="17" />
    <span v-show="!layoutStore.sidebarCollapsed" class="nav-label">{{ label }}</span>
  </router-link>
</template>

<style scoped lang="scss">
.nav-item {
  display: flex;
  height: 34px;
  align-items: center;
  gap: 10px;
  padding: 0 10px;
  border-radius: 10px;
  color: var(--text-secondary);
  font-size: 12.5px;
  font-weight: 520;
  transition: color 140ms ease, background 140ms ease, transform 140ms ease;
}
.nav-item:hover { color: var(--text-primary); background: var(--surface-strong); }
.nav-item:active { transform: scale(0.98); }
.nav-item.router-link-exact-active { color: var(--text-primary); background: rgba(255, 255, 255, 0.7); box-shadow: 0 1px 3px rgba(26, 33, 48, 0.08), inset 0 0 0 1px var(--border-color); }
.nav-label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
@media (prefers-color-scheme: dark) { .nav-item.router-link-exact-active { background: rgba(255, 255, 255, 0.1); } }
</style>
