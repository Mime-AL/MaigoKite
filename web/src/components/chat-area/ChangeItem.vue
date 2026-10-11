<script setup lang="ts">
import CodeBlock from '@/components/common/CodeBlock.vue'
defineProps<{
  change: {
    file_path: string
    status: 'accepted' | 'rejected' | 'pending' | 'modified'
    additions: number
    deletions: number
    diff?: string
  }
}>()
</script>

<template>
  <article class="change-item">
    <header>
      <code>{{ change.file_path }}</code><span class="add">+{{ change.additions }}</span><span class="del">−{{ change.deletions }}</span>
    </header>
    <CodeBlock
      v-if="change.diff"
      :content="change.diff"
      kind="diff"
    />
  </article>
</template>

<style scoped lang="scss">
.change-item {
  padding: var(--space-3) 0;
  border-bottom: var(--hairline) solid var(--rule);
}
.change-item:last-child {
  border-bottom: 0;
}
header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}
code {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  color: var(--ink-2);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  text-overflow: ellipsis;
  white-space: nowrap;
}
header span {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  font-variant-numeric: tabular-nums;
}
.add {
  color: var(--code-addition-ink);
}
.del {
  color: var(--code-deletion-ink);
}
</style>
