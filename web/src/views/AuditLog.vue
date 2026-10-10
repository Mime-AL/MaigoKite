<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api, type AuditEvent } from '@/api/client'
import IconSymbol from '@/components/common/IconSymbol.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'

const events = ref<AuditEvent[]>([])
const error = ref('')
const loading = ref(true)

onMounted(async () => {
  try {
    events.value = await api.listAuditEvents()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : String(reason)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <main class="page-shell audit-page">
    <header>
      <h1 class="page-title">{{ $t('审计日志') }}</h1>
    </header>
    <section class="audit-card glass-card">
      <div class="audit-toolbar">
        <span><IconSymbol name="shield" :size="17" />{{ $t('最近事件') }}</span
        ><span class="event-count">{{ $t('{0} 项', [events.length]) }}</span>
      </div>
      <LoadingSpinner v-if="loading" :message="$t('正在读取审计事件')" />
      <div v-else-if="error" class="state error">
        <IconSymbol name="alert" :size="20" /><strong>{{ $t('无法读取审计日志') }}</strong>
        <p>{{ error }}</p>
      </div>
      <div v-else-if="events.length" class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>{{ $t('时间') }}</th>
              <th>{{ $t('动作') }}</th>
              <th>{{ $t('资源') }}</th>
              <th>{{ $t('结果') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="event in events" :key="event.id">
              <td>{{ new Date(event.created_at).toLocaleString($i18n.locale) }}</td>
              <td>
                <code>{{ event.action }}</code>
              </td>
              <td>{{ event.resource }}</td>
              <td>
                <span class="result" :class="event.result">{{ event.result }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="state">
        <span class="state-icon"><IconSymbol name="shield" :size="24" /></span><strong>{{ $t('还没有审计事件') }}</strong>
      </div>
    </section>
  </main>
</template>

<style scoped lang="scss">
.audit-page {
  display: flex;
  flex-direction: column;
  gap: 30px;
}
.audit-card {
  min-height: 340px;
  overflow: hidden;
}
.audit-toolbar {
  display: flex;
  height: 58px;
  align-items: center;
  justify-content: space-between;
  padding: 0 19px;
  border-bottom: 1px solid var(--border-color);
}
.audit-toolbar > span:first-child {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
}
.event-count {
  color: var(--text-secondary);
  font-size: var(--text-xs);
}
.table-wrap {
  overflow-x: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
}
th,
td {
  padding: 13px 18px;
  border-bottom: 1px solid var(--border-color);
  text-align: left;
}
th {
  color: var(--text-secondary);
  background: var(--surface-muted);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
td {
  color: var(--text-secondary);
  font-size: var(--text-xs);
}
code {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}
.result {
  padding: 4px 7px;
  border-radius: var(--radius-sm);
  background: var(--surface-strong);
  font-size: var(--text-xs);
}
.result.success,
.result.allowed {
  color: var(--success);
  background: var(--success-soft);
}
.result.failed,
.result.denied {
  color: var(--danger);
  background: var(--danger-soft);
}
.state {
  display: flex;
  min-height: 280px;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  padding: 30px;
  text-align: center;
}
.state-icon {
  display: grid;
  width: 52px;
  height: 52px;
  margin-bottom: 14px;
  place-items: center;
  border-radius: var(--radius-lg);
  color: var(--success);
  background: var(--success-soft);
}
.state strong {
  font-size: var(--text-xs);
}
.state p {
  max-width: 420px;
  margin: 6px 0 0;
  color: var(--text-secondary);
  font-size: var(--text-xs);
}
.state.error {
  color: var(--danger);
}
.state.error p {
  color: var(--text-secondary);
}
</style>
