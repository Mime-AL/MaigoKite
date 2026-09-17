<script setup lang="ts">
import { onMounted } from 'vue'
import { useLayoutStore } from '@/stores/layout'
import { useSettingsStore } from '@/stores/settings'
import { useLayout } from '@/composables/useLayout'
import Sidebar from './Sidebar.vue'
import MainContent from './MainContent.vue'
import FileExplorer from './FileExplorer.vue'

const layoutStore = useLayoutStore()
const settingsStore = useSettingsStore()
const { isDragging, startDrag } = useLayout()

onMounted(() => { void settingsStore.loadPreferences() })
</script>

<template>
  <div class="desktop-stage">
    <div class="app-layout" :class="{ dragging: isDragging }">
      <aside
        class="sidebar-container"
        :style="{ width: layoutStore.sidebarCollapsed ? '64px' : `${layoutStore.sidebarWidth}px` }"
      >
        <Sidebar />
      </aside>

      <button
        class="divider divider-left"
        type="button"
        aria-label="调整侧边栏宽度"
        @mousedown="startDrag('left', $event.clientX, layoutStore.sidebarWidth)"
      />

      <section class="main-content-container">
        <MainContent />
      </section>

      <button
        class="divider divider-right"
        type="button"
        aria-label="调整文件栏宽度"
        @mousedown="startDrag('right', $event.clientX, layoutStore.fileExplorerWidth)"
      />

      <aside
        class="file-explorer-container"
        :style="{ width: layoutStore.fileExplorerCollapsed ? '48px' : `${layoutStore.fileExplorerWidth}px` }"
      >
        <FileExplorer />
      </aside>
    </div>
  </div>
</template>

<style scoped lang="scss">
.desktop-stage {
  width: 100vw;
  height: 100vh;
  padding: 12px;
}

.app-layout {
  display: flex;
  width: 100%;
  height: 100%;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.34);
  border-radius: 22px;
  background: var(--surface);
  box-shadow: var(--shadow-window);

  &.dragging { cursor: col-resize; user-select: none; }
  &.dragging .sidebar-container { transition: none; }
}

.sidebar-container {
  flex: none;
  min-width: 0;
  overflow: hidden;
  transition: width 220ms cubic-bezier(0.22, 1, 0.36, 1);
}

.main-content-container {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  background: var(--surface-solid);
}

.file-explorer-container { flex: none; min-width: 0; overflow: hidden; transition: width 220ms cubic-bezier(0.22, 1, 0.36, 1); }

.divider {
  position: relative;
  z-index: 4;
  width: 1px;
  flex: 0 0 1px;
  padding: 0;
  border: 0;
  background: var(--border-color);
  cursor: col-resize;

  &::after {
    position: absolute;
    inset: 0 -4px;
    content: '';
  }

  &:hover { background: var(--primary-color); }
}

@media (max-width: 760px) {
  .desktop-stage { padding: 0; }
  .app-layout { border: 0; border-radius: 0; }
  .file-explorer-container,.divider-right { display: none; }
}
</style>
