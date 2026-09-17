<script setup lang="ts">
import CollapseCard from '../common/CollapseCard.vue'

defineProps<{ task?: { id: string; title: string; status: 'queued' | 'running' | 'paused' | 'completed' | 'failed' | 'timeout'; progress?: number } }>()
</script>

<template>
  <CollapseCard v-if="task" title="当前任务" icon="bolt" default-expanded>
    <div class="task-row">
      <div><strong>{{ task.title }}</strong><span>{{ task.status }}</span></div>
      <small v-if="task.progress != null">{{ task.progress }}%</small>
    </div>
    <div v-if="task.progress != null" class="progress"><span :style="{ width: `${task.progress}%` }" /></div>
  </CollapseCard>
</template>

<style scoped lang="scss">
.task-row { display: flex; align-items: center; justify-content: space-between; }
.task-row div { display: flex; flex-direction: column; gap: 3px; }
.task-row strong { font-size: 11px; }
.task-row span, .task-row small { color: var(--text-tertiary); font-size: 9px; text-transform: capitalize; }
.progress { height: 5px; margin-top: 10px; overflow: hidden; border-radius: 999px; background: var(--surface-strong); }
.progress span { display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, #0a84ff, #6a8dff); transition: width 260ms ease; }
</style>
