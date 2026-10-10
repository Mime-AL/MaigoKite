<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import { useUIStore } from '@/stores/ui'
import { useInboxStore } from '@/stores/inbox'
import { usePulse } from '@/composables/usePulse'
import { useElectron } from '@/composables/useElectron'
import IconSymbol from '@/components/common/IconSymbol.vue'
import Pulse from './Pulse.vue'
const session = useSessionStore(),
  ui = useUIStore(),
  inbox = useInboxStore(),
  route = useRoute()
const { state } = usePulse(),
  { isElectron, platform, windowControl } = useElectron()
const title = computed(() =>
  route.name === 'Chat'
    ? session.activeSession?.title || '新页'
    : String(route.meta.title || '个人空间'),
)
const demo = import.meta.env.VITE_MOCK === '1'
</script>
<template>
  <header class="titlebar" :class="{ mac: platform === 'darwin', offline: state === 'offline' }">
    <button class="icon-button" aria-label="切换侧栏" :aria-expanded="!ui.layout.sidebarCollapsed" @click="ui.layout.toggleSidebar">
      <IconSymbol name="sidebar" :size="16" />
    </button>
    <Pulse :state="state" /><span
      class="session-title"
      :class="{ 'conversation-title': route.name === 'Chat' }"
      >{{ title }}</span
    >
    <div class="title-actions">
      <span v-if="demo" class="demo-label" role="status">演示模式</span>
      <button
        class="inbox-button"
        :aria-expanded="ui.inboxOpen"
        @click="ui.inboxOpen = !ui.inboxOpen"
      >
        等你 <b v-if="inbox.items.length">{{ inbox.items.length }}</b>
      </button>
      <button
        class="icon-button"
        title="切换宣纸 / 松烟"
        @click="ui.setAppearance({ theme: ui.theme === 'dark' ? 'light' : 'dark' })"
      >
        ◐
      </button>
      <button class="icon-button" title="打开抽屉" :aria-expanded="ui.drawerOpen" @click="ui.drawerOpen = !ui.drawerOpen">
        <IconSymbol name="files" :size="16" />
      </button>
      <template v-if="isElectron && platform !== 'darwin'">
        <button class="window-button" aria-label="最小化" @click="windowControl('minimize')">
          ─
        </button>
        <button class="window-button" aria-label="最大化" @click="windowControl('maximize')">
          □
        </button>
        <button class="window-button close" aria-label="关闭窗口" @click="windowControl('close')">
          ×
        </button>
      </template>
    </div>
  </header>
</template>
<style scoped lang="scss">
@use '@/styles/mixins' as mixins;
.titlebar {
  height: var(--titlebar-height);
  flex: none;
  display: flex;
  align-items: center;
  gap: 10px;
  padding-left: 8px;
  border-bottom: 1px solid var(--rule);
  background: var(--paper);
  -webkit-app-region: drag;
  position: relative;
}
.titlebar.mac {
  padding-left: 82px;
}
.titlebar.offline::after {
  content: '';
  height: 2px;
  position: absolute;
  inset: auto 0 0;
  background: var(--wait);
}
.session-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: var(--font-sans);
  font-size: var(--text-sm);
}
.title-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 100%;
}
.demo-label {
  color: var(--wait);
  font-size: var(--text-xs);
  white-space: nowrap;
}
.conversation-title {
  font-family: var(--font-serif);
}
button {
  -webkit-app-region: no-drag;
}
.inbox-button,
.window-button {
  @include mixins.interactive-row;
  height: 100%;
  border: 0;
  background: var(--transparent);
  color: var(--ink-2);
  padding: 0 12px;
  font-size: var(--text-xs);
}
.inbox-button b {
  margin-left: 5px;
  color: var(--wait);
  font-weight: var(--weight-medium);
}
.inbox-button[aria-expanded='true'] {
  color: var(--accent);
  background: var(--accent-selected);
}
</style>
