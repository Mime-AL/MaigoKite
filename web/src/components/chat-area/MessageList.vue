/**
 * 消息列表组件
 *
 * 遍历渲染用户消息和 Agent 消息。
 */

<script setup lang="ts">
import UserMessage from './UserMessage.vue'
import AgentMessage from './AgentMessage.vue'

defineProps<{
  sessionId: string
}>()
</script>

<template>
  <div class="message-list">
    <!-- 消息内容由父组件传入或通过 store 获取 -->
    <slot :name="'messages'">
      <p class="placeholder">暂无消息</p>
    </slot>
  </div>
</template>

<style scoped lang="scss">
.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.placeholder {
  color: #999;
  text-align: center;
  padding: 48px 0;
}
</style>
