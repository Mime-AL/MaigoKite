<script setup lang="ts">
import { t } from '@/i18n'
import { computed } from 'vue'
import type { ContextUsage } from '@/api/events'
import { normalizeEndpoint, type ModelOption } from '@/config/model-groups'
import { useRunStore } from '@/stores/run'
import { useUIStore } from '@/stores/ui'
import { sessionUsage } from '@/stores/run-usage'
import { formatDuration } from '@/utils/format'
import IconSymbol from '@/components/common/IconSymbol.vue'
import StatPopover from './StatPopover.vue'
import InkMeter from './InkMeter.vue'
import CompactionStatus from './CompactionStatus.vue'
const props = defineProps<{ sessionId: string; model?: ModelOption }>()
const run = useRunStore(),
  ui = useUIStore()
const empty = sessionUsage([])
const stats = computed(() => run.metrics[props.sessionId]?.usage || empty)
const context = computed<ContextUsage | undefined>(() => {
  const selected = props.model
  if (!selected) return undefined
  const key = JSON.stringify([
    selected.provider, normalizeEndpoint(selected.baseUrl || ''), selected.model, selected.contextWindow ?? null,
  ])
  const value = run.metrics[props.sessionId]?.context
  // Old receipts without profile identity cannot prove which same-named service
  // produced the count. Do not reuse their capacity after a model switch.
  if (value?.modelId === selected.id && value.modelKey === key && value.modelName === selected.model)
    return value
  const capacity = selected.contextWindow
  const known = capacity !== undefined && Number.isSafeInteger(capacity) && capacity > 0
  return {
    seq: 0, callId: '', modelName: selected.model, modelId: selected.id, modelKey: key,
    usedTokens: null, windowTokens: known ? capacity ?? null : null, measurement: null,
    capacitySource: known ? 'model_profile' : null, capacityStatus: known ? 'known' : 'unknown',
  }
})
const turn = computed(() => (run.turns[props.sessionId] || []).slice(-1)[0])
const footerCompaction = computed(() =>
  turn.value?.compaction?.status !== 'failed' ? turn.value?.compaction : undefined,
)
const active = computed(() => stats.value.calls + stats.value.summaryCalls + stats.value.subagentCalls > 0)
const compact = (value: number) =>
  Intl.NumberFormat('en', { notation: 'compact', maximumFractionDigits: 1 }).format(value)
const count = (value: number | undefined) =>
  value === undefined ? t("未提供") : value.toLocaleString()
const duration = (value: number | null) => (value === null ? t("未提供") : formatDuration(value))
const speed = computed(() =>
  stats.value.tokensPerSecond === null ? '—' : stats.value.tokensPerSecond.toFixed(1),
)
const cache = computed(() =>
  stats.value.cachePct === null ? '—' : `${Math.floor(stats.value.cachePct * 10) / 10}%`,
)
const tokenLabel = computed(() =>
  stats.value.totalTokens === null
    ? '—'
    : `${stats.value.partial ? '≥ ' : ''}${compact(stats.value.totalTokens)}`,
)
</script>
<template>
  <div
    v-if="active || footerCompaction || (ui.appearance.showContextUsage !== false && context)"
    class="composer-dock"
    :aria-label="$t('对话统计')"
  >
    <template v-if="active">
      <StatPopover :label="$t('执行统计')" :title="$t('生成速度 {0} tok/s', [speed])">
        <template #trigger
          ><IconSymbol name="activity" :size="14" /><span>{{ speed }} tok/s</span></template
        >
        <dl class="stat-rows">
          <div>
            <dt>{{ $t('模型请求') }}</dt>
            <dd>{{ $t('{0} 次', [stats.calls]) }}</dd>
          </div>
          <div v-if="stats.summaryCalls">
            <dt>{{ $t('上下文摘要') }}</dt>
            <dd>{{ $t('{0} 次', [stats.summaryCalls]) }}</dd>
          </div>
          <div v-if="stats.subagentCalls">
            <dt>{{ $t('子 Agent 模型请求') }}</dt>
            <dd>{{ $t('{0} 次', [stats.subagentCalls]) }}</dd>
          </div>
          <div>
            <dt>{{ $t('模型耗时') }}</dt>
            <dd>{{ duration(stats.modelMs) }}</dd>
          </div>
          <div>
            <dt>{{ $t('工具耗时') }}</dt>
            <dd>{{ duration(stats.toolMs) }}</dd>
          </div>
          <div>
            <dt>{{ $t('平均首 Token 延迟') }}</dt>
            <dd>{{ duration(stats.firstTokenMs) }}</dd>
          </div>
          <div>
            <dt>{{ $t('平均生成速度') }}</dt>
            <dd>{{ speed }} tok/s</dd>
          </div>
        </dl>
      </StatPopover>
      <StatPopover :label="$t('Token 用量')" :title="$t('本对话已报告 {0} Token', [tokenLabel])">
        <template #trigger
          ><IconSymbol name="cube" :size="14" /><span>{{ tokenLabel }} Token</span></template
        >
        <dl class="stat-rows">
          <div>
            <dt>{{ $t('输入（含缓存）') }}</dt>
            <dd>{{ count(stats.tokens.input_tokens) }}</dd>
          </div>
          <div>
            <dt>{{ $t('输出') }}</dt>
            <dd>{{ count(stats.tokens.output_tokens) }}</dd>
          </div>
          <div>
            <dt>{{ $t('总用量') }}</dt>
            <dd>
              {{ stats.totalTokens === null ? $t('未提供') : stats.totalTokens.toLocaleString() }}
            </dd>
          </div>
          <div>
            <dt>{{ $t('缓存读取') }}</dt>
            <dd>{{ count(stats.tokens.cache_read_tokens) }}</dd>
          </div>
          <div>
            <dt>{{ $t('缓存写入') }}</dt>
            <dd>{{ count(stats.tokens.cache_creation_tokens) }}</dd>
          </div>
          <div v-if="stats.tokens.reasoning_tokens !== undefined">
            <dt>{{ $t('思考（含于输出）') }}</dt>
            <dd>{{ count(stats.tokens.reasoning_tokens) }}</dd>
          </div>
        </dl>
        <p v-if="stats.partial" class="stat-note">{{ $t('用量不完整') }}</p>
      </StatPopover>
      <StatPopover :label="$t('缓存命中率')" :title="$t('缓存命中 {0}', [cache])">
        <template #trigger
          ><IconSymbol name="bolt" :size="14" /><span>{{ $t('缓存 {0}', [cache]) }}</span></template
        >
        <dl class="stat-rows">
          <div>
            <dt>{{ $t('命中率') }}</dt>
            <dd>{{ cache }}</dd>
          </div>
          <div>
            <dt>{{ $t('命中输入 Token') }}</dt>
            <dd>{{ count(stats.tokens.cache_read_tokens) }}</dd>
          </div>
          <div>
            <dt>{{ $t('总输入 Token') }}</dt>
            <dd>{{ count(stats.tokens.input_tokens) }}</dd>
          </div>
        </dl>
      </StatPopover>
    </template>
    <InkMeter v-if="ui.appearance.showContextUsage !== false && context" :context="context" />
    <CompactionStatus
      v-if="turn && footerCompaction"
      :compaction="footerCompaction"
      :turn-status="turn.status"
      compact
      announce
    />
  </div>
</template>
<style scoped lang="scss">
@use '@/styles/composer-stats';
</style>
