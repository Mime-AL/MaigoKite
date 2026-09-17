<script setup lang="ts">
import { computed } from 'vue'
import { renderAssistantMarkdown } from '@/utils/markdown'

const props = defineProps<{ content: string }>()
const renderedContent = computed(() => renderAssistantMarkdown(props.content))
</script>

<template>
  <!-- renderAssistantMarkdown sanitizes the generated HTML before it reaches v-html. -->
  <div class="markdown-content" v-html="renderedContent" />
</template>

<style scoped lang="scss">
.markdown-content {
  color: var(--text-primary);
  font-size: 13px;
  line-height: 1.68;
  overflow-wrap: anywhere;
}

.markdown-content :deep(> :first-child) {
  margin-top: 0;
}
.markdown-content :deep(> :last-child) {
  margin-bottom: 0;
}
.markdown-content :deep(p) {
  margin: 0 0 10px;
}
.markdown-content :deep(h1),
.markdown-content :deep(h2),
.markdown-content :deep(h3),
.markdown-content :deep(h4) {
  margin: 20px 0 9px;
  color: var(--text-primary);
  line-height: 1.35;
  letter-spacing: -0.018em;
}
.markdown-content :deep(h1) {
  font-size: 21px;
}
.markdown-content :deep(h2) {
  font-size: 18px;
}
.markdown-content :deep(h3) {
  font-size: 15px;
}
.markdown-content :deep(h4) {
  font-size: 13px;
}
.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin: 8px 0 12px;
  padding-left: 24px;
}
.markdown-content :deep(li) {
  margin: 4px 0;
  padding-left: 2px;
}
.markdown-content :deep(li > p) {
  margin: 0;
}
.markdown-content :deep(blockquote) {
  margin: 12px 0;
  padding: 2px 0 2px 13px;
  border-left: 3px solid var(--border-strong);
  color: var(--text-secondary);
}
.markdown-content :deep(blockquote p) {
  margin: 0;
}
.markdown-content :deep(a) {
  color: var(--primary-color);
  text-decoration: none;
}
.markdown-content :deep(a:hover) {
  text-decoration: underline;
}
.markdown-content :deep(code) {
  padding: 2px 5px;
  border-radius: 5px;
  color: var(--text-primary);
  background: var(--surface-strong);
  font-family: var(--font-mono);
  font-size: 0.9em;
}
.markdown-content :deep(pre) {
  max-width: 100%;
  margin: 12px 0;
  padding: 12px 14px;
  overflow: auto;
  border: 1px solid var(--border-color);
  border-radius: 11px;
  background: var(--surface-muted);
}
.markdown-content :deep(pre code) {
  padding: 0;
  border-radius: 0;
  background: transparent;
  font-size: 11px;
  line-height: 1.6;
  white-space: pre;
}
.markdown-content :deep(table) {
  display: block;
  max-width: 100%;
  margin: 12px 0;
  overflow-x: auto;
  border-collapse: collapse;
}
.markdown-content :deep(th),
.markdown-content :deep(td) {
  padding: 7px 10px;
  border: 1px solid var(--border-color);
  text-align: left;
}
.markdown-content :deep(th) {
  background: var(--surface-muted);
  font-weight: 650;
}
.markdown-content :deep(hr) {
  margin: 18px 0;
  border: 0;
  border-top: 1px solid var(--border-color);
}
</style>
