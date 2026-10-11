<script setup lang="ts">
import MessageActions from './MessageActions.vue'
defineProps<{ content: string; timestamp?: Date }>()
</script>
<template>
  <article class="user-message">
    <p>{{ content }}</p>
    <time v-if="timestamp">{{
      timestamp.toLocaleTimeString($i18n.locale, { hour: '2-digit', minute: '2-digit' })
    }}</time>
    <MessageActions :content="content" />
  </article>
</template>
<style scoped lang="scss">
.user-message {
  margin: var(--space-4) 0 var(--space-7) calc(var(--rail-width) + var(--space-4));
  display: flex;
  align-items: flex-end;
  flex-direction: column;
}
p {
  max-width: 90%;
  padding: var(--space-4) var(--space-5);
  margin: 0;
  border-radius: var(--radius-md);
  background: var(--paper-3);
  color: var(--ink);
  font-size: var(--type-body);
  line-height: var(--leading-message);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
time {
  color: var(--ink-3);
  margin-top: var(--size-6);
  font-size: var(--text-xs);
}
</style>
