/**
 * 三栏主布局组件
 *
 * 左侧导航栏 + 中间工作区 + 右侧文件管理器，
 * 分隔线支持拖拽调整宽度。
 */

<script setup lang="ts">
import { useLayoutStore } from '@/stores/layout'
import Sidebar from './Sidebar.vue'
import MainContent from './MainContent.vue'
import FileExplorer from './FileExplorer.vue'
import { useLayout } from '@/composables/useLayout'

const layoutStore = useLayoutStore()
const { isDragging, startDrag } = useLayout()
</script>

<template>
  <div class="app-layout">
    <!-- 左侧导航栏 -->
    <div
      class="sidebar-container"
      :style="{ width: layoutStore.sidebarCollapsed ? '64px' : layoutStore.sidebarWidth + 'px' }"
    >
      <Sidebar />
    </div>

    <!-- 左侧分隔线 -->
    <div
      class="divider divider-left"
      :class="{ dragging: isDragging }"
      @mousedown="startDrag('left', $event.clientX, layoutStore.sidebarWidth)"
    />

    <!-- 中间工作区 -->
    <div class="main-content-container">
      <MainContent />
    </div>

    <!-- 右侧分隔线 -->
    <div
      class="divider divider-right"
      :class="{ dragging: isDragging }"
      @mousedown="startDrag('right', $event.clientX, layoutStore.fileExplorerWidth)"
    />

    <!-- 右侧文件管理器 -->
    <div
      class="file-explorer-container"
      :style="{ width: layoutStore.fileExplorerCollapsed ? '48px' : layoutStore.fileExplorerWidth + 'px' }"
    >
      <FileExplorer />
    </div>
  </div>
</template>

<style scoped lang="scss">
.app-layout {
  display: flex;
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}

.sidebar-container,
.file-explorer-container {
  flex-shrink: 0;
  overflow: hidden;
}

.main-content-container {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.divider {
  width: 4px;
  cursor: col-resize;
  background-color: #e0e0e0;
  transition: background-color 0.2s;

  &:hover,
  &.dragging {
    background-color: #0066cc;
  }
}
</style>
