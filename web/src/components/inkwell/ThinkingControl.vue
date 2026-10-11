<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { api, type ThinkingControl } from '@/api/client'
import type { ModelOption } from '@/config/model-groups'
import { t } from '@/i18n'

const props = defineProps<{
  modelId: string
  models: ModelOption[]
  modelValue: string
  disabled?: boolean
  saving?: boolean
}>()
const emit = defineEmits<{ (event: 'update:modelValue', value: string): void }>()
const capability = ref<ThinkingControl | null>(null)
const loading = ref(false)
const failed = ref(false)
const revision = ref(0)
const preview = ref<string | null>(null)
const current = computed(() => props.models.find((model) => model.id === props.modelId))
const locked = computed(() => props.disabled || props.saving || loading.value)
const levels = computed(() => capability.value?.options || [])
const stops = computed(() => ['', ...levels.value])
const adjustable = computed(
  () => capability.value?.kind !== 'unavailable' && levels.value.length > 1,
)
const choice = computed(() => preview.value ?? props.modelValue)
const selected = computed(() => choice.value || capability.value?.default || '')
const index = computed(() => Math.max(0, stops.value.indexOf(choice.value)))
const valid = computed(() => !props.modelValue || levels.value.includes(props.modelValue))
const progress = computed(
  () => `${levels.value.length ? (index.value / levels.value.length) * 100 : 0}%`,
)
function label(value: string) {
  if (!value) return t('服务默认')
  const labels: Record<string, string> = {
    off: '关闭',
    on: '开启',
    none: '不思考',
    minimal: '极低',
    low: '低',
    medium: '中',
    high: '高',
    xhigh: '极高',
    max: '最高',
  }
  return labels[value] ? t(labels[value]) : value
}
const valueLabel = computed(() => {
  if (!valid.value) return t('设置已失效')
  if (!choice.value) return t('服务默认')
  return label(selected.value)
})
const notice = computed(() => {
  if (failed.value || capability.value?.reason === 'metadata_unavailable')
    return t('暂时无法读取思考能力')
  if (capability.value?.reason === 'native_control_only')
    return t('请在模型服务中调整思考设置')
  return t('未提供可调节的思考能力')
})
watch(
  () => [
    props.modelId,
    current.value?.provider,
    current.value?.model,
    current.value?.baseUrl,
    revision.value,
  ],
  async (_, __, onCleanup) => {
    const controller = new AbortController()
    onCleanup(() => controller.abort())
    capability.value = null
    preview.value = null
    failed.value = false
    loading.value = Boolean(props.modelId)
    if (!props.modelId) return
    try {
      const result = await api.getModelThinking(props.modelId, controller.signal)
      if (!controller.signal.aborted) capability.value = result
    } catch {
      if (!controller.signal.aborted) failed.value = true
    } finally {
      if (!controller.signal.aborted) loading.value = false
    }
  },
  { immediate: true },
)
watch(
  () => [props.modelValue, props.saving],
  () => {
    preview.value = null
  },
)
function slide(event: Event) {
  preview.value = stops.value[Number((event.target as HTMLInputElement).value)] || ''
}
function commit(value: string) {
  if (locked.value || (value && !levels.value.includes(value))) return
  preview.value = null
  emit('update:modelValue', value)
}
</script>

<template>
  <div
    v-if="modelId"
    class="thinking-control"
    :aria-busy="loading || saving || undefined"
  >
    <template v-if="adjustable">
      <div class="thinking-heading">
        <span>{{ $t('思考') }}</span>
        <span
          class="thinking-value"
          aria-live="polite"
        >{{
          saving ? $t('保存中…') : valueLabel
        }}</span>
        <button
          v-if="modelValue"
          type="button"
          class="thinking-reset"
          :disabled="locked"
          :aria-label="$t('恢复服务默认')"
          :title="$t('恢复服务默认')"
          @click="commit('')"
        >
          ↺
        </button>
      </div>
      <input
        v-if="capability?.kind === 'effort'"
        type="range"
        min="0"
        :max="stops.length - 1"
        step="1"
        :value="index"
        :disabled="locked"
        :aria-label="$t('思考强度')"
        :aria-valuetext="valueLabel"
        :style="{ '--thinking-progress': progress }"
        @input="slide"
        @change="commit(stops[Number(($event.target as HTMLInputElement).value)] || '')"
      >
      <button
        v-else
        type="button"
        class="thinking-switch"
        role="switch"
        :aria-label="$t('开启思考')"
        :aria-checked="selected === 'on'"
        :disabled="locked"
        @click="commit(selected === 'on' ? 'off' : 'on')"
      >
        <span />
      </button>
      <div
        v-if="capability?.kind === 'effort'"
        class="thinking-ticks"
        aria-hidden="true"
      >
        <span
          v-for="level in stops"
          :key="level"
          :class="{ active: level === choice }"
          :title="label(level)"
        >·</span>
      </div>
    </template>
    <template v-else>
      <span
        class="thinking-unavailable"
        :title="notice"
      >{{
        loading ? $t('读取思考能力…') : modelValue ? $t('思考') + '：' + valueLabel : $t('思考：服务默认')
      }}</span>
      <button
        v-if="!loading && (failed || capability?.reason === 'metadata_unavailable')"
        type="button"
        class="thinking-reset"
        :disabled="locked"
        :aria-label="$t('重新读取思考能力')"
        @click="revision++"
      >
        ↻
      </button>
      <button
        v-if="!loading && modelValue"
        type="button"
        class="thinking-reset"
        :disabled="locked"
        :title="$t('设置已失效')"
        @click="commit('')"
      >
        {{ $t('恢复服务默认') }}
      </button>
    </template>
  </div>
</template>

<style scoped lang="scss">
.thinking-control {
  min-width: 7rem;
  max-width: 12rem;
  color: var(--ink-2);
  font-size: var(--text-xs);
}
.thinking-heading {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.thinking-value {
  margin-inline-start: auto;
  color: var(--ink-3);
}
.thinking-reset {
  border: 0;
  padding: 0 var(--space-1);
  background: transparent;
  color: var(--ink-2);
  cursor: pointer;
}
input[type='range'] {
  appearance: none;
  display: block;
  width: 100%;
  height: 24px;
  margin: 0;
  border-radius: 4px;
  background: transparent;
  cursor: pointer;
  accent-color: var(--accent);
  &::-webkit-slider-runnable-track {
    height: 4px;
    border-radius: 4px;
    background: linear-gradient(to right, var(--accent) var(--thinking-progress), var(--rule) var(--thinking-progress));
  }
  &::-moz-range-track {
    height: 4px;
    border-radius: 4px;
    background: linear-gradient(to right, var(--accent) var(--thinking-progress), var(--rule) var(--thinking-progress));
  }
  &::-webkit-slider-thumb {
    appearance: none;
    width: 12px;
    height: 12px;
    margin-top: -4px;
    border-radius: 50%;
    background: var(--accent);
  }
  &::-moz-range-thumb {
    width: 12px;
    height: 12px;
    border: 0;
    border-radius: 50%;
    background: var(--accent);
  }
  &:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 5px;
  }
}
.thinking-ticks {
  display: flex;
  justify-content: space-between;
  color: var(--ink-3);
  line-height: 12px;
}
.thinking-ticks .active {
  color: var(--accent);
}
.thinking-switch {
  display: block;
  width: 30px;
  height: 18px;
  margin-top: 4px;
  padding: 2px;
  border: 0;
  border-radius: 12px;
  background: var(--rule);
  cursor: pointer;
  span {
    display: block;
    width: 14px;
    height: 14px;
    background: var(--paper);
    border-radius: 50%;
  }
  &[aria-checked='true'] {
    background: var(--accent);
    span {
      transform: translateX(12px);
    }
  }
}
:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.thinking-unavailable {
  color: var(--ink-3);
}
</style>
