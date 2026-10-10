<script setup lang="ts">
import { t } from '@/i18n'
import { computed, ref, watch } from 'vue'
import IconSymbol from '@/components/common/IconSymbol.vue'
import type { DiscoveredChatModel } from '@/api/client'

const props = defineProps<{
  models: DiscoveredChatModel[]
  selectedModels: string[]
  loading: boolean
  canRefresh: boolean
  message?: string
  error?: boolean
}>()

const emit = defineEmits<{
  close: []
  manual: []
  refresh: []
  select: [modelId: string]
}>()

const query = ref('')
const visibleCount = ref(80)
watch(query, () => {
  visibleCount.value = 80
})

const filteredModels = computed(() => {
  const needle = query.value.trim().toLocaleLowerCase()
  if (!needle) return props.models
  return props.models.filter((model) =>
    `${model.id} ${model.name ?? ''}`.toLocaleLowerCase().includes(needle),
  )
})
const visibleModels = computed(() => filteredModels.value.slice(0, visibleCount.value))
const selectedIds = computed(() => new Set(props.selectedModels))

function describeModel(model: DiscoveredChatModel): string {
  return [
    model.owned_by,
    model.context_window ? t("{0} Token 上下文", [model.context_window.toLocaleString('en-US')]) : '',
    model.details,
  ]
    .filter(Boolean)
    .join(' · ')
}
</script>

<template>
  <section
    id="model-catalog-card"
    class="catalog-card"
    data-testid="model-catalog"
    aria-labelledby="model-catalog-title"
    @keydown.esc.stop.prevent="emit('close')"
  >
    <header>
      <div>
        <h3 id="model-catalog-title">{{ $t('模型列表') }}</h3>
      </div>
      <button type="button" class="icon-button" :aria-label="$t('收起模型列表')" @click="emit('close')">
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
          :placeholder="$t('按模型 ID 或名称搜索')"
          :aria-label="$t('搜索可用模型')"
          @keydown.enter.prevent
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
        {{ loading ? $t('正在获取…') : $t('重新获取') }}
      </button>
    </div>

    <p v-if="message" class="catalog-message" :role="error ? 'alert' : 'status'">{{ message }}</p>

    <div class="model-list" role="group" :aria-label="$t('可用模型')" :aria-busy="loading || undefined">
      <button
        v-for="model in visibleModels"
        :key="model.id"
        type="button"
        class="model-option"
        :class="{ selected: selectedIds.has(model.id) }"
        :data-model-id="model.id"
        :aria-pressed="selectedIds.has(model.id)"
        :disabled="loading"
        @click="emit('select', model.id)"
      >
        <span class="checkbox-mark" aria-hidden="true">
          <IconSymbol v-if="selectedIds.has(model.id)" name="check" :size="12" />
        </span>
        <span class="model-copy">
          <strong>{{ model.name || model.id }}</strong>
          <code v-if="model.name && model.name !== model.id">{{ model.id }}</code>
          <small v-if="describeModel(model)">{{ describeModel(model) }}</small>
        </span>
      </button>

      <button
        v-if="visibleModels.length < filteredModels.length"
        type="button"
        class="secondary-button"
        @click="visibleCount += 80"
      >{{ $t('显示更多模型') }}</button>

      <div v-if="loading" class="catalog-empty" role="status">
        <strong>{{ $t('正在获取模型…') }}</strong>
      </div>
      <div v-else-if="!filteredModels.length" class="catalog-empty">
        <IconSymbol name="search" :size="22" />
        <strong>{{
          models.length ? $t('没有匹配的模型') : error ? $t('暂时无法获取模型列表') : $t('没有可用模型')
        }}</strong>
      </div>
    </div>

    <footer>
      <span
        >{{ $t('{0} / {1} 个模型 · 已选 {2} 个', [filteredModels.length, models.length, selectedModels.length]) }}</span
      >
      <div>
        <button type="button" class="secondary-button" @click="emit('manual')">{{ $t('手动填写模型 ID') }}</button>
        <button type="button" class="secondary-button" @click="emit('close')">{{ $t('完成选择') }}</button>
      </div>
    </footer>
  </section>
</template>

<style scoped lang="scss">
@use '@/styles/model-catalog';
</style>
