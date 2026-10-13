<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { api, type AuditEvent } from '@/api/client'
import InkLoader from '@/components/common/InkLoader.vue'
import RailGlyph from '@/components/rail/RailGlyph.vue'
import InkSelect from '@/components/common/InkSelect.vue'
const events = ref<AuditEvent[]>([]),
  error = ref(''),
  loading = ref(true)
const query = ref(''),
  result = ref(''),
  limit = ref(60)
const results = computed(() => [...new Set(events.value.map((event) => event.result))])
const filtered = computed(() => {
  const text = query.value.trim().toLocaleLowerCase()
  return events.value.filter(
    (event) =>
      (!result.value || event.result === result.value) &&
      (!text ||
        [event.action, event.resource, actor(event)].join(' ').toLocaleLowerCase().includes(text)),
  )
})
const visible = computed(() => filtered.value.slice(0, limit.value))
function clearFilters() {
  query.value = ''
  result.value = ''
}
watch([query, result], () => {
  limit.value = 60
})
function actor(event: AuditEvent) {
  try {
    const detail: unknown = JSON.parse(event.details_json)
    if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
      const value =
        (detail as Record<string, unknown>).actor ??
        (detail as Record<string, unknown>).principal_id
      if (typeof value === 'string' && value.trim()) return value
    }
  } catch {
    /* Unstructured audit payloads do not establish an actor. */
  }
  return ''
}
async function load() {
  loading.value = true
  error.value = ''
  try {
    events.value = await api.listAuditEvents()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : String(reason)
  } finally {
    loading.value = false
  }
}
onMounted(() => {
  void load()
})
</script>
<template>
  <main class="page-shell audit-page">
    <header class="page-heading">
      <h1 class="page-title">
        {{ $t('审计日志') }}
      </h1>
      <button
        class="secondary-button"
        :disabled="loading"
        @click="load"
      >
        {{ $t('刷新') }}
      </button>
    </header>
    <div class="audit-filters">
      <input
        v-model="query"
        type="search"
        :placeholder="$t('搜索动作、目标或操作者')"
        :aria-label="$t('搜索审计记录')"
      ><InkSelect
        v-model="result"
        :options="[{ value: '', label: $t('全部结果') }, ...results.map(item => ({ value: item, label: $t(item) }))]"
        :aria-label="$t('筛选结果')"
      /><span>{{ $t('{0} 项', [filtered.length]) }}</span>
    </div>
    <div
      v-if="loading"
      class="page-loading"
    >
      <InkLoader /><InkLoader /><InkLoader /><span class="sr-only">{{
        $t('正在读取审计事件')
      }}</span>
    </div>
    <section
      v-else-if="error"
      class="page-state"
      role="alert"
    >
      <strong>{{ $t('无法读取审计日志') }}</strong>
      <p>{{ error }}</p>
      <button
        class="secondary-button"
        @click="load"
      >
        {{ $t('重试') }}
      </button>
    </section>
    <ol
      v-else-if="visible.length"
      class="audit-timeline"
    >
      <li
        v-for="event in visible"
        :key="event.id"
      >
        <RailGlyph
          :kind="event.result === 'denied' || event.result === 'failed' ? 'failed' : 'read'"
        />
        <div>
          <header>
            <time :datetime="event.created_at">{{
              new Date(event.created_at).toLocaleString($i18n.locale)
            }}</time><span
              class="audit-verdict"
              :class="{ denied: event.result === 'denied' || event.result === 'failed' }"
            >{{ $t(event.result) }}</span>
          </header>
          <strong><code>{{ event.action }}</code></strong>
          <p>{{ event.resource }}</p>
          <small>{{ $t('操作者') }} · {{ actor(event) || $t('未记录') }}</small>
        </div>
      </li>
    </ol>
    <section
      v-else
      class="page-state"
    >
      <RailGlyph kind="read" /><strong>{{
        events.length ? $t('没有匹配的记录') : $t('还没有审计事件')
      }}</strong>
      <p>{{ $t('工具执行和权限决定会留下操作记录。') }}</p>
      <button
        v-if="events.length"
        class="secondary-button"
        @click="clearFilters"
      >
        {{ $t('清除筛选') }}
      </button><RouterLink
        v-else
        to="/chat"
      >
        {{ $t('新建对话') }}
      </RouterLink>
    </section>
    <button
      v-if="visible.length < filtered.length"
      class="secondary-button"
      @click="limit += 60"
    >
      {{ $t('显示更多记录') }}
    </button>
  </main>
</template>
<style scoped lang="scss">
@use '@/styles/audit';
</style>
