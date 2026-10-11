<script setup lang="ts">
import CollapseCard from '../common/CollapseCard.vue'
import StatusIcon from '../common/StatusIcon.vue'

defineProps<{
  steps?: Array<{ id: string; title: string; status: 'todo' | 'running' | 'completed' | 'failed' }>
}>()
</script>

<template>
  <CollapseCard
    v-if="steps?.length"
    :title="$t('执行步骤')"
    icon="activity"
    default-expanded
  >
    <div class="step-list">
      <div
        v-for="step in steps"
        :key="step.id"
        class="step-item"
        :class="step.status"
      >
        <StatusIcon :status="step.status" />
        <span>{{ step.title }}</span>
      </div>
    </div>
  </CollapseCard>
</template>

<style scoped lang="scss">
.step-list {
  display: grid;
  gap: var(--measure-5px);
}
.step-item {
  display: flex;
  min-height: var(--measure-34px);
  align-items: center;
  gap: var(--measure-9px);
  color: var(--ink-2);
  font-size: var(--text-xs);
}
.step-item.running {
  color: var(--ink);
  font-weight: var(--weight-semibold);
}
</style>
