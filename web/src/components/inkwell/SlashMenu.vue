<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
export interface SlashCommand {
  id: string
  label: string
}
const props = withDefaults(
  defineProps<{ items: SlashCommand[]; selected: number; id?: string }>(),
  { id: 'inkwell-commands' },
)
const emit = defineEmits<{ (event: 'select', item: SlashCommand): void }>()
const menu = ref<HTMLElement | null>(null)
watch(
  () => [props.selected, props.items.length],
  async () => {
    await nextTick()
    menu.value
      ?.querySelector<HTMLElement>('[aria-selected="true"]')
      ?.scrollIntoView?.({ block: 'nearest' })
  },
  { immediate: true, flush: 'post' },
)
</script>
<template>
  <div
    :id="id"
    ref="menu"
    class="slash-menu"
    role="listbox"
    :aria-label="$t('命令')"
  >
    <button
      v-for="(item, index) in items"
      :id="id + '-option-' + index"
      :key="item.id"
      role="option"
      :aria-selected="index === selected"
      @mousedown.prevent
      @click="emit('select', item)"
    >
      <code>/{{ item.id }}</code><span>{{ $t(item.label) }}</span><kbd v-if="index < 9">{{ index + 1 }}</kbd>
    </button>
    <footer>{{ $t('↑ ↓ 选择 · Enter 确认 · Alt + 数字') }}</footer>
  </div>
</template>
<style scoped lang="scss">
@use '@/styles/composer-menu';
</style>
