<script setup lang="ts">
import { t } from '@/i18n'
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import { useUIStore } from '@/stores/ui'
import { useInboxStore } from '@/stores/inbox'
import { usePulse } from '@/composables/usePulse'
import { useElectron } from '@/composables/useElectron'
import IconSymbol from '@/components/common/IconSymbol.vue'
import AppIcon from '@/components/common/AppIcon.vue'
import Pulse from './Pulse.vue'
const session = useSessionStore(),
  ui = useUIStore(),
  inbox = useInboxStore(),
  route = useRoute()
const { state } = usePulse(),
  { isElectron, platform, windowControl } = useElectron()
const title = computed(() =>
  route.name === 'Chat'
    ? session.activeSession?.title || t('新页')
    : t(String(route.meta.title || '个人空间')),
)
const notificationLabel = computed(() =>
  inbox.items.length ? t('通知，{0} 项待处理', [inbox.items.length]) : t('通知'),
)
</script>
<template>
  <header class="titlebar" :class="{ mac: platform === 'darwin', offline: state === 'offline' }">
    <button
      class="title-button"
      type="button"
      :title="ui.layout.sidebarCollapsed ? $t('展开侧栏') : $t('收起侧栏')"
      :aria-label="ui.layout.sidebarCollapsed ? $t('展开侧栏') : $t('收起侧栏')"
      :aria-expanded="!ui.layout.sidebarCollapsed"
      aria-controls="session-sidebar"
      @click="ui.layout.toggleSidebar"
    >
      <IconSymbol name="sidebar" :size="20" />
    </button>
    <AppIcon :size="20" />
    <Pulse :state="state" /><span
      class="session-title"
      :class="{ 'conversation-title': route.name === 'Chat' }"
      >{{ title }}</span
    >
    <div class="title-actions">
      <button
        class="title-button notification-button"
        type="button"
        :title="notificationLabel"
        :aria-label="notificationLabel"
        :aria-expanded="ui.inboxOpen"
        aria-haspopup="dialog"
        @click="ui.inboxOpen = !ui.inboxOpen"
      >
        <IconSymbol name="bell" :size="20" />
        <i v-if="inbox.items.length" class="notification-dot" aria-hidden="true" />
      </button>
      <button
        class="title-button"
        type="button"
        :title="ui.theme === 'dark' ? $t('切换到宣纸') : $t('切换到松烟')"
        :aria-label="ui.theme === 'dark' ? $t('切换到宣纸') : $t('切换到松烟')"
        @click="ui.setAppearance({ theme: ui.theme === 'dark' ? 'light' : 'dark' })"
      >
        <IconSymbol :name="ui.theme === 'dark' ? 'sun' : 'moon'" :size="20" />
      </button>
      <button
        class="title-button"
        type="button"
        :title="ui.drawerOpen ? $t('收起抽屉') : $t('打开抽屉')"
        :aria-label="ui.drawerOpen ? $t('收起抽屉') : $t('打开抽屉')"
        :aria-expanded="ui.drawerOpen"
        aria-controls="work-drawer"
        @click="ui.drawerOpen = !ui.drawerOpen"
      >
        <IconSymbol name="files" :size="20" />
      </button>
      <div v-if="isElectron && platform !== 'darwin'" class="window-controls">
        <button
          class="title-button window-button"
          type="button"
          :title="$t('最小化')"
          :aria-label="$t('最小化')"
          @click="windowControl('minimize')"
        >
          <IconSymbol name="minimize" :size="18" />
        </button>
        <button
          class="title-button window-button"
          type="button"
          :title="$t('最大化 / 还原')"
          :aria-label="$t('最大化 / 还原')"
          @click="windowControl('maximize')"
        >
          <IconSymbol name="maximize" :size="16" />
        </button>
        <button
          class="title-button window-button close"
          type="button"
          :title="$t('关闭窗口')"
          :aria-label="$t('关闭窗口')"
          @click="windowControl('close')"
        >
          <IconSymbol name="close" :size="18" />
        </button>
      </div>
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
  gap: 6px;
  height: 100%;
  padding-right: 4px;
}
.conversation-title {
  font-family: var(--font-serif);
}
button {
  -webkit-app-region: no-drag;
}
.title-button {
  @include mixins.interactive-row;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: none;
  width: var(--titlebar-button-size);
  height: var(--titlebar-button-size);
  padding: 0;
  border: 1px solid var(--rule);
  border-radius: var(--radius-sm);
  background: var(--paper-2);
  color: var(--ink);
}
.title-button[aria-expanded='true'] {
  color: var(--accent);
  border-color: var(--accent);
  background: var(--accent-selected);
}
.title-button:not(:disabled):active {
  scale: var(--press-scale);
}
.notification-button {
  position: relative;
}
.notification-dot {
  position: absolute;
  top: 5px;
  right: 6px;
  width: 7px;
  height: 7px;
  border-radius: var(--radius-round);
  background: var(--notification-dot);
  outline: 2px solid var(--paper-2);
  pointer-events: none;
}
.window-controls {
  display: flex;
  height: 100%;
  align-items: center;
  gap: 4px;
  margin-left: 6px;
  padding-left: 6px;
  border-left: 1px solid var(--rule);
}
.window-button {
  width: var(--titlebar-window-button-width);
  background: var(--transparent);
  border-color: var(--transparent);
}
.window-button.close:hover,
.window-button.close:focus-visible {
  color: var(--seal);
  background: var(--seal-hover);
}
.window-button.close:active {
  color: var(--seal);
  background: var(--seal-pressed);
}
</style>
