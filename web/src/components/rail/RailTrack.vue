<script setup lang="ts">
import { t } from '@/i18n'
import { computed, ref, watch } from 'vue'
import type { RailNode as ActivityNode, Turn } from '@/api/events'
import { railNodes } from '@/stores/run-projection'
import IconSymbol from '@/components/common/IconSymbol.vue'
import RailNode from './RailNode.vue'
import Receipt from './Receipt.vue'
const props = defineProps<{ turn: Turn }>()
const nodes = computed(() => railNodes(props.turn))
function needsAttention(node: ActivityNode) {
  return node.kind === 'failed' || Boolean(node.await && !node.await.verdict &&
    !node.await.closed && node.await.answer === undefined)
}
const attentionNodes = computed(() => nodes.value.filter(needsAttention))
const processNodes = computed(() => nodes.value.filter((node) => !needsAttention(node)))
const hasThinking = computed(() => Boolean(props.turn.thinking || props.turn.thinkingStatus === 'running'))
const active = computed(() => ['running', 'waiting'].includes(props.turn.status))
const expanded = ref(active.value || Boolean(attentionNodes.value.length))
const thinkingExpanded = ref(active.value)
const heading = computed(() => {
  const turn = props.turn
  if (turn.status === 'waiting') return t("等待你确认")
  if (turn.status === 'failed') return t("执行遇到问题")
  if (turn.status === 'cancelled') return t("已停止")
  if (turn.status === 'completed') return attentionNodes.value.length ? t("有操作需要查看") : t("已完成")
  const step = [...turn.steps].reverse().find((item) => item.status === 'running')
  if (step) return step.title
  if (turn.steps.some((item) => item.status === 'pending')) return t("等待执行")
  if (turn.thinkingStatus === 'running' && !turn.text) return t("正在思考")
  return turn.text ? t("正在回复") : t("正在处理")
})
watch(() => props.turn.status, () => {
  expanded.value = active.value || Boolean(attentionNodes.value.length)
})
watch(() => attentionNodes.value.map((node) => node.id).join('|'), (ids) => {
  if (ids) expanded.value = true
})
watch(() => props.turn.thinkingStatus, (status) => {
  if (status === 'running') thinkingExpanded.value = true
})
function toggleProcess(event: Event) {
  if (event.currentTarget instanceof HTMLDetailsElement) expanded.value = event.currentTarget.open
}
function toggleThinking(event: Event) {
  if (event.currentTarget instanceof HTMLDetailsElement) thinkingExpanded.value = event.currentTarget.open
}
</script>
<template>
  <section class="rail-track" :class="{ growing: turn.status === 'running' }">
    <svg class="track-line" viewBox="0 0 2 100" preserveAspectRatio="none" aria-hidden="true">
      <path d="M1 0V100" pathLength="100" />
    </svg>
    <details
      v-if="active || hasThinking || nodes.length"
      class="process"
      :open="expanded"
      @toggle="toggleProcess"
    >
      <summary class="process-heading">
        <span class="process-glyph" :class="{ active }">
          <IconSymbol :name="active ? 'activity' : attentionNodes.length ? 'alert' : 'check'" :size="16" />
        </span>
        <strong>{{ $t('思考与操作') }}</strong>
        <span class="process-status" :title="heading">{{ heading }}</span>
        <small v-if="turn.steps.length">{{ $t('{0} 项操作', [turn.steps.length]) }}</small>
        <IconSymbol name="chevron" :size="13" class="process-disclosure" />
      </summary>
      <details v-if="hasThinking" class="thinking" :open="thinkingExpanded" @toggle="toggleThinking">
        <summary class="thinking-heading">
          <IconSymbol name="brain" :size="14" />
          <span>{{ $t('思考') }}</span>
          <IconSymbol name="chevron" :size="12" class="thinking-disclosure" />
        </summary>
        <p v-if="turn.thinking">{{ turn.thinking }}</p>
        <p v-else role="status">{{ $t('正在思考…') }}</p>
      </details>
      <p v-if="active && !hasThinking && !nodes.length" class="process-placeholder">{{ heading }}…</p>
      <RailNode v-for="node in processNodes" :key="node.id" :node="node" :turn-id="turn.id" />
    </details>
    <!-- Pending decisions and failures remain visible even when the log is folded. -->
    <RailNode v-for="node in attentionNodes" :key="node.id" :node="node" :turn-id="turn.id" />
    <div class="answer"><slot /></div>
    <Receipt :turn="turn" />
  </section>
</template>
<style scoped lang="scss">
@use '@/styles/mixins' as mixins;
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
.answer {
  position: relative;
  margin-left: calc(var(--rail-width) + 12px);
}
.process {
  position: relative;
  margin: 4px 0 12px;
}
.process-heading {
  @include mixins.interactive-row;
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 40px;
  border-radius: var(--radius-sm);
  color: var(--ink-2);
  font-size: var(--text-xs);
}
.process-heading strong {
  flex: none;
  color: var(--ink);
  font-weight: var(--weight-medium);
}
.process-glyph {
  display: grid;
  width: var(--rail-width);
  flex: none;
  place-items: center;
  background: var(--paper);
}
.process-glyph.active {
  color: var(--accent);
  animation: ink-breathe var(--motion-pulse) var(--ease) infinite;
}
.process-status {
  @include mixins.ellipsis;
  flex: 1;
  min-width: 0;
}
.process-heading small {
  flex: none;
  color: var(--ink-3);
  font-size: var(--text-xs);
}
.process-disclosure,
.thinking-disclosure {
  color: var(--ink-3);
  transition: transform var(--motion-fast) var(--ease);
}
.process[open] > .process-heading .process-disclosure,
.thinking[open] > .thinking-heading .thinking-disclosure {
  transform: rotate(90deg);
}
.thinking,
.process-placeholder {
  margin-left: calc(var(--rail-width) + 12px);
  color: var(--ink-2);
  font-size: var(--text-xs);
}
.thinking {
  padding: 8px 0;
}
.thinking-heading {
  @include mixins.interactive-row;
  display: flex;
  width: fit-content;
  align-items: center;
  gap: 8px;
  padding: 4px 6px;
  border-radius: var(--radius-sm);
}
.thinking p {
  white-space: pre-wrap;
  max-height: 220px;
  overflow: auto;
  overflow-wrap: anywhere;
  line-height: var(--leading-small);
}
summary {
  list-style: none;
  cursor: pointer;
}
summary::-webkit-details-marker {
  display: none;
}
.answer {
  padding-top: 12px;
}
</style>
