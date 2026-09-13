/**
 * 导航菜单组件
 *
 * 按功能分组展示所有导航项。
 */

<script setup lang="ts">
import NavItem from './NavItem.vue'
</script>

<template>
  <nav class="nav-menu">
    <!-- 核心功能 -->
    <div class="nav-group">
      <NavItem icon="home" to="/" label="总览" />
      <NavItem icon="plus" to="/chat/new" label="新建对话" />
      <NavItem icon="search" to="/search" label="搜索" />
    </div>

    <!-- 工具功能 -->
    <div class="nav-group">
      <NavItem icon="clock" to="/scheduled-tasks" label="定时任务" />
      <NavItem icon="browser" to="/browser" label="浏览器" />
      <NavItem icon="package" to="/packages" label="包管理" />
      <NavItem icon="skill" to="/skills" label="Skill 管理" />
    </div>

    <!-- 管理功能 -->
    <div class="nav-group">
      <NavItem icon="review" to="/daily-review" label="每日回顾" />
      <NavItem icon="plan" to="/long-term-plan" label="长期计划" />
      <NavItem icon="archive" to="/archive" label="归档" />
    </div>
  </nav>
</template>

<style scoped lang="scss">
.nav-menu {
  padding: 8px 0;
}

.nav-group {
  padding: 4px 0;
  border-bottom: 1px solid #313244;

  &:last-child {
    border-bottom: none;
  }
}
</style>
