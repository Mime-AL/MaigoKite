<script setup lang="ts">
import type { TimelineNode as TimelineNodeData } from '@/types'

defineProps<{ node: TimelineNodeData; depth: number }>()
</script>

<template><div class="timeline-node" :style="{ marginLeft: `${depth * 18}px` }"><span class="rail" /><div><header><span class="type">{{ node.type }}</span><time>{{ new Date(node.timestamp).toLocaleTimeString('zh-CN') }}</time></header><pre v-if="Object.keys(node.data).length">{{ JSON.stringify(node.data, null, 2) }}</pre><TimelineNode v-for="child in node.children || []" :key="child.id" :node="child" :depth="depth + 1" /></div></div></template>

<style scoped lang="scss">
.timeline-node { position: relative; display: grid; grid-template-columns: 12px 1fr; gap: 7px; padding: 6px 0; }.rail { width: 7px; height: 7px; margin-top: 6px; border: 2px solid var(--surface-solid); border-radius: 50%; background: var(--primary-color); box-shadow: 0 0 0 2px var(--primary-soft); }.timeline-node::before { position: absolute; top: 18px; bottom: -7px; left: 3px; width: 1px; background: var(--border-strong); content: ''; }.timeline-node:last-child::before { display: none; }header { display: flex; align-items: center; justify-content: space-between; }.type { font-size: 9.5px; font-weight: 650; text-transform: capitalize; }time { color: var(--text-tertiary); font-size: 8.5px; }pre { margin: 6px 0 0; padding: 8px; overflow: auto; border-radius: 8px; color: var(--text-secondary); background: var(--surface-strong); font-family: var(--font-mono); font-size: 8.5px; white-space: pre-wrap; }
</style>
