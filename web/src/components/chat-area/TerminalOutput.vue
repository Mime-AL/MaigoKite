<script setup lang="ts">
defineProps<{ content: string; title?: string }>()
</script>

<template>
  <div class="terminal-output">
    <header><span class="dots"><i /><i /><i /></span><strong v-if="title">{{ title }}</strong></header>
    <pre>{{ content }}</pre>
  </div>
</template>

<style scoped lang="scss">
.terminal-output { margin-bottom: 8px; overflow: hidden; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; background: #17181c; box-shadow: inset 0 1px rgba(255, 255, 255, 0.04); }
header { display: flex; height: 31px; align-items: center; gap: 10px; padding: 0 11px; border-bottom: 1px solid rgba(255, 255, 255, 0.06); color: #8b8d95; }
header strong { font-family: var(--font-mono); font-size: 9px; font-weight: 500; }
.dots { display: flex; gap: 4px; }
.dots i { width: 6px; height: 6px; border-radius: 50%; background: #4f5158; }
.dots i:first-child { background: #ff6259; }.dots i:nth-child(2) { background: #ffbd2e; }.dots i:last-child { background: #28c840; }
pre { max-height: 290px; margin: 0; padding: 13px; overflow: auto; color: #d4d7df; font-family: var(--font-mono); font-size: 10px; line-height: 1.55; white-space: pre-wrap; }
</style>
