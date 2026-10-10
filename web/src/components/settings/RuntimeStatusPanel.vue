<script setup lang="ts">
import { computed, watch } from 'vue'
import IconSymbol from '@/components/common/IconSymbol.vue'
import { useSettingsStore } from '@/stores/settings'
import { useWorkspaceStore } from '@/stores/workspace'

const settings = useSettingsStore()
const workspace = useWorkspaceStore()
const status = computed(() => settings.runtimeStatus)

watch(() => workspace.selectedId, (id) => void settings.loadRuntimeStatus(id), { immediate: true })
</script>

<template>
  <section class="runtime-settings glass-card">
    <header class="runtime-heading">
      <span class="section-icon"><IconSymbol name="folder" :size="21" /></span>
      <div>
        <h2>{{ $t('工作区与运行状态') }}</h2>
      </div>
      <button
        class="refresh-button"
        type="button"
        :disabled="settings.runtimeLoading"
        @click="settings.loadRuntimeStatus(workspace.selectedId)"
      >
        <IconSymbol name="refresh" :size="14" />{{ settings.runtimeLoading ? $t('刷新中…') : $t('刷新') }}
      </button>
    </header>

    <div v-if="settings.runtimeError" class="runtime-error" role="alert">
      <IconSymbol name="alert" :size="15" />{{ settings.runtimeError }}
    </div>
    <div v-else-if="!status" class="runtime-loading" role="status">{{ $t('正在读取运行状态…') }}</div>
    <template v-else>
      <div class="workspace-block">
        <span class="block-label">{{ $t('工作区位置') }}</span>
        <code>{{ status.workspaceRoot }}</code>
      </div>

      <div class="service-grid">
        <article>
          <span class="service-icon"><IconSymbol name="globe" :size="17" /></span>
          <div>
            <strong>{{ $t('应用服务') }}</strong><small>{{ status.gateway.version || $t('版本未知') }}</small>
          </div>
          <span class="service-state ready"><i />{{ $t('运行中') }}</span>
        </article>
        <article>
          <span class="service-icon core"><IconSymbol name="brain" :size="17" /></span>
          <div>
            <strong>{{ $t('智能服务') }}</strong><small>{{ status.agentCore.version || $t('版本未知') }}</small>
          </div>
          <span class="service-state" :class="status.agentCore.status === 'serving' ? 'ready' : 'unavailable'">
            <i />{{ status.agentCore.status === 'serving' ? $t('运行中') : $t('不可用') }}
          </span>
        </article>
      </div>

      <footer v-if="status.restart.pending" class="pending">
        <IconSymbol name="alert" :size="14" />{{ $t('重启应用后生效。') }}</footer>
    </template>
  </section>
</template>

<style scoped lang="scss">
@use '@/styles/runtime-status';
</style>
