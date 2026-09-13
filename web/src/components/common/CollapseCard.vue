/**
 * 折叠卡片组件
 *
 * 可展开/收起的内容卡片。
 */

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
  title: string
  defaultExpanded?: boolean
}>()

const isExpanded = ref(props.defaultExpanded ?? false)

watch(
  () => props.defaultExpanded,
  (val) => {
    isExpanded.value = val
  }
)

function toggle() {
  isExpanded.value = !isExpanded.value
}
</script>

<template>
  <div class="collapse-card">
    <div class="card-header" @click="toggle">
      <span class="card-title">{{ title }}</span>
      <span class="collapse-icon">{{ isExpanded ? '▲' : '▼' }}</span>
    </div>
    <div v-if="isExpanded" class="card-body">
      <slot />
    </div>
  </div>
</template>

<style scoped lang="scss">
.collapse-card {
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  margin-bottom: 8px;
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 14px;
  background-color: #f9f9f9;
  cursor: pointer;
  user-select: none;

  &:hover {
    background-color: #f0f0f0;
  }
}

.card-title {
  font-size: 14px;
  font-weight: 500;
}

.collapse-icon {
  font-size: 12px;
  color: #999;
}

.card-body {
  padding: 8px 14px;
}
</style>
