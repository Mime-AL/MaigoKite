<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useLayoutStore } from '@/stores/layout'
import { api } from '@/api/client'
import IconSymbol from '@/components/common/IconSymbol.vue'

const route = useRoute()
const layoutStore = useLayoutStore()
const title = computed(() => String(route.meta.title || '工作区'))
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

const runtimeLabel = computed(() => ({ checking: '检查运行时…', online: '运行正常', offline: '运行时离线' })[runtimeStatus.value])
onMounted(() => { void checkHealth() })
onUnmounted(() => { disposed = true; if (healthRetry) clearTimeout(healthRetry) })
</script>

<template>
  <div class="main-content">
    <header class="titlebar">
      <div class="titlebar-left">
        <button class="icon-button no-drag" type="button" aria-label="切换侧边栏" @click="layoutStore.toggleSidebar">
          <IconSymbol name="sidebar" :size="17" />
        </button>
        <span class="titlebar-divider" />
        <strong>{{ title }}</strong>
      </div>
      <div class="titlebar-right">
        <span class="runtime-status" :class="runtimeStatus"><i /> {{ runtimeLabel }}</span>
      </div>
    </header>

    <div class="route-viewport">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" :key="String(route.name || route.path)" />
        </transition>
      </router-view>
    </div>
  </div>
</template>

<style scoped lang="scss">
.main-content { display: flex; height: 100%; min-width: 0; flex-direction: column; background: var(--surface-solid); }
.titlebar { display: flex; height: 52px; flex: none; align-items: center; justify-content: space-between; padding: 0 15px; border-bottom: 1px solid var(--border-color); background: rgba(255, 255, 255, 0.72); -webkit-app-region: drag; }
.titlebar-left, .titlebar-right { display: flex; align-items: center; gap: 10px; }
.titlebar-left strong { font-size: 12.5px; font-weight: 650; letter-spacing: -0.01em; }
.titlebar-divider { width: 1px; height: 16px; background: var(--border-strong); }
.no-drag { -webkit-app-region: no-drag; }
.runtime-status { display: inline-flex; align-items: center; gap: 6px; color: var(--text-tertiary); font-size: 10.5px; font-weight: 550; }
.runtime-status i { width: 6px; height: 6px; border-radius: 50%; background: var(--success); box-shadow: 0 0 0 3px var(--success-soft); }
.runtime-status.checking i { background: var(--warning); box-shadow: 0 0 0 3px var(--warning-soft); }
.runtime-status.offline i { background: var(--danger); box-shadow: 0 0 0 3px var(--danger-soft); }
.route-viewport { min-height: 0; flex: 1; overflow: auto; background: linear-gradient(180deg, var(--surface-solid), var(--surface-muted)); }
.page-enter-active, .page-leave-active { transition: opacity 150ms ease, transform 180ms ease; }
.page-enter-from { opacity: 0; transform: translateY(4px); }
.page-leave-to { opacity: 0; }
@media (prefers-color-scheme: dark) { .titlebar { background: rgba(32, 33, 38, 0.78); } }
</style>
