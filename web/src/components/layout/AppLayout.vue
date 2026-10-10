<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
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
const session = useSessionStore(),
  settings = useSettingsStore(),
  ui = useUIStore(),
  inbox = useInboxStore()
useShortcuts()
useDesktopBridge()
onMounted(() => {
  void session.loadSessions()
  void settings.loadPreferences()
  if (!settings.loaded) void settings.loadSettings()
  inbox.start()
  if (window.innerWidth < 720 && !ui.layout.sidebarCollapsed) ui.layout.toggleSidebar()
})
onUnmounted(() => {
  inbox.stop()
  session.disconnect()
})
</script>
<template>
  <div class="app-layout">
    <TitleBar />
    <div class="app-body">
      <div v-if="!ui.layout.sidebarCollapsed" class="sidebar-shade" @click="ui.layout.toggleSidebar()" />
      <Sidebar />
      <main class="main-content"><router-view /></main>
      <Drawer />
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
