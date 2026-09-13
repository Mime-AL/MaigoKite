/**
 * 导航项组件
 *
 * 单个导航菜单项，支持图标和路由链接。
 */

<script setup lang="ts">
defineProps<{
  icon: string
  to: string
  label: string
}>()
</script>

<template>
  <router-link :to="to" class="nav-item">
    <span class="nav-icon">{{ icon }}</span>
    <span class="nav-label">{{ label }}</span>
  </router-link>
</template>

<style scoped lang="scss">
.nav-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  color: #bac2de;
  text-decoration: none;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.2s;

  &:hover {
    background-color: #313244;
  }
}

.nav-icon {
  width: 20px;
  text-align: center;
}
</style>
