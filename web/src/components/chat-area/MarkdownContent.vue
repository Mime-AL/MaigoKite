<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { assistantMarkdownBlocks } from '@/utils/markdown'
import CodeBlock from '@/components/common/CodeBlock.vue'
const props = withDefaults(defineProps<{ content: string; isStreaming?: boolean }>(), {
  isStreaming: false,
})
const displayed = ref(props.content)
let timer: ReturnType<typeof setTimeout> | undefined
// Keep parsing out of the per-token path; final text flushes immediately.
watch(
  () => [props.content, props.isStreaming],
  () => {
    if (!props.isStreaming) {
      if (timer) clearTimeout(timer)
      timer = undefined
      displayed.value = props.content
    } else if (!timer)
      timer = setTimeout(() => {
        timer = undefined
        displayed.value = props.content
      }, 100)
  },
)
const blocks = computed(() => assistantMarkdownBlocks(displayed.value))
onBeforeUnmount(() => {
  if (timer) clearTimeout(timer)
})
</script>
<template>
  <div class="markdown-content">
    <template
      v-for="(block, index) in blocks"
      :key="index"
    >
      <!-- Sanitized prose; fences render as literal Vue text, never raw HTML. -->
      <div
        v-if="block.kind === 'html'"
        class="markdown-prose"
        v-html="block.html"
      />
      <CodeBlock
        v-else
        :content="block.content"
        :language="block.language"
      />
    </template>
  </div>
</template>
<style scoped lang="scss">
@use '@/styles/markdown-content';
</style>
