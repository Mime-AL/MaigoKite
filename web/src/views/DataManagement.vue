<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { usePhase2Store } from '@/stores/phase2'
import InkLoader from '@/components/common/InkLoader.vue'
import RailGlyph from '@/components/rail/RailGlyph.vue'
const phase2 = usePhase2Store()
const entries = computed(() => {
  const data = phase2.dataSummary
  return data
    ? [
        { label: '对话', count: data.conversation_count },
        { label: '消息', count: data.message_count },
        { label: '用户记忆', count: data.memory_count },
        { label: '运行记录', count: data.task_count },
        { label: '操作记录', count: data.audit_event_count },
      ]
    : []
})
const empty = computed(() => entries.value.every((entry) => entry.count === 0))
onMounted(() => {
  void phase2.loadDataSummary()
})
</script>
<template>
  <main class="page-shell data-page">
    <header class="page-heading">
      <h1 class="page-title">
        {{ $t('数据概览') }}
      </h1>
      <button
        class="secondary-button"
        :disabled="phase2.dataLoading"
        :aria-busy="phase2.dataLoading || undefined"
        @click="phase2.loadDataSummary"
      >
        {{ $t('刷新') }}
      </button>
    </header>
    <section
      v-if="phase2.dataError"
      class="page-state"
      role="alert"
    >
      <strong>{{ $t('无法读取数据概览') }}</strong>
      <p>{{ phase2.dataError }}</p>
      <button
        class="secondary-button"
        :disabled="phase2.dataLoading"
        @click="phase2.loadDataSummary"
      >
        {{ $t('重试') }}
      </button>
    </section>
    <div
      v-else-if="phase2.dataLoading && !phase2.dataSummary"
      class="page-loading"
    >
      <InkLoader /><InkLoader /><InkLoader /><span class="sr-only">{{ $t('正在统计数据…') }}</span>
    </div>
    <template v-else-if="phase2.dataSummary">
      <dl class="data-ledger">
        <div
          v-for="entry in entries"
          :key="entry.label"
        >
          <dt>{{ $t(entry.label) }}</dt>
          <dd>{{ entry.count.toLocaleString($i18n.locale) }}</dd>
        </div>
      </dl>
      <p class="data-storage">
        {{ $t('本地存储') }}
      </p>
      <section
        v-if="empty"
        class="page-state"
      >
        <RailGlyph kind="memory" /><strong>{{ $t('这里还没有记录') }}</strong>
        <p>{{ $t('开始对话后，消息与操作记录会显示在这里。') }}</p>
        <RouterLink to="/chat">
          {{ $t('新建对话') }}
        </RouterLink>
      </section>
    </template>
    <section
      v-else
      class="page-state"
    >
      <p>{{ $t('尚未读取数据概览。') }}</p>
      <button
        class="secondary-button"
        @click="phase2.loadDataSummary"
      >
        {{ $t('刷新') }}
      </button>
    </section>
  </main>
</template>
<style scoped lang="scss">
@use '@/styles/data';
</style>
