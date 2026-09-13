/**
 * 终端输出组件
 *
 * 以终端样式展示文本输出。
 */

<script setup lang="ts">
defineProps<{
  content: string
  title?: string
}>()
</script>

<template>
  <div class="terminal-output">
    <div class="terminal-header" v-if="title">{{ title }}</div>
    <pre class="terminal-body">{{ content }}</pre>
  </div>
</template>

<style scoped lang="scss">
.terminal-output {
  border: 1px solid #ddd;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.terminal-header {
  padding: 4px 12px;
  background-color: #333;
  color: #ccc;
  font-size: 12px;
}

.terminal-body {
  padding: 12px;
  margin: 0;
  background-color: #1e1e1e;
  color: #d4d4d4;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  white-space: pre-wrap;
  max-height: 300px;
  overflow-y: auto;
}
</style>
