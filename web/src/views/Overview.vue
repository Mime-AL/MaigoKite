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

const todayLabel = computed(() =>
  new Intl.DateTimeFormat('zh-CN', {
    month: 'long',
    day: 'numeric',
    weekday: 'long',
  }).format(new Date()),
)

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
  return new Intl.DateTimeFormat('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}
</script>

<template>
  <main class="page-shell overview">
    <section class="hero">
      <div>
        <p class="page-eyebrow">{{ todayLabel }}</p>
        <h1 class="page-title">{{ greeting }}，今天想完成什么？</h1>
        <p class="page-subtitle">
          从一个想法开始。{{ settingsStore.profile.assistantName }} 会组织当前对话的上下文，并给出清晰回答。
        </p>
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
        <div>
          <strong>{{ sessionStore.sessions.length }}</strong
          ><span>对话</span>
        </div>
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
          <div>
            <p>Continue</p>
            <h2>最近对话</h2>
          </div>
          <button class="icon-button" type="button" title="新建对话" @click="createNewSession">
            <IconSymbol name="plus" :size="18" />
          </button>
        </header>

        <div v-if="sessionStore.isLoading" class="panel-empty">正在同步对话…</div>
        <div v-else-if="sessionStore.sessions.length" class="session-list">
          <router-link
            v-for="session in sessionStore.sessions.slice(0, 6)"
            :key="session.id"
            :to="`/chat/${session.id}`"
            class="session-row"
          >
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
@use '@/styles/overview';
</style>
