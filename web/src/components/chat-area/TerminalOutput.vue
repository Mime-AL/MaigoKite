<script setup lang="ts">
defineProps<{ content: string; title?: string }>()
</script>

<template>
  <div class="terminal-output">
    <header>
      <span class="dots"><i /><i /><i /></span><strong v-if="title">{{ title }}</strong>
    </header>
    <pre>{{ content }}</pre>
  </div>
</template>

<style scoped lang="scss">
.terminal-output {
  margin-bottom: 8px;
  overflow: hidden;
  border: 1px solid var(--paper-3);
  border-radius: var(--radius-md);
  background: var(--ink);
  box-shadow: var(--shadow-card);
}
header {
  display: flex;
  height: 31px;
  align-items: center;
  gap: 10px;
  padding: 0 11px;
  border-bottom: 1px solid var(--paper-3);
  color: var(--ink-2);
}
header strong {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: var(--weight-medium);
}
.dots {
  display: flex;
  gap: 4px;
}
.dots i {
  width: 6px;
  height: 6px;
  border-radius: var(--radius-round);
  background: var(--ink-2);
}
.dots i:first-child {
  background: var(--ink-2);
}
.dots i:nth-child(2) {
  background: var(--ink-2);
}
.dots i:last-child {
  background: var(--ink);
}
pre {
  max-height: 290px;
  margin: 0;
  padding: 13px;
  overflow: auto;
  color: var(--ink-2);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: var(--leading-normal);
  white-space: pre-wrap;
}
</style>
