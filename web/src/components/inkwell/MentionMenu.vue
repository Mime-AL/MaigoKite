<script setup lang="ts">
export interface Mention {
  id: string
  kind: '文件' | '会话' | '记忆'
  label: string
  value: string
}
defineProps<{ items: Mention[]; selected: number; loading?: boolean }>()
const emit = defineEmits<{ (event: 'select', item: Mention): void }>()
</script>
<template>
  <div class="mention-menu" role="listbox" :aria-label="$t('引用')">
    <p v-if="loading">{{ $t('正在查找…') }}</p>
    <p v-else-if="!items.length">{{ $t('没有找到相关内容') }}</p>
    <button
      v-for="(item, index) in items"
      :key="item.id"
      role="option"
      :aria-selected="index === selected"
      @mousedown.prevent
      @click="emit('select', item)"
    >
      <small>{{ $t(item.kind) }}</small
      ><span>{{ item.label }}</span>
    </button>
  </div>
</template>
<style scoped lang="scss">
@use '@/styles/mixins' as mixins;
.mention-menu {
  position: absolute;
  bottom: calc(100% + 8px);
  left: 0;
  right: 0;
  max-height: 280px;
  overflow: auto;
  padding: 6px;
  border: 1px solid var(--rule);
  border-radius: var(--radius-md);
  background: var(--paper);
  box-shadow: var(--shadow-float);
  z-index: 10;
}
button {
  @include mixins.interactive-row;
  display: flex;
  width: 100%;
  align-items: center;
  gap: 12px;
  border: 0;
  padding: 10px;
  text-align: left;
  color: var(--ink-2);
  background: var(--transparent);
  font-size: var(--text-sm);
}
button[aria-selected='true'] {
  background: var(--accent-selected);
}
small {
  color: var(--ink-3);
  font-size: var(--text-xs);
}
span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
p {
  margin: 10px;
  color: var(--ink-3);
  font-size: var(--text-sm);
}
</style>
