/**
 * 左侧导航栏组件
 *
 * 包含 Logo、导航菜单、最近对话列表。
 */

<script setup lang="ts">
import NavMenu from '../sidebar/NavMenu.vue'
import RecentChats from '../sidebar/RecentChats.vue'
import { useLayoutStore } from '@/stores/layout'

const layoutStore = useLayoutStore()
</script>

<template>
  <div class="sidebar" :class="{ collapsed: layoutStore.sidebarCollapsed }">
    <div class="sidebar-header">
      <h1 class="logo" v-show="!layoutStore.sidebarCollapsed">NanamiGopher</h1>
    </div>

    <nav-menu />

    <div class="sidebar-section" v-show="!layoutStore.sidebarCollapsed">
      <h3>最近对话</h3>
      <recent-chats />
    </div>

    <div class="sidebar-footer">
      <router-link to="/settings">设置</router-link>
    </div>
  </div>
</template>

<style scoped lang="scss">
.sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: #1e1e2e;
  color: #cdd6f4;
  overflow-y: auto;

  &.collapsed {
    .sidebar-header,
    .sidebar-section,
    .sidebar-footer {
      display: none;
    }
  }
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid #313244;
}

.logo {
  margin: 0;
  font-size: 18px;
}

.sidebar-section {
  padding: 12px 16px;

  h3 {
    font-size: 12px;
    text-transform: uppercase;
    color: #6c7086;
    margin-bottom: 8px;
  }
}

.sidebar-footer {
  padding: 12px 16px;
  border-top: 1px solid #313244;
  margin-top: auto;
}
</style>
