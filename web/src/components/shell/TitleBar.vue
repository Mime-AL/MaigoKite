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
import SessionTitle from '@/components/common/SessionTitle.vue'
import Pulse from './Pulse.vue'
defineProps<{ sidebarOverlay?: boolean }>()
const session = useSessionStore(), ui = useUIStore(), inbox = useInboxStore(), route = useRoute()
const { state } = usePulse(), { isElectron, platform, windowControl } = useElectron()
const currentId = computed(() => route.name === 'Chat' ? String(route.params.id || '') : '')
const title = computed(() => route.name === 'Chat' ? session.activeSession?.title || t('新页') : t(String(route.meta.title || '个人空间')))
const otherPending = computed(() => inbox.items.filter(item => !item.closed && !item.verdict &&
  item.answer === undefined && item.sessionId !== currentId.value).length)
const drawerLabel = computed(() => [t(ui.drawerOpen ? '收起抽屉' : '打开抽屉'),
  ...(otherPending.value ? [t('{0} 项等你处理', [otherPending.value])] : [])].join(' · '))
function toggleDrawer() {
  if (ui.drawerOpen) ui.drawerOpen = false
  else ui.openDrawer(otherPending.value ? 'pending' : ui.drawerTab)
}
</script>
<template>
  <header class="titlebar" :class="{ mac: platform === 'darwin', offline: state === 'offline' }">
    <button class="title-button" type="button" :title="$t(ui.layout.sidebarCollapsed ? '展开侧栏' : '收起侧栏')"
      :aria-label="$t(ui.layout.sidebarCollapsed ? '展开侧栏' : '收起侧栏')" :aria-expanded="!ui.layout.sidebarCollapsed"
      aria-controls="session-sidebar" @click="ui.layout.toggleSidebar">
      <IconSymbol name="sidebar" :size="20" />
      <span v-if="otherPending && (ui.layout.sidebarCollapsed || sidebarOverlay)" class="pending-count"
        :aria-label="$t('{0} 项等你处理', [otherPending])">{{ otherPending }}</span>
    </button>
    <AppIcon :size="20" /><Pulse :state="state" :size="12" />
    <SessionTitle :title="title" :serif="route.name === 'Chat'"
      :session-id="currentId && session.activeSession?.id === currentId ? currentId : undefined" />
    <div class="title-actions">
      <button class="title-button" type="button" :title="$t(ui.theme === 'dark' ? '切换到宣纸' : '切换到松烟')"
        :aria-label="$t(ui.theme === 'dark' ? '切换到宣纸' : '切换到松烟')"
        @click="ui.setAppearance({ theme: ui.theme === 'dark' ? 'light' : 'dark' })">
        <IconSymbol :name="ui.theme === 'dark' ? 'sun' : 'moon'" :size="20" />
      </button>
      <button class="title-button drawer-toggle" type="button" :title="drawerLabel" :aria-label="drawerLabel"
        :aria-expanded="ui.drawerOpen" aria-controls="work-drawer" @click="toggleDrawer">
        <IconSymbol name="files" :size="20" />
        <span v-if="otherPending" class="pending-count" :aria-label="$t('{0} 项等你处理', [otherPending])">{{ otherPending }}</span>
      </button>
      <div v-if="isElectron && platform !== 'darwin'" class="window-controls">
        <button v-for="control in (['minimize', 'maximize', 'close'] as const)" :key="control"
          class="window-button" :class="{ close: control === 'close' }"
          :title="$t(control === 'minimize' ? '最小化' : control === 'maximize' ? '最大化 / 还原' : '关闭窗口')"
          :aria-label="$t(control === 'minimize' ? '最小化' : control === 'maximize' ? '最大化 / 还原' : '关闭窗口')"
          @click="windowControl(control)"><IconSymbol :name="control" :size="18" /></button>
      </div>
    </div>
  </header>
</template>
<style scoped lang="scss">
@use '@/styles/mixins' as mixins;
.titlebar { height: var(--titlebar-height); flex: none; display: flex; align-items: center; gap: var(--space-4); padding-left: var(--space-3); border-bottom: var(--hairline) solid var(--rule); background: var(--paper); -webkit-app-region: drag; position: relative; }
.titlebar.mac { padding-left: var(--mac-titlebar-inset); }
.titlebar.offline::after { content: ''; height: var(--pending-line); position: absolute; inset: auto 0 0; background: var(--wait); }
.title-actions { display: flex; align-items: center; gap: var(--space-2); height: 100%; padding-right: var(--space-2); }
button { -webkit-app-region: no-drag; }
.title-button { @include mixins.interactive-row; position: relative; display: grid; place-items: center; flex: none; width: var(--titlebar-button-size); height: var(--titlebar-button-size); padding: 0; border: var(--hairline) solid var(--transparent); border-radius: var(--radius-sm); background: var(--transparent); color: var(--ink-2); }
.title-button[aria-expanded='true'] { color: var(--accent); background: var(--accent-selected); }
.title-button:active { transform: scale(var(--press-scale)); }
.pending-count { display: grid; place-items: center; position: absolute; top: 0; right: 0; min-width: var(--pending-badge-size); height: var(--pending-badge-size); padding-inline: var(--space-2); border-radius: var(--radius-pill); background: var(--wait-soft); color: var(--wait-ink); font-size: var(--text-xs); font-variant-numeric: tabular-nums; box-shadow: 0 0 0 var(--hairline) var(--paper); }
.window-controls { display: flex; height: 100%; margin-left: var(--space-3); margin-right: calc(-1 * var(--space-2)); }
.window-button { @include mixins.interactive-row; display: grid; place-items: center; width: var(--titlebar-window-button-width); height: 100%; padding: 0; border: 0; border-radius: var(--radius-none); background: var(--transparent); color: var(--ink-2); }
.window-button.close:hover, .window-button.close:focus-visible { color: var(--seal); background: var(--seal-hover); }
.window-button.close:active { color: var(--seal); background: var(--seal-pressed); }
</style>
