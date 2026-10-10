<script setup lang="ts">
defineProps<{ modelValue: 'ask' | 'plan' | 'auto'; disabled?: boolean }>()
const emit = defineEmits<{ (event: 'update:modelValue', mode: 'ask' | 'plan' | 'auto'): void }>()
const modes = [
  { id: 'ask', label: '问', title: '只读：回答问题' },
  { id: 'plan', label: '谋', title: '只读：先列出计划' },
  { id: 'auto', label: '做', title: '在工作区执行任务' },
] as const
</script>
<template>
  <div class="mode-pill" aria-label="工作方式">
    <button
      v-for="mode in modes"
      :key="mode.id"
      :title="mode.title"
      :aria-pressed="modelValue === mode.id"
      :disabled="disabled"
      @click="emit('update:modelValue', mode.id)"
    >
      {{ mode.label }}
    </button>
  </div>
</template>
<style scoped lang="scss">
@use '@/styles/mixins' as mixins;
.mode-pill {
  display: inline-flex;
  padding: 2px;
  border: 1px solid var(--rule);
  border-radius: var(--radius-sm);
}
button {
  @include mixins.interactive-row;
  border: 0;
  width: 28px;
  height: 24px;
  color: var(--ink-3);
  background: var(--transparent);
  font-size: var(--text-sm);
}
button[aria-pressed='true'] {
  color: var(--accent);
  background: var(--accent-selected);
  font-weight: var(--weight-semibold);
}
</style>
