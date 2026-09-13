/**
 * 单个文件更改组件
 *
 * 展示单个文件的增删行数和 diff 预览。
 */

<script setup lang="ts">
defineProps<{
  change: {
    file_path: string
    status: 'accepted' | 'rejected' | 'pending' | 'modified'
    additions: number
    deletions: number
    diff?: string
  }
}>()
</script>

<template>
  <div class="change-item">
    <div class="change-header">
      <span class="file-path">{{ change.file_path }}</span>
      <span class="change-stats">+{{ change.additions }} -{{ change.deletions }}</span>
    </div>
    <div class="change-diff" v-if="change.diff">
      <pre>{{ change.diff }}</pre>
    </div>
  </div>
</template>

<style scoped lang="scss">
.change-item {
  padding: 8px 12px;
  border-bottom: 1px solid #eee;
  font-size: 13px;
}

.change-header {
  display: flex;
  justify-content: space-between;
}

.file-path {
  font-family: monospace;
}

.change-stats {
  color: #666;
}

.change-diff {
  margin-top: 8px;
  padding: 8px;
  background-color: #f5f5f5;
  border-radius: 4px;
  overflow-x: auto;
}

pre {
  margin: 0;
  white-space: pre-wrap;
  font-family: monospace;
  font-size: 12px;
}
</style>
