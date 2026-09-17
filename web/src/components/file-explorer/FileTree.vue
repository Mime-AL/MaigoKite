<script setup lang="ts">
import type { FileTreeNode } from '@/composables/useFileTree'
import FileNode from './FileNode.vue'

defineProps<{ nodes?: FileTreeNode[] }>()
const emit = defineEmits<{ (event: 'expand' | 'select', node: FileTreeNode): void }>()
</script>

<template><div class="file-tree"><FileNode v-for="node in nodes" :key="node.path" :node="node" :depth="0" @expand="emit('expand', $event)" @select="emit('select', $event)" /></div></template>

<style scoped>.file-tree { padding: 7px; }</style>
