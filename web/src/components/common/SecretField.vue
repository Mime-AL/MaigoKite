<script setup lang="ts">
import { onBeforeUnmount, ref, watch } from 'vue'
import IconSymbol from './IconSymbol.vue'
import { t } from '@/i18n'
const props = defineProps<{ modelValue: string; label: string; disabled?: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const revealed = ref(false),
  copied = ref(false),
  error = ref('')
let timer: ReturnType<typeof setTimeout> | undefined,
  alive = true
watch(
  () => props.modelValue,
  () => {
    copied.value = false
    error.value = ''
  },
)
async function copy() {
  if (!props.modelValue || props.disabled) return
  error.value = ''
  try {
    await navigator.clipboard.writeText(props.modelValue)
    if (!alive) return
    copied.value = true
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      copied.value = false
    }, 1800)
  } catch {
    if (alive) error.value = t('无法复制，请选中文字后复制。')
  }
}
onBeforeUnmount(() => {
  alive = false
  if (timer) clearTimeout(timer)
})
</script>
<template>
  <div class="secret-field">
    <div>
      <input
        :value="modelValue"
        :type="revealed ? 'text' : 'password'"
        autocomplete="new-password"
        :aria-label="label"
        :disabled="disabled"
        @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
      ><button
        type="button"
        class="icon-button"
        :disabled="disabled"
        :aria-label="revealed ? $t('隐藏 API Key') : $t('显示 API Key')"
        @click="revealed = !revealed"
      >
        <IconSymbol
          :name="revealed ? 'eye-off' : 'eye'"
          :size="16"
        />
      </button><button
        type="button"
        class="icon-button"
        :disabled="disabled || !modelValue"
        :aria-label="$t('复制 API Key')"
        @click="copy"
      >
        <IconSymbol
          :name="copied ? 'check' : 'copy'"
          :size="16"
        />
      </button>
    </div>
    <small
      v-if="copied"
      role="status"
    >{{ $t('已复制') }}</small><small
      v-if="error"
      role="alert"
    >{{ error }}</small>
  </div>
</template>
<style scoped lang="scss">
.secret-field {
  min-width: 0;
}
.secret-field > div {
  display: flex;
  gap: var(--space-2);
  align-items: center;
}
input {
  flex: 1;
  min-width: 0;
  width: 100%;
  font-family: var(--font-mono);
  font-size: var(--text-sm);
}
button {
  flex: none;
}
small {
  display: block;
  color: var(--ink-2);
  margin-top: var(--space-2);
  font-size: var(--text-xs);
}
</style>
