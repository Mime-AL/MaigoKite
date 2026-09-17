<script setup lang="ts">
withDefaults(defineProps<{ size?: number; message?: string }>(), { size: 18 })
</script>

<template>
  <div class="loading-spinner" :class="{ horizontal: message }">
    <span class="spinner" :style="{ width: `${size}px`, height: `${size}px` }" />
    <span v-if="message">{{ message }}</span>
  </div>
</template>

<style scoped lang="scss">
.loading-spinner { display: flex; align-items: center; justify-content: center; gap: 9px; padding: 16px; color: var(--text-tertiary); font-size: 11px; }
.spinner { display: block; border: 2px solid var(--border-strong); border-top-color: var(--primary-color); border-radius: 50%; animation: spin 700ms linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
</style>
