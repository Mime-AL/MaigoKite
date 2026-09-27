<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import { useSettingsStore } from '@/stores/settings'
import IconSymbol from '@/components/common/IconSymbol.vue'

const sessionStore = useSessionStore()
const settingsStore = useSettingsStore()
const router = useRouter()
const isCreating = ref(false)

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 11) return '早上好'
  if (hour < 18) return '下午好'
  return '晚上好'
})

const todayLabel = computed(() => new Intl.DateTimeFormat('zh-CN', {
  month: 'long',
  day: 'numeric',
  weekday: 'long',
}).format(new Date()))

onMounted(() => {
  void sessionStore.loadSessions()
})

async function createNewSession() {
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

function formatUpdatedAt(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '刚刚'
  return new Intl.DateTimeFormat('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(date)
}
</script>

<template>
  <main class="page-shell overview">
    <section class="hero">
      <div>
        <p class="page-eyebrow">{{ todayLabel }}</p>
        <h1 class="page-title">{{ greeting }}，今天想完成什么？</h1>
        <p class="page-subtitle">从一个想法开始。{{ settingsStore.profile.assistantName }} 会组织当前对话的上下文，并给出清晰回答。</p>
      </div>
      <button class="primary-button" type="button" :disabled="isCreating" @click="createNewSession">
        <IconSymbol name="compose" :size="17" />
        {{ isCreating ? '正在创建' : '开始新对话' }}
      </button>
    </section>

    <p v-if="sessionStore.error" class="error-banner"><IconSymbol name="alert" :size="16" />{{ sessionStore.error }}</p>

    <section class="metrics" aria-label="工作区摘要">
      <article class="metric-card glass-card">
        <span class="metric-icon blue"><IconSymbol name="review" :size="20" /></span>
        <div><strong>{{ sessionStore.sessions.length }}</strong><span>对话</span></div>
        <small>个人空间</small>
      </article>
      <article class="metric-card glass-card">
        <span class="metric-icon green"><IconSymbol name="shield" :size="20" /></span>
        <div><strong>本地</strong><span>工作区</span></div>
        <small>当前工作区</small>
      </article>
    </section>

    <section class="content-grid">
      <div class="recent-panel glass-card">
        <header class="panel-header">
          <div><p>Continue</p><h2>最近对话</h2></div>
          <button class="icon-button" type="button" title="新建对话" @click="createNewSession"><IconSymbol name="plus" :size="18" /></button>
        </header>

        <div v-if="sessionStore.isLoading" class="panel-empty">正在同步对话…</div>
        <div v-else-if="sessionStore.sessions.length" class="session-list">
          <router-link v-for="session in sessionStore.sessions.slice(0, 6)" :key="session.id" :to="`/chat/${session.id}`" class="session-row">
            <span class="session-icon"><IconSymbol name="review" :size="17" /></span>
            <span class="session-copy">
              <strong>{{ session.title || '未命名对话' }}</strong>
              <small>{{ session.message_count }} 条消息 · {{ formatUpdatedAt(session.updated_at) }}</small>
            </span>
            <IconSymbol name="chevron" :size="15" />
          </router-link>
        </div>
        <div v-else class="panel-empty rich-empty">
          <span><IconSymbol name="compose" :size="23" /></span>
          <strong>这里会保存你的工作脉络</strong>
          <p>创建第一段对话，稍后可以从这里继续。</p>
        </div>
      </div>

      <aside class="shortcuts">
        <router-link to="/audit" class="shortcut glass-card">
          <span class="shortcut-icon green"><IconSymbol name="shield" :size="19" /></span>
          <div><strong>审计日志</strong><small>查看已记录的安全操作</small></div>
          <IconSymbol name="chevron" :size="15" />
        </router-link>
        <router-link to="/settings" class="shortcut glass-card">
          <span class="shortcut-icon gray"><IconSymbol name="settings" :size="19" /></span>
          <div><strong>称呼与模型</strong><small>管理界面称呼与模型接入</small></div>
          <IconSymbol name="chevron" :size="15" />
        </router-link>
      </aside>
    </section>
  </main>
</template>

<style scoped lang="scss">
.overview { display: flex; flex-direction: column; gap: 28px; }
.hero { display: flex; align-items: flex-end; justify-content: space-between; gap: 30px; padding-top: 6px; }
.hero .primary-button { flex: none; margin-bottom: 3px; }
.error-banner { display: flex; align-items: center; gap: 9px; margin: -8px 0 0; padding: 11px 14px; border-radius: 12px; color: var(--danger); background: var(--danger-soft); font-size: 12px; }
.metrics { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 13px; }
.metric-card { display: grid; grid-template-columns: auto 1fr; align-items: center; gap: 13px; padding: 17px; }
.metric-icon, .shortcut-icon { display: grid; place-items: center; border-radius: 13px; }
.metric-icon { width: 42px; height: 42px; }
.blue { color: #087bd7; background: rgba(74, 158, 255, 0.13); }
.purple { color: #8a63d2; background: rgba(138, 99, 210, 0.13); }
.green { color: var(--success); background: var(--success-soft); }
.orange { color: #da782b; background: rgba(218, 120, 43, 0.13); }
.gray { color: var(--text-secondary); background: var(--surface-strong); }
.metric-card div { display: flex; flex-direction: column; }
.metric-card strong { font-size: 20px; line-height: 1; letter-spacing: -0.035em; }
.metric-card div span { margin-top: 5px; color: var(--text-secondary); font-size: 11px; }
.metric-card small { grid-column: 1 / -1; display: flex; align-items: center; gap: 6px; padding-top: 11px; border-top: 1px solid var(--border-color); color: var(--text-tertiary); font-size: 10px; }
.metric-card small i { width: 5px; height: 5px; border-radius: 50%; background: var(--success); }
.content-grid { display: grid; grid-template-columns: minmax(0, 1.65fr) minmax(220px, 0.8fr); gap: 14px; align-items: start; }
.recent-panel { min-height: 330px; overflow: hidden; }
.panel-header { display: flex; height: 74px; align-items: center; justify-content: space-between; padding: 0 19px 0 22px; border-bottom: 1px solid var(--border-color); }
.panel-header p { margin: 0 0 2px; color: var(--text-tertiary); font-size: 9px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; }
.panel-header h2 { margin: 0; font-size: 17px; letter-spacing: -0.025em; }
.session-list { padding: 7px; }
.session-row { display: flex; min-height: 50px; align-items: center; gap: 11px; padding: 7px 10px; border-radius: 13px; transition: background 150ms ease, transform 150ms ease; }
.session-row:hover { background: var(--surface-strong); transform: translateX(2px); }
.session-icon { display: grid; width: 33px; height: 33px; flex: none; place-items: center; border-radius: 10px; color: var(--primary-color); background: var(--primary-soft); }
.session-copy { min-width: 0; display: flex; flex: 1; flex-direction: column; }
.session-copy strong { overflow: hidden; font-size: 12.5px; font-weight: 620; text-overflow: ellipsis; white-space: nowrap; }
.session-copy small { margin-top: 3px; color: var(--text-tertiary); font-size: 10px; }
.panel-empty { display: grid; min-height: 250px; place-items: center; color: var(--text-tertiary); font-size: 12px; }
.rich-empty { align-content: center; justify-items: center; gap: 5px; text-align: center; }
.rich-empty > span { display: grid; width: 48px; height: 48px; margin-bottom: 7px; place-items: center; border-radius: 15px; color: var(--primary-color); background: var(--primary-soft); }
.rich-empty strong { color: var(--text-primary); font-size: 13px; }
.rich-empty p { margin: 0; font-size: 10.5px; }
.shortcuts { display: grid; gap: 10px; }
.shortcut { display: flex; min-height: 72px; align-items: center; gap: 11px; padding: 13px; transition: transform 160ms ease, box-shadow 160ms ease; }
.shortcut:hover { transform: translateY(-2px); box-shadow: var(--shadow-float); }
.shortcut-icon { width: 39px; height: 39px; flex: none; }
.shortcut div { min-width: 0; display: flex; flex: 1; flex-direction: column; }
.shortcut strong { font-size: 12px; font-weight: 650; }
.shortcut small { margin-top: 4px; overflow: hidden; color: var(--text-tertiary); font-size: 9.5px; text-overflow: ellipsis; white-space: nowrap; }
@media (max-width: 1080px) { .content-grid { grid-template-columns: 1fr; } .shortcuts { grid-template-columns: repeat(2, 1fr); } .shortcut { align-items: flex-start; } .shortcut > :deep(.icon-symbol:last-child) { display: none; } }
@media (max-width: 800px) { .metrics { grid-template-columns: 1fr; } .hero { align-items: flex-start; flex-direction: column; } .shortcuts { grid-template-columns: 1fr; } }
</style>
