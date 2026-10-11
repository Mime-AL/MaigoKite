<script setup lang="ts">
import { t } from '@/i18n'
import { computed, onMounted, ref } from 'vue'
import { api, type ToolSetting } from '@/api/client'
import SearchToolSettingsPanel from './SearchToolSettingsPanel.vue'
import InkLoader from '@/components/common/InkLoader.vue'
const tools = ref<ToolSetting[]>([]),
  draft = ref<Record<string, boolean>>({})
const loading = ref(false),
  saving = ref(false),
  error = ref(''),
  message = ref('')
const failedAction = ref<'load' | 'save'>('load')
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
  ask_user_question: ['向你提问', '向你提问，等待回答后继续。'],
  delegate: ['派发子任务', '将子任务交给只读助手处理。'],
  list_subagent_models: ['查看子助手模型', '查看可供子助手使用的模型。'],
}
function apply(items: ToolSetting[]) {
  tools.value = items
  draft.value = Object.fromEntries(items.map((tool) => [tool.name, tool.enabled]))
}
async function load() {
  loading.value = true
  error.value = ''
  failedAction.value = 'load'
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
  failedAction.value = 'save'
  const changes = Object.fromEntries(
    tools.value
      .filter((tool) => draft.value[tool.name] !== tool.enabled)
      .map((tool) => [tool.name, draft.value[tool.name]]),
  )
  try {
    apply((await api.updateToolSettings(changes)).tools)
    message.value = t('已保存')
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
    <section
      class="selection settings-panel"
      data-settings-field="tool-selection"
      :aria-busy="loading || saving"
    >
      <header class="panel-heading">
        <h2>{{ $t('助手可用工具') }}</h2>
        <p>{{ $t('工具仍遵循当前权限。') }}</p>
      </header>
      <div
        v-if="loading"
        class="panel-loading"
      >
        <InkLoader /><InkLoader /><span class="sr-only">{{ $t('正在读取工具…') }}</span>
      </div>
      <p
        v-if="error"
        class="field-error"
        role="alert"
      >
        {{ error
        }}<button
          class="secondary-button"
          :disabled="loading || saving"
          @click="failedAction === 'save' ? save() : load()"
        >
          {{ $t('重试') }}
        </button>
      </p>
      <template v-if="!loading && tools.length">
        <section
          v-for="group in groups"
          :key="group.title"
          class="setting-group"
        >
          <h3>{{ $t(group.title) }}</h3>
          <p
            v-if="!group.tools.length"
            class="panel-copy"
          >
            {{ $t('暂无已连接的工具。') }}
            <RouterLink to="/integrations">
              {{ $t('查看技能与外部连接') }}
            </RouterLink>
          </p>
          <article
            v-for="tool in group.tools"
            :key="tool.name"
            class="tool-entry"
          >
            <label class="tool-row"><span><strong>{{ labels[tool.name] ? $t(labels[tool.name][0]) : tool.name }}</strong><small>{{ labels[tool.name] ? $t(labels[tool.name][1]) : $t('暂无说明') }}</small><small v-if="!tool.configurable">{{ $t('当前不可用') }}</small></span><input
              v-model="draft[tool.name]"
              type="checkbox"
              :disabled="saving || !tool.configurable"
              :aria-label="labels[tool.name] ? $t(labels[tool.name][0]) : tool.name"
            ></label>
            <details
              v-if="tool.description"
              class="model-description"
            >
              <summary>{{ $t('查看模型说明') }}</summary>
              <p>{{ $t('这是提供给模型的说明') }}</p>
              <pre>{{ tool.description }}</pre>
            </details>
          </article>
        </section>
        <footer class="settings-actions">
          <RouterLink to="/integrations">
            {{ $t('查看技能与外部连接') }}
          </RouterLink>
          <div>
            <span
              v-if="message && !dirty"
              class="field-saved"
              role="status"
            >{{ message }}</span><button
              class="primary-button"
              :disabled="saving || !dirty"
              :aria-busy="saving || undefined"
              @click="save"
            >
              {{ saving ? $t('正在保存…') : $t('保存工具设置') }}
            </button>
          </div>
        </footer>
      </template>
      <p
        v-else-if="!loading && !error"
        class="panel-empty"
      >
        {{ $t('没有可用工具，连接外部服务后可在这里管理。') }}
        <RouterLink to="/integrations">
          {{ $t('添加 MCP') }}
        </RouterLink>
      </p>
    </section>
    <SearchToolSettingsPanel />
  </div>
</template>
<style scoped lang="scss">
.tools-panels {
  display: grid;
  gap: var(--space-8);
}
.panel-heading {
  align-items: baseline;
  flex-wrap: wrap;
}
.panel-heading p {
  font-size: var(--text-sm);
  color: var(--ink-2);
  margin: 0;
}
.tool-entry {
  padding: var(--space-4) 0;
  border-bottom: var(--hairline) solid var(--rule);
}
.tool-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-5);
}
.tool-row span {
  display: grid;
  gap: var(--space-2);
  min-width: 0;
}
.tool-row strong {
  font-size: var(--text-sm);
}
.tool-row small,
.model-description {
  color: var(--ink-2);
  font-size: var(--text-xs);
}
.tool-row input {
  width: var(--size-18);
  height: var(--size-18);
  accent-color: var(--accent);
}
.model-description {
  margin-top: var(--space-3);
}
.model-description summary {
  cursor: pointer;
}
.model-description pre {
  font-family: var(--font-mono);
  padding: var(--space-4);
  background: var(--paper-2);
  border: var(--hairline) solid var(--rule);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  max-height: var(--detail-max-height);
  overflow: auto;
}
.settings-actions,
.settings-actions > div {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  font-size: var(--text-sm);
}
.panel-loading {
  display: grid;
  gap: var(--space-5);
  padding-block: var(--space-7);
}
.panel-empty {
  color: var(--ink-2);
  padding-block: var(--space-6);
  font-size: var(--text-sm);
}
</style>
