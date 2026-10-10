<script setup lang="ts">
defineProps<{ content: string; timestamp?: Date }>()
</script>
<template>
  <article class="user-message">
    <p>{{ content }}</p>
    <time v-if="timestamp">{{ timestamp.toLocaleTimeString($i18n.locale, { hour: '2-digit', minute: '2-digit' }) }}</time>
  </article>
</template>
<style scoped lang="scss">
.user-message {
  margin: 12px 0 24px 60px;
  display: flex;
  align-items: flex-end;
  flex-direction: column;
}
p {
  max-width: 90%;
  padding: 12px 16px;
  margin: 0;
  border-radius: var(--radius-md);
  background: var(--paper-3);
  color: var(--ink);
  font-size: var(--text-md);
  line-height: var(--leading-body);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
time {
  color: var(--ink-3);
  margin-top: 6px;
  font-size: var(--text-xs);
}
</style>
