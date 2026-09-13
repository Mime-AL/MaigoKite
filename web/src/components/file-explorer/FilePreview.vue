/**
 * 文件预览组件
 *
 * 展示选中文件的缩略预览或基本信息。
 */

<script setup lang="ts">
defineProps<{
  node: {
    name: string
    path: string
    type: 'file' | 'directory'
    size?: number
    modified_at?: Date
  }
}>()
</script>

<template>
  <div class="file-preview">
    <h4>{{ node.name }}</h4>
    <dl>
      <dt>路径</dt>
      <dd>{{ node.path }}</dd>
      <dt v-if="node.size">大小</dt>
      <dd v-if="node.size">{{ node.size }} bytes</dd>
      <dt v-if="node.modified_at">修改时间</dt>
      <dd v-if="node.modified_at">{{ node.modified_at.toLocaleString() }}</dd>
    </dl>
  </div>
</template>

<style scoped lang="scss">
.file-preview {
  padding: 12px 16px;
  border-top: 1px solid #e0e0e0;
  background-color: #fff;
}

h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
}

dl {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 4px 12px;
  font-size: 12px;
}

dt {
  color: #666;
}

dd {
  margin: 0;
  color: #333;
  word-break: break-all;
}
</style>
