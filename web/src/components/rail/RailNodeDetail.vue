<script setup lang="ts">
import { ref } from 'vue'
import type { Step } from '@/api/events'
import { formatDuration } from '@/utils/format'
defineProps<{ steps: Step[] }>()
const all = ref<Record<string, boolean>>({})
const statusLabels = { pending: '等待执行', running: '进行中', completed: '完成', failed: '失败' }
function lines(step: Step) {
  const list = step.output.split('\n')
  return (all.value[step.id] ? list.slice(-200) : list.slice(0, 20))
    .map((line) => line.slice(0, 2000))
    .join('\n')
}
function argumentsText(input: unknown) {
  return JSON.stringify(input, null, 2)?.slice(0, 20_000) || '{}'
}
</script>
<template>
  <div class="node-details">
    <article v-for="step in steps" :key="step.id">
      <header>
        <span>{{ step.title }}</span
        ><small
          >{{ $t(statusLabels[step.status]) }} · {{ formatDuration(step.durationMs)
          }}<template v-if="step.exitCode !== undefined">{{ $t('· 退出码 {0}', [step.exitCode]) }}</template
          ></small
        >
      </header>
      <details>
        <summary>{{ $t('参数') }}</summary>
        <p v-if="step.errorCode">{{ $t('错误代码：') }}<code>{{ step.errorCode }}</code>
        </p>
        <pre>{{ argumentsText(step.input) }}</pre>
      </details>
      <pre v-if="step.output">{{ lines(step) }}</pre>
      <button
        v-if="step.output.split('\n').length > 20"
        class="output-more"
        @click="all[step.id] = !all[step.id]"
      >
        {{ all[step.id] ? $t('收起') : $t('展开输出')
        }}<template v-if="all[step.id] && step.output.split('\n').length > 200">{{ $t('· 显示最后 200 行') }}</template
        >
      </button>
      <p v-if="step.hint || step.action" class="hint" role="status">
        {{ step.hint }}
        <router-link v-if="step.action" :to="step.action.to">{{ step.action.label }}</router-link>
      </p>
    </article>
  </div>
</template>
<style scoped lang="scss">
.node-details {
  margin: 6px 0 16px;
  border-left: 1px solid var(--rule);
  padding: 4px 14px;
  color: var(--ink-2);
  font-size: var(--text-sm);
}
article + article {
  margin-top: 16px;
}
header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin: 6px 0;
}
small {
  color: var(--ink-3);
  font-size: var(--text-xs);
  flex: none;
}
summary {
  cursor: pointer;
  color: var(--ink-3);
  font-size: var(--text-xs);
}
pre {
  max-height: 360px;
  overflow: auto;
  margin: 8px 0;
  padding: 10px;
  background: var(--paper-2);
  border-radius: var(--radius-sm);
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: var(--leading-small);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.output-more {
  border: 0;
  padding: 3px 0;
  background: var(--transparent);
  color: var(--accent);
  font-size: var(--text-xs);
}
.hint {
  color: var(--ink-2);
  border-left: 2px solid var(--wait);
  padding-left: 8px;
}
</style>
