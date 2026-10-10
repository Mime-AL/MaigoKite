/** * 右键菜单组件 * * 文件节点上的上下文菜单。 */

<script setup lang="ts">
defineProps<{
  visible: boolean
  x: number
  y: number
}>()

const emit = defineEmits<{
  (e: 'rename'): void
  (e: 'delete'): void
  (e: 'copy'): void
  (e: 'paste'): void
}>()
</script>

<template>
  <div v-if="visible" class="context-menu" :style="{ left: x + 'px', top: y + 'px' }">
    <ul>
      <li @click="emit('rename')">{{ $t('重命名') }}</li>
      <li @click="emit('copy')">{{ $t('复制') }}</li>
      <li @click="emit('paste')">{{ $t('粘贴') }}</li>
      <li class="separator" @click="emit('delete')">{{ $t('删除') }}</li>
    </ul>
  </div>
</template>

<style scoped lang="scss">
.context-menu {
  position: fixed;
  z-index: 1000;
  min-width: 150px;
  padding: 5px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  background: var(--surface);
  box-shadow: var(--shadow-float);
  backdrop-filter: var(--blur);
}

ul {
  list-style: none;
  margin: 0;
  padding: 0;
}

li {
  padding: 7px 11px;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: var(--text-xs);
  cursor: pointer;

  &:hover {
    color: var(--text-primary);
    background: var(--surface-strong);
  }

  &.separator {
    margin-top: 4px;
    padding-top: 8px;
    border-top: 1px solid var(--border-color);
    border-radius: var(--radius-none) var(--radius-none) var(--radius-sm) var(--radius-sm);
    color: var(--danger);
  }
}
</style>
