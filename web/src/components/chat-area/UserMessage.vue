<script setup lang="ts">
defineProps<{ content: string; timestamp?: Date }>()
</script>

<template>
  <article class="message user-message">
    <div class="message-content">{{ content }}</div>
    <time v-if="timestamp">{{ timestamp.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) }}</time>
  </article>
</template>

<style scoped lang="scss">
.user-message { content-visibility: auto; contain-intrinsic-size: auto 72px; display: flex; align-items: flex-end; flex-direction: column; margin: 0 0 24px; }
.message-content { max-width: min(78%, 590px); padding: 11px 15px; border-radius: 18px 18px 5px 18px; color: #fff; background: linear-gradient(160deg, #1688f8, #0068d6); box-shadow: 0 7px 18px rgba(0, 113, 227, 0.15); font-size: 13px; line-height: 1.55; white-space: pre-wrap; word-break: break-word; }
time { margin: 5px 4px 0; color: var(--text-tertiary); font-size: 8.5px; }
</style>
