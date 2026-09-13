/**
 * Inspector 监控页
 *
 * 展示活跃/已完成/失败的对话卡片和时间线。
 */

<script setup lang="ts">
import InspectorView from '@/components/inspector/InspectorView.vue'
</script>

<template>
  <div class="inspector-page">
    <InspectorView />
  </div>
</template>

<style scoped lang="scss">
.inspector-page {
  height: 100%;
}
</style>
