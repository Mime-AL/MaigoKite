/**
 * 右侧文件管理器组件
 *
 * 展示项目文件树、文件预览和操作工具栏。
 */

<script setup lang="ts">
import FileTree from '../file-explorer/FileTree.vue'
import FilePreview from '../file-explorer/FilePreview.vue'
import Toolbar from '../file-explorer/Toolbar.vue'
import { useFileTree } from '@/composables/useFileTree'

const { tree, selectedNode, loadFileTree } = useFileTree()

// 默认加载项目根目录
loadFileTree('./')
</script>

<template>
  <div class="file-explorer">
    <div class="explorer-header" v-if="$slots.header">
      <slot name="header" />
    </div>
    <toolbar />
    <div class="explorer-body">
      <file-tree :nodes="tree" />
      <file-preview v-if="selectedNode" :node="selectedNode" />
    </div>
  </div>
</template>

<style scoped lang="scss">
.file-explorer {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: #fafafa;
  border-left: 1px solid #e0e0e0;
}

.explorer-body {
  flex: 1;
  overflow: auto;
}
</style>
