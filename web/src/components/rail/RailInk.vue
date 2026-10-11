<script setup lang="ts">
defineProps<{ active?: boolean }>()
const gradient = 'ink-tail-' + Array.from(crypto.getRandomValues(new Uint32Array(2)), value => value.toString(16)).join('-')
</script>
<template>
  <svg
    class="rail-ink"
    :class="{ active }"
    viewBox="0 0 16 100"
    preserveAspectRatio="none"
    aria-hidden="true"
  >
    <defs v-if="active"><linearGradient
      :id="gradient"
      x1="0"
      y1="0"
      x2="0"
      y2="1"
    ><stop
      class="tail"
      offset="0"
    /><stop
      class="head"
      offset="1"
    /></linearGradient></defs>
    <path
      class="brush"
      :style="active ? { fill: 'url(#' + gradient + ')' } : undefined"
      d="M8 0C3 22 13 36 8 55S5 81 8 100L9 100C6 80 12 65 9 55S7 20 8 0Z"
    />
    <path
      class="hair"
      d="M10 0C8 29 12 47 10 65S9 89 10 100"
    />
  </svg>
</template>
<style scoped lang="scss">
.rail-ink {
  position: absolute;
  left: calc((var(--rail-width) - var(--rail-path-width)) / 2);
  top: 0;
  width: var(--rail-path-width);
  height: 100%;
  pointer-events: none;
  color: var(--preview-rail-idle);
}
.brush {
  fill: currentColor;
}
.tail, .head { stop-color: currentColor; }
.tail { stop-opacity: var(--rail-soft-opacity); }
.hair {
  fill: none;
  stroke: currentColor;
  stroke-width: var(--rail-hair-stroke);
  vector-effect: non-scaling-stroke;
  opacity: var(--rail-soft-opacity);
}
.active {
  color: var(--accent);
  transform-origin: top;
  animation: ink-reveal var(--motion-grow) var(--ease-out) both;
}
@media (prefers-reduced-motion: reduce) {
  .active {
    animation: paper-fade var(--motion-reduced) var(--ease-out) both !important;
  }
}
</style>
