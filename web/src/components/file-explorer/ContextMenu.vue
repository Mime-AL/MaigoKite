/**
 * 右键菜单组件
 *
 * 文件节点上的上下文菜单。
 */

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
  <div
    v-if="visible"
    class="context-menu"
    :style="{ left: x + 'px', top: y + 'px' }"
  >
    <ul>
      <li @click="emit('rename')">重命名</li>
      <li @click="emit('copy')">复制</li>
      <li @click="emit('paste')">粘贴</li>
      <li class="separator" @click="emit('delete')">删除</li>
    </ul>
  </div>
</template>

<style scoped lang="scss">
.context-menu {
  position: fixed;
  z-index: 1000;
  background: #fff;
  border: 1px solid #ddd;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  padding: 4px 0;
  min-width: 140px;
}

ul {
  list-style: none;
  margin: 0;
  padding: 0;
}

li {
  padding: 6px 16px;
  font-size: 13px;
  cursor: pointer;

  &:hover {
    background-color: #f0f0f0;
  }

  &.separator {
    border-top: 1px solid #eee;
    color: #dc3545;
  }
}
</style>
