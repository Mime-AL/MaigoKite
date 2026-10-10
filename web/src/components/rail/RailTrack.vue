<script setup lang="ts">
import { computed } from 'vue'
import type { Turn } from '@/api/events'
import { railNodes } from '@/stores/run-projection'
import RailNode from './RailNode.vue'
import Receipt from './Receipt.vue'
const props = defineProps<{ turn: Turn }>()
const nodes = computed(() => railNodes(props.turn))
</script>
<template>
  <section class="rail-track" :class="{ growing: turn.status === 'running' }">
    <svg class="track-line" viewBox="0 0 2 100" preserveAspectRatio="none" aria-hidden="true">
      <path d="M1 0V100" pathLength="100" />
    </svg>
    <details v-if="turn.thinking" class="thinking">
      <summary>过程说明</summary>
      <p>{{ turn.thinking }}</p>
    </details>
    <RailNode v-for="node in nodes" :key="node.id" :node="node" :turn-id="turn.id" />
    <div class="answer"><slot /></div>
    <Receipt :turn="turn" />
  </section>
</template>
<style scoped lang="scss">
.rail-track {
  position: relative;
}
.track-line {
  position: absolute;
  left: calc(var(--rail-width) / 2);
  top: 0;
  width: 1px;
  height: 100%;
  overflow: visible;
  stroke: var(--rule);
  stroke-width: 1;
}
.track-line path {
  vector-effect: non-scaling-stroke;
}
.growing .track-line path {
  stroke: var(--accent);
  stroke-dasharray: 100;
  animation: ink-grow var(--motion-grow) var(--ease);
}
.answer,
.thinking {
  position: relative;
  margin-left: calc(var(--rail-width) + 12px);
}
.thinking {
  color: var(--ink-3);
  font-size: var(--text-xs);
  padding: 8px 0;
}
.thinking p {
  white-space: pre-wrap;
  max-height: 220px;
  overflow: auto;
  line-height: var(--leading-small);
}
summary {
  cursor: pointer;
}
.answer {
  padding-top: 12px;
}
</style>
