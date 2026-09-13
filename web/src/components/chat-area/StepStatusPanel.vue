/**
 * 步骤状态面板组件
 *
 * 展示当前任务的步骤执行进度。
 */

<script setup lang="ts">
import CollapseCard from '../common/CollapseCard.vue'

defineProps<{
  steps?: Array<{
    id: string
    title: string
    status: 'todo' | 'running' | 'completed' | 'failed'
  }>
}>()
</script>

<template>
  <CollapseCard title="执行步骤">
    <div class="step-list">
      <div
        v-for="step in steps"
        :key="step.id"
        class="step-item"
        :class="step.status"
      >
        <StatusIcon :status="step.status" />
        <span class="step-title">{{ step.title }}</span>
      </div>
    </div>
  </CollapseCard>
</template>

<style scoped lang="scss">
.step-list {
  padding: 8px 0;
}

.step-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  font-size: 14px;

  &.running {
    color: #0066cc;
  }

  &.completed {
    color: #28a745;
  }

  &.failed {
    color: #dc3545;
  }

  &.todo {
    color: #999;
  }
}
</style>
