<script setup lang="ts">
import { useInspectorStore } from '@/stores/inspector'

const inspectorStore = useInspectorStore()
const dimensions = [{ value: 'task', label: '任务' }, { value: 'tool', label: '工具' }, { value: 'model', label: '模型' }, { value: 'subagent', label: 'SubAgent' }, { value: 'error', label: '异常' }]
</script>

<template><div class="dimension-selector"><button v-for="item in dimensions" :key="item.value" type="button" :aria-pressed="inspectorStore.selectedDimensions.includes(item.value)" :class="{ active: inspectorStore.selectedDimensions.includes(item.value) }" @click="inspectorStore.toggleDimension(item.value)">{{ item.label }}</button></div></template>

<style scoped lang="scss">
.dimension-selector { display: flex; gap: 3px; padding: 3px; border-radius: 11px; background: var(--surface-strong); }.dimension-selector button { height: 28px; padding: 0 9px; border: 0; border-radius: 8px; color: var(--text-tertiary); background: transparent; cursor: pointer; font-size: 9px; }.dimension-selector button.active { color: var(--text-primary); background: var(--surface-solid); box-shadow: 0 2px 7px rgba(0,0,0,.08); }
</style>
