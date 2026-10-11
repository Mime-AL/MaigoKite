<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useInboxStore } from '@/stores/inbox'
import { pendingItem } from '@/utils/rail-presentation'
import IconSymbol from '@/components/common/IconSymbol.vue'
import SidebarToggle from './SidebarToggle.vue'
defineProps<{ platform: string; sidebarOverlay?: boolean }>()
const inbox = useInboxStore(),
  route = useRoute()
const currentId = computed(() => (route.name === 'Chat' ? String(route.params.id || '') : ''))
const otherPending = computed(
  () => inbox.items.filter((item) => pendingItem(item) && item.sessionId !== currentId.value).length,
)
function windowControl(action: 'minimize' | 'maximize' | 'close') {
  void window.electronAPI?.windowControl(action)
}
</script>
<template>
  <header
    class="windowbar"
    :class="{ mac: platform === 'darwin' }"
    :aria-label="$t('应用窗口')"
    @dblclick.self="windowControl('maximize')"
  >
    <SidebarToggle
      :pending-count="otherPending"
      :sidebar-overlay="sidebarOverlay"
    />
    <span
      class="window-title"
      @dblclick="windowControl('maximize')"
    >MaigoKite</span>
    <div
      v-if="platform !== 'darwin'"
      class="window-controls"
      role="group"
      :aria-label="$t('窗口控制')"
    >
      <button
        v-for="control in ['minimize', 'maximize', 'close'] as const"
        :key="control"
        class="window-button"
        :class="{ close: control === 'close' }"
        type="button"
        :title="$t(control === 'minimize' ? '最小化' : control === 'maximize' ? '最大化 / 还原' : '关闭窗口')"
        :aria-label="$t(control === 'minimize' ? '最小化' : control === 'maximize' ? '最大化 / 还原' : '关闭窗口')"
        @click="windowControl(control)"
      >
        <IconSymbol
          :name="control"
          :size="18"
        />
      </button>
    </div>
  </header>
</template>
<style scoped lang="scss">
.windowbar {
  display: flex;
  align-items: center;
  flex: none;
  height: var(--window-titlebar-height);
  padding-inline-start: var(--space-3);
  gap: var(--space-3);
  border-bottom: var(--hairline) solid var(--rule);
  background: var(--paper-2);
  -webkit-app-region: drag;
}
.windowbar.mac {
  padding-inline-start: var(--mac-titlebar-inset);
}
.window-title {
  flex: 1;
  min-width: 0;
  color: var(--ink-2);
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.window-controls {
  display: flex;
  flex: none;
  height: 100%;
  margin-inline-start: var(--titlebar-system-gap);
  -webkit-app-region: no-drag;
}
.window-button {
  display: grid;
  place-items: center;
  flex: none;
  width: var(--titlebar-window-button-width);
  height: 100%;
  padding: 0;
  border: 0;
  border-radius: var(--radius-none);
  background: var(--transparent);
  color: var(--ink-2);
}
@media (hover: hover) {
  .window-button:hover {
    color: var(--ink);
    background: var(--control-hover);
  }
}
.window-button:focus-visible {
  background: var(--control-hover);
  outline-offset: calc(-1 * var(--focus-width));
}
.window-button:active {
  background: var(--control-pressed);
  transform: none;
  translate: none;
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
