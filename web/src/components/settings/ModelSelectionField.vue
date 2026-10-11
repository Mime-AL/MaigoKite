<script setup lang="ts">
import { ref, toRefs, type UnwrapNestedRefs } from 'vue'
import type { useModelSettings } from '@/composables/useModelSettings'
import IconSymbol from '@/components/common/IconSymbol.vue'
import ModelCatalogPicker from './ModelCatalogPicker.vue'
import ModelContextFields from './ModelContextFields.vue'

const props = defineProps<{ editor: UnwrapNestedRefs<ReturnType<typeof useModelSettings>> }>()
const {
  draft,
  manualModelId,
  selectedModels,
  modelOptions,
  catalogOpen,
  canDiscover,
  discovering,
  selectedModelInfo,
  discoveryMessage,
  discoveryFailed,
  discoveredModels,
  requiresEndpoint,
  keyRequired,
  openCatalog,
  closeCatalog,
  discoverModels,
  useCatalogModel,
  addModel,
  removeModel,
} = toRefs(props.editor)
const modelIdInput = ref<HTMLInputElement | null>(null)

function addManualModel() {
  if (!addModel.value(manualModelId.value)) return
  manualModelId.value = ''
  modelIdInput.value?.focus()
}

function editModelManually() {
  closeCatalog.value()
  modelIdInput.value?.focus()
}
</script>

<template>
  <div
    class="form-field model-field"
    data-settings-field="model-selection"
  >
    <label for="model-id-input">{{ $t('模型（可多选）') }}<b>{{ $t('至少一个') }}</b></label>
    <ModelContextFields :editor="editor" />
    <div
      v-if="selectedModels.length"
      class="selected-models"
      :aria-label="$t('已选模型')"
    >
      <span
        v-for="model in selectedModels"
        :key="model"
        class="selected-model"
      >
        <code>{{ model }}</code>
        <button
          type="button"
          :aria-label="$t('移除模型 {0}', [model])"
          @click="removeModel(model)"
        >
          ×
        </button>
      </span>
    </div>
    <div class="model-input-row">
      <input
        id="model-id-input"
        ref="modelIdInput"
        v-model.trim="manualModelId"
        data-testid="model-id"
        maxlength="200"
        :placeholder="$t('手动填写模型 ID')"
        autocomplete="off"
        @keydown.enter.stop.prevent="addManualModel"
      >
      <button
        type="button"
        class="secondary-button"
        :disabled="!manualModelId.trim()"
        @click="addManualModel"
      >
        {{ $t('添加') }}
      </button>
    </div>
    <div class="model-catalog-actions">
      <button
        v-if="modelOptions.length"
        type="button"
        class="secondary-button"
        data-testid="browse-models"
        :disabled="discovering"
        :aria-expanded="catalogOpen"
        aria-controls="model-catalog-card"
        @click="catalogOpen ? closeCatalog() : openCatalog()"
      >
        {{ catalogOpen ? $t('收起列表') : $t('选择模型') }}
      </button>
      <button
        type="button"
        class="secondary-button discover-button"
        :disabled="!canDiscover || discovering"
        :aria-busy="discovering || undefined"
        :aria-expanded="catalogOpen"
        aria-controls="model-catalog-card"
        data-testid="discover-models"
        @click="discoverModels"
      >
        <IconSymbol
          v-if="!discovering"
          name="refresh"
          :size="14"
        />
        {{
          discovering ? $t('正在获取…') : modelOptions.length ? $t('重新获取') : $t('获取模型列表')
        }}
      </button>
      <small
        v-if="selectedModels.length"
        role="status"
      >{{
        $t('已选 {0} 个', [selectedModels.length])
      }}</small>
    </div>
    <small
      v-if="selectedModelInfo"
      class="model-meta"
    >{{ selectedModelInfo }}</small>
    <small
      v-else-if="discoveryMessage && !catalogOpen"
      :class="{ warning: discoveryFailed || !discoveredModels.length }"
      :role="discoveryFailed ? 'alert' : 'status'"
    >{{ discoveryMessage }}</small>
    <small
      v-else-if="
        !catalogOpen && ((requiresEndpoint && !draft.baseUrl) || (!canDiscover && keyRequired))
      "
    >{{ requiresEndpoint && !draft.baseUrl ? $t('请填写服务地址') : $t('请填写 API Key') }}</small>
    <ModelCatalogPicker
      v-if="catalogOpen"
      :models="modelOptions"
      :selected-models="selectedModels"
      :loading="discovering"
      :can-refresh="canDiscover"
      :message="discoveryMessage"
      :error="discoveryFailed"
      @close="editModelManually"
      @refresh="discoverModels"
      @select="useCatalogModel"
      @manual="editModelManually"
    />
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/model-selection';
</style>
