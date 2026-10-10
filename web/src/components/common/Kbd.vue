<script setup lang="ts">
defineProps<{ keys: string }>()
</script>
<template>
  <kbd>{{ keys }}</kbd>
</template>
<style scoped lang="scss">
kbd {
  border: 1px solid var(--rule);
  border-radius: var(--radius-sm);
  padding: 2px 5px;
  font: var(--text-xs) var(--font-mono);
  color: var(--ink-2);
  background: var(--paper-2);
}
</style>
