<script setup lang="ts">
import { t } from '@/i18n'
import { computed, ref, watch } from 'vue'
import type { ModelOption } from '@/config/model-groups'
const props = withDefaults(defineProps<{
  calls: number
  concurrent: number
  saving: boolean
  disabled: boolean
  modelIds?: string[]
  modelOptions?: ModelOption[]
  modelSelectionSupported?: boolean
}>(), { modelIds: () => [], modelOptions: () => [], modelSelectionSupported: false })
const emit = defineEmits<{ change: [value: { calls: number; concurrent: number; modelIds?: string[] }] }>()
const calls = ref(props.calls), concurrent = ref(props.concurrent)
const selectedModels = ref([...props.modelIds])
watch(() => JSON.stringify(props.modelIds), () => { selectedModels.value = [...props.modelIds] })
const modelChoices = computed(() => [
  ...props.modelOptions,
  ...selectedModels.value.filter(id => !props.modelOptions.some(model => model.id === id))
    .map(id => ({ id, name: t("配置已不存在，请取消选择"), model: id })),
])
watch(() => [props.calls, props.concurrent], () => {
  calls.value = props.calls
  concurrent.value = props.concurrent
})
const valid = computed(() => Number.isInteger(calls.value) && calls.value >= 0 && calls.value <= 32 &&
  Number.isInteger(concurrent.value) && concurrent.value >= 1 && concurrent.value <= 8 &&
  (calls.value === 0 || concurrent.value <= calls.value) && selectedModels.value.length <= 32)
function apply() {
  if (valid.value && !props.disabled && !props.saving)
    emit('change', { calls: calls.value, concurrent: concurrent.value,
      ...(props.modelSelectionSupported ? { modelIds: [...selectedModels.value] } : {}),
    })
}
</script>

<template>
  <details class="subagent-settings">
    <summary>{{ $t('子 Agent · {0}', [props.calls ? $t('每次任务 {0} 个 / 并行 {1}', [props.calls, props.concurrent]) : $t('关闭')]) }}</summary>
    <div class="subagent-settings__body">
      <label>{{ $t('每次任务最多派发（0 关闭）') }}<input v-model.number="calls" type="number" min="0" max="32" step="1" :disabled="disabled || saving" />
      </label>
      <label>{{ $t('最多同时运行') }}<input v-model.number="concurrent" type="number" min="1" :max="calls ? Math.min(8, calls) : 8" step="1" :disabled="disabled || saving || calls === 0" />
      </label>
      <fieldset v-if="modelSelectionSupported" :disabled="disabled || saving" class="subagent-settings__models">
        <legend>{{ $t('允许指定的其他模型') }}</legend>
        <label v-for="model in modelChoices" :key="model.id" :title="model.id">
          <input v-model="selectedModels" type="checkbox" :value="model.id" />
          {{ model.name || model.model }} · {{ model.model }}
        </label>
        <span v-if="!modelChoices.length">{{ $t('请先在模型设置中添加模型。') }}</span>
        <p>{{ $t('默认跟随主模型。勾选后可在聊天中指定；任务材料会发送给所选模型服务。') }}</p>
      </fieldset>
      <button type="button" class="secondary-button" :disabled="disabled || saving || !valid" @click="apply">
        {{ saving ? $t('保存中…') : $t('应用') }}
      </button>
      <p>{{ $t('新任务生效。子 Agent 仅可读取和搜索。') }}</p>
      <p v-if="!valid" role="alert">{{ $t('每次任务限 0–32 个，并行限 1–8 个且不能大于任务派发上限；允许指定的模型最多 32 个。') }}</p>
    </div>
  </details>
</template>

<style scoped>
.subagent-settings { margin-top: 8px; font-size: var(--text-xs); color: var(--ink-2); }
summary { cursor: pointer; width: fit-content; }
.subagent-settings__body { display: flex; flex-wrap: wrap; gap: 10px; padding: 10px 0; align-items: center; }
label { display: flex; align-items: center; gap: 8px; }
input { width: 58px; padding: 4px; color: var(--ink); background: var(--paper); border: 1px solid var(--rule); border-radius: var(--radius-sm); }
.subagent-settings__models { flex-basis: 100%; border: 1px solid var(--rule); border-radius: var(--radius-sm); padding: 8px; max-height: 200px; overflow: auto; }
.subagent-settings__models label { margin: 6px 0; }
.subagent-settings__models input { width: auto; }
p { flex-basis: 100%; margin: 0; line-height: 1.6; opacity: .75; }
</style>
