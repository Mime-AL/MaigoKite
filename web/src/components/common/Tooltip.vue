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
  bottom: calc(100% + 7px);
  left: 50%;
  transform: translateX(-50%);
  padding: 6px 9px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: #fff;
  background: rgba(32, 32, 36, 0.92);
  box-shadow: var(--shadow-float);
  font-size: 10px;
  white-space: nowrap;
  z-index: 100;
}
</style>
