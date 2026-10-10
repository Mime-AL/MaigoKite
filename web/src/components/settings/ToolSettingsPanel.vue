<script setup lang="ts">
import { t } from '@/i18n'
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
  glob: ['查找文件', '按文件名或路径查找文件。'],
  grep: ['搜索内容', '搜索文件中的文字。'],
  exec_command: ['执行命令', '在工作区中运行命令。'],
  web_search: ['联网搜索', '查找网上的信息。'],
  web_fetch: ['读取网页', '提取网页正文。'],
  browser: ['操作浏览器', '打开网页、填写表单、点击和截图。'],
  skill: ['读取技能', '按需加载本地技能的工作指引。'],
  todo_write: ['工作区待办', '记录和更新待办事项。'],
  sleep: ['短暂等待', '等待片刻后继续当前任务。'],
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
    message.value = t("已保存")
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
        <h2>{{ $t('助手可用工具') }}</h2>
        <p>{{ $t('工具仍遵循当前权限。') }}</p>
      </header>
      <p v-if="loading" class="notice">{{ $t('正在读取工具…') }}</p>
      <template v-else>
        <section v-for="group in groups" :key="group.title" class="tool-group">
          <h3>{{ $t(group.title) }}</h3>
          <p v-if="!group.tools.length" class="muted">{{ $t('暂无已连接的工具。') }}</p>
          <label v-for="tool in group.tools" :key="tool.name" class="tool-row">
            <span
              ><strong>{{ labels[tool.name] ? $t(labels[tool.name][0]) : tool.name }}</strong>
              <small>{{ labels[tool.name] ? $t(labels[tool.name][1]) : tool.description }}</small>
              <small v-if="!tool.configurable">{{ $t('当前不可用') }}</small>
            </span>
            <input
              v-model="draft[tool.name]"
              type="checkbox"
              :disabled="saving || !tool.configurable"
              :aria-label="labels[tool.name] ? $t(labels[tool.name][0]) : tool.name"
            />
          </label>
        </section>
        <footer>
          <RouterLink to="/integrations">{{ $t('查看技能与外部连接') }}</RouterLink>
          <button type="button" class="primary-button" :disabled="saving || !dirty" :aria-busy="saving || undefined" @click="save">
            {{ saving ? $t('正在保存…') : $t('保存工具设置') }}
          </button>
        </footer>
      </template>
      <p v-if="error" class="notice error" role="alert">
        {{ error }} <button type="button" :disabled="loading || saving" @click="load">{{ $t('重试') }}</button>
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
