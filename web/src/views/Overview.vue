<script setup lang="ts">
import { i18n, t } from '@/i18n'
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
  if (hour < 11) return t("早上好")
  if (hour < 18) return t("下午好")
  return t("晚上好")
})

const todayLabel = computed(() =>
  new Intl.DateTimeFormat(i18n.global.locale.value, {
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
  if (Number.isNaN(date.getTime())) return t("刚刚")
  return new Intl.DateTimeFormat(i18n.global.locale.value, {
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
        <h1 class="page-title">{{ greeting }}</h1>
        <p class="page-subtitle">
          {{ $t('{0} · 个人助手', [settingsStore.profile.assistantName]) }}</p>
      </div>
      <button class="primary-button" type="button" :disabled="isCreating" @click="createNewSession">
        <IconSymbol name="compose" :size="17" />
        {{ isCreating ? $t('正在创建') : $t('新建对话') }}
      </button>
    </section>

    <p v-if="sessionStore.error" class="error-banner"><IconSymbol name="alert" :size="16" />{{ sessionStore.error }}</p>

    <section class="metrics" :aria-label="$t('工作区摘要')">
      <article class="metric-card glass-card">
        <span class="metric-icon blue"><IconSymbol name="review" :size="20" /></span>
        <div>
          <strong>{{ sessionStore.sessions.length }}</strong
          ><span>{{ $t('对话') }}</span>
        </div>
      </article>
      <article class="metric-card glass-card">
        <span class="metric-icon green"><IconSymbol name="shield" :size="20" /></span>
        <div><strong>{{ $t('本地') }}</strong><span>{{ $t('工作区') }}</span></div>
      </article>
    </section>

    <section class="content-grid">
      <div class="recent-panel glass-card">
        <header class="panel-header">
          <div>
            <h2>{{ $t('最近对话') }}</h2>
          </div>
          <button class="icon-button" type="button" :title="$t('新建对话')" @click="createNewSession">
            <IconSymbol name="plus" :size="18" />
          </button>
        </header>

        <div v-if="sessionStore.isLoading" class="panel-empty">{{ $t('正在同步对话…') }}</div>
        <div v-else-if="sessionStore.sessions.length" class="session-list">
          <router-link
            v-for="session in sessionStore.sessions.slice(0, 6)"
            :key="session.id"
            :to="`/chat/${session.id}`"
            class="session-row"
          >
            <span class="session-icon"><IconSymbol name="review" :size="17" /></span>
            <span class="session-copy">
              <strong>{{ session.title || $t('未命名对话') }}</strong>
              <small>{{ $t('{0} 条消息 · {1}', [session.message_count, formatUpdatedAt(session.updated_at)]) }}</small>
            </span>
            <IconSymbol name="chevron" :size="15" />
          </router-link>
        </div>
        <div v-else class="panel-empty rich-empty">
          <span><IconSymbol name="compose" :size="23" /></span>
          <strong>{{ $t('暂无对话') }}</strong>
        </div>
      </div>

      <aside class="shortcuts">
        <router-link to="/audit" class="shortcut glass-card">
          <span class="shortcut-icon green"><IconSymbol name="shield" :size="19" /></span>
          <div><strong>{{ $t('审计日志') }}</strong></div>
          <IconSymbol name="chevron" :size="15" />
        </router-link>
        <router-link to="/settings" class="shortcut glass-card">
          <span class="shortcut-icon gray"><IconSymbol name="settings" :size="19" /></span>
          <div><strong>{{ $t('称呼与模型') }}</strong></div>
          <IconSymbol name="chevron" :size="15" />
        </router-link>
      </aside>
    </section>
  </main>
</template>

<style scoped lang="scss">
@use '@/styles/overview';
</style>
