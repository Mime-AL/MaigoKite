/** * 提示框组件 * * 鼠标悬停时显示文字提示。 */

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
    <span
      v-if="isVisible"
      class="tooltip"
    >{{ content }}</span>
  </span>
</template>

<style scoped lang="scss">
.tooltip-wrapper {
  position: relative;
  display: inline-block;
}

.tooltip {
  position: absolute;
  bottom: calc(100% + var(--measure-7px));
  left: 50%;
  transform: translateX(-50%);
  padding: var(--size-6) var(--measure-9px);
  border: var(--hairline) solid var(--paper-3);
  border-radius: var(--radius-sm);
  color: var(--on-accent);
  background: var(--paper-3);
  box-shadow: var(--shadow-float);
  font-size: var(--text-xs);
  white-space: nowrap;
  z-index: var(--z-tooltip);
}
</style>
