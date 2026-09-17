<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import IconSymbol from '@/components/common/IconSymbol.vue'
import type { AgentActivityGroup, AgentActivityItem } from '@/api/client'

const props = defineProps<{ group: AgentActivityGroup }>()
const expanded = ref(props.group.status === 'running')

const isRunning = computed(
  () =>
    props.group.status === 'running' ||
    props.group.items.some((item) => item.status === 'pending' || item.status === 'running'),
)
const heading = computed(() => {
  if (props.group.status === 'failed') return '执行失败'
  if (props.group.status === 'cancelled') return '已停止'
  if (isRunning.value) return '正在工作'
  return `已完成 ${props.group.items.length} 项操作`
})

watch(isRunning, (running) => {
  if (running) expanded.value = true
})

function itemIcon(item: AgentActivityItem): string {
  if (item.status === 'failed' || item.status === 'denied') return 'alert'
  if (item.kind === 'reasoning') return 'brain'
  if (item.kind === 'subagent') return 'cube'
  return item.status === 'completed' ? 'check' : 'terminal'
}

function statusLabel(item: AgentActivityItem): string {
  return {
    pending: '等待执行',
    running: '进行中',
    completed: '完成',
    failed: '失败',
    denied: '已拦截',
  }[item.status]
}

function detailText(item: AgentActivityItem): string {
  if (item.detail === undefined || item.detail === null) return ''
  const value = typeof item.detail === 'string' ? item.detail : JSON.stringify(item.detail, null, 2)
  return value === '{}' ? '' : value.slice(0, 20000)
}
</script>

<template>
  <section class="activity-panel" :class="group.status" data-testid="agent-activity">
    <button
      type="button"
      class="activity-heading"
      :aria-expanded="expanded"
      @click="expanded = !expanded"
    >
      <span class="activity-state" :class="{ pulse: isRunning }">
        <IconSymbol
          :name="isRunning ? 'activity' : group.status === 'failed' ? 'alert' : 'check'"
          :size="14"
        />
      </span>
      <strong>{{ heading }}</strong>
      <small v-if="group.items.length">{{ group.items.length }} 个事件</small>
      <IconSymbol name="chevron" :size="13" class="disclosure" :class="{ open: expanded }" />
    </button>

    <div v-show="expanded" class="activity-items">
      <p v-if="!group.items.length" class="waiting-row"><span />正在分析任务…</p>
      <article
        v-for="item in group.items"
        :key="item.id"
        class="activity-item"
        :class="[item.kind, item.status]"
        :data-activity-kind="item.kind"
      >
        <span class="item-rail"><i /><span /></span>
        <span class="item-icon"><IconSymbol :name="itemIcon(item)" :size="14" /></span>
        <div class="item-copy">
          <div class="item-title">
            <strong>{{ item.title }}</strong>
            <small>{{ statusLabel(item) }}</small>
          </div>
          <p v-if="item.summary">{{ item.summary }}</p>
          <details v-if="detailText(item)" class="item-detail">
            <summary>查看详情</summary>
            <pre>{{ detailText(item) }}</pre>
          </details>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped lang="scss">
.activity-panel {
  margin: 2px 0 20px 40px;
  color: var(--text-secondary);
}

.activity-heading {
  display: flex;
  width: 100%;
  min-height: 34px;
  align-items: center;
  gap: 8px;
  padding: 3px 6px;
  border: 0;
  border-radius: 9px;
  color: inherit;
  background: transparent;
  cursor: pointer;
  text-align: left;
}
.activity-heading:hover {
  background: var(--surface-muted);
}
.activity-heading strong {
  color: var(--text-primary);
  font-size: 11.5px;
  font-weight: 650;
}
.activity-heading small {
  color: var(--text-tertiary);
  font-size: 10px;
}
.activity-state {
  display: grid;
  width: 24px;
  height: 24px;
  flex: none;
  place-items: center;
  border-radius: 8px;
  color: var(--primary-color);
  background: var(--primary-soft);
}
.activity-state.pulse {
  animation: status-pulse 1.5s ease-in-out infinite;
}
.failed .activity-state {
  color: var(--danger);
  background: var(--danger-soft);
}
.disclosure {
  margin-left: auto;
  color: var(--text-tertiary);
  transition: transform 150ms ease;
}
.disclosure.open {
  transform: rotate(90deg);
}

.activity-items {
  padding: 4px 0 0 8px;
}
.waiting-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 7px 0 3px 11px;
  color: var(--text-tertiary);
  font-size: 11px;
}
.waiting-row span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--primary-color);
  animation: status-pulse 1.2s ease-in-out infinite;
}
.activity-item {
  position: relative;
  display: grid;
  grid-template-columns: 20px 26px minmax(0, 1fr);
  gap: 7px;
  min-height: 43px;
}
.item-rail {
  position: relative;
  display: flex;
  justify-content: center;
}
.item-rail i {
  z-index: 1;
  width: 6px;
  height: 6px;
  margin-top: 11px;
  border: 1px solid var(--border-strong);
  border-radius: 50%;
  background: var(--surface-solid);
}
.item-rail span {
  position: absolute;
  top: 17px;
  bottom: -11px;
  width: 1px;
  background: var(--border-color);
}
.activity-item:last-child .item-rail span {
  display: none;
}
.item-icon {
  display: grid;
  width: 26px;
  height: 26px;
  margin-top: 1px;
  place-items: center;
  border-radius: 8px;
  color: var(--text-secondary);
  background: var(--surface-muted);
}
.activity-item.completed .item-icon {
  color: var(--success);
}
.activity-item.failed .item-icon,
.activity-item.denied .item-icon {
  color: var(--danger);
}
.item-copy {
  min-width: 0;
  padding: 4px 4px 12px 0;
}
.item-title {
  display: flex;
  align-items: baseline;
  gap: 7px;
}
.item-title strong {
  overflow-wrap: anywhere;
  color: var(--text-primary);
  font-size: 11px;
  font-weight: 620;
}
.item-title small {
  flex: none;
  color: var(--text-tertiary);
  font-size: 9.5px;
}
.item-copy > p {
  margin: 5px 0 0;
  color: var(--text-secondary);
  font-size: 11px;
  line-height: 1.55;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.item-detail {
  margin-top: 6px;
}
.item-detail summary {
  width: max-content;
  color: var(--text-tertiary);
  cursor: pointer;
  font-size: 9.5px;
}
.item-detail pre {
  max-height: 220px;
  margin: 6px 0 0;
  padding: 9px 10px;
  overflow: auto;
  border: 1px solid var(--border-color);
  border-radius: 9px;
  color: var(--text-secondary);
  background: var(--surface-muted);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 9.5px;
  line-height: 1.5;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

@keyframes status-pulse {
  50% {
    opacity: 0.55;
    transform: scale(0.94);
  }
}

@media (max-width: 560px) {
  .activity-panel {
    margin-left: 0;
  }
}
</style>
