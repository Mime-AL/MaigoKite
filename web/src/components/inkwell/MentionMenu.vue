<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
export interface Mention {
  id: string
  kind: '文件' | '会话' | '记忆'
  label: string
  value: string
}
const props = withDefaults(
  defineProps<{ items: Mention[]; selected: number; loading?: boolean; id?: string }>(),
  { id: 'inkwell-mentions' },
)
const emit = defineEmits<{ (event: 'select', item: Mention): void }>()
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
    class="mention-menu"
    role="listbox"
    :aria-label="$t('引用')"
  >
    <p v-if="loading">
      {{ $t('正在查找…') }}
    </p>
    <p v-else-if="!items.length">
      {{ $t('没有找到相关内容') }}
    </p>
    <button
      v-for="(item, index) in items"
      :id="id + '-option-' + index"
      :key="item.id"
      role="option"
      :aria-selected="index === selected"
      @mousedown.prevent
      @click="emit('select', item)"
    >
      <small>{{ $t(item.kind) }}</small><span>{{ item.label }}</span><kbd v-if="index < 9">{{ index + 1 }}</kbd>
    </button>
    <footer v-if="items.length">
      {{ $t('↑ ↓ 选择 · Enter 确认 · Alt + 数字') }}
    </footer>
  </div>
</template>
<style scoped lang="scss">
@use '@/styles/composer-menu';
</style>
