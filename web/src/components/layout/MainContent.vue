/**
 * 中间工作区组件
 *
 * 路由视图容器，渲染当前路由对应的页面组件。
 */

<script setup lang="ts">
</script>

<template>
  <div class="main-content">
    <router-view />
  </div>
</template>

<style scoped lang="scss">
.main-content {
  height: 100%;
  overflow: auto;
  background-color: #ffffff;
}
</style>
