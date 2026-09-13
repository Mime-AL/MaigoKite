/**
 * 对话卡片组件
 *
 * 展示单次 Agent 执行会话的概览信息。
 */

<script setup lang="ts">
import TimelineNode from './TimelineNode.vue'
import { formatDuration } from '@/utils/format'

defineProps<{
  card: {
    session_id: string
    title: string
    status: 'running' | 'completed' | 'failed' | 'paused'
    current_step?: string
    running_duration_sec?: number
    total_duration_sec?: number
    token_count?: number
    tool_call_count?: number
  }
  expanded: boolean
}>()

const emit = defineEmits<{
  (e: 'expand', sessionId: string): void
  (e: 'collapse', sessionId: string): void
  (e: 'stop', sessionId: string): void
  (e: 'pause', sessionId: string): void
}>()

function getStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    running: '运行中',
    completed: '已完成',
    failed: '失败',
    paused: '已暂停'
  }
  return labels[status] || status
}
</script>

<template>
  <div class="inspector-card" :class="{ expanded }">
    <div class="card-header" @click="expanded ? emit('collapse', card.session_id) : emit('expand', card.session_id)">
      <span class="status-badge" :class="card.status">{{ getStatusLabel(card.status) }}</span>
      <span class="card-title">{{ card.title }}</span>
      <span class="card-meta">
        {{ card.current_step || getStatusLabel(card.status) }}
      </span>
      <span class="card-stats">
        <span v-if="card.token_count">Token: {{ card.token_count }}</span>
        <span v-if="card.tool_call_count">工具: {{ card.tool_call_count }}</span>
        <span>{{ formatDuration((card.running_duration_sec || card.total_duration_sec || 0) * 1000) }}</span>
      </span>
    </div>

    <div class="card-actions" v-if="card.status === 'running'">
      <button @click.stop="emit('pause', card.session_id)">暂停</button>
      <button @click.stop="emit('stop', card.session_id)">停止</button>
    </div>

    <div class="card-timeline" v-if="expanded">
      <TimelineNode
        v-for="node in []"
        :key="node.id"
        :node="node"
        :depth="0"
      />
    </div>
  </div>
</template>

<style scoped lang="scss">
.inspector-card {
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  margin-bottom: 8px;
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  cursor: pointer;
  background-color: #fafafa;

  &:hover {
    background-color: #f0f0f0;
  }
}

.status-badge {
  padding: 2px 8px;
  border-radius: 3px;
  font-size: 12px;
  color: #fff;

  &.running {
    background-color: #0066cc;
  }

  &.completed {
    background-color: #28a745;
  }

  &.failed {
    background-color: #dc3545;
  }

  &.paused {
    background-color: #ffc107;
    color: #333;
  }
}

.card-title {
  flex: 1;
  font-size: 14px;
  font-weight: 500;
}

.card-meta {
  font-size: 12px;
  color: #666;
}

.card-stats {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #999;
}

.card-actions {
  padding: 8px 14px;
  display: flex;
  gap: 8px;
  border-top: 1px solid #eee;
}

button {
  padding: 4px 12px;
  font-size: 12px;
  border: 1px solid #ddd;
  border-radius: 3px;
  cursor: pointer;
}

.card-timeline {
  padding: 8px 14px;
  border-top: 1px solid #eee;
  background-color: #fff;
}
</style>
