/**
 * 维度选择器组件
 *
 * 允许用户选择要在时间线中显示的维度。
 */

<script setup lang="ts">
import { useInspectorStore } from '@/stores/inspector'

const inspectorStore = useInspectorStore()

const availableDimensions = [
  { value: 'task', label: '任务' },
  { value: 'tool', label: '工具' },
  { value: 'model', label: '模型' },
  { value: 'subagent', label: 'SubAgent' },
  { value: 'error', label: '异常' }
] as const

function toggleDimension(dim: string) {
  inspectorStore.toggleDimension(dim)
}
</script>

<template>
  <div class="dimension-selector">
    <label v-for="dim in availableDimensions" :key="dim.value" class="dimension-item">
      <input
        type="checkbox"
        :value="dim.value"
        :checked="inspectorStore.selectedDimensions.includes(dim.value)"
        @change="toggleDimension(dim.value)"
      />
      {{ dim.label }}
    </label>
  </div>
</template>

<style scoped lang="scss">
.dimension-selector {
  display: flex;
  gap: 12px;
  font-size: 13px;
}

.dimension-item {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
}
</style>
