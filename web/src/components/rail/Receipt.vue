<script setup lang="ts">
import { ref } from 'vue'
import type { Turn } from '@/api/events'
import { formatDuration } from '@/utils/format'
import { useUIStore } from '@/stores/ui'
defineProps<{ turn: Turn }>()
const ui = useUIStore()
const expanded = ref(true)
</script>
<template>
  <section v-if="turn.summary" class="receipt" :class="turn.status">
    <button
      class="end-glyph"
      :data-rail-node="`${turn.id}:end`"
      :aria-expanded="expanded"
      aria-label="展开或收起回合小结"
      @click="expanded = !expanded"
    >
      {{ turn.status === 'cancelled' ? '×' : turn.status === 'failed' ? '×' : '◆' }}
    </button>
    <div>
      <header>
        <h3>
          {{ turn.status === 'cancelled' ? '你叫停了' : turn.status === 'failed' ? '这回遇到了问题' : '回合小结' }}
        </h3>
        <time>{{ formatDuration(turn.summary.durationMs) }}</time>
      </header>
      <template v-if="expanded">
        <div class="receipt-rule" />
        <p>
          改动 {{ turn.summary.files }} 个文件
          <span v-if="turn.changes.length">+{{ turn.summary.added }} −{{ turn.summary.removed }}</span
          ><span v-else-if="turn.summary.files">行数见变更</span
          ><button v-if="turn.summary.files" @click="ui.openDrawer('changes')">查看变更</button>
        </p>
        <p>
          执行 {{ turn.summary.commands }} 条命令
          <span>{{ turn.summary.failed ? `${turn.summary.failed} 项失败` : '未发现失败步骤' }}</span>
        </p>
        <p>
          等你 {{ turn.summary.awaits }} 次
          <span>上下文 {{ turn.summary.contextPct === null ? '未提供' : `${turn.summary.contextPct}%` }}</span>
        </p>
      </template>
    </div>
  </section>
</template>
<style scoped lang="scss">
.receipt {
  display: grid;
  grid-template-columns: var(--rail-width) minmax(0, 1fr);
  gap: 12px;
  margin: 20px 0 32px;
  color: var(--ink-2);
  font-size: var(--text-sm);
}
.end-glyph {
  margin: 0;
  width: var(--rail-width);
  display: grid;
  place-content: start center;
  padding-top: 3px;
  color: var(--ink);
  background: var(--paper);
  z-index: 1;
}
header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
}
h3 {
  margin: 0;
  font: var(--text-md) var(--font-serif);
  color: var(--ink);
}
time {
  color: var(--ink-3);
  font-size: var(--text-xs);
}
.receipt-rule {
  margin: 12px 0;
  border-top: 1px dashed var(--rule);
}
p {
  display: flex;
  gap: 16px;
  margin: 8px 0;
  flex-wrap: wrap;
}
p span {
  color: var(--ink-3);
}
.receipt div button {
  margin-left: auto;
  border: 0;
  padding: 0;
  color: var(--accent);
  background: var(--transparent);
  font-size: var(--text-sm);
}
</style>
