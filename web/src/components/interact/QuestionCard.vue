<script setup lang="ts">
import type { AwaitItem } from '@/api/events'
defineProps<{ item: AwaitItem }>()
</script>
<template>
  <article class="question-card">
    <strong>{{ item.title }}</strong>
    <p>{{ item.detail }}</p>
    <ul>
      <li v-for="option in item.options" :key="option.label">
        {{ option.label }}{{ option.recommended ? ' · 推荐' : '' }}
      </li>
    </ul>
    <small>请在对话中回复。</small>
  </article>
</template>
<style scoped lang="scss">
.question-card {
  border-left: 2px solid var(--wait);
  padding: 12px 16px;
  color: var(--ink);
  background: var(--paper-2);
  font-size: var(--text-sm);
}
small {
  color: var(--ink-3);
}
</style>
