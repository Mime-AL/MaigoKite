/**
 * Agent 消息组件
 *
 * 渲染 Agent 回复的文本消息，支持流式输出。
 */

<script setup lang="ts">
defineProps<{
  content: string
  timestamp?: Date
  isStreaming?: boolean
}>()
</script>

<template>
  <div class="message agent-message">
    <div class="message-content">{{ content }}</div>
    <div class="message-time" v-if="timestamp">{{ timestamp.toLocaleTimeString() }}</div>
    <div class="streaming-indicator" v-if="isStreaming">...</div>
  </div>
</template>

<style scoped lang="scss">
.agent-message {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  margin-bottom: 16px;
}

.message-content {
  max-width: 70%;
  padding: 10px 14px;
  background-color: #f0f0f0;
  border-radius: 12px 12px 12px 0;
  white-space: pre-wrap;
}

.message-time {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.streaming-indicator {
  font-size: 12px;
  color: #999;
  animation: pulse 1.5s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
</style>
