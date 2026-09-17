<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import IconSymbol from '@/components/common/IconSymbol.vue'
import type { PermissionMode, ResponseMode } from '@/api/client'

withDefaults(
  defineProps<{
    sessionId: string
    assistantName?: string
    isSending?: boolean
    modelId?: string
    modelOptions?: Array<{ id: string; name: string; model: string }>
    responseMode?: ResponseMode
    permissionMode?: PermissionMode
  }>(),
  {
    assistantName: '助手',
    isSending: false,
    modelId: '',
    modelOptions: () => [],
    responseMode: 'balanced',
    permissionMode: 'workspace',
  },
)
const emit = defineEmits<{
  (event: 'send', content: string): void
  (event: 'model-change', modelId: string): void
  (event: 'response-mode-change', mode: ResponseMode): void
  (event: 'permission-mode-change', mode: PermissionMode): void
}>()
const inputValue = ref('')
const textarea = ref<HTMLTextAreaElement | null>(null)

function handleSend() {
  const content = inputValue.value.trim()
  if (!content) return
  emit('send', content)
  inputValue.value = ''
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key !== 'Enter' || event.shiftKey || event.isComposing) return
  event.preventDefault()
  handleSend()
}

watch(inputValue, async () => {
  await nextTick()
  if (!textarea.value) return
  textarea.value.style.height = 'auto'
  textarea.value.style.height = `${Math.min(textarea.value.scrollHeight, 160)}px`
})
</script>

<template>
  <div class="composer-wrap">
    <div class="composer" :class="{ active: inputValue }" :aria-busy="isSending">
      <div class="composer-controls">
        <label>
          <IconSymbol name="brain" :size="13" />
          <select
            :value="modelId"
            :disabled="isSending || !modelOptions.length"
            aria-label="当前对话模型"
            @change="emit('model-change', ($event.target as HTMLSelectElement).value)"
          >
            <option v-if="!modelOptions.length" value="">未配置模型</option>
            <option v-for="option in modelOptions" :key="option.id" :value="option.id">
              {{ option.name }} · {{ option.model }}
            </option>
          </select>
        </label>
        <label>
          <IconSymbol name="shield" :size="13" />
          <select
            :value="permissionMode"
            :disabled="isSending"
            aria-label="执行权限"
            @change="
              emit(
                'permission-mode-change',
                ($event.target as HTMLSelectElement).value as PermissionMode,
              )
            "
          >
            <option value="read_only">只读</option>
            <option value="workspace">工作区</option>
            <option value="full_access">完全访问</option>
          </select>
        </label>
        <label>
          <IconSymbol name="sparkles" :size="13" />
          <select
            :value="responseMode"
            :disabled="isSending"
            aria-label="响应速度"
            @change="
              emit(
                'response-mode-change',
                ($event.target as HTMLSelectElement).value as ResponseMode,
              )
            "
          >
            <option value="fast">快速</option>
            <option value="balanced">均衡</option>
            <option value="thorough">深度</option>
          </select>
        </label>
      </div>
      <div class="input-row">
        <textarea
          ref="textarea"
          v-model="inputValue"
          :placeholder="`问问 ${assistantName}…`"
          rows="1"
          :disabled="isSending || !modelOptions.length"
          aria-label="消息内容"
          @keydown="handleKeydown"
        />
        <button
          class="send-button"
          type="button"
          :disabled="!inputValue.trim() || isSending || !modelOptions.length"
          aria-label="发送消息"
          @click="handleSend"
        >
          <span v-if="isSending" class="sending-dot" />
          <IconSymbol v-else name="send" :size="17" :stroke-width="2" />
        </button>
      </div>
    </div>
    <p>Enter 发送 · Shift + Enter 换行</p>
  </div>
</template>

<style scoped lang="scss">
.composer-wrap {
  flex: none;
  padding: 8px clamp(20px, 4vw, 48px) 18px;
  background: linear-gradient(180deg, transparent, var(--surface-solid) 24%);
}
.composer {
  display: flex;
  width: min(760px, 100%);
  min-height: 76px;
  flex-direction: column;
  gap: 5px;
  margin: 0 auto;
  padding: 7px 9px 9px 13px;
  border: 1px solid var(--border-strong);
  border-radius: 19px;
  background: var(--surface-solid);
  box-shadow:
    0 10px 34px rgba(32, 42, 58, 0.11),
    inset 0 1px rgba(255, 255, 255, 0.5);
  transition:
    border 160ms ease,
    box-shadow 160ms ease;
}
.composer:focus-within {
  border-color: rgba(0, 113, 227, 0.38);
  box-shadow:
    0 12px 36px rgba(32, 42, 58, 0.12),
    0 0 0 4px var(--focus-ring);
}
.composer-controls {
  display: flex;
  align-items: center;
  gap: 5px;
}
.composer-controls label {
  display: flex;
  max-width: 45%;
  align-items: center;
  gap: 4px;
  padding: 3px 6px;
  border-radius: 7px;
  color: var(--text-tertiary);
  background: var(--surface-muted);
}
.composer-controls select {
  min-width: 0;
  max-width: 220px;
  border: 0;
  outline: 0;
  color: var(--text-secondary);
  background: transparent;
  font-size: 9.5px;
  font-weight: 600;
  cursor: pointer;
}
.composer-controls select:disabled {
  cursor: default;
  opacity: 0.6;
}
.input-row {
  display: flex;
  align-items: flex-end;
  gap: 10px;
}
textarea {
  min-height: 34px;
  max-height: 160px;
  flex: 1;
  padding: 7px 0 5px;
  overflow-y: auto;
  resize: none;
  border: 0;
  outline: none;
  color: var(--text-primary);
  background: transparent;
  font-size: 13px;
  line-height: 1.5;
}
textarea::placeholder {
  color: var(--text-tertiary);
}
.send-button {
  display: grid;
  width: 36px;
  height: 36px;
  flex: none;
  place-items: center;
  border: 0;
  border-radius: 12px;
  color: #fff;
  background: var(--primary-color);
  box-shadow: 0 5px 12px rgba(0, 113, 227, 0.23);
  cursor: pointer;
  transition:
    transform 150ms ease,
    opacity 150ms ease;
}
.send-button:hover:not(:disabled) {
  transform: translateY(-1px);
}
.send-button:active:not(:disabled) {
  transform: scale(0.95);
}
.send-button:disabled {
  color: var(--text-tertiary);
  background: var(--surface-strong);
  box-shadow: none;
}
.sending-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: currentColor;
  animation: breathe 1s ease-in-out infinite;
}
.composer-wrap > p {
  margin: 7px auto 0;
  color: var(--text-tertiary);
  font-size: 9px;
  text-align: center;
}
@keyframes breathe {
  50% {
    opacity: 0.3;
    transform: scale(0.75);
  }
}
</style>
