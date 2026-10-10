<script setup lang="ts">
import type { Verdict } from '@/api/events'
defineProps<{ verdict: Verdict }>()
</script>
<template>
  <span class="seal-mark" :class="{ denied: verdict === 'deny' }" :title="verdict === 'deny' ? '已驳回' : '已批准'">{{
    verdict === 'deny' ? '驳' : '准'
  }}</span>
</template>
<style scoped lang="scss">
.seal-mark {
  display: inline-grid;
  width: 12px;
  height: 12px;
  place-content: center;
  font: var(--text-xs) var(--font-serif);
  color: var(--stone);
  border: 1px solid currentColor;
}
.denied {
  color: var(--seal);
}
</style>
