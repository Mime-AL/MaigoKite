<script setup lang="ts">
import { t } from '@/i18n'
import { computed } from 'vue'
import type { ContextUsage } from '@/api/events'
import StatPopover from './StatPopover.vue'
const props = defineProps<{ context: ContextUsage }>()
const percent = computed(() =>
  props.context.usedTokens === null || !props.context.windowTokens
    ? null
    : (props.context.usedTokens / props.context.windowTokens) * 100,
)
const label = computed(() =>
  percent.value === null ? '—' : `${Math.floor(percent.value * 10) / 10}%`,
)
const fill = computed(() =>
  percent.value === null ? 0 : Math.min(100, Math.max(0, percent.value)),
)
const count = (value: number | null) => (value === null ? t("未提供") : value.toLocaleString())
</script>
<template>
  <StatPopover
    :label="$t('本次请求上下文')"
    :title="$t('上下文已用 {0}{1}', [label, context.measurement === 'estimate' ? $t('（估算）') : ''])"
  >
    <template #trigger>
      <svg class="context-ring" viewBox="0 0 16 16" aria-hidden="true">
        <circle class="ring-track" cx="8" cy="8" r="6" />
        <circle
          v-if="percent !== null"
          class="ring-fill"
          cx="8"
          cy="8"
          r="6"
          pathLength="100"
          :stroke-dasharray="`${fill} 100`"
        />
      </svg>
      <span
        >{{ context.measurement === 'estimate' && percent !== null ? '~ ' : '' }}{{ label }}</span
      >
    </template>
    <dl class="stat-rows">
      <div>
        <dt>{{ $t('已用上下文{0}', [context.measurement === 'estimate' ? $t('（估算）') : '']) }}</dt>
        <dd>{{ count(context.usedTokens) }} Token</dd>
      </div>
      <div>
        <dt>{{ $t('模型窗口') }}</dt>
        <dd>
          {{ context.windowTokens === null ? $t('未提供') : `${count(context.windowTokens)} Token` }}
        </dd>
      </div>
    </dl>
    <div v-if="percent !== null" class="context-track"><i :style="{ width: `${fill}%` }" /></div>
  </StatPopover>
</template>
<style scoped lang="scss">
@use '@/styles/composer-stats';
.context-ring {
  width: 14px;
  height: 14px;
  fill: none;
  stroke-width: 1.5;
  flex: none;
}
.ring-track {
  stroke: var(--rule);
}
.ring-fill {
  stroke: var(--ink-2);
  transform: rotate(-90deg);
  transform-origin: center;
}
.context-track {
  height: 4px;
  margin-top: 12px;
  border-radius: var(--radius-pill);
  background: var(--rule);
  overflow: hidden;
}
.context-track i {
  display: block;
  height: 100%;
  background: var(--ink-2);
}
</style>
