<script setup lang="ts">
import { t } from '@/i18n'
import { computed, ref, watch } from 'vue'
import type { Turn } from '@/api/events'
import type { PresentationNode as ActivityNode } from '@/utils/rail-presentation'
import { presentationNodes, pendingItem, hasOrder } from '@/utils/rail-presentation'
import IconSymbol from '@/components/common/IconSymbol.vue'
import RailNode from './RailNode.vue'
import Receipt from './Receipt.vue'
import RailInk from './RailInk.vue'
const props = defineProps<{
  turn: Turn
  canResend?: boolean
  resendInput?: (id: string) => Promise<void>
}>()
const nodes = computed(() => presentationNodes(props.turn))
const atEnd = (node: ActivityNode) =>
  Boolean(node.await?.mode === 'question' && !hasOrder(node.await))
const fallbackQuestions = computed(() => nodes.value.filter(atEnd))
const active = computed(() => ['running', 'waiting'].includes(props.turn.status))
const expanded = ref(active.value),
  thinkingExpanded = ref(active.value)
const hasThinking = computed(() =>
  Boolean(props.turn.thinking || props.turn.thinkingStatus === 'running'),
)
const blocks = computed(() => {
  const result: { id: string; attention: boolean; nodes: ActivityNode[] }[] = []
  for (const node of nodes.value) {
    if (atEnd(node)) continue
    const attention =
      node.kind === 'failed' ||
      node.kind === 'input' ||
      Boolean(node.await && pendingItem(node.await))
    const previous = result[result.length - 1]
    if (!attention && previous && !previous.attention) previous.nodes.push(node)
    else result.push({ id: node.id, attention, nodes: [node] })
  }
  return result
})
const heading = computed(() => {
  if (props.turn.status === 'waiting') return t('等你处理')
  if (props.turn.status === 'failed') return t('执行遇到问题')
  if (props.turn.status === 'cancelled') return t('已停止')
  if (props.turn.status === 'completed') return t('已完成')
  const step = [...props.turn.steps].reverse().find((item) => item.status === 'running')
  return step?.title || t(props.turn.text ? '正在回复' : '正在思考')
})
watch(
  () => props.turn.status,
  () => {
    expanded.value = active.value
    if (!active.value) thinkingExpanded.value = false
  },
)
function toggleProcess(event: Event) {
  if (event.currentTarget instanceof HTMLDetailsElement) expanded.value = event.currentTarget.open
}
</script>
<template>
  <section
    class="rail-track"
    :class="{ growing: turn.status === 'running' }"
  >
    <RailInk />
    <details
      v-if="hasThinking"
      class="thinking"
      :open="thinkingExpanded"
    >
      <summary class="thinking-heading">
        <IconSymbol
          name="brain"
          :size="14"
        /><span>{{ $t('思考') }}</span>
        <IconSymbol
          name="chevron"
          :size="12"
          class="thinking-disclosure"
        />
      </summary>
      <p>{{ turn.thinking || $t('正在思考…') }}</p>
    </details>
    <p
      v-if="active && !nodes.length"
      class="process-placeholder"
    >
      {{ heading }}…
    </p>
    <!-- Fold regular segments around awaits, never extract awaits from their position. -->
    <template
      v-for="(block, index) in blocks"
      :key="block.id"
    >
      <RailNode
        v-if="block.attention"
        :node="block.nodes[0]"
        :turn-id="turn.id"
        :can-resend="canResend"
        :resend-input="resendInput"
      />
      <details
        v-else
        class="process"
        :open="expanded"
        @toggle="toggleProcess"
      >
        <summary class="process-heading">
          <span
            class="process-glyph"
            :class="{ active }"
          ><IconSymbol
            :name="active ? 'activity' : 'check'"
            :size="16"
          /></span>
          <strong>{{ $t(index ? '操作记录' : '思考与操作') }}</strong>
          <span class="process-status">{{ heading }}</span>
          <small>{{
            $t('{0} 项操作', [block.nodes.reduce((count, node) => count + node.steps.length, 0)])
          }}</small>
          <IconSymbol
            name="chevron"
            :size="13"
            class="process-disclosure"
          />
        </summary>
        <RailNode
          v-for="node in block.nodes"
          :key="node.id"
          :node="node"
          :turn-id="turn.id"
        />
      </details>
    </template>
    <div class="answer">
      <slot />
    </div>
    <!-- No real ordering metadata: after the untouched reply, not a guessed sentence. -->
    <RailNode
      v-for="node in fallbackQuestions"
      :key="node.id"
      :node="node"
      :turn-id="turn.id"
    />
    <Receipt :turn="turn" />
  </section>
</template>
<style scoped lang="scss">
@use '@/styles/mixins' as mixins;
.rail-track {
  position: relative;
}
.answer {
  position: relative;
  margin-left: calc(var(--rail-width) + var(--space-4));
}
.process {
  position: relative;
  margin: var(--space-2) 0 var(--space-4);
}
.process-heading {
  @include mixins.interactive-row;
  display: flex;
  align-items: center;
  gap: var(--space-4);
  min-height: var(--rail-node-height);
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
  margin-left: calc(var(--rail-width) + var(--space-4));
  color: var(--ink-2);
  font-size: var(--text-xs);
}
.thinking {
  padding: var(--space-3) 0;
}
.thinking-heading {
  @include mixins.interactive-row;
  display: flex;
  width: fit-content;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--size-6);
  border-radius: var(--radius-sm);
}
.thinking p {
  white-space: pre-wrap;
  max-height: var(--thinking-max-height);
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
  padding-top: var(--space-4);
}
</style>
