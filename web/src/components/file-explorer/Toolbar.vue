/**
 * 文件管理器工具栏组件
 *
 * 提供新建、刷新等操作按钮。
 */

<script setup lang="ts">
const emit = defineEmits<{
  (e: 'new-file'): void
  (e: 'new-folder'): void
  (e: 'refresh'): void
}>()
</script>

<template>
  <div class="toolbar">
    <button @click="emit('new-file')" title="新建文件">+ 文件</button>
    <button @click="emit('new-folder')" title="新建文件夹">+ 文件夹</button>
    <button @click="emit('refresh')" title="刷新">刷新</button>
  </div>
</template>

<style scoped lang="scss">
.toolbar {
  display: flex;
  gap: 4px;
  padding: 8px 12px;
  border-bottom: 1px solid #e0e0e0;
  background-color: #f5f5f5;
}

button {
  padding: 4px 8px;
  font-size: 12px;
  border: 1px solid #ddd;
  border-radius: 3px;
  background: #fff;
  cursor: pointer;

  &:hover {
    background-color: #e8e8e8;
  }
}
</style>
