<script setup lang="ts">
import { nextTick, onMounted, ref, watch } from 'vue'
import type { FileTreeNode } from '@/composables/useFileTree'
import FileNode from './FileNode.vue'
const props = defineProps<{ nodes?: FileTreeNode[]; selectedPath?: string }>()
const emit = defineEmits<{ (event: 'expand' | 'select', node: FileTreeNode): void }>()
const tree = ref<HTMLElement | null>(null)
function rows() {
  return Array.from(
    tree.value?.querySelectorAll<HTMLButtonElement>('[data-tree-item]') || [],
  ).filter((row) => row.getClientRects().length > 0)
}
function findNode(path: string, nodes = props.nodes || []): FileTreeNode | undefined {
  for (const node of nodes) {
    if (node.path === path) return node
    const found = findNode(path, node.children || [])
    if (found) return found
  }
}
function focus(row?: HTMLButtonElement) {
  if (!row) return
  for (const item of rows()) item.tabIndex = item === row ? 0 : -1
  row.focus({ preventScroll: true })
  row.scrollIntoView({ block: 'nearest' })
}
async function ensureEntry() {
  await nextTick()
  const list = rows()
  const current =
    list.find((row) => row.dataset.treeItem === props.selectedPath) ||
    list.find((row) => row.tabIndex === 0) ||
    list[0]
  for (const row of list) row.tabIndex = row === current ? 0 : -1
}
function keydown(event: KeyboardEvent) {
  if (event.isComposing || !(event.target instanceof HTMLElement)) return
  const row = event.target.closest<HTMLButtonElement>('[data-tree-item]')
  if (
    !row ||
    !['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Home', 'End', 'Enter', ' '].includes(
      event.key,
    )
  )
    return
  event.preventDefault()
  event.stopPropagation()
  const list = rows(),
    index = list.indexOf(row),
    node = findNode(row.dataset.treeItem || '')
  if (event.key === 'ArrowUp') focus(list[Math.max(0, index - 1)])
  else if (event.key === 'ArrowDown') focus(list[Math.min(list.length - 1, index + 1)])
  else if (event.key === 'Home') focus(list[0])
  else if (event.key === 'End') focus(list[list.length - 1])
  else if (event.key === 'Enter' || event.key === ' ') row.click()
  else if (event.key === 'ArrowRight') {
    if (node?.type === 'directory' && !node.expanded) emit('expand', node)
    else if (
      node?.type === 'directory' &&
      Number(list[index + 1]?.getAttribute('aria-level')) > Number(row.getAttribute('aria-level'))
    )
      focus(list[index + 1])
  } else if (node?.type === 'directory' && node.expanded) emit('expand', node)
  else {
    const parent = list
      .slice(0, index)
      .reverse()
      .find(
        (item) => Number(item.getAttribute('aria-level')) < Number(row.getAttribute('aria-level')),
      )
    focus(parent)
  }
}
watch(() => [props.nodes, props.selectedPath], ensureEntry, { flush: 'post' })
onMounted(ensureEntry)
</script>
<template>
  <div
    ref="tree"
    class="file-tree"
    role="tree"
    :aria-label="$t('工作区文件')"
    @keydown="keydown"
  >
    <FileNode
      v-for="node in nodes"
      :key="node.path"
      :node="node"
      :depth="0"
      :selected-path="selectedPath"
      @expand="emit('expand', $event)"
      @select="emit('select', $event)"
    />
  </div>
</template>
<style scoped lang="scss">
.file-tree {
  padding: var(--space-3);
}
</style>
