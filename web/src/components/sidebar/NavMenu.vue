<script setup lang="ts">
import { useLayoutStore } from '@/stores/layout'
import NavItem from './NavItem.vue'

const layoutStore = useLayoutStore()
const workspaceItems = [
  { icon: 'home', to: '/', label: '总览' },
  { icon: 'cube', to: '/integrations', label: '扩展' },
  { icon: 'shield', to: '/audit', label: '审计日志' },
]
const dataItems = [
  { icon: 'brain', to: '/memory', label: '记忆' },
  { icon: 'archive', to: '/data', label: '数据概览' },
]
</script>

<template>
  <nav class="nav-menu" :aria-label="$t('主导航')">
    <div class="nav-group">
      <p v-show="!layoutStore.sidebarCollapsed" class="group-label">{{ $t('工作区') }}</p>
      <NavItem v-for="item in workspaceItems" :key="item.to" v-bind="item" />
    </div>
    <div class="nav-group">
      <p v-show="!layoutStore.sidebarCollapsed" class="group-label">{{ $t('数据') }}</p>
      <NavItem v-for="item in dataItems" :key="item.to" v-bind="item" />
    </div>
  </nav>
</template>

<style scoped lang="scss">
.nav-menu {
  display: flex;
  flex-direction: column;
  gap: 11px;
}
.nav-group {
  display: grid;
  gap: 2px;
}
.group-label {
  margin: 0;
  padding: 0 10px 4px;
  color: var(--text-secondary);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  letter-spacing: 0.055em;
  text-transform: uppercase;
}
</style>
