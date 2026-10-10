<script setup lang="ts">
import { ref, watch } from 'vue'
import type { FileTreeNode } from '@/composables/useFileTree'
import type { WorkspaceFileContent } from '@/api/client'
import IconSymbol from '@/components/common/IconSymbol.vue'
import { desktopEffects } from '@/composables/useElectron'
import { useWorkspaceStore } from '@/stores/workspace'

const props = defineProps<{
  node: FileTreeNode
  content?: WorkspaceFileContent | null
  loading?: boolean
  loadError?: string | null
}>()
defineEmits<{ (event: 'retry'): void }>()
const isElectron = Boolean(desktopEffects),
  error = ref(''),
  opening = ref(false)
const workspace = useWorkspaceStore()
watch(
  () => [props.node.path, workspace.selectedId],
  () => {
    error.value = ''
  },
)
async function openFile() {
  if (opening.value) return
  opening.value = true
  const path = props.node.path
  const folderId = workspace.selectedId
  try {
    const result = await desktopEffects?.openPath(path, folderId)
    if (path === props.node.path && folderId === workspace.selectedId) error.value = result || ''
  } catch (reason) {
    if (path === props.node.path && folderId === workspace.selectedId) error.value = String(reason)
  } finally { opening.value = false }
}
</script>

<template>
  <section class="file-preview">
    <header>
      <span><IconSymbol :name="node.type === 'directory' ? 'folder' : 'file'" :size="16" /></span>
      <div>
        <strong>{{ node.name }}</strong
        ><small>{{ node.type === 'directory' ? '文件夹' : '只读预览' }}</small>
      </div>
    </header>
    <button v-if="isElectron" class="secondary-button" :disabled="opening" :aria-busy="opening || undefined" @click="openFile">{{ opening ? '正在打开…' : '在本机打开' }}</button>
    <p v-if="error" role="alert">{{ error }}</p>
    <dl>
      <dt>路径</dt>
      <dd>{{ node.path }}</dd>
      <template v-if="node.size != null"
        ><dt>大小</dt>
        <dd>{{ node.size }} bytes</dd></template
      ><template v-if="node.modified_at"
        ><dt>修改</dt>
        <dd>{{ new Date(node.modified_at).toLocaleString('zh-CN') }}</dd></template
      >
    </dl>
    <div v-if="node.type === 'file'" class="content">
      <p v-if="loading">正在加载…</p>
      <p v-else-if="loadError" role="alert">
        {{ loadError }} <button class="secondary-button" @click="$emit('retry')">重试</button>
      </p>
      <p v-else-if="content?.binary">二进制文件无法预览</p>
      <pre v-else-if="content">{{ content.content }}</pre>
      <small v-if="content?.truncated">文件较大，仅显示前 512 KiB。</small>
    </div>
  </section>
</template>

<style scoped lang="scss">
.file-preview {
  max-height: 52%;
  padding: 14px;
  overflow: auto;
  border-top: 1px solid var(--border-color);
  background: var(--surface-muted);
}
header {
  display: flex;
  align-items: center;
  gap: 9px;
}
header > span {
  display: grid;
  width: 31px;
  height: 31px;
  place-items: center;
  border-radius: var(--radius-md);
  color: var(--primary-color);
  background: var(--primary-soft);
}
header div {
  min-width: 0;
  display: flex;
  flex-direction: column;
}
header strong {
  overflow: hidden;
  font-size: var(--text-xs);
  text-overflow: ellipsis;
  white-space: nowrap;
}
header small {
  margin-top: 2px;
  color: var(--text-tertiary);
  font-size: var(--text-xs);
}
dl {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: 5px 9px;
  margin: 12px 0 0;
  font-size: var(--text-xs);
}
dt {
  color: var(--text-tertiary);
}
dd {
  margin: 0;
  overflow: hidden;
  color: var(--text-secondary);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.content {
  margin-top: 12px;
}
.content p,
.content small {
  color: var(--text-tertiary);
  font-size: var(--text-xs);
}
.content pre {
  max-height: 360px;
  margin: 0;
  padding: 10px;
  overflow: auto;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  background: var(--surface-solid);
  font-family: var(--font-mono);
  font-size: var(--text-xs);
  line-height: var(--leading-normal);
  white-space: pre;
}
</style>
