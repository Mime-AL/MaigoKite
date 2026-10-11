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
  <CollapseCard
    v-if="task"
    :title="$t('当前任务')"
    icon="bolt"
    default-expanded
  >
    <div class="task-row">
      <div>
        <strong>{{ task.title }}</strong><span>{{ task.status }}</span>
      </div>
      <small v-if="task.progress != null">{{ task.progress }}%</small>
    </div>
    <div
      v-if="task.progress != null"
      class="progress"
    >
      <span :style="{ width: `${task.progress}%` }" />
    </div>
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
  gap: var(--focus-offset);
}
.task-row strong {
  font-size: var(--text-xs);
}
.task-row span,
.task-row small {
  color: var(--ink-2);
  font-size: var(--text-xs);
  text-transform: capitalize;
}
.progress {
  height: var(--measure-5px);
  margin-top: var(--size-10);
  overflow: hidden;
  border-radius: var(--radius-pill);
  background: var(--paper-3);
}
.progress span {
  display: block;
  height: 100%;
  border-radius: var(--radius-lg);
  background: var(--paper-2);
  transition: none;
}
</style>
