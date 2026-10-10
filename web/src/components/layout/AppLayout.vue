<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useSessionStore } from '@/stores/session'
import { useSettingsStore } from '@/stores/settings'
import { useUIStore } from '@/stores/ui'
import { useInboxStore } from '@/stores/inbox'
import { useShortcuts } from '@/composables/useShortcuts'
import { useDesktopBridge } from '@/composables/useDesktopBridge'
import TitleBar from '@/components/shell/TitleBar.vue'
import Drawer from '@/components/shell/Drawer.vue'
import InboxPopover from '@/components/interact/InboxPopover.vue'
import CommandPalette from '@/components/common/CommandPalette.vue'
import Sidebar from './Sidebar.vue'
import { panelWidths } from '@/stores/layout'
const session = useSessionStore(),
  settings = useSettingsStore(),
  ui = useUIStore(),
  inbox = useInboxStore()
const viewportWidth = ref(window.innerWidth)
const sidebarMaximum = computed(() => Math.min(panelWidths.left.max, viewportWidth.value - 24))
const sidebarWidth = computed(() => Math.min(ui.layout.sidebarWidth, sidebarMaximum.value))
const drawerMaximum = computed(() =>
  Math.max(
    panelWidths.right.min,
    viewportWidth.value < 1100
      ? viewportWidth.value - 16
      : viewportWidth.value - (ui.layout.sidebarCollapsed ? 56 : sidebarWidth.value) - 420,
  ),
)
const panelStyle = computed(() => ({
  '--sidebar-width': sidebarWidth.value + 'px',
  '--drawer-width': Math.min(ui.layout.fileExplorerWidth, drawerMaximum.value) + 'px',
  '--drawer-maximum-width': drawerMaximum.value + 'px',
}))
function updateViewport() {
  viewportWidth.value = window.innerWidth
}
useShortcuts()
useDesktopBridge()
onMounted(() => {
  window.addEventListener('resize', updateViewport)
  void session.loadSessions()
  void settings.loadPreferences()
  if (!settings.loaded) void settings.loadSettings()
  inbox.start()
  if (window.innerWidth < 720 && !ui.layout.sidebarCollapsed) ui.layout.toggleSidebar()
})
onUnmounted(() => {
  window.removeEventListener('resize', updateViewport)
  inbox.stop()
  session.disconnect()
})
</script>
<template>
  <div class="app-layout">
    <TitleBar />
    <div class="app-body" :style="panelStyle">
      <div
        v-if="!ui.layout.sidebarCollapsed"
        class="sidebar-shade"
        @click="ui.layout.toggleSidebar()"
      />
      <Sidebar :maximum-width="sidebarMaximum" />
      <main class="main-content"><router-view /></main>
      <Drawer :maximum-width="drawerMaximum" />
    </div>
    <InboxPopover /><CommandPalette />
  </div>
</template>
<style scoped lang="scss">
.app-layout {
  display: flex;
  flex-direction: column;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: var(--paper);
}
.app-body {
  display: flex;
  min-height: 0;
  flex: 1;
}
.main-content {
  flex: 1;
  min-width: 0;
  overflow: auto;
}
.sidebar-shade {
  display: none;
}
@media (max-width: 720px) {
  .sidebar-shade {
    display: block;
    position: fixed;
    inset: var(--titlebar-height) 0 0;
    background: var(--backdrop);
    z-index: 29;
  }
}
</style>
