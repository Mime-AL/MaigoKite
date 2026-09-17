<script setup lang="ts">
import { ref } from 'vue'
import type { FileTreeNode } from '@/composables/useFileTree'
import IconSymbol from '@/components/common/IconSymbol.vue'

const props = defineProps<{ node: FileTreeNode; depth: number }>()
const emit = defineEmits<{ (event: 'expand' | 'select', node: FileTreeNode): void }>()
const isExpanded = ref(props.depth === 0 && props.node.type === 'directory')

function select() {
  emit('select', props.node)
  if (props.node.type === 'directory') {
    isExpanded.value = !isExpanded.value
    emit('expand', props.node)
  }
}
</script>

<template><div class="file-node"><button type="button" :style="{ paddingLeft: `${8 + depth * 14}px` }" @click="select"><IconSymbol v-if="node.type === 'directory'" name="chevron" :size="12" class="chevron" :class="{ expanded: isExpanded }" /><span v-else class="spacer" /><IconSymbol :name="node.type === 'directory' ? 'folder' : 'file'" :size="15" /><span>{{ node.name }}</span></button><div v-if="node.type === 'directory' && isExpanded"><FileNode v-for="child in node.children || []" :key="child.path" :node="child" :depth="depth + 1" @expand="emit('expand', $event)" @select="emit('select', $event)" /></div></div></template>

<style scoped lang="scss">
.file-node button { display: flex; width: 100%; height: 29px; align-items: center; gap: 6px; padding-right: 8px; border: 0; border-radius: 8px; color: var(--text-secondary); background: transparent; cursor: pointer; text-align: left; }.file-node button:hover { color: var(--text-primary); background: var(--surface-strong); }.file-node button span:last-child { overflow: hidden; font-size: 10.5px; text-overflow: ellipsis; white-space: nowrap; }.chevron { transition: transform 140ms ease; }.chevron.expanded { transform: rotate(90deg); }.spacer { width: 12px; flex: none; }
</style>
