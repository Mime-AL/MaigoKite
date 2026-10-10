<script setup lang="ts">
withDefaults(defineProps<{ size?: number; message?: string }>(), { size: 18 })
</script>

<template>
  <div class="loading-spinner" :class="{ horizontal: message }">
    <span class="spinner" :style="{ width: `${size * 2}px` }" role="status" :aria-label="message || $t('正在读取')"><i /></span>
    <span v-if="message">{{ message }}</span>
  </div>
</template>

<style scoped lang="scss">
.loading-spinner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-4);
  padding: var(--space-5);
  color: var(--text-secondary);
  font-size: var(--text-xs);
}
.spinner {
  display: block;
  height: var(--ink-loader-height);
  overflow: hidden;
  background: var(--rule);
  border-radius: var(--radius-pill);
}
.spinner i { display: block; width: var(--ink-loader-segment); height: 100%; background: var(--accent); animation: ink-load var(--motion-pulse) var(--ease) infinite; }
</style>
