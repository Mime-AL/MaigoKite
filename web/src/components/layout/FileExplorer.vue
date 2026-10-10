<script setup lang="ts">
import { ref } from 'vue'
import { useLayoutStore } from '@/stores/layout'
import { useWorkspaceStore } from '@/stores/workspace'
import { useFileTree } from '@/composables/useFileTree'
import IconSymbol from '@/components/common/IconSymbol.vue'
import FileTree from '../file-explorer/FileTree.vue'
import FilePreview from '../file-explorer/FilePreview.vue'
import Toolbar from '../file-explorer/Toolbar.vue'
import WorkspaceDiff from '../file-explorer/WorkspaceDiff.vue'

const layoutStore = useLayoutStore()
const workspace = useWorkspaceStore()
withDefaults(defineProps<{ embedded?: boolean }>(), { embedded: false })
const {
  tree,
  selectedNode,
  selectedContent,
  loading,
  previewLoading,
  previewError,
  error,
  loadFileTree,
  toggleExpand,
  selectNode,
  closePreview,
} = useFileTree()
const activeTab = ref<'files' | 'changes'>('files')
</script>

<template>
  <div
    class="file-explorer"
    :class="{ embedded, collapsed: !embedded && layoutStore.fileExplorerCollapsed }"
  >
    <button
      v-if="!embedded && layoutStore.fileExplorerCollapsed"
      class="collapsed-button icon-button"
      type="button"
      :title="$t('展开文件栏')"
      @click="layoutStore.toggleFileExplorer"
    >
      <IconSymbol name="files" :size="17" />
    </button>

    <template v-else>
      <header v-if="!embedded" class="explorer-header">
        <div>
          <p :title="workspace.current?.root_path">{{ workspace.current?.name || $t('工作区') }}</p>
          <h2>{{ $t('文件') }}</h2>
        </div>
        <button
          class="icon-button"
          type="button"
          :aria-label="$t('收起文件栏')"
          @click="layoutStore.toggleFileExplorer"
        >
          <IconSymbol name="chevron" :size="16" />
        </button>
      </header>
      <nav v-if="!embedded" class="explorer-tabs">
        <button
          type="button"
          :class="{ active: activeTab === 'files' }"
          @click="activeTab = 'files'"
        >{{ $t('文件') }}</button
        ><button
          type="button"
          :class="{ active: activeTab === 'changes' }"
          @click="activeTab = 'changes'"
        >{{ $t('变更') }}</button>
      </nav>
      <template v-if="embedded || activeTab === 'files'">
        <Toolbar :loading="loading" @refresh="loadFileTree('')" />
        <p v-if="error && tree.length" class="empty-copy" role="alert">{{ error }}</p>
        <div class="explorer-body">
          <FileTree v-if="tree.length" :nodes="tree" :selected-path="selectedNode?.path" @expand="toggleExpand" @select="selectNode" />
          <div v-else class="empty-files">
            <span class="empty-icon"><IconSymbol name="folder" :size="24" /></span>
            <strong>{{ loading ? $t('正在读取工作区…') : $t('没有可显示的文件') }}</strong>
            <p v-if="error" role="alert">{{ error }}</p>
          </div>
        </div>
        <FilePreview
          v-if="selectedNode"
          :node="selectedNode"
          :content="selectedContent"
          :loading="previewLoading"
          :load-error="previewError"
          @retry="selectedNode && selectNode(selectedNode)"
          @close="closePreview"
        />
      </template>
      <WorkspaceDiff v-else />
      <footer v-if="!embedded"><span>{{ $t('工作区 · 只读预览') }}</span></footer>
    </template>
  </div>
</template>

<style scoped lang="scss">
.file-explorer {
  display: flex;
  height: 100%;
  min-width: 48px;
  flex-direction: column;
  background: var(--paper-3);
}
.file-explorer.collapsed {
  align-items: center;
  padding-top: 9px;
}
.file-explorer.embedded {
  flex: 1;
  min-height: 0;
  height: auto;
}
.collapsed-button {
  transform: rotate(180deg);
}
.explorer-header {
  display: flex;
  height: 68px;
  flex: none;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px 8px 17px;
}
.explorer-header p {
  margin: 0 0 2px;
  color: var(--text-tertiary);
  font-size: var(--text-xs);
  font-weight: var(--weight-bold);
  letter-spacing: 0.07em;
  text-transform: uppercase;
}
.explorer-header h2 {
  margin: 0;
  font-size: var(--text-md);
  letter-spacing: -0.025em;
}
.explorer-header .icon-button {
  transform: rotate(180deg);
}
.explorer-tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 3px;
  margin: 0 10px 8px;
  padding: 3px;
  border-radius: var(--radius-md);
  background: var(--surface-strong);
}
.explorer-tabs button {
  height: 27px;
  border: 0;
  border-radius: var(--radius-sm);
  color: var(--text-tertiary);
  background: var(--transparent);
  cursor: pointer;
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
}
.explorer-tabs button.active {
  color: var(--text-primary);
  background: var(--surface-solid);
  box-shadow: var(--shadow-card);
}
.explorer-body {
  min-height: 0;
  flex: 1;
  overflow: auto;
}
.empty-files {
  display: flex;
  height: 100%;
  min-height: 220px;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  padding: 24px;
  text-align: center;
}
.empty-icon {
  display: grid;
  width: 48px;
  height: 48px;
  margin-bottom: 13px;
  place-items: center;
  border-radius: var(--radius-lg);
  color: var(--text-secondary);
  background: var(--surface-strong);
}
.empty-files strong {
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
}
.empty-files p {
  max-width: 190px;
  margin: 5px 0 0;
  color: var(--text-tertiary);
  font-size: var(--text-xs);
  line-height: var(--leading-normal);
}
footer {
  display: flex;
  height: 38px;
  flex: none;
  align-items: center;
  justify-content: flex-end;
  gap: 7px;
  padding: 0 15px;
  border-top: 1px solid var(--border-color);
  color: var(--text-tertiary);
  font-size: var(--text-xs);
}
footer i {
  width: 5px;
  height: 5px;
  border-radius: var(--radius-round);
  background: var(--success);
}
@media (prefers-color-scheme: dark) {
  .file-explorer {
    background: var(--paper-3);
  }
}
</style>
