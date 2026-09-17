<script setup lang="ts">
import IconSymbol from '@/components/common/IconSymbol.vue'
import MarkdownContent from './MarkdownContent.vue'

withDefaults(
  defineProps<{
    content: string
    assistantName?: string
    timestamp?: Date
    isStreaming?: boolean
  }>(),
  { assistantName: '助手' },
)
</script>

<template>
  <article class="message agent-message">
    <div class="avatar"><IconSymbol name="sparkles" :size="14" /></div>
    <div class="message-body">
      <div class="message-meta">
        <strong>{{ assistantName }}</strong
        ><time v-if="timestamp">{{
          timestamp.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
        }}</time>
      </div>
      <MarkdownContent class="message-content" :content="content" />
      <div v-if="isStreaming" class="streaming-indicator" aria-label="正在生成">
        <i /><i /><i />
      </div>
    </div>
  </article>
</template>

<style scoped lang="scss">
.agent-message {
  content-visibility: auto;
  contain-intrinsic-size: auto 96px;
  display: grid;
  grid-template-columns: 29px minmax(0, 1fr);
  gap: 11px;
  margin: 0 0 26px;
}
.avatar {
  display: grid;
  width: 29px;
  height: 29px;
  place-items: center;
  border-radius: 10px;
  color: #fff;
  background: linear-gradient(145deg, #687ff2, #946bdf);
  box-shadow: 0 5px 12px rgba(100, 93, 205, 0.18);
}
.message-body {
  min-width: 0;
  padding-top: 1px;
}
.message-meta {
  display: flex;
  align-items: baseline;
  gap: 7px;
  margin-bottom: 7px;
}
.message-meta strong {
  font-size: 11.5px;
  font-weight: 680;
}
.message-meta time {
  color: var(--text-tertiary);
  font-size: 8.5px;
}
.message-content {
  min-width: 0;
}
.streaming-indicator {
  display: flex;
  gap: 3px;
  margin-top: 8px;
}
.streaming-indicator i {
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--primary-color);
  animation: pulse 1.2s infinite ease-in-out;
}
.streaming-indicator i:nth-child(2) {
  animation-delay: 120ms;
}
.streaming-indicator i:nth-child(3) {
  animation-delay: 240ms;
}
@keyframes pulse {
  0%,
  70%,
  100% {
    opacity: 0.22;
    transform: translateY(0);
  }
  35% {
    opacity: 1;
    transform: translateY(-2px);
  }
}
</style>
