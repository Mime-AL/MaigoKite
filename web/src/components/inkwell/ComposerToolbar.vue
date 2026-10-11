<script setup lang="ts">
import { nextTick, ref } from 'vue'
import type { PermissionMode, ResponseMode } from '@/api/client'
import { composerDefaults, type ComposerProps } from '@/utils/composer-presentation'
import ModePill from './ModePill.vue'
import ModelPicker from './ModelPicker.vue'
import Pulse from '@/components/shell/Pulse.vue'
import IconSymbol from '@/components/common/IconSymbol.vue'
defineOptions({ inheritAttrs: false })
const props = withDefaults(
  defineProps<
    ComposerProps & {
      mode: 'ask' | 'plan' | 'auto'
      busy: boolean
      hasDraft: boolean
      guideDisabled: boolean
    }
  >(),
  composerDefaults,
)
const emit = defineEmits<{
  (event: 'reference' | 'cancel'): void
  (event: 'send', later?: boolean): void
  (event: 'mode', value: 'ask' | 'plan' | 'auto'): void
  (event: 'model-change', value: string): void
  (event: 'response-mode-change', value: ResponseMode): void
  (event: 'permission-mode-change', value: PermissionMode): void
}>()
const menuOpen = ref(false),
  trigger = ref<HTMLButtonElement | null>(null),
  menu = ref<HTMLElement | null>(null)
function closeMenu() {
  if (!menuOpen.value) return false
  menuOpen.value = false
  trigger.value?.focus()
  return true
}
async function toggleMenu() {
  menuOpen.value = !menuOpen.value
  if (menuOpen.value) {
    await nextTick()
    menu.value?.querySelector<HTMLButtonElement>('button:not(:disabled)')?.focus()
  }
}
function send(later = false) {
  menuOpen.value = false
  emit('send', later)
}
function menuKey(event: KeyboardEvent) {
  if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return
  const buttons = [
    ...(menu.value?.querySelectorAll<HTMLButtonElement>('button:not(:disabled)') || []),
  ]
  if (!buttons.length) return
  event.preventDefault()
  const index = buttons.indexOf(document.activeElement as HTMLButtonElement)
  buttons[
    event.key === 'Home'
      ? 0
      : event.key === 'End'
        ? buttons.length - 1
        : (index + (event.key === 'ArrowDown' ? 1 : -1) + buttons.length) % buttons.length
  ].focus()
}
defineExpose({ closeMenu })
</script>
<template>
  <div class="composer-controls">
    <button
      class="reference-button"
      :aria-label="$t('引用文件、会话或记忆')"
      @click="emit('reference')"
    >
      <IconSymbol
        name="at"
        :size="16"
      />
    </button>
    <ModePill
      :model-value="mode"
      :disabled="isSending || isSubmitting"
      @update:model-value="emit('mode', $event)"
    />
    <div class="control-spacer" />
    <ModelPicker
      :key="sessionId"
      :model-value="modelId"
      :models="modelOptions"
      :disabled="isSending || isSubmitting || !modelOptions.length"
      @update:model-value="emit('model-change', $event)"
    />
    <select
      :value="responseMode"
      :disabled="isSending || isSubmitting"
      :aria-label="$t('响应速度')"
      @change="
        emit('response-mode-change', ($event.target as HTMLSelectElement).value as ResponseMode)
      "
    >
      <option value="fast">
        {{ $t('快速') }}
      </option>
      <option value="balanced">
        {{ $t('均衡') }}
      </option>
      <option value="thorough">
        {{ $t('深度') }}
      </option>
    </select>
    <select
      :value="permissionMode"
      :disabled="isSubmitting"
      :aria-label="$t('执行权限')"
      :title="$t('权限调整从下一个尚未开始的操作生效')"
      @change="
        emit('permission-mode-change', ($event.target as HTMLSelectElement).value as PermissionMode)
      "
    >
      <option value="read_only">
        {{ $t('只读') }}
      </option>
      <option value="workspace">
        {{ $t('工作区') }}
      </option>
      <option value="full_access">
        {{ $t('完全访问') }}
      </option>
    </select>
    <button
      v-if="isSending"
      class="icon-button stop-button"
      :disabled="isStopping"
      :aria-busy="isStopping || undefined"
      :aria-label="isStopping ? $t('正在请求停止') : $t('停止任务')"
      @click="emit('cancel')"
    >
      <Pulse
        v-if="isStopping"
        state="acting"
      /><IconSymbol
        v-else
        name="stop"
        :size="15"
      />
    </button>
    <button
      class="send-button"
      :disabled="busy || !hasDraft || !modelOptions.length || (isSending && guideDisabled)"
      :aria-busy="busy || undefined"
      :aria-label="busy ? $t('正在发送消息') : isSending ? $t('立即发送') : $t('发送消息')"
      :title="isSending ? props.guideReason : undefined"
      @click="send()"
    >
      <Pulse
        v-if="busy"
        state="acting"
      /><IconSymbol
        v-else
        name="send"
        :size="15"
      />
    </button>
    <div
      v-if="isSending"
      class="send-options"
      @keydown.esc.stop.prevent="closeMenu"
      @keydown="menuKey"
    >
      <button
        ref="trigger"
        class="icon-button"
        :aria-label="$t('发送选项')"
        :aria-expanded="menuOpen"
        :disabled="busy"
        @click="toggleMenu"
      >
        <IconSymbol
          name="chevron"
          :size="15"
        />
      </button>
      <div
        v-if="menuOpen"
        ref="menu"
        class="send-options-menu"
      >
        <button
          :disabled="guideDisabled || !hasDraft"
          @click="send()"
        >
          {{ $t('立即发送') }}<small>Enter</small>
        </button>
        <button
          :disabled="!hasDraft"
          @click="send(true)"
        >
          {{ $t('加入队列') }}<small>Alt + Enter</small>
        </button>
      </div>
    </div>
  </div>
</template>
<style scoped lang="scss">
@use '@/styles/composer-controls';
</style>
