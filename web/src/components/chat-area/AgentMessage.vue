<script setup lang="ts">
import MarkdownContent from './MarkdownContent.vue'
import Pulse from '@/components/shell/Pulse.vue'
withDefaults(defineProps<{ content: string; assistantName?: string; timestamp?: Date; isStreaming?: boolean }>(), {
  assistantName: '助手',
  isStreaming: false,
})
</script>
<template>
  <article class="agent-message">
    <header>
      <strong>{{ assistantName }}</strong
      ><time v-if="timestamp">{{ timestamp.toLocaleTimeString($i18n.locale, { hour: '2-digit', minute: '2-digit' }) }}</time
      ><Pulse v-if="isStreaming" state="thinking" />
    </header>
    <MarkdownContent :content="content" :is-streaming="isStreaming" />
  </article>
</template>
<style scoped lang="scss">
.agent-message {
  min-width: 0;
  padding: 6px 0 20px;
}
header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}
strong {
  font-size: var(--text-xs);
  color: var(--ink-2);
  font-weight: var(--weight-medium);
}
time {
  font-size: var(--text-xs);
  color: var(--ink-3);
}
</style>
