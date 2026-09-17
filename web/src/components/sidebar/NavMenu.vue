<script setup lang="ts">
import { useLayoutStore } from '@/stores/layout'
import NavItem from './NavItem.vue'

const layoutStore = useLayoutStore()
const workspaceItems = [
  { icon: 'home', to: '/', label: '总览' },
  { icon: 'shield', to: '/audit', label: '审计日志' },
]
</script>

<template>
  <nav class="nav-menu" aria-label="主导航">
    <div class="nav-group">
      <p v-show="!layoutStore.sidebarCollapsed" class="group-label">工作区</p>
      <NavItem v-for="item in workspaceItems" :key="item.to" v-bind="item" />
    </div>
  </nav>
</template>

<style scoped lang="scss">
.nav-menu { display: flex; flex-direction: column; gap: 11px; }
.nav-group { display: grid; gap: 2px; }
.group-label { margin: 0; padding: 0 10px 4px; color: var(--text-tertiary); font-size: 10px; font-weight: 700; letter-spacing: 0.055em; text-transform: uppercase; }
</style>
