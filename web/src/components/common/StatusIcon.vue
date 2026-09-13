/**
 * 状态图标组件
 *
 * 根据不同状态显示对应的图标。
 */

<script setup lang="ts">
defineProps<{
  status: 'pending' | 'running' | 'completed' | 'failed' | 'paused' | 'todo'
}>()
</script>

<template>
  <span class="status-icon" :class="status">
    <template v-if="status === 'pending' || status === 'todo'">&#9203;</template>
    <template v-else-if="status === 'running'">&#9881;</template>
    <template v-else-if="status === 'completed'">&#10004;</template>
    <template v-else-if="status === 'failed'">&#10008;</template>
    <template v-else-if="status === 'paused'">&#10074;&#10074;</template>
  </span>
</template>

<style scoped lang="scss">
.status-icon {
  display: inline-block;
  width: 16px;
  text-align: center;
  font-size: 14px;

  &.pending,
  &.todo {
    color: #999;
  }

  &.running {
    color: #0066cc;
    animation: spin 1s linear infinite;
  }

  &.completed {
    color: #28a745;
  }

  &.failed {
    color: #dc3545;
  }

  &.paused {
    color: #ffc107;
  }
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
