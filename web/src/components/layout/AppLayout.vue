<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useSessionStore } from '@/stores/session'
import { useSettingsStore } from '@/stores/settings'
import { useUIStore } from '@/stores/ui'
import { useInboxStore } from '@/stores/inbox'
import { useShortcuts } from '@/composables/useShortcuts'
import { useDesktopBridge } from '@/composables/useDesktopBridge'
import TitleBar from '@/components/shell/TitleBar.vue'
import Drawer from '@/components/shell/Drawer.vue'
import CommandPalette from '@/components/common/CommandPalette.vue'
import Sidebar from './Sidebar.vue'
import { panelWidths } from '@/stores/layout'
import { layoutPixels, overlayPanel } from '@/utils/layout-media'
const session = useSessionStore(), settings = useSettingsStore(), ui = useUIStore(), inbox = useInboxStore()
const viewportWidth = ref(window.innerWidth)
const narrowSidebar = computed(() => overlayPanel('sidebar', viewportWidth.value))
const narrowDrawer = computed(() => overlayPanel('drawer', viewportWidth.value))
const sidebarMaximum = computed(() => Math.min(panelWidths.left.max, viewportWidth.value - layoutPixels('--space-7')))
const sidebarWidth = computed(() => Math.min(ui.layout.sidebarWidth, sidebarMaximum.value))
const drawerMaximum = computed(() => Math.max(panelWidths.right.min, narrowDrawer.value
  ? viewportWidth.value - layoutPixels('--panel-edge-gap')
  : viewportWidth.value - (ui.layout.sidebarCollapsed ? layoutPixels('--sidebar-collapsed-width') : sidebarWidth.value) - layoutPixels('--chat-min-width')))
const panelStyle = computed(() => ({
  '--sidebar-width': sidebarWidth.value + 'px',
  '--drawer-width': Math.min(ui.layout.fileExplorerWidth, drawerMaximum.value) + 'px',
  '--drawer-maximum-width': drawerMaximum.value + 'px',
}))
function updateViewport() {
  const wasWide = !narrowSidebar.value
  viewportWidth.value = window.innerWidth
  if (wasWide && narrowSidebar.value && !ui.layout.sidebarCollapsed) ui.layout.toggleSidebar()
}
// Overlay ownership is local presentation state, not a second task/session store.
watch(() => ui.drawerOpen, open => {
  if (open && narrowSidebar.value && !ui.layout.sidebarCollapsed) ui.layout.toggleSidebar()
}, { flush: 'sync' })
watch(() => ui.layout.sidebarCollapsed, collapsed => {
  if (!collapsed && narrowSidebar.value) ui.drawerOpen = false
}, { flush: 'sync' })
const activeOverlay = computed(() => ui.drawerOpen && narrowDrawer.value ? 'work-drawer'
  : !ui.layout.sidebarCollapsed && narrowSidebar.value ? 'session-sidebar' : '')
let opener: HTMLElement | null = null
watch(activeOverlay, async (next, previous) => {
  if (next && !previous) opener = document.activeElement instanceof HTMLElement ? document.activeElement : null
  await nextTick()
  if (activeOverlay.value !== next) return
  if (next) document.getElementById(next)?.querySelector<HTMLElement>('button:not(:disabled), a, input')?.focus({ preventScroll: true })
  else if (previous && opener?.isConnected) opener.focus({ preventScroll: true })
})
function trapOverlay(event: KeyboardEvent) {
  if (!activeOverlay.value || event.key !== 'Tab' || document.querySelector('dialog[open]')) return
  const panel = document.getElementById(activeOverlay.value)
  const controls = Array.from(panel?.querySelectorAll<HTMLElement>('button:not(:disabled), a[href], input, textarea, select, [tabindex="0"]') || [])
    .filter(element => element.getClientRects().length && !element.closest('[inert]'))
  const first = controls[0], last = controls[controls.length - 1]
  if (!first || !last) return
  if (event.shiftKey && (document.activeElement === first || !panel?.contains(document.activeElement))) {
    event.preventDefault(); last.focus()
  } else if (!event.shiftKey && (document.activeElement === last || !panel?.contains(document.activeElement))) {
    event.preventDefault(); first.focus()
  }
}
useShortcuts()
useDesktopBridge()
onMounted(() => {
  window.addEventListener('resize', updateViewport)
  window.addEventListener('keydown', trapOverlay, true)
  void session.loadSessions()
  void settings.loadPreferences()
  if (!settings.loaded) void settings.loadSettings()
  inbox.start()
  if (narrowSidebar.value && !ui.layout.sidebarCollapsed) ui.layout.toggleSidebar()
})
onUnmounted(() => {
  window.removeEventListener('resize', updateViewport)
  window.removeEventListener('keydown', trapOverlay, true)
  inbox.stop()
  session.disconnect()
})
</script>
<template>
  <div class="app-layout inkline-shell">
    <TitleBar :sidebar-overlay="narrowSidebar" />
    <div class="app-body" :style="panelStyle">
      <div v-if="!ui.layout.sidebarCollapsed" class="sidebar-shade" @click="ui.layout.toggleSidebar()" />
      <Sidebar :maximum-width="sidebarMaximum" :inert="activeOverlay === 'work-drawer' ? true : undefined" />
      <main class="main-content" :inert="activeOverlay ? true : undefined"><router-view /></main>
      <Drawer :maximum-width="drawerMaximum" />
    </div>
    <CommandPalette />
  </div>
</template>
<style scoped lang="scss">
@use '@/styles/breakpoints' as breakpoints;
.app-layout { display: flex; flex-direction: column; width: 100vw; height: 100vh; overflow: hidden; background: var(--paper); }
.app-body { display: flex; min-height: 0; flex: 1; }
.main-content { flex: 1; min-width: 0; overflow: auto; }
.sidebar-shade { display: none; }
@include breakpoints.sidebar-overlay {
  .sidebar-shade { display: block; position: fixed; inset: var(--titlebar-height) 0 0; background: var(--backdrop); z-index: 29; }
}
</style>
