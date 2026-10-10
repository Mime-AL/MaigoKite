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
  <CollapseCard v-if="task" :title="$t('当前任务')" icon="bolt" default-expanded>
    <div class="task-row">
      <div>
        <strong>{{ task.title }}</strong
        ><span>{{ task.status }}</span>
      </div>
      <small v-if="task.progress != null">{{ task.progress }}%</small>
    </div>
    <div v-if="task.progress != null" class="progress"><span :style="{ width: `${task.progress}%` }" /></div>
  </CollapseCard>
</template>

<style scoped lang="scss">
.task-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.task-row div {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.task-row strong {
  font-size: var(--text-xs);
}
.task-row span,
.task-row small {
  color: var(--text-secondary);
  font-size: var(--text-xs);
  text-transform: capitalize;
}
.progress {
  height: 5px;
  margin-top: 10px;
  overflow: hidden;
  border-radius: var(--radius-pill);
  background: var(--surface-strong);
}
.progress span {
  display: block;
  height: 100%;
  border-radius: var(--radius-lg);
  background: var(--paper-2);
  transition: width var(--motion-pulse) var(--ease);
}
</style>
