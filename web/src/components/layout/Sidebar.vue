<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import { useSettingsStore } from '@/stores/settings'
import { useUIStore } from '@/stores/ui'
import WorkspaceSelector from '@/components/sidebar/WorkspaceSelector.vue'
import SessionItem from '@/components/sidebar/SessionItem.vue'
import IconSymbol from '@/components/common/IconSymbol.vue'
const session = useSessionStore(),
  settings = useSettingsStore(),
  ui = useUIStore(),
  router = useRouter()
const creating = ref(false)
const groups = computed(() => {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const week = new Date(today)
  week.setDate(week.getDate() - ((week.getDay() + 6) % 7))
  return [
    { label: '今天', min: today.getTime(), max: Infinity },
    { label: '本周', min: week.getTime(), max: today.getTime() },
    { label: '更早', min: -Infinity, max: week.getTime() },
  ].map((group) => ({
    ...group,
    sessions: session.visibleSessions
      .slice()
      .sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at))
      .filter((s) => {
        const time = Date.parse(s.updated_at)
        return time >= group.min && time < group.max
      }),
  }))
})
async function create() {
  if (creating.value) return
  creating.value = true
  try {
    const item = await session.createSession('新对话')
    await router.push('/chat/' + item.id)
    closeOnNarrowScreen()
  } catch {
    /* Store exposes the failure. */
  } finally {
    creating.value = false
  }
}
function closeOnNarrowScreen() {
  if (window.innerWidth < 720 && !ui.layout.sidebarCollapsed) ui.layout.toggleSidebar()
}
</script>
<template>
  <aside class="sidebar" :class="{ collapsed: ui.layout.sidebarCollapsed }">
    <div class="identity">
      <span class="avatar">{{ ui.appearance.avatar }}</span
      ><strong v-if="!ui.layout.sidebarCollapsed">{{ settings.profile.assistantName }}</strong>
    </div>
    <WorkspaceSelector :collapsed="ui.layout.sidebarCollapsed" />
    <button class="new-page" title="新页" :disabled="creating" :aria-busy="creating || undefined" @click="create">
      <IconSymbol v-if="!creating" name="compose" :size="16" /><span v-if="!ui.layout.sidebarCollapsed">{{ creating ? '正在新建…' : '新页' }}</span>
    </button>
    <button class="search-page" title="搜索会话" @click="ui.commandOpen = true">
      <IconSymbol name="search" :size="16" /><span v-if="!ui.layout.sidebarCollapsed">搜索</span>
    </button>
    <button class="search-page" :aria-pressed="session.showArchived" :title="session.showArchived ? '查看当前对话' : '查看归档对话'" @click="session.showArchived = !session.showArchived">
      <IconSymbol name="archive" :size="16" /><span v-if="!ui.layout.sidebarCollapsed">{{ session.showArchived ? '返回对话' : '归档对话' }}</span>
    </button>
    <div class="session-groups">
      <p v-if="!ui.layout.sidebarCollapsed && session.isLoading" class="empty-copy">
        正在读取会话…
      </p>
      <p
        v-else-if="!ui.layout.sidebarCollapsed && session.error && !session.sessions.length"
        class="empty-copy"
        role="alert"
      >
        {{ session.error }}
        <button class="secondary-button" @click="session.loadSessions">重新连接</button>
      </p>
      <p v-else-if="!ui.layout.sidebarCollapsed && !session.visibleSessions.length" class="empty-copy">
        {{ session.showArchived ? '这个工作区还没有归档对话。' : '这个工作区还没有对话。' }}
      </p>
      <section v-for="group in groups" :key="group.label">
        <h2 v-if="group.sessions.length && !ui.layout.sidebarCollapsed">{{ group.label }}</h2>
        <SessionItem
          v-for="item in group.sessions"
          :key="item.id"
          :item="item"
          :collapsed="ui.layout.sidebarCollapsed"
          @select="closeOnNarrowScreen"
        />
      </section>
    </div>
    <footer>
      <router-link to="/memory" title="它记得" @click="closeOnNarrowScreen"
        ><span>✦</span><span v-if="!ui.layout.sidebarCollapsed">它记得</span></router-link
      >
      <router-link to="/settings" title="设置" @click="closeOnNarrowScreen"
        ><IconSymbol name="settings" :size="16" /><span v-if="!ui.layout.sidebarCollapsed"
          >设置</span
        ></router-link
      >
    </footer>
  </aside>
</template>
<style scoped lang="scss">
@use '@/styles/mixins' as mixins;
.sidebar {
  width: var(--sidebar-width);
  height: 100%;
  flex: none;
  background: var(--paper-2);
  border-right: 1px solid var(--rule);
  display: flex;
  flex-direction: column;
  padding: 22px 14px 16px;
  transition: width var(--duration-slow) var(--ease);
}
.sidebar.collapsed {
  width: 56px;
  padding-inline: 8px;
}
.identity {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 4px 24px;
}
.identity strong {
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
}
.avatar {
  display: grid;
  width: 26px;
  height: 26px;
  place-content: center;
  border: 1px solid var(--rule);
  border-radius: var(--radius-sm);
  color: var(--ink-2);
  font-size: var(--text-sm);
}
.new-page,
.search-page {
  @include mixins.interactive-row;
  display: flex;
  align-items: center;
  gap: 10px;
  height: 36px;
  padding: 8px;
  margin-bottom: 4px;
  background: var(--transparent);
  border: 0;
  text-align: left;
  font-size: var(--text-sm);
}
.new-page {
  color: var(--ink);
}
.search-page {
  color: var(--ink-2);
}
.session-groups {
  min-height: 0;
  flex: 1;
  overflow-y: auto;
  padding-top: 20px;
}
h2 {
  font-size: var(--text-xs);
  font-weight: var(--weight-normal);
  color: var(--ink-3);
  margin: 18px 8px 8px;
}
footer {
  border-top: 1px solid var(--rule);
  padding-top: 12px;
}
footer a {
  @include mixins.interactive-row;
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 10px 8px;
  color: var(--ink-2);
  font-size: var(--text-sm);
  text-decoration: none;
  border-radius: var(--radius-sm);
}
footer a.router-link-active {
  color: var(--accent);
  background: var(--accent-selected);
}
@media (max-width: 720px) {
  .sidebar {
    position: fixed;
    inset: var(--titlebar-height) auto 0 0;
    z-index: 30;
    box-shadow: var(--shadow-float);
  }
  .sidebar.collapsed {
    display: none;
  }
}
</style>
