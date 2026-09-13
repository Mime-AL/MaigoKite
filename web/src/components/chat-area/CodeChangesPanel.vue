/**
 * 代码更改面板组件
 *
 * 展示 Agent 发起的文件修改列表，支持接受/拒绝。
 */

<script setup lang="ts">
import ChangeItem from './ChangeItem.vue'

defineProps<{
  changes?: Array<{
    file_path: string
    status: 'accepted' | 'rejected' | 'pending' | 'modified'
    additions: number
    deletions: number
    diff?: string
  }>
}>()
</script>

<template>
  <div class="code-changes-panel">
    <h3>代码更改</h3>
    <ChangeItem
      v-for="(change, index) in changes"
      :key="index"
      :change="change"
    />
  </div>
</template>

<style scoped lang="scss">
.code-changes-panel {
  padding: 12px 16px;
  border-top: 1px solid #e0e0e0;
  background-color: #fafafa;

  h3 {
    font-size: 14px;
    margin-bottom: 8px;
  }
}
</style>
