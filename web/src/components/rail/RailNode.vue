<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { RailNode } from '@/api/events'
import RailNodeDetail from './RailNodeDetail.vue'
import SealMark from './SealMark.vue'
import ApprovalCard from '@/components/chat-area/ApprovalCard.vue'
import QuestionCard from '@/components/interact/QuestionCard.vue'
import { useMemoryStore } from '@/stores/memory'
import { useRunStore } from '@/stores/run'
const props = defineProps<{ node: RailNode; turnId: string }>()
const needsAttention = computed(() => props.node.kind === 'failed' || Boolean(
  props.node.await && !props.node.await.verdict && !props.node.await.closed &&
  props.node.await.answer === undefined,
))
const expanded = ref(needsAttention.value)
const glyphs = { read: '○', act: '●', await: '◇', end: '◆', failed: '×', memory: '✦' }
const memory = useMemoryStore(),
  run = useRunStore()
watch(
  needsAttention,
  (attention) => {
    if (attention) expanded.value = true
  },
)
watch(
  () => Boolean(props.node.await && (props.node.await.verdict || props.node.await.closed ||
    props.node.await.answer !== undefined)),
  (resolved) => {
    if (resolved) expanded.value = false
  },
)
async function undoMemory() {
  if (props.node.memoryId && (await memory.remove(props.node.memoryId)))
    run.removeMemory(props.node.memoryId)
}
</script>
<template>
  <div
    class="rail-node"
    :class="[
      node.kind,
      { running: node.running, waiting: node.await && !node.await.verdict && !node.await.closed },
    ]"
    :id="`rail-${turnId}-${node.id}`"
  >
    <button
      class="node-button"
      :data-rail-node="`${turnId}:${node.id}`"
      :aria-expanded="expanded"
      @click="expanded = !expanded"
    >
      <span class="node-glyph">{{ glyphs[node.kind] }}</span
      ><span class="node-title">{{ node.title }}</span>
      <SealMark v-if="node.await?.verdict" :verdict="node.await.verdict" />
      <span v-else class="disclosure">{{ expanded ? '−' : '+' }}</span>
    </button>
    <div v-if="expanded" class="node-body">
      <RailNodeDetail v-if="node.steps.length" :steps="node.steps" />
      <ApprovalCard
        v-if="node.await?.mode === 'approval' && !node.await.verdict && !node.await.closed"
        :item="node.await"
      />
      <QuestionCard
        v-if="node.await?.mode === 'question' && !node.await.verdict && !node.await.closed"
        :item="node.await"
      />
      <p v-if="node.await?.answer !== undefined">{{ $t('已回答：{0}', [node.await.answer]) }}</p>
      <p v-else-if="node.await?.closed && !node.await.verdict">{{ $t('已关闭') }}</p>
      <p v-if="node.await?.note">{{ node.await.note }}</p>
      <button v-if="node.memoryId" class="secondary-button" @click="undoMemory">{{ $t('撤销这条记忆') }}</button>
    </div>
  </div>
</template>
<style scoped lang="scss">
@use '@/styles/mixins' as mixins;
.node-button {
  @include mixins.interactive-row;
  display: flex;
  width: 100%;
  gap: 12px;
  align-items: center;
  min-height: 40px;
  padding: 0;
  border: 0;
  text-align: left;
  background: var(--transparent);
  color: var(--ink-2);
  font-size: var(--text-sm);
}
.node-button[aria-expanded='true'] {
  color: var(--ink);
  background: var(--paper-2);
}
.node-button[aria-expanded='true'] .disclosure {
  color: var(--accent);
}
.node-glyph {
  display: grid;
  width: var(--rail-width);
  flex: none;
  place-content: center;
  color: var(--ink-2);
  position: relative;
  z-index: 1;
  background: var(--paper);
}
.node-title {
  flex: 1;
  min-width: 0;
  overflow-wrap: anywhere;
}
.disclosure {
  color: var(--ink-3);
  font-size: var(--text-xs);
}
.node-body {
  margin-left: calc(var(--rail-width) + 12px);
}
.running .node-glyph {
  color: var(--accent);
}
.await .node-glyph {
  color: var(--wait);
}
.waiting .node-glyph {
  animation: ink-breathe var(--motion-pulse) var(--ease) infinite;
}
.failed .node-glyph {
  color: var(--ink);
}
.memory .node-glyph {
  color: var(--ink-2);
}
</style>
