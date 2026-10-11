<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import MentionMenu, { type Mention } from './MentionMenu.vue'
import SlashMenu, { type SlashCommand } from './SlashMenu.vue'
const props = defineProps<{
  modelValue: string
  menuId: string
  mentions: Mention[]
  mentionQuery?: string
  loading?: boolean
  commands: SlashCommand[]
  placeholder: string
  disabled: boolean
}>()
const emit = defineEmits<{
  (event: 'update:modelValue', value: string): void
  (event: 'keydown', value: KeyboardEvent): void
  (event: 'mention', value: Mention): void
  (event: 'command', value: SlashCommand): void
  (event: 'focus'): void
}>()
const textarea = ref<HTMLTextAreaElement | null>(null)
const selected = ref(0),
  dismissed = ref(false)
const count = computed(() =>
  props.mentionQuery !== undefined ? props.mentions.length : props.commands.length,
)
function menu() {
  return !dismissed.value && count.value
}
function listId() {
  return props.menuId + (props.mentionQuery !== undefined ? '-mentions' : '-commands')
}
function select(index: number) {
  const mention = props.mentionQuery !== undefined ? props.mentions[index] : undefined
  if (mention) emit('mention', mention)
  else if (props.mentionQuery === undefined && props.commands[index])
    emit('command', props.commands[index])
}
function keydown(event: KeyboardEvent) {
  if (event.isComposing || event.keyCode === 229) return
  if (
    event.key === 'Escape' &&
    !dismissed.value &&
    (props.mentionQuery !== undefined || props.commands.length)
  ) {
    event.preventDefault()
    event.stopPropagation()
    dismissed.value = true
    return
  }
  if (menu() && ['ArrowDown', 'ArrowUp'].includes(event.key)) {
    event.preventDefault()
    selected.value =
      (selected.value + (event.key === 'ArrowDown' ? 1 : -1) + count.value) % count.value
    return
  }
  if (menu() && event.altKey && /^[1-9]$/.test(event.key)) {
    event.preventDefault()
    select(Number(event.key) - 1)
    return
  }
  if (
    menu() && !event.shiftKey && !event.altKey && !event.ctrlKey && !event.metaKey &&
    ['Enter', 'Tab'].includes(event.key)
  ) {
    event.preventDefault()
    select(selected.value)
    return
  }
  emit('keydown', event)
}
watch(
  () => props.modelValue,
  () => {
    selected.value = 0
    dismissed.value = false
  },
)
watch(count, (length) => {
  selected.value = Math.min(selected.value, Math.max(0, length - 1))
})
watch(
  () => props.modelValue,
  async () => {
    await nextTick()
    if (!textarea.value) return
    textarea.value.style.height = 'auto'
    const height = Number.parseFloat(getComputedStyle(textarea.value).lineHeight)
    textarea.value.style.height =
      Math.min(
        textarea.value.scrollHeight,
        (Number.isFinite(height) ? height : textarea.value.scrollHeight) * 10,
      ) + 'px'
  },
  { flush: 'post', immediate: true },
)
defineExpose({
  focus() {
    textarea.value?.focus()
  },
})
</script>
<template>
  <MentionMenu
    v-if="!dismissed && mentionQuery !== undefined"
    :id="menuId + '-mentions'"
    :items="mentions"
    :selected="selected"
    :loading="loading"
    @select="emit('mention', $event)"
  />
  <SlashMenu
    v-else-if="!dismissed && commands.length"
    :id="menuId + '-commands'"
    :items="commands"
    :selected="selected"
    @select="emit('command', $event)"
  />
  <textarea
    ref="textarea"
    :value="modelValue"
    :role="menu() ? 'combobox' : undefined"
    :aria-expanded="menu() ? true : undefined"
    :aria-controls="menu() ? listId() : undefined"
    :aria-activedescendant="menu() ? listId() + '-option-' + selected : undefined"
    :placeholder="placeholder"
    :disabled="disabled"
    rows="1"
    :aria-label="$t('消息内容')"
    @input="emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)"
    @keydown="keydown"
    @focus="emit('focus')"
  />
</template>
<style scoped lang="scss">
textarea {
  display: block;
  width: 100%;
  max-height: calc(var(--size-26) * 10);
  min-height: var(--size-26);
  border: 0;
  outline: 0;
  padding: 0 0 var(--space-4);
  resize: none;
  color: var(--ink);
  font-size: var(--type-body);
  line-height: var(--leading-message);
  background: var(--transparent);
}
textarea::placeholder {
  color: var(--ink-3);
}
</style>
