<script setup lang="ts">
import { useUIStore } from '@/stores/ui'
import ChangesTab from '@/components/drawer/ChangesTab.vue'
import JobsTab from '@/components/drawer/JobsTab.vue'
import PlanTab from '@/components/drawer/PlanTab.vue'
import FileExplorer from '@/components/layout/FileExplorer.vue'
const ui = useUIStore()
const tabs = [
  { id: 'changes', label: '变更' },
  { id: 'jobs', label: '任务' },
  { id: 'plan', label: '计划' },
  { id: 'files', label: '文件' },
] as const
</script>
<template>
  <div v-if="ui.drawerOpen" class="drawer-shade" @click="ui.drawerOpen = false" />
  <aside v-if="ui.drawerOpen" class="drawer" aria-label="工作抽屉">
    <header>
      <nav>
        <button
          v-for="tab in tabs"
          :key="tab.id"
          :class="{ active: ui.drawerTab === tab.id }"
          :aria-pressed="ui.drawerTab === tab.id"
          @click="ui.drawerTab = tab.id"
        >
          {{ tab.label }}
        </button>
      </nav>
      <button class="icon-button" aria-label="关闭抽屉" @click="ui.drawerOpen = false">×</button>
    </header>
    <ChangesTab v-if="ui.drawerTab === 'changes'" /><JobsTab
      v-else-if="ui.drawerTab === 'jobs'"
    /><PlanTab v-else-if="ui.drawerTab === 'plan'" /><FileExplorer v-else embedded />
  </aside>
</template>
<style scoped lang="scss">
@use '@/styles/mixins' as mixins;
.drawer {
  display: flex;
  flex-direction: column;
  width: var(--drawer-width);
  flex: none;
  min-height: 0;
  border-left: 1px solid var(--rule);
  background: var(--paper);
  z-index: 20;
}
header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  border-bottom: 1px solid var(--rule);
}
nav {
  display: flex;
  gap: 4px;
}
nav button {
  @include mixins.interactive-row;
  padding: 6px 10px;
  border: 0;
  color: var(--ink-3);
  background: var(--transparent);
  font-size: var(--text-sm);
}
nav button.active {
  color: var(--accent);
  background: var(--accent-selected);
}
.drawer-shade {
  display: none;
}
@media (max-width: 1100px) {
  .drawer {
    position: absolute;
    right: 0;
    top: var(--titlebar-height);
    bottom: 0;
    width: min(var(--drawer-width), 100vw);
    box-shadow: var(--shadow-float);
  }
  .drawer-shade {
    display: block;
    position: fixed;
    inset: var(--titlebar-height) 0 0;
    z-index: 19;
    background: var(--backdrop);
  }
}
</style>
