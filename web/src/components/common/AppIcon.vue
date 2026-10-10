<script setup lang="ts">
// Let Vite resolve the URL for both nested browser routes and Electron file:// pages.
import source from '/brand/app-icon-cat-ribbon-v1.png?url'

withDefaults(defineProps<{ size?: number; alt?: string }>(), {
  size: 28,
  alt: 'MaigoKite',
})
</script>

<template>
  <img
    class="app-icon"
    :src="source"
    :alt="alt"
    :width="size"
    :height="size"
    :draggable="false"
    decoding="async"
  />
</template>

<style scoped lang="scss">
.app-icon {
  display: block;
  flex: none;
  object-fit: contain;
  user-select: none;
}
</style>
