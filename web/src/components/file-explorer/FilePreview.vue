<script setup lang="ts">
import { ref, watch } from 'vue'
import type { FileTreeNode } from '@/composables/useFileTree'
import type { WorkspaceFileContent } from '@/api/client'
import IconSymbol from '@/components/common/IconSymbol.vue'
import CodeBlock from '@/components/common/CodeBlock.vue'
import InkLoader from '@/components/common/InkLoader.vue'
import { desktopEffects } from '@/composables/useElectron'
import { useWorkspaceStore } from '@/stores/workspace'

const props = defineProps<{
  node: FileTreeNode
  content?: WorkspaceFileContent | null
  loading?: boolean
  loadError?: string | null
}>()
defineEmits<{ (event: 'retry' | 'close'): void }>()
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
  } finally {
    opening.value = false
  }
}
</script>

<template>
  <section class="file-preview">
    <header>
      <span><IconSymbol
        :name="node.type === 'directory' ? 'folder' : 'file'"
        :size="16"
      /></span>
      <div>
        <strong>{{ node.name }}</strong><small>{{ node.type === 'directory' ? $t('文件夹') : $t('只读预览') }}</small>
      </div>
      <button
        class="icon-button preview-close"
        :aria-label="$t('关闭预览')"
        :title="$t('关闭预览')"
        @click="$emit('close')"
      >
        <IconSymbol
          name="close"
          :size="16"
        />
      </button>
    </header>
    <button
      v-if="isElectron"
      class="secondary-button"
      :disabled="opening"
      :aria-busy="opening || undefined"
      @click="openFile"
    >
      {{ opening ? $t('正在打开…') : $t('在本机打开') }}
    </button>
    <p
      v-if="error"
      role="alert"
    >
      {{ error }}
    </p>
    <dl>
      <dt>{{ $t('路径') }}</dt>
      <dd>{{ node.path }}</dd>
      <template v-if="node.size != null">
        <dt>{{ $t('大小') }}</dt>
        <dd>{{ node.size }} bytes</dd>
      </template><template v-if="node.modified_at">
        <dt>{{ $t('修改') }}</dt>
        <dd>{{ new Date(node.modified_at).toLocaleString($i18n.locale) }}</dd>
      </template>
    </dl>
    <div
      v-if="node.type === 'file'"
      class="content"
    >
      <InkLoader v-if="loading" />
      <p
        v-else-if="loadError"
        role="alert"
      >
        {{ loadError }}
        <button
          class="secondary-button"
          @click="$emit('retry')"
        >
          {{ $t('重试') }}
        </button>
      </p>
      <p v-else-if="content?.binary">
        {{ $t('二进制文件无法预览') }}
      </p>
      <p v-else-if="content && !content.content">
        {{ $t('文件没有文本内容。') }}
      </p>
      <CodeBlock
        v-else-if="content"
        :content="content.content"
        :title="node.name"
      />
      <small v-if="content?.truncated">{{ $t('文件较大，仅显示前 512 KiB。') }}</small>
    </div>
  </section>
</template>

<style scoped lang="scss">
.file-preview {
  max-height: 52%;
  padding: var(--size-14);
  overflow: auto;
  border-top: var(--hairline) solid var(--rule);
  background: var(--paper-2);
}
header {
  display: flex;
  align-items: center;
  gap: var(--measure-9px);
}
header > span {
  display: grid;
  width: var(--measure-31px);
  height: var(--measure-31px);
  place-items: center;
  border-radius: var(--radius-md);
  color: var(--accent);
  background: var(--accent-soft);
}
header div {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.preview-close {
  flex: none;
  width: var(--space-8);
  min-height: var(--space-8);
}
header strong {
  overflow: hidden;
  font-size: var(--text-xs);
  text-overflow: ellipsis;
  white-space: nowrap;
}
header small {
  margin-top: var(--space-1);
  color: var(--ink-2);
  font-size: var(--text-xs);
}
dl {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr);
  gap: var(--measure-5px) var(--measure-9px);
  margin: var(--space-4) 0 0;
  font-size: var(--text-xs);
}
dt {
  color: var(--ink-2);
}
dd {
  margin: 0;
  overflow: hidden;
  color: var(--ink-2);
  text-overflow: ellipsis;
  white-space: nowrap;
}
.content {
  margin-top: var(--space-4);
}
.content p,
.content small {
  color: var(--ink-2);
  font-size: var(--text-xs);
}
</style>
