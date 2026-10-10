<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps<{ nodes: { id: string; turnId: string }[] }>()
const emit = defineEmits<{ (event: 'jump', node: { id: string; turnId: string }): void }>()
const buckets = computed(() => {
  const total = Math.min(80, props.nodes.length)
  return Array.from({ length: total }, (_, index) => {
    const start = Math.floor((index * props.nodes.length) / total),
      end = Math.floor(((index + 1) * props.nodes.length) / total)
    return { node: props.nodes[start], density: Math.min(1, (end - start) / 5 + 0.15), top: (index * 100) / total }
  })
})
</script>
<template>
  <nav v-if="nodes.length" class="rail-minimap" :aria-label="$t('墨线缩略图')">
    <button
      v-for="(bucket, index) in buckets"
      :key="index"
      :style="{ top: `${bucket.top}%`, opacity: bucket.density }"
      :aria-label="$t('跳到步骤 {0}', [index + 1])"
      @click="emit('jump', bucket.node)"
    />
  </nav>
</template>
<style scoped lang="scss">
.rail-minimap {
  position: absolute;
  right: 2px;
  top: 18px;
  bottom: 18px;
  width: 8px;
  z-index: 3;
}
button {
  position: absolute;
  width: 6px;
  height: 5px;
  border: 0;
  border-radius: var(--radius-sm);
  padding: 0;
  background: var(--ink-2);
}
button:hover {
  background: var(--accent);
}
</style>
