<script setup lang="ts">
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
      <code>{{ change.file_path }}</code
      ><span class="add">+{{ change.additions }}</span
      ><span class="del">−{{ change.deletions }}</span>
    </header>
    <pre v-if="change.diff">{{ change.diff }}</pre>
  </article>
</template>

<style scoped lang="scss">
.change-item {
  padding: 9px 0;
  border-bottom: 1px solid var(--border-color);
}
.change-item:last-child {
  border-bottom: 0;
}
header {
  display: flex;
  align-items: center;
  gap: 8px;
}
code {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  text-overflow: ellipsis;
  white-space: nowrap;
}
header span {
  font-family: var(--font-mono);
  font-size: var(--text-xs);
}
.add {
  color: var(--success);
}
.del {
  color: var(--danger);
}
pre {
  margin: 9px 0 0;
  padding: 11px;
  overflow: auto;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  background: var(--surface-strong);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: var(--leading-normal);
  white-space: pre-wrap;
}
</style>
