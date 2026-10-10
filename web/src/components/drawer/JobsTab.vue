<script setup lang="ts">
import { t } from '@/i18n'
import { computed, onUnmounted, ref, watch } from 'vue'
import { api, type AgentTask } from '@/api/client'
import { useRunStore } from '@/stores/run'
import { useSessionStore } from '@/stores/session'
const run = useRunStore(),
  session = useSessionStore()
const tasks = ref<AgentTask[]>([]),
  error = ref(''),
  loading = ref(false)
const jobs = computed(() => (run.turns[session.activeSessionId || ''] || []).flatMap((t) => t.jobs))
const labels: Record<AgentTask['status'], string> = {
  created: '待开始',
  queued: '排队中',
  running: '正在做',
  waiting_approval: '等你批准',
  retry_wait: '等待重试',
  succeeded: '已完成',
  failed: '失败',
  cancelled: '已停止',
  timed_out: '超时',
  interrupted: '已中断',
}
let generation = 0
let disposed = false
async function load() {
  const current = ++generation,
    id = session.activeSessionId
  if (!id) {
    tasks.value = []
    loading.value = false
    error.value = ''
    return
  }
  loading.value = true
  try {
    const items = await api.listTasks(id)
    if (current === generation) {
      tasks.value = items
      error.value = ''
    }
  } catch (reason) {
    if (current === generation) error.value = String(reason)
  } finally {
    if (current === generation) loading.value = false
  }
}
async function stop(task: AgentTask) {
  const stopped = await session.cancelTask(task.id, task.conversation_id)
  if (disposed || task.conversation_id !== session.activeSessionId) return
  if (stopped) {
    await load()
  } else error.value = session.error || t("未能确认停止，请稍后重试。")
}
onUnmounted(() => {
  disposed = true
  generation++
})
watch(
  () => session.activeSessionId,
  () => {
    tasks.value = []
    error.value = ''
    void load()
  },
  { immediate: true },
)
watch(
  () => (run.turns[session.activeSessionId || ''] || []).map((t) => t.id + t.status).join('|'),
  () => {
    void load()
  },
)
</script>
<template>
  <section class="jobs-tab">
    <header>{{ $t('会话任务') }}<button class="icon-button" :title="$t('刷新任务')" @click="load">↻</button></header>
    <p v-if="error" class="empty-copy" role="alert">{{ error }}</p>
    <p v-else-if="loading && !tasks.length" class="empty-copy">{{ $t('正在读取任务…') }}</p>
    <p v-else-if="!tasks.length" class="empty-copy">{{ $t('还没有会话任务。') }}</p>
    <article v-for="task in tasks" :key="task.id">
      <strong>{{ task.input_text || $t('当前任务') }}</strong>
      <div>
        <span>{{ $t(labels[task.status]) }}</span
        ><button
          v-if="
            ['created', 'queued', 'running', 'waiting_approval', 'retry_wait'].includes(task.status)
          "
          class="secondary-button"
          :disabled="session.stoppingTaskIds.includes(task.id)"
          @click="stop(task)"
        >
          {{ session.stoppingTaskIds.includes(task.id) ? $t('请求停止中…') : $t('停止') }}
        </button>
      </div>
      <p v-if="task.last_error" class="empty-copy">{{ task.last_error }}</p>
    </article>
    <article v-for="job in jobs" :key="job.id">
      <header>{{ job.id }} · {{ job.status }}</header>
      <pre>{{ job.logTail.split('\n').slice(-200).join('\n') }}</pre>
    </article>
  </section>
</template>
<style scoped lang="scss">
.jobs-tab {
  padding: 20px;
  overflow: auto;
}
header,
article > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: var(--text-sm);
  color: var(--ink-2);
}
article {
  padding: 16px 0;
  border-bottom: 1px solid var(--rule);
}
strong {
  display: block;
  font-weight: var(--weight-medium);
  font-size: var(--text-sm);
  margin-bottom: 12px;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
article span {
  font-size: var(--text-xs);
  color: var(--ink-2);
}
pre {
  overflow: auto;
  max-height: 300px;
  background: var(--paper-2);
  font: var(--text-sm)/var(--leading-small) var(--font-mono);
  padding: 12px;
}
</style>
