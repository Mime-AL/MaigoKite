<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, type AuditEvent } from '@/api/client'
import IconSymbol from '@/components/common/IconSymbol.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'

const events = ref<AuditEvent[]>([])
const error = ref('')
const loading = ref(true)

onMounted(async () => {
  try { events.value = await api.listAuditEvents() }
  catch (reason) { error.value = reason instanceof Error ? reason.message : String(reason) }
  finally { loading.value = false }
})
</script>

<template>
  <main class="page-shell audit-page">
    <header><p class="page-eyebrow">Security</p><h1 class="page-title">审计日志</h1><p class="page-subtitle">按时间追踪权限判断与敏感操作，所有结果都可回溯。</p></header>
    <section class="audit-card glass-card">
      <div class="audit-toolbar"><span><IconSymbol name="shield" :size="17" />最近事件</span><span class="event-count">{{ events.length }} 项</span></div>
      <LoadingSpinner v-if="loading" message="正在读取审计事件" />
      <div v-else-if="error" class="state error"><IconSymbol name="alert" :size="20" /><strong>无法读取审计日志</strong><p>{{ error }}</p></div>
      <div v-else-if="events.length" class="table-wrap"><table><thead><tr><th>时间</th><th>动作</th><th>资源</th><th>结果</th></tr></thead><tbody><tr v-for="event in events" :key="event.id"><td>{{ new Date(event.created_at).toLocaleString('zh-CN') }}</td><td><code>{{ event.action }}</code></td><td>{{ event.resource }}</td><td><span class="result" :class="event.result">{{ event.result }}</span></td></tr></tbody></table></div>
      <div v-else class="state"><span class="state-icon"><IconSymbol name="shield" :size="24" /></span><strong>还没有审计事件</strong><p>需要记录的安全操作会自动出现在这里。</p></div>
    </section>
  </main>
</template>

<style scoped lang="scss">
.audit-page { display: flex; flex-direction: column; gap: 30px; }.audit-card { min-height: 340px; overflow: hidden; }.audit-toolbar { display: flex; height: 58px; align-items: center; justify-content: space-between; padding: 0 19px; border-bottom: 1px solid var(--border-color); }.audit-toolbar > span:first-child { display: flex; align-items: center; gap: 8px; font-size: 11px; font-weight: 650; }.event-count { color: var(--text-tertiary); font-size: 9px; }.table-wrap { overflow-x: auto; }table { width: 100%; border-collapse: collapse; }th,td { padding: 13px 18px; border-bottom: 1px solid var(--border-color); text-align: left; }th { color: var(--text-tertiary); background: var(--surface-muted); font-size: 9px; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; }td { color: var(--text-secondary); font-size: 10.5px; }code { font-family: var(--font-mono); font-size: 9.5px; }.result { padding: 4px 7px; border-radius: 7px; background: var(--surface-strong); font-size: 9px; }.result.success, .result.allowed { color: var(--success); background: var(--success-soft); }.result.failed, .result.denied { color: var(--danger); background: var(--danger-soft); }.state { display: flex; min-height: 280px; align-items: center; justify-content: center; flex-direction: column; padding: 30px; text-align: center; }.state-icon { display: grid; width: 52px; height: 52px; margin-bottom: 14px; place-items: center; border-radius: 16px; color: var(--success); background: var(--success-soft); }.state strong { font-size: 12px; }.state p { max-width: 420px; margin: 6px 0 0; color: var(--text-tertiary); font-size: 10.5px; }.state.error { color: var(--danger); }.state.error p { color: var(--text-secondary); }
</style>
