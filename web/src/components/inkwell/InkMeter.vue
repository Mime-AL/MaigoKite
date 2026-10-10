<script setup lang="ts">
defineProps<{ value: number | null }>()
</script>
<template>
  <span class="ink-meter" :title="value === null ? '当前服务未提供上下文占用' : `上下文 ${value}%`"
    ><i><b :style="{ width: value === null ? '0%' : `${Math.min(100, Math.max(0, value))}%` }" /></i
    ><small>{{ value === null ? '—' : `${value}%` }}</small></span
  >
</template>
<style scoped lang="scss">
.ink-meter {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--ink-3);
}
i {
  width: 38px;
  height: 3px;
  background: var(--rule);
}
b {
  display: block;
  height: 100%;
  background: var(--ink-2);
}
small {
  font-size: var(--text-xs);
}
</style>
