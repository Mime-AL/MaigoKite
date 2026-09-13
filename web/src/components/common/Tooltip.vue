/**
 * 提示框组件
 *
 * 鼠标悬停时显示文字提示。
 */

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  content: string
}>()

const isVisible = ref(false)
</script>

<template>
  <span
    class="tooltip-wrapper"
    @mouseenter="isVisible = true"
    @mouseleave="isVisible = false"
  >
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
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  padding: 4px 8px;
  background-color: #333;
  color: #fff;
  font-size: 12px;
  border-radius: 4px;
  white-space: nowrap;
  z-index: 100;
}

.tooltip::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 4px solid transparent;
  border-top-color: #333;
}
</style>
