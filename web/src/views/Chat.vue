/**
 * 对话页
 *
 * 展示消息列表、工具输出、代码更改面板和输入框。
 */

<script setup lang="ts">
import { useRoute } from 'vue-router'
import MessageList from '@/components/chat-area/MessageList.vue'
import InputBox from '@/components/chat-area/InputBox.vue'
import CodeChangesPanel from '@/components/chat-area/CodeChangesPanel.vue'
import ToolOutputPanel from '@/components/chat-area/ToolOutputPanel.vue'
import StepStatusPanel from '@/components/chat-area/StepStatusPanel.vue'
import TaskViewPanel from '@/components/chat-area/TaskViewPanel.vue'

const route = useRoute()
const sessionId = route.params.id as string
</script>

<template>
  <div class="chat-page">
    <StepStatusPanel />
    <TaskViewPanel />
    <MessageList :session-id="sessionId" />
    <CodeChangesPanel />
    <ToolOutputPanel />
    <InputBox :session-id="sessionId" />
  </div>
</template>

<style scoped lang="scss">
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100%;
}
</style>
