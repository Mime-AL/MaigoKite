<script setup lang="ts">
import type { FileTreeNode } from '@/composables/useFileTree'
import IconSymbol from '@/components/common/IconSymbol.vue'

const props = defineProps<{ node: FileTreeNode; depth: number; selectedPath?: string }>()
const emit = defineEmits<{ (event: 'expand' | 'select', node: FileTreeNode): void }>()

function select() {
  emit('select', props.node)
  if (props.node.type === 'directory') {
    emit('expand', props.node)
  }
}
</script>

<template>
  <div class="file-node">
    <button
      type="button"
      :class="{ selected: node.path === selectedPath }"
      :aria-pressed="node.path === selectedPath"
      :title="node.path"
      :aria-expanded="node.type === 'directory' ? Boolean(node.expanded) : undefined"
      :aria-busy="node.loading || undefined"
      :style="{ paddingLeft: `${8 + depth * 14}px` }"
      @click="select"
    >
      <IconSymbol
        v-if="node.type === 'directory'"
        name="chevron"
        :size="12"
        class="chevron"
        :class="{ expanded: node.expanded }"
      /><span v-else class="spacer" /><IconSymbol
        :name="node.type === 'directory' ? 'folder' : 'file'"
        :size="15"
      /><span>{{ node.name }}</span>
    </button>
    <div v-if="node.type === 'directory' && node.expanded">
      <p v-if="node.loading" class="empty-copy">{{ $t('正在读取…') }}</p>
      <p v-else-if="node.loaded && !node.children?.length" class="empty-copy">{{ $t('空文件夹') }}</p>
      <FileNode
        v-for="child in node.children || []"
        :key="child.path"
        :node="child"
        :depth="depth + 1"
        :selected-path="selectedPath"
        @expand="emit('expand', $event)"
        @select="emit('select', $event)"
      />
    </div>
  </div>
</template>

<style scoped lang="scss">
@use '@/styles/mixins' as mixins;
.file-node button {
  @include mixins.interactive-row;
  display: flex;
  width: 100%;
  height: 32px;
  align-items: center;
  gap: 6px;
  padding-right: 8px;
  border: 0;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  background: var(--transparent);
  cursor: pointer;
  text-align: left;
}
.file-node button.selected { background: var(--accent-selected); color: var(--accent); }
.file-node button span:last-child {
  overflow: hidden;
  font-size: var(--text-xs);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.chevron {
  transition: transform var(--motion-fast) var(--ease);
}
.chevron.expanded {
  transform: rotate(90deg);
}
.spacer {
  width: 12px;
  flex: none;
}
</style>
