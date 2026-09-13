/**
 * 用户消息组件
 *
 * 渲染用户发送的文本消息。
 */

<script setup lang="ts">
defineProps<{
  content: string
  timestamp?: Date
}>()
</script>

<template>
  <div class="message user-message">
    <div class="message-content">{{ content }}</div>
    <div class="message-time" v-if="timestamp">{{ timestamp.toLocaleTimeString() }}</div>
  </div>
</template>

<style scoped lang="scss">
.user-message {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  margin-bottom: 16px;
}

.message-content {
  max-width: 70%;
  padding: 10px 14px;
  background-color: #0066cc;
  color: #fff;
  border-radius: 12px 12px 0 12px;
  white-space: pre-wrap;
}

.message-time {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}
</style>
