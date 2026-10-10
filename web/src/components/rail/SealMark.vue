<script setup lang="ts">
import type { Verdict } from '@/api/events'
defineProps<{ verdict: Verdict }>()
</script>
<template>
  <span class="seal-mark" :class="{ denied: verdict === 'deny' }" :title="verdict === 'deny' ? $t('已驳回') : $t('已批准')">{{
    verdict === 'deny' ? $t('驳') : $t('准')
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
