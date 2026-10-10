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
      :aria-label="$t('展开或收起执行小结')"
      @click="expanded = !expanded"
    >
      {{ turn.status === 'cancelled' ? '×' : turn.status === 'failed' ? '×' : '◆' }}
    </button>
    <div>
      <header>
        <h3>
          {{ turn.status === 'cancelled' ? $t('已停止') : turn.status === 'failed' ? $t('执行未完成') : $t('执行小结') }}
        </h3>
        <time>{{ formatDuration(turn.summary.durationMs) }}</time>
      </header>
      <template v-if="expanded">
        <div class="receipt-rule" />
        <p>{{ $t('改动 {0} 个文件', [turn.summary.files]) }}<span v-if="turn.changes.length">+{{ turn.summary.added }} −{{ turn.summary.removed }}</span
          ><span v-else-if="turn.summary.files">{{ $t('行数见变更') }}</span
          ><button v-if="turn.summary.files" @click="ui.openDrawer('changes')">{{ $t('查看变更') }}</button>
        </p>
        <p>{{ $t('执行 {0} 条命令', [turn.summary.commands]) }}<span>{{ turn.summary.failed ? $t('{0} 项失败', [turn.summary.failed]) : $t('无失败项') }}</span>
        </p>
        <p>{{ $t('等你 {0} 次', [turn.summary.awaits]) }}</p>
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
  color: var(--ink-2);
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
