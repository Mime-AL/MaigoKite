/**
 * 加载动画组件
 *
 * 通用的旋转加载指示器。
 */

<script setup lang="ts">
defineProps<{
  size?: number
  message?: string
}>()
</script>

<template>
  <div class="loading-spinner" :class="{ with_message: message }">
    <div class="spinner" :style="{ width: size + 'px', height: size + 'px' }" />
    <span class="loading-text" v-if="message">{{ message }}</span>
  </div>
</template>

<style scoped lang="scss">
.loading-spinner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px;
  color: #999;
}

.with_message {
  flex-direction: row;
}

.spinner {
  border: 3px solid #e0e0e0;
  border-top-color: #0066cc;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  font-size: 13px;
}
</style>
