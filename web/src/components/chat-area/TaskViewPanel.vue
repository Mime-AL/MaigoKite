/**
 * 任务视图面板组件
 *
 * 展示当前任务的整体信息和状态。
 */

<script setup lang="ts">
import CollapseCard from '../common/CollapseCard.vue'

defineProps<{
  task?: {
    id: string
    title: string
    status: 'queued' | 'running' | 'paused' | 'completed' | 'failed' | 'timeout'
    progress?: number
  }
}>()
</script>

<template>
  <CollapseCard title="任务">
    <div class="task-info" v-if="task">
      <h4>{{ task.title }}</h4>
      <p>状态: {{ task.status }}</p>
      <div class="progress-bar" v-if="task.progress != null">
        <div class="progress-fill" :style="{ width: task.progress + '%' }" />
      </div>
    </div>
    <p v-else class="empty">暂无活跃任务</p>
  </CollapseCard>
</template>

<style scoped lang="scss">
.task-info {
  padding: 8px 16px;

  h4 {
    margin: 0 0 4px 0;
  }

  p {
    margin: 0;
    font-size: 13px;
    color: #666;
  }
}

.progress-bar {
  height: 4px;
  background-color: #e0e0e0;
  border-radius: 2px;
  margin-top: 8px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background-color: #0066cc;
  transition: width 0.3s;
}

.empty {
  padding: 8px 16px;
  color: #999;
  font-size: 13px;
}
</style>
