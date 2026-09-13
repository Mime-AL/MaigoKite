/**
 * 文件树组件
 *
 * 递归渲染文件目录树。
 */

<script setup lang="ts">
import FileNode from './FileNode.vue'
import { useFileTree } from '@/composables/useFileTree'

const { toggleExpand, selectNode } = useFileTree()

defineProps<{
  nodes?: Array<{
    name: string
    path: string
    type: 'file' | 'directory'
    children?: any[]
  }>
}>()
</script>

<template>
  <div class="file-tree">
    <template v-for="node in nodes" :key="node.path">
      <FileNode :node="node" :depth="0" @expand="toggleExpand" @select="selectNode" />
    </template>
  </div>
</template>

<style scoped lang="scss">
.file-tree {
  padding: 8px 0;
}
</style>
