<script setup lang="ts">
import type { PresentationNode } from '@/utils/rail-presentation'
defineProps<{ kind: PresentationNode['kind']; waiting?: boolean; running?: boolean }>()
</script>
<template>
  <svg
    class="rail-glyph"
    :class="{ waiting, running }"
    viewBox="0 0 24 24"
    fill="none"
    aria-hidden="true"
  >
    <path
      v-if="waiting || kind === 'await'"
      d="M12 4 20 12 12 20 4 12Z"
    />
    <path
      v-else-if="kind === 'failed'"
      class="cross"
      d="m6 6 12 12M18 6 6 18"
    />
    <path
      v-else-if="kind === 'memory'"
      d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z"
    />
    <path
      v-else-if="kind === 'input'"
      d="M5 7h8m-3-3 3 3-3 3M19 17h-8m3-3-3 3 3 3"
    />
    <path
      v-else-if="kind === 'end'"
      class="filled"
      d="m12 6 6 6-6 6-6-6Z"
    />
    <circle
      v-else
      cx="12"
      cy="12"
      r="5.5"
      :class="{ filled: kind === 'act' }"
    />
  </svg>
</template>
<style scoped lang="scss">
.rail-glyph {
  display: block;
  width: var(--rail-glyph-size);
  height: var(--rail-glyph-size);
  stroke: currentColor;
  stroke-width: var(--rail-glyph-stroke);
  stroke-linecap: round;
  stroke-linejoin: round;
  animation: ink-land var(--motion-panel) var(--ease-spring) both;
}
.filled {
  fill: currentColor;
}
.waiting {
  animation: ink-wait var(--motion-pulse) var(--ease-in-out) infinite;
}
.running {
  animation: ink-breathe var(--motion-pulse) var(--ease) infinite;
}
@media (prefers-reduced-motion: reduce) {
  .rail-glyph {
    animation: paper-fade var(--motion-reduced) var(--ease-out) both !important;
  }
}
</style>
