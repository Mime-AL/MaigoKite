<script setup lang="ts">
import { onMounted } from 'vue'
import IconSymbol from '@/components/common/IconSymbol.vue'
import { usePhase2Store } from '@/stores/phase2'

const phase2 = usePhase2Store()
onMounted(() => {
  void phase2.loadDataSummary()
})
</script>

<template>
  <main class="page-shell data-page">
    <header class="page-header">
      <div>
        <h1 class="page-title">数据概览</h1>
        <p class="page-subtitle">查看当前工作区保存的数据数量。</p>
      </div>
      <button class="secondary-button" type="button" :disabled="phase2.dataLoading" @click="phase2.loadDataSummary">
        <IconSymbol name="refresh" :size="15" />{{ phase2.dataLoading ? '刷新中…' : '刷新' }}
      </button>
    </header>

    <p v-if="phase2.dataError" class="error-banner" role="alert">{{ phase2.dataError }}</p>
    <section v-if="phase2.dataSummary" class="summary-grid">
      <article class="glass-card">
        <span><IconSymbol name="review" :size="20" /></span><strong>{{ phase2.dataSummary.conversation_count }}</strong
        ><small>对话</small>
      </article>
      <article class="glass-card">
        <span><IconSymbol name="compose" :size="20" /></span><strong>{{ phase2.dataSummary.message_count }}</strong
        ><small>消息</small>
      </article>
      <article class="glass-card">
        <span><IconSymbol name="brain" :size="20" /></span><strong>{{ phase2.dataSummary.memory_count }}</strong
        ><small>用户记忆</small>
      </article>
      <article class="glass-card">
        <span><IconSymbol name="activity" :size="20" /></span><strong>{{ phase2.dataSummary.task_count }}</strong
        ><small>任务</small>
      </article>
      <article class="glass-card">
        <span><IconSymbol name="shield" :size="20" /></span><strong>{{ phase2.dataSummary.audit_event_count }}</strong
        ><small>操作记录</small>
      </article>
    </section>
    <div v-else-if="phase2.dataLoading" class="loading-card glass-card">正在统计数据…</div>
  </main>
</template>

<style scoped lang="scss">
.data-page {
  display: flex;
  flex-direction: column;
  gap: 21px;
}
.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 22px;
}
.page-header .secondary-button {
  flex: none;
  gap: 7px;
}
.summary-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
}
.summary-grid article {
  display: grid;
  grid-template-columns: auto 1fr;
  align-items: center;
  gap: 10px;
  padding: 15px;
}
.summary-grid article span {
  display: grid;
  width: 36px;
  height: 36px;
  grid-row: span 2;
  place-items: center;
  border-radius: var(--radius-md);
  color: var(--primary-color);
  background: var(--primary-soft);
}
.summary-grid strong {
  font-size: var(--text-lg);
  line-height: var(--leading-tight);
}
.summary-grid small {
  color: var(--text-tertiary);
  font-size: var(--text-xs);
}
.loading-card {
  display: grid;
  min-height: 110px;
  place-items: center;
  color: var(--text-tertiary);
}
.error-banner {
  margin: 0;
  padding: 11px 13px;
  border-radius: var(--radius-md);
  color: var(--danger);
  background: var(--danger-soft);
}
@media (max-width: 1000px) {
  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
