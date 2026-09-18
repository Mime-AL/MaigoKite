<script setup lang="ts">
import { computed, onMounted } from 'vue'
import IconSymbol from '@/components/common/IconSymbol.vue'
import { useSettingsStore } from '@/stores/settings'

const settings = useSettingsStore()
const status = computed(() => settings.runtimeStatus)

const sourceLabel = computed(() =>
  status.value?.workspaceSource === 'environment' ? '环境变量' : '配置文件',
)

onMounted(() => {
  void settings.loadRuntimeStatus()
})
</script>

<template>
  <section class="runtime-settings glass-card">
    <header class="runtime-heading">
      <span class="section-icon"><IconSymbol name="folder" :size="21" /></span>
      <div>
        <h2>工作区与运行状态</h2>
        <p>这里展示当前进程实际采用的配置，不在前端复制部署参数。</p>
      </div>
      <button class="refresh-button" type="button" :disabled="settings.runtimeLoading" @click="settings.loadRuntimeStatus">
        <IconSymbol name="refresh" :size="14" />{{ settings.runtimeLoading ? '刷新中…' : '刷新' }}
      </button>
    </header>

    <div v-if="settings.runtimeError" class="runtime-error" role="alert">
      <IconSymbol name="alert" :size="15" />{{ settings.runtimeError }}
    </div>
    <div v-else-if="!status" class="runtime-loading" role="status">正在读取运行状态…</div>
    <template v-else>
      <div class="workspace-block">
        <span class="block-label">Workspace 根目录</span>
        <code>{{ status.workspaceRoot }}</code>
        <div class="workspace-meta">
          <span>{{ status.workspaceId }}</span>
          <span>{{ sourceLabel }}</span>
          <span>{{ status.environment || '未标注环境' }}</span>
        </div>
      </div>

      <div class="service-grid">
        <article>
          <span class="service-icon"><IconSymbol name="globe" :size="17" /></span>
          <div><strong>Gateway</strong><small>{{ status.gateway.version || '版本未知' }}</small></div>
          <span class="service-state ready"><i />运行中</span>
        </article>
        <article>
          <span class="service-icon core"><IconSymbol name="brain" :size="17" /></span>
          <div><strong>Agent Core</strong><small>{{ status.agentCore.version || '版本未知' }}</small></div>
          <span class="service-state" :class="status.agentCore.status === 'serving' ? 'ready' : 'unavailable'">
            <i />{{ status.agentCore.status === 'serving' ? '运行中' : '不可用' }}
          </span>
        </article>
      </div>

      <div class="policy-grid">
        <article>
          <h3><IconSymbol name="bolt" :size="15" />即时生效</h3>
          <ul><li v-for="item in status.restart.hotApplied" :key="item">{{ item }}</li></ul>
        </article>
        <article>
          <h3><IconSymbol name="refresh" :size="15" />修改后需重启</h3>
          <ul><li v-for="item in status.restart.requiredFor" :key="item">{{ item }}</li></ul>
        </article>
      </div>
      <footer :class="{ pending: status.restart.pending }">
        <IconSymbol :name="status.restart.pending ? 'alert' : 'info'" :size="14" />
        {{ status.restart.note }}
      </footer>
    </template>
  </section>
</template>

<style scoped lang="scss">
.runtime-settings { overflow: hidden; }
.runtime-heading { display: flex; align-items: center; gap: 13px; padding: 20px 22px; border-bottom: 1px solid var(--border-color); }
.runtime-heading > div { min-width: 0; flex: 1; }
.runtime-heading h2 { margin: 0; font-size: 16px; letter-spacing: -0.025em; }
.runtime-heading p { margin: 4px 0 0; color: var(--text-secondary); font-size: 10.5px; }
.section-icon, .service-icon { display: grid; flex: none; place-items: center; color: var(--primary-color); background: var(--primary-soft); }
.section-icon { width: 43px; height: 43px; border-radius: 13px; }
.refresh-button { display: inline-flex; min-height: 34px; align-items: center; gap: 7px; padding: 0 12px; border: 1px solid var(--border-color); border-radius: 10px; color: var(--text-secondary); background: var(--surface-muted); cursor: pointer; font-size: 10px; }
.refresh-button:disabled { cursor: default; opacity: .55; }
.runtime-error, .runtime-loading { display: flex; min-height: 120px; align-items: center; justify-content: center; gap: 8px; padding: 24px; color: var(--text-secondary); font-size: 11px; }
.runtime-error { color: var(--danger); }
.workspace-block { padding: 18px 22px; border-bottom: 1px solid var(--border-color); }
.block-label { display: block; margin-bottom: 8px; color: var(--text-tertiary); font-size: 9px; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; }
.workspace-block code { display: block; overflow: hidden; padding: 11px 12px; border: 1px solid var(--border-color); border-radius: 10px; color: var(--text-primary); background: var(--surface-muted); font-family: var(--font-mono); font-size: 10.5px; text-overflow: ellipsis; white-space: nowrap; }
.workspace-meta { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 9px; }
.workspace-meta span { padding: 4px 7px; border-radius: 7px; color: var(--text-tertiary); background: var(--surface-strong); font-size: 8.5px; }
.service-grid, .policy-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; padding: 16px 22px; border-bottom: 1px solid var(--border-color); }
.service-grid article { display: flex; min-width: 0; align-items: center; gap: 10px; padding: 13px; border: 1px solid var(--border-color); border-radius: 13px; background: var(--surface-muted); }
.service-icon { width: 34px; height: 34px; border-radius: 10px; }
.service-icon.core { color: #8a63d2; background: rgba(138, 99, 210, .13); }
.service-grid article > div { min-width: 0; display: flex; flex: 1; flex-direction: column; }
.service-grid strong { font-size: 11px; }
.service-grid small { margin-top: 3px; color: var(--text-tertiary); font-family: var(--font-mono); font-size: 8.5px; }
.service-state { display: inline-flex; align-items: center; gap: 5px; color: var(--text-tertiary); font-size: 9px; font-weight: 650; }
.service-state i { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.service-state.ready { color: var(--success); }
.service-state.unavailable { color: var(--danger); }
.policy-grid { border-bottom: 0; }
.policy-grid article { padding: 14px 15px; border-radius: 13px; background: var(--surface-muted); }
.policy-grid h3 { display: flex; align-items: center; gap: 7px; margin: 0; font-size: 10.5px; }
.policy-grid ul { display: grid; gap: 6px; margin: 10px 0 0; padding-left: 17px; color: var(--text-secondary); font-size: 9.5px; }
.runtime-settings footer { display: flex; align-items: flex-start; gap: 7px; padding: 13px 22px; color: var(--text-tertiary); background: var(--surface-muted); font-size: 9.5px; line-height: 1.45; }
.runtime-settings footer.pending { color: var(--warning); background: var(--warning-soft); }
@media (max-width: 760px) {
  .service-grid, .policy-grid { grid-template-columns: 1fr; }
  .runtime-heading { align-items: flex-start; flex-wrap: wrap; }
  .refresh-button { margin-left: 56px; }
}
</style>
