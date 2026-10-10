/** * 提示框组件 * * 鼠标悬停时显示文字提示。 */

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  content: string
}>()

const isVisible = ref(false)
</script>

<template>
  <span class="tooltip-wrapper" @mouseenter="isVisible = true" @mouseleave="isVisible = false">
    <slot />
    <span v-if="isVisible" class="tooltip">{{ content }}</span>
  </span>
</template>

<style scoped lang="scss">
.tooltip-wrapper {
  position: relative;
  display: inline-block;
}

.tooltip {
  position: absolute;
  bottom: calc(100% + 7px);
  left: 50%;
  transform: translateX(-50%);
  padding: 6px 9px;
  border: 1px solid var(--paper-3);
  border-radius: var(--radius-sm);
  color: var(--on-accent);
  background: var(--paper-3);
  box-shadow: var(--shadow-float);
  font-size: var(--text-xs);
  white-space: nowrap;
  z-index: 100;
}
</style>
