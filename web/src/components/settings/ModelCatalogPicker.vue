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
  return props.models.filter((model) => `${model.id} ${model.name ?? ''}`.toLocaleLowerCase().includes(needle))
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
  <div class="catalog-backdrop" data-testid="model-catalog" @click.self="emit('close')" @keydown.esc="emit('close')">
    <section class="catalog-dialog" role="dialog" aria-modal="true" aria-labelledby="model-catalog-title">
      <header>
        <div>
          <p>Model catalog</p>
          <h3 id="model-catalog-title">选择模型</h3>
        </div>
        <button type="button" class="icon-button" aria-label="关闭模型目录" @click="emit('close')">×</button>
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
          :aria-busy="loading || undefined"
          @click="emit('refresh')"
        >
          <IconSymbol v-if="!loading" name="refresh" :size="14" />
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
@use '@/styles/model-catalog';
</style>
