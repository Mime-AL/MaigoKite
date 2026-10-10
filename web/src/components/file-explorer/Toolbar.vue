<script setup lang="ts">
import IconSymbol from '@/components/common/IconSymbol.vue'
const emit = defineEmits<{ (event: 'refresh'): void }>()
</script>

<template>
  <div class="toolbar">
    <span><IconSymbol name="folder" :size="14" />项目根目录</span
    ><button class="icon-button" type="button" title="刷新" @click="emit('refresh')">
      <IconSymbol name="refresh" :size="15" />
    </button>
  </div>
</template>

<style scoped lang="scss">
.toolbar {
  display: flex;
  height: 39px;
  flex: none;
  align-items: center;
  justify-content: space-between;
  padding: 0 10px 0 16px;
  border-block: 1px solid var(--border-color);
}
.toolbar > span {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 7px;
  overflow: hidden;
  color: var(--text-secondary);
  font-size: var(--text-xs);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.icon-button {
  width: 28px;
  height: 28px;
}
</style>
