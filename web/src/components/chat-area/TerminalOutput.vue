<script setup lang="ts">
import CodeBlock from '@/components/common/CodeBlock.vue'
defineProps<{ content: string; title?: string }>()
</script>
<template>
  <CodeBlock
    class="terminal-output"
    :content="content"
    :title="title"
    kind="terminal"
  />
</template>
