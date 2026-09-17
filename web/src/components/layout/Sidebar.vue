<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useLayoutStore } from '@/stores/layout'
import { useSessionStore } from '@/stores/session'
import { useSettingsStore } from '@/stores/settings'
import IconSymbol from '@/components/common/IconSymbol.vue'
import NavMenu from '../sidebar/NavMenu.vue'
import RecentChats from '../sidebar/RecentChats.vue'

const layoutStore = useLayoutStore()
const sessionStore = useSessionStore()
const settingsStore = useSettingsStore()
const router = useRouter()
const isCreating = ref(false)
const assistantName = computed(() => settingsStore.profile.assistantName)
const assistantInitial = computed(() => Array.from(assistantName.value)[0]?.toUpperCase() || '助')

onMounted(() => {
  if (sessionStore.sessions.length === 0) void sessionStore.loadSessions()
})

async function createConversation() {
  if (isCreating.value) return
  isCreating.value = true
  try {
    const session = await sessionStore.createSession('新对话')
    await router.push(`/chat/${session.id}`)
  } catch {
    // Store 已向界面暴露可恢复的错误状态。
  } finally {
    isCreating.value = false
  }
}
</script>

<template>
  <div class="sidebar" :class="{ collapsed: layoutStore.sidebarCollapsed }">
    <div class="window-chrome" aria-hidden="true">
      <span class="traffic red" />
      <span class="traffic amber" />
      <span class="traffic green" />
    </div>

    <div class="brand-row">
      <div class="brand-mark">{{ assistantInitial }}</div>
      <div v-show="!layoutStore.sidebarCollapsed" class="brand-copy">
        <strong>{{ assistantName }}</strong>
        <span>Personal Workspace</span>
      </div>
    </div>

    <button
      class="new-chat"
      type="button"
      :disabled="isCreating"
      :title="layoutStore.sidebarCollapsed ? '新建对话' : undefined"
      @click="createConversation"
    >
      <IconSymbol name="compose" :size="17" />
      <span v-show="!layoutStore.sidebarCollapsed">{{ isCreating ? '正在创建…' : '新建对话' }}</span>
    </button>

    <NavMenu />

    <section v-show="!layoutStore.sidebarCollapsed" class="recent-section">
      <div class="section-label">
        <span>最近对话</span>
        <span>{{ sessionStore.sessions.length }}</span>
      </div>
      <RecentChats />
    </section>

    <div class="sidebar-footer">
      <router-link to="/settings" class="workspace-card" title="设置">
        <span class="avatar">{{ assistantInitial }}</span>
        <span v-show="!layoutStore.sidebarCollapsed" class="workspace-copy">
          <strong>个人空间</strong>
          <small>本地优先</small>
        </span>
        <IconSymbol v-show="!layoutStore.sidebarCollapsed" name="settings" :size="16" />
      </router-link>
    </div>
  </div>
</template>

<style scoped lang="scss">
.sidebar {
  display: flex;
  height: 100%;
  min-width: 64px;
  flex-direction: column;
  padding: 0 11px 12px;
  overflow: hidden;
  background: rgba(245, 247, 251, 0.72);
}

.window-chrome {
  display: flex;
  height: 42px;
  align-items: center;
  gap: 7px;
  padding: 3px 4px 0;
  -webkit-app-region: drag;
}

.traffic { width: 11px; height: 11px; border-radius: 50%; box-shadow: inset 0 0 0 0.5px rgba(0, 0, 0, 0.12); }
.traffic.red { background: #ff5f57; }
.traffic.amber { background: #febc2e; }
.traffic.green { background: #28c840; }

.brand-row {
  display: flex;
  min-height: 46px;
  align-items: center;
  gap: 10px;
  padding: 2px 5px 10px;
}

.brand-mark,
.avatar {
  display: grid;
  flex: none;
  place-items: center;
  color: #fff;
  background: linear-gradient(145deg, #222b42, #69789b);
  box-shadow: inset 0 1px rgba(255, 255, 255, 0.28), 0 4px 12px rgba(27, 39, 65, 0.18);
}

.brand-mark { width: 32px; height: 32px; border-radius: 10px; font-size: 15px; font-weight: 750; }
.brand-copy { min-width: 0; display: flex; flex-direction: column; }
.brand-copy strong { font-size: 14px; letter-spacing: -0.01em; }
.brand-copy span { margin-top: 1px; color: var(--text-tertiary); font-size: 10px; }

.new-chat {
  display: flex;
  width: 100%;
  height: 39px;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin: 5px 0 10px;
  border: 0;
  border-radius: 12px;
  color: #fff;
  background: linear-gradient(180deg, #1689f8, #0071e3);
  box-shadow: 0 7px 16px rgba(0, 113, 227, 0.18), inset 0 1px rgba(255, 255, 255, 0.28);
  cursor: pointer;
  font-size: 13px;
  font-weight: 650;
  transition: transform 150ms ease, filter 150ms ease;
}
.new-chat:hover:not(:disabled) { filter: brightness(1.04); transform: translateY(-1px); }
.new-chat:active:not(:disabled) { transform: scale(0.98); }

.recent-section { min-height: 0; flex: 1; margin-top: 10px; overflow: hidden; }
.section-label { display: flex; justify-content: space-between; padding: 0 8px 7px; color: var(--text-tertiary); font-size: 10px; font-weight: 700; letter-spacing: 0.045em; text-transform: uppercase; }

.sidebar-footer { margin-top: auto; padding-top: 9px; border-top: 1px solid var(--border-color); }
.workspace-card { display: flex; height: 45px; align-items: center; gap: 9px; padding: 6px; border-radius: 13px; color: var(--text-secondary); transition: background 150ms ease; }
.workspace-card:hover { background: var(--surface-strong); }
.avatar { width: 31px; height: 31px; border-radius: 50%; font-size: 12px; font-weight: 750; }
.workspace-copy { min-width: 0; display: flex; flex: 1; flex-direction: column; }
.workspace-copy strong { color: var(--text-primary); font-size: 12px; font-weight: 650; }
.workspace-copy small { color: var(--text-tertiary); font-size: 10px; }

.collapsed {
  align-items: center;
  padding-inline: 8px;
  .window-chrome { width: 100%; justify-content: center; gap: 3px; }
  .traffic { width: 6px; height: 6px; }
  .brand-row { justify-content: center; padding-inline: 0; }
  .new-chat { width: 42px; }
  .sidebar-footer { width: 100%; }
  .workspace-card { justify-content: center; padding: 6px 0; }
}

@media (prefers-color-scheme: dark) {
  .sidebar { background: rgba(27, 28, 33, 0.78); }
}
</style>
