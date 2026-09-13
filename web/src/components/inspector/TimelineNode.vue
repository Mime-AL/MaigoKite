/**
 * 时间线节点组件
 *
 * 递归渲染 Inspector 时间线上的节点，支持嵌套和折叠。
 */

<script setup lang="ts">
defineProps<{
  node: {
    id: string
    type: string
    status: string
    title: string
    duration_ms?: number
    details?: Record<string, any>
    children?: any[]
  }
  depth: number
}>()
</script>

<template>
  <div class="timeline-node" :class="[node.type, node.status]" :style="{ marginLeft: depth * 20 + 'px' }">
    <div class="node-header">
      <span class="node-type">{{ node.type }}</span>
      <span class="node-title">{{ node.title }}</span>
      <span class="node-status">{{ node.status }}</span>
      <span class="node-duration" v-if="node.duration_ms">{{ node.duration_ms }}ms</span>
    </div>

    <div class="node-details" v-if="node.details">
      <pre>{{ JSON.stringify(node.details, null, 2) }}</pre>
    </div>

    <div class="node-children" v-if="node.children && node.children.length > 0">
      <TimelineNode
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :depth="depth + 1"
      />
    </div>
  </div>
</template>

<style scoped lang="scss">
.timeline-node {
  padding: 4px 0;
  border-left: 2px solid #e0e0e0;
  margin-left: 12px;
}

.node-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
  font-size: 13px;
}

.node-type {
  padding: 1px 6px;
  background-color: #f0f0f0;
  border-radius: 3px;
  font-size: 11px;
  text-transform: uppercase;
}

.node-status {
  font-size: 11px;
  color: #999;
}

.node-duration {
  font-size: 11px;
  color: #666;
  margin-left: auto;
}

.node-details {
  padding: 4px 8px;
  font-size: 12px;
  color: #666;
}

pre {
  margin: 0;
  white-space: pre-wrap;
  font-size: 11px;
}
</style>
