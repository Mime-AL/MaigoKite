<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api, type ToolSetting } from '@/api/client'
import SearchToolSettingsPanel from './SearchToolSettingsPanel.vue'

const tools = ref<ToolSetting[]>([])
const draft = ref<Record<string, boolean>>({})
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const message = ref('')
const dirty = computed(() => tools.value.some((tool) => draft.value[tool.name] !== tool.enabled))
const groups = computed(() => [
  { title: '内置工具', tools: tools.value.filter((tool) => tool.source === 'builtin') },
  { title: '外部工具', tools: tools.value.filter((tool) => tool.source === 'mcp') },
])
const labels: Record<string, [string, string]> = {
  file_read: ['读取文件', '读取工作区中的文本文件。'],
  file_write: ['写入文件', '创建或覆盖文本文件。'],
  file_edit: ['编辑文件', '精确替换文件中的指定内容。'],
  glob: ['查找文件', '按文件名或路径匹配，需要 ripgrep。'],
  grep: ['搜索内容', '搜索文件内的文字，需要 ripgrep。'],
  exec_command: ['执行命令', '运行工作区命令，不自动解释管道或重定向。'],
  web_search: ['联网搜索', '搜索网页；服务凭证在下方配置。'],
  web_fetch: ['读取网页', '读取网页文本，不执行网页脚本。'],
  browser: ['操作浏览器', '打开网页、填写、点击和截图，需要可用的 Chromium。'],
  skill: ['读取技能', '按需加载本地技能的工作指引。'],
  todo_write: ['工作区待办', '管理待办事项，不负责自动执行或调度。'],
  sleep: ['短暂等待', '在任务内等待，不用于定时任务。'],
}

function apply(items: ToolSetting[]) {
  tools.value = items
  draft.value = Object.fromEntries(items.map((tool) => [tool.name, tool.enabled]))
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    apply((await api.getToolSettings()).tools)
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : String(reason)
  } finally {
    loading.value = false
  }
}

async function save() {
  if (saving.value || !dirty.value) return
  saving.value = true
  error.value = ''
  message.value = ''
  const changes = Object.fromEntries(
    tools.value
      .filter((tool) => draft.value[tool.name] !== tool.enabled)
      .map((tool) => [tool.name, draft.value[tool.name]]),
  )
  try {
    apply((await api.updateToolSettings(changes)).tools)
    message.value = '已保存。新任务会使用所选工具，权限审批规则不变。'
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : String(reason)
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="tools-panels">
    <section class="selection glass-card" :aria-busy="loading || saving">
      <header>
        <h2>助手可用工具</h2>
        <p>选择助手可以调用的能力。启用工具不会跳过权限确认。</p>
      </header>
      <p v-if="loading" class="notice">正在读取工具…</p>
      <template v-else>
        <section v-for="group in groups" :key="group.title" class="tool-group">
          <h3>{{ group.title }}</h3>
          <p v-if="!group.tools.length" class="muted">暂无已连接的工具。</p>
          <label v-for="tool in group.tools" :key="tool.name" class="tool-row">
            <span
              ><strong>{{ labels[tool.name]?.[0] || tool.name }}</strong>
              <small>{{ labels[tool.name]?.[1] || tool.description }}</small>
              <small v-if="!tool.configurable">已被启动配置停用</small>
            </span>
            <input
              v-model="draft[tool.name]"
              type="checkbox"
              :disabled="saving || !tool.configurable"
              :aria-label="labels[tool.name]?.[0] || tool.name"
            />
          </label>
        </section>
        <footer>
          <RouterLink to="/integrations">查看技能与外部连接</RouterLink>
          <button type="button" class="primary-button" :disabled="saving || !dirty" :aria-busy="saving || undefined" @click="save">
            {{ saving ? '正在保存…' : '保存工具设置' }}
          </button>
        </footer>
      </template>
      <p v-if="error" class="notice error" role="alert">
        {{ error }} <button type="button" :disabled="loading || saving" @click="load">重试</button>
      </p>
      <p v-else-if="message && !dirty" class="notice" role="status">{{ message }}</p>
    </section>
    <SearchToolSettingsPanel />
  </div>
</template>

<style scoped lang="scss">
.tools-panels {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.selection {
  overflow: hidden;
}
.selection header {
  padding: 20px 22px;
  border-bottom: 1px solid var(--border-color);
}
h2 {
  margin: 0;
  font-size: var(--text-md);
}
header p,
small,
.muted {
  color: var(--text-secondary);
  font-size: var(--text-xs);
  line-height: var(--leading-normal);
}
header p {
  margin: 6px 0 0;
}
.tool-group {
  padding: 0 22px;
}
h3 {
  margin: 20px 0 6px;
  font-size: var(--text-sm);
}
.tool-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 13px 0;
  border-bottom: 1px solid var(--border-color);
}
.tool-row span {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  overflow-wrap: anywhere;
}
strong {
  font-size: var(--text-sm);
}
input {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  accent-color: var(--primary-color);
  cursor: pointer;
}
input:disabled {
  cursor: not-allowed;
}
footer {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  align-items: center;
  justify-content: space-between;
  padding: 18px 22px;
}
footer a {
  font-size: var(--text-xs);
  color: var(--primary-color);
}
footer button {
  padding: 9px 14px;
  font-size: var(--text-xs);
}
.notice {
  margin: 12px 22px;
  font-size: var(--text-xs);
  color: var(--text-secondary);
}
.error {
  color: var(--danger);
}
</style>
