<script setup lang="ts">
import { t } from '@/i18n'
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useLayoutStore } from '@/stores/layout'
import { api } from '@/api/client'
import IconSymbol from '@/components/common/IconSymbol.vue'

const route = useRoute()
const layoutStore = useLayoutStore()
const title = computed(() => t(String(route.meta.title || '工作区')))
const runtimeStatus = ref<'checking' | 'online' | 'offline'>('checking')
let healthRetry: ReturnType<typeof setTimeout> | undefined
let healthAttempts = 0
let disposed = false

function scheduleHealthCheck(delay: number) {
  if (disposed) return
  if (healthRetry) clearTimeout(healthRetry)
  healthRetry = setTimeout(checkHealth, delay)
}

async function checkHealth() {
  try {
    const health = await api.getHealth()
    runtimeStatus.value = health.status === 'ok' ? 'online' : 'offline'
    healthAttempts = 0
    scheduleHealthCheck(30_000)
  } catch {
    runtimeStatus.value = 'offline'
    scheduleHealthCheck(++healthAttempts < 3 ? 1500 : 30_000)
  }
}

const runtimeLabel = computed(
  () =>
    ({ checking: t('正在连接…'), online: t('已连接'), offline: t('未连接') })[runtimeStatus.value],
)
onMounted(() => {
  void checkHealth()
})
onUnmounted(() => {
  disposed = true
  if (healthRetry) clearTimeout(healthRetry)
})
</script>

<template>
  <div class="main-content">
    <header class="titlebar">
      <div class="titlebar-left">
        <button
          class="icon-button no-drag"
          type="button"
          :aria-label="$t('切换侧边栏')"
          @click="layoutStore.toggleSidebar"
        >
          <IconSymbol
            name="sidebar"
            :size="17"
          />
        </button>
        <span class="titlebar-divider" />
        <strong>{{ title }}</strong>
      </div>
      <div class="titlebar-right">
        <span
          class="runtime-status"
          :class="runtimeStatus"
        ><i /> {{ runtimeLabel }}</span>
      </div>
    </header>

    <div class="route-viewport">
      <router-view v-slot="{ Component }">
        <transition
          name="page"
          mode="out-in"
        >
          <component
            :is="Component"
            :key="String(route.name || route.path)"
          />
        </transition>
      </router-view>
    </div>
  </div>
</template>

<style scoped lang="scss">
.main-content {
  display: flex;
  height: 100%;
  min-width: 0;
  flex-direction: column;
  background: var(--paper);
}
.titlebar {
  display: flex;
  height: var(--measure-52px);
  flex: none;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--measure-15px);
  border-bottom: var(--hairline) solid var(--rule);
  background: var(--paper-3);
  -webkit-app-region: drag;
}
.titlebar-left,
.titlebar-right {
  display: flex;
  align-items: center;
  gap: var(--size-10);
}
.titlebar-left strong {
  font-size: var(--text-sm);
  font-weight: var(--weight-semibold);
  letter-spacing: var(--tracking-heading);
}
.titlebar-divider {
  width: var(--hairline);
  height: var(--space-5);
  background: var(--rule);
}
.no-drag {
  -webkit-app-region: no-drag;
}
.runtime-status {
  display: inline-flex;
  align-items: center;
  gap: var(--size-6);
  color: var(--ink-2);
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
}
.runtime-status i {
  width: var(--size-6);
  height: var(--size-6);
  border-radius: var(--radius-round);
  background: var(--ink-2);
  box-shadow: var(--shadow-card);
}
.runtime-status.checking i {
  background: var(--wait);
  box-shadow: var(--shadow-card);
}
.runtime-status.offline i {
  background: var(--ink-2);
  box-shadow: var(--shadow-card);
}
.route-viewport {
  min-height: 0;
  flex: 1;
  overflow: auto;
  background: var(--paper-2);
}
.page-enter-active,
.page-leave-active {
  transition:
    opacity var(--motion-panel) var(--ease),
    transform var(--motion-panel) var(--ease);
}
.page-enter-from {
  opacity: 0;
  transform: translateY(var(--space-2));
}
.page-leave-to {
  opacity: 0;
}
</style>
