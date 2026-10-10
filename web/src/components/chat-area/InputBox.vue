<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import type { PermissionMode, ResponseMode } from '@/api/client'
import { useUIStore } from '@/stores/ui'
import { useMentions } from '@/composables/useMentions'
import ModePill from '@/components/inkwell/ModePill.vue'
import InkMeter from '@/components/inkwell/InkMeter.vue'
import MentionMenu, { type Mention } from '@/components/inkwell/MentionMenu.vue'
import SlashMenu, { type SlashCommand } from '@/components/inkwell/SlashMenu.vue'
import IconSymbol from '@/components/common/IconSymbol.vue'
const props = withDefaults(
  defineProps<{
    sessionId: string
    assistantName?: string
    isSending?: boolean
    isSubmitting?: boolean
    isStopping?: boolean
    modelId?: string
    modelOptions?: Array<{ id: string; name: string; model: string }>
    responseMode?: ResponseMode
    permissionMode?: PermissionMode
    lastMessage?: string
    contextPct?: number | null
  }>(),
  {
    assistantName: '助手',
    isSending: false,
    isSubmitting: false,
    isStopping: false,
    modelId: '',
    modelOptions: () => [],
    responseMode: 'balanced',
    permissionMode: 'workspace',
    lastMessage: '',
    contextPct: null,
  },
)
const emit = defineEmits<{
  (event: 'send', content: string): void
  (event: 'cancel'): void
  (event: 'model-change', value: string): void
  (event: 'response-mode-change', value: ResponseMode): void
  (event: 'permission-mode-change', value: PermissionMode): void
}>()
const inputValue = ref(''),
  textarea = ref<HTMLTextAreaElement | null>(null),
  selected = ref(0),
  menuDismissed = ref(false)
const mode = ref<'ask' | 'plan' | 'auto'>(props.permissionMode === 'read_only' ? 'ask' : 'auto')
const ui = useUIStore(),
  router = useRouter(),
  mentions = useMentions(inputValue)
const commands: SlashCommand[] = [
  { id: 'new', label: '新页' },
  { id: 'memory', label: '它记得' },
  { id: 'settings', label: '设置' },
  { id: 'files', label: '工作区文件' },
  { id: 'changes', label: '查看变更' },
  { id: 'plan', label: '查看计划' },
  { id: 'stop', label: '中断任务' },
]
const slashItems = computed(() =>
  inputValue.value.startsWith('/') && !inputValue.value.includes(' ')
    ? commands.filter((c) => c.id.includes(inputValue.value.slice(1)))
    : [],
)
const menuLength = computed(() =>
  mentions.query.value !== undefined ? mentions.items.value.length : slashItems.value.length,
)
watch(inputValue, async () => {
  menuDismissed.value = false
  selected.value = 0
  await nextTick()
  if (textarea.value) {
    textarea.value.style.height = 'auto'
    const lineHeight = Number.parseFloat(getComputedStyle(textarea.value).lineHeight) || 26
    textarea.value.style.height = Math.min(textarea.value.scrollHeight, lineHeight * 10) + 'px'
  }
})
watch(
  () => props.permissionMode,
  (value) => {
    if (mode.value !== 'plan' || value !== 'read_only')
      mode.value = value === 'read_only' ? 'ask' : 'auto'
  },
)
watch(
  () => props.sessionId,
  () => {
    inputValue.value = ''
  },
)
function chooseMode(value: 'ask' | 'plan' | 'auto') {
  mode.value = value
  emit('permission-mode-change', value === 'auto' ? 'workspace' : 'read_only')
}
function send() {
  const content = inputValue.value.trim()
  if (!content || !props.modelOptions.length || props.isSubmitting) return
  emit('send', mode.value === 'plan' ? '请先分析并列出计划，暂不执行修改。\n\n' + content : content)
  inputValue.value = ''
}
function chooseMention(item: Mention) {
  mentions.select(item)
  void nextTick(() => textarea.value?.focus())
}
function reference() {
  inputValue.value += ' @'
  textarea.value?.focus()
}
defineExpose({
  restoreDraft(content: string) {
    const draft =
      mode.value === 'plan'
        ? content.replace(/^请先分析并列出计划，暂不执行修改。\n\n/, '')
        : content
    inputValue.value = inputValue.value ? `${inputValue.value}\n\n${draft}` : draft
    void nextTick(() => textarea.value?.focus())
  },
})
function command(item: SlashCommand) {
  inputValue.value = ''
  if (item.id === 'new') void router.push('/chat')
  else if (['memory', 'settings'].includes(item.id)) void router.push('/' + item.id)
  else if (item.id === 'stop') emit('cancel')
  else ui.openDrawer(item.id as 'files' | 'changes' | 'plan')
}
function handleKeydown(event: KeyboardEvent) {
  if (event.isComposing) return
  if (
    event.key === 'Escape' &&
    !menuDismissed.value &&
    (mentions.query.value !== undefined || slashItems.value.length)
  ) {
    event.preventDefault()
    event.stopPropagation()
    menuDismissed.value = true
    return
  }
  if (
    event.key === 'Escape' &&
    !ui.drawerOpen &&
    !ui.inboxOpen &&
    !ui.commandOpen &&
    !ui.shortcutsOpen
  ) {
    event.stopPropagation()
    emit('cancel')
    return
  }
  if (!menuDismissed.value && menuLength.value && ['ArrowDown', 'ArrowUp'].includes(event.key)) {
    event.preventDefault()
    selected.value =
      (selected.value + (event.key === 'ArrowDown' ? 1 : -1) + menuLength.value) % menuLength.value
    return
  }
  if (event.key === 'ArrowUp' && !inputValue.value) {
    event.preventDefault()
    inputValue.value = props.lastMessage
    return
  }
  if (event.key !== 'Enter' || event.shiftKey) return
  event.preventDefault()
  if (
    !menuDismissed.value &&
    mentions.query.value !== undefined &&
    mentions.items.value[selected.value]
  )
    chooseMention(mentions.items.value[selected.value])
  else if (!menuDismissed.value && slashItems.value[selected.value])
    command(slashItems.value[selected.value])
  else send()
}
</script>
<template>
  <div class="composer-wrap">
    <div class="composer" :aria-busy="isSending || isSubmitting">
      <MentionMenu
        v-if="!menuDismissed && mentions.query.value !== undefined"
        :items="mentions.items.value"
        :selected="selected"
        :loading="mentions.loading.value"
        @select="chooseMention"
      />
      <SlashMenu
        v-else-if="!menuDismissed && slashItems.length"
        :items="slashItems"
        :selected="selected"
        @select="command"
      />
      <textarea
        ref="textarea"
        v-model="inputValue"
        :placeholder="'问问 ' + assistantName + '…'"
        :disabled="!modelOptions.length"
        rows="1"
        aria-label="消息内容"
        @keydown="handleKeydown"
      />
      <div class="composer-controls">
        <button class="reference-button" aria-label="引用文件、会话或记忆" @click="reference">
          ＠
        </button>
        <ModePill :model-value="mode" :disabled="isSending || isSubmitting" @update:model-value="chooseMode" />
        <div class="control-spacer" />
        <InkMeter :value="contextPct" />
        <select
          :value="modelId"
          :disabled="isSending || isSubmitting || !modelOptions.length"
          aria-label="当前对话模型"
          @change="emit('model-change', ($event.target as HTMLSelectElement).value)"
        >
          <option v-if="!modelOptions.length" value="">未配置模型</option>
          <option v-for="item in modelOptions" :key="item.id" :value="item.id">
            {{ item.name }}
          </option>
        </select>
        <select
          :value="responseMode"
          :disabled="isSending || isSubmitting"
          aria-label="响应速度"
          @change="
            emit('response-mode-change', ($event.target as HTMLSelectElement).value as ResponseMode)
          "
        >
          <option value="fast">快速</option>
          <option value="balanced">均衡</option>
          <option value="thorough">深度</option>
        </select>
        <select
          :value="permissionMode"
          :disabled="isSending || isSubmitting"
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
        <button
          v-if="isSending"
          class="icon-button"
          :disabled="isStopping"
          :aria-busy="isStopping || undefined"
          :aria-label="isStopping ? '正在请求停止' : '停止任务'"
          @click="emit('cancel')"
        >
          <IconSymbol v-if="!isStopping" name="stop" :size="15" />
        </button>
        <button
          class="send-button"
          :disabled="isSubmitting || !inputValue.trim() || !modelOptions.length"
          :aria-busy="isSubmitting || undefined"
          :aria-label="isSubmitting ? '正在发送消息' : isSending ? '排队发送' : '发送消息'"
          @click="send"
        >
          <IconSymbol v-if="!isSubmitting" name="send" :size="15" />
        </button>
      </div>
    </div>
    <p class="composer-help">
      {{
        isStopping
          ? '正在请求停止，等待服务确认…'
          : isSubmitting
            ? '正在发送，草稿会保留…'
          : isSending
            ? '可继续写，当前回合成功后发送 · Esc 中断'
            : 'Enter 发送 · Shift + Enter 换行'
      }}
    </p>
    <router-link v-if="!modelOptions.length" class="configure-link" to="/settings?tab=models"
      >先连接一个模型</router-link
    >
  </div>
</template>
<style scoped lang="scss">
@use '@/styles/input-box';
</style>
