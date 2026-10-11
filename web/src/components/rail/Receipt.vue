<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Turn } from '@/api/events'
import { formatDuration } from '@/utils/format'
import { useUIStore } from '@/stores/ui'
import RailGlyph from './RailGlyph.vue'
const props = defineProps<{ turn: Turn }>()
const ui = useUIStore(),
  expanded = ref(true)
const hasOperations = computed(() =>
  Boolean(
    props.turn.steps.length ||
    props.turn.awaits.length ||
    props.turn.changes.length ||
    props.turn.memories.length ||
    props.turn.jobs.length ||
    props.turn.summary?.files ||
    props.turn.summary?.commands ||
    props.turn.summary?.awaits,
  ),
)
</script>
<template>
  <section
    v-if="turn.summary"
    class="receipt"
    :class="[turn.status, { compact: !hasOperations }]"
  >
    <button
      class="end-glyph"
      :data-rail-node="turn.id + ':end'"
      :aria-expanded="hasOperations ? expanded : undefined"
      :aria-label="hasOperations ? $t('展开或收起执行小结') : $t('已回复')"
      @click="hasOperations && (expanded = !expanded)"
    >
      <RailGlyph
        :kind="turn.status === 'failed' || turn.status === 'cancelled' ? 'failed' : 'end'"
      />
    </button>
    <div class="receipt-sheet">
      <header>
        <h3>
          {{
            turn.status === 'cancelled'
              ? $t('已停止')
              : turn.status === 'failed'
                ? $t('执行未完成')
                : hasOperations
                  ? $t('执行小结')
                  : $t('已回复')
          }}
        </h3>
        <time>{{ formatDuration(turn.summary.durationMs) }}</time>
      </header>
      <template v-if="hasOperations && expanded">
        <div class="receipt-rule" />
        <dl class="receipt-facts">
          <div>
            <dt>{{ $t('改动文件') }}</dt>
            <dd>
              {{ turn.summary.files
              }}<small v-if="turn.changes.length">+{{ turn.summary.added }} / −{{ turn.summary.removed }}</small><small v-else-if="turn.summary.files">{{ $t('行数见变更') }}</small>
            </dd>
          </div>
          <div>
            <dt>{{ $t('执行命令') }}</dt>
            <dd>{{ turn.summary.commands }}</dd>
          </div>
          <div>
            <dt>{{ $t('等你处理') }}</dt>
            <dd>{{ turn.summary.awaits }}</dd>
          </div>
          <div
            v-if="turn.summary.failed"
            class="failed-fact"
          >
            <dt>{{ $t('失败') }}</dt>
            <dd>{{ turn.summary.failed }}</dd>
          </div>
        </dl>
        <button
          v-if="turn.summary.files"
          class="changes-link"
          @click="ui.openDrawer('changes')"
        >
          {{ $t('查看变更') }}<span aria-hidden="true">↗</span>
        </button>
      </template>
    </div>
  </section>
</template>
<style scoped lang="scss">
@use '@/styles/receipt';
</style>
