<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import IconSymbol from '@/components/common/IconSymbol.vue'
import type { DiscoveredChatModel } from '@/api/client'

const props = defineProps<{
  models: DiscoveredChatModel[]
  selectedModel: string
  loading: boolean
  canRefresh: boolean
  message?: string
}>()

const emit = defineEmits<{
  close: []
  refresh: []
  select: [modelId: string]
}>()

const query = ref('')
const pendingModel = ref(props.selectedModel)

watch(
  () => props.selectedModel,
  (value) => {
    pendingModel.value = value
  },
)

const filteredModels = computed(() => {
  const needle = query.value.trim().toLocaleLowerCase()
  if (!needle) return props.models
  return props.models.filter((model) =>
    `${model.id} ${model.name ?? ''}`.toLocaleLowerCase().includes(needle),
  )
})

function describeModel(model: DiscoveredChatModel): string {
  return [
    model.owned_by,
    model.context_window ? `${model.context_window.toLocaleString('en-US')} Token 上下文` : '',
    model.details,
  ]
    .filter(Boolean)
    .join(' · ')
}
</script>

<template>
  <div
    class="catalog-backdrop"
    data-testid="model-catalog"
    @click.self="emit('close')"
    @keydown.esc="emit('close')"
  >
    <section
      class="catalog-dialog"
      role="dialog"
      aria-modal="true"
      aria-labelledby="model-catalog-title"
    >
      <header>
        <div>
          <p>Model catalog</p>
          <h3 id="model-catalog-title">选择模型</h3>
        </div>
        <button type="button" class="icon-button" aria-label="关闭模型目录" @click="emit('close')">
          ×
        </button>
      </header>

      <div class="catalog-tools">
        <label class="search-field">
          <IconSymbol name="search" :size="16" />
          <input
            v-model="query"
            data-testid="catalog-search"
            type="search"
            placeholder="按模型 ID 或名称搜索"
            autofocus
          />
        </label>
        <button
          type="button"
          class="secondary-button refresh-button"
          :disabled="!canRefresh || loading"
          @click="emit('refresh')"
        >
          <IconSymbol name="refresh" :size="14" />
          {{ loading ? '正在获取…' : '重新获取' }}
        </button>
      </div>

      <p v-if="message" class="catalog-message">{{ message }}</p>

      <div class="model-list" role="radiogroup" aria-label="可用模型">
        <button
          v-for="model in filteredModels"
          :key="model.id"
          type="button"
          class="model-option"
          :class="{ selected: pendingModel === model.id }"
          :data-model-id="model.id"
          role="radio"
          :aria-checked="pendingModel === model.id"
          @click="pendingModel = model.id"
        >
          <span class="radio-mark"><i /></span>
          <span class="model-copy">
            <strong>{{ model.name || model.id }}</strong>
            <code v-if="model.name && model.name !== model.id">{{ model.id }}</code>
            <small v-if="describeModel(model)">{{ describeModel(model) }}</small>
          </span>
          <IconSymbol v-if="pendingModel === model.id" name="check" :size="16" />
        </button>

        <div v-if="!filteredModels.length" class="catalog-empty">
          <IconSymbol name="search" :size="22" />
          <strong>{{ models.length ? '没有匹配的模型' : '服务端没有返回模型' }}</strong>
          <small>{{
            models.length
              ? '试试其他关键词，或直接手工填写模型 ID。'
              : '检查连接参数后重新获取，也可以关闭目录后手工输入。'
          }}</small>
        </div>
      </div>

      <footer>
        <span>{{ filteredModels.length }} / {{ models.length }} 个模型</span>
        <div>
          <button type="button" class="secondary-button" @click="emit('close')">取消</button>
          <button
            type="button"
            class="primary-button"
            data-testid="catalog-apply"
            :disabled="!pendingModel"
            @click="emit('select', pendingModel)"
          >
            使用所选模型
          </button>
        </div>
      </footer>
    </section>
  </div>
</template>

<style scoped lang="scss">
.catalog-backdrop {
  position: fixed;
  z-index: 120;
  inset: 0;
  display: grid;
  padding: 24px;
  place-items: center;
  background: rgba(18, 24, 34, 0.42);
  backdrop-filter: blur(10px);
}

.catalog-dialog {
  display: flex;
  width: min(620px, 100%);
  max-height: min(720px, calc(100vh - 48px));
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--border-color);
  border-radius: 20px;
  background: var(--surface-solid);
  box-shadow: 0 24px 70px rgba(15, 23, 42, 0.24);
}

.catalog-dialog > header,
.catalog-dialog > footer,
.catalog-tools {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.catalog-dialog > header {
  padding: 20px 22px 14px;
}
.catalog-dialog > header p {
  margin: 0 0 3px;
  color: var(--text-tertiary);
  font-size: 11px;
  font-weight: 750;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.catalog-dialog > header h3 {
  margin: 0;
  font-size: 20px;
}
.icon-button {
  width: 34px;
  height: 34px;
  border: 0;
  border-radius: 50%;
  color: var(--text-secondary);
  background: var(--surface-muted);
  cursor: pointer;
  font-size: 22px;
}

.catalog-tools {
  padding: 0 22px 14px;
}
.search-field {
  display: flex;
  min-width: 0;
  height: 40px;
  flex: 1;
  align-items: center;
  gap: 8px;
  padding: 0 12px;
  border: 1px solid var(--border-strong);
  border-radius: 11px;
  color: var(--text-tertiary);
  background: var(--surface-muted);
}
.search-field:focus-within {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px var(--focus-ring);
}
.search-field input {
  min-width: 0;
  flex: 1;
  border: 0;
  outline: 0;
  color: var(--text-primary);
  background: transparent;
  font-size: 13px;
}
.refresh-button {
  display: inline-flex;
  min-height: 40px;
  align-items: center;
  gap: 6px;
}
.catalog-message {
  margin: 0;
  padding: 9px 22px;
  color: var(--text-secondary);
  background: var(--surface-muted);
  font-size: 12px;
}

.model-list {
  min-height: 220px;
  padding: 6px 12px 12px;
  overflow-y: auto;
  border-top: 1px solid var(--border-color);
  border-bottom: 1px solid var(--border-color);
}
.model-option {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 12px;
  padding: 12px 10px;
  border: 0;
  border-radius: 12px;
  color: var(--text-primary);
  background: transparent;
  cursor: pointer;
  text-align: left;
}
.model-option:hover {
  background: var(--surface-muted);
}
.model-option.selected {
  background: var(--primary-soft);
}
.radio-mark {
  display: grid;
  width: 18px;
  height: 18px;
  flex: none;
  place-items: center;
  border: 1.5px solid var(--border-strong);
  border-radius: 50%;
}
.model-option.selected .radio-mark {
  border-color: var(--primary-color);
}
.model-option.selected .radio-mark i {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--primary-color);
}
.model-copy {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  gap: 3px;
}
.model-copy strong {
  overflow-wrap: anywhere;
  font-size: 13px;
}
.model-copy code {
  overflow-wrap: anywhere;
  color: var(--text-secondary);
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 11px;
}
.model-copy small {
  color: var(--text-tertiary);
  font-size: 11px;
  line-height: 1.45;
}
.model-option > svg {
  flex: none;
  color: var(--primary-color);
}
.catalog-empty {
  display: grid;
  min-height: 220px;
  place-content: center;
  justify-items: center;
  gap: 7px;
  padding: 30px;
  color: var(--text-tertiary);
  text-align: center;
}
.catalog-empty strong {
  color: var(--text-secondary);
  font-size: 13px;
}
.catalog-empty small {
  max-width: 340px;
  font-size: 12px;
  line-height: 1.5;
}

.catalog-dialog > footer {
  padding: 14px 18px;
}
.catalog-dialog > footer > span {
  color: var(--text-tertiary);
  font-size: 12px;
}
.catalog-dialog > footer > div {
  display: flex;
  gap: 8px;
}

@media (max-width: 560px) {
  .catalog-backdrop {
    padding: 10px;
    place-items: end center;
  }
  .catalog-dialog {
    max-height: calc(100vh - 20px);
    border-radius: 18px;
  }
  .catalog-tools {
    align-items: stretch;
    flex-direction: column;
  }
  .refresh-button {
    justify-content: center;
  }
}
</style>
