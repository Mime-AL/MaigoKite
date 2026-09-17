<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useLayoutStore } from '@/stores/layout'
import { useFileTree } from '@/composables/useFileTree'
import IconSymbol from '@/components/common/IconSymbol.vue'
import FileTree from '../file-explorer/FileTree.vue'
import FilePreview from '../file-explorer/FilePreview.vue'
import Toolbar from '../file-explorer/Toolbar.vue'
import WorkspaceDiff from '../file-explorer/WorkspaceDiff.vue'

const layoutStore = useLayoutStore()
const { tree, selectedNode, selectedContent, loading, error, loadFileTree, toggleExpand, selectNode } = useFileTree()
const activeTab = ref<'files' | 'changes'>('files')
onMounted(() => { void loadFileTree('') })
</script>

<template>
  <div class="file-explorer" :class="{ collapsed: layoutStore.fileExplorerCollapsed }">
    <button
      v-if="layoutStore.fileExplorerCollapsed"
      class="collapsed-button icon-button"
      type="button"
      title="展开文件栏"
      @click="layoutStore.toggleFileExplorer"
    >
      <IconSymbol name="files" :size="17" />
    </button>

    <template v-else>
      <header class="explorer-header">
        <div>
          <p>Workspace</p>
          <h2>文件</h2>
        </div>
        <button class="icon-button" type="button" aria-label="收起文件栏" @click="layoutStore.toggleFileExplorer">
          <IconSymbol name="chevron" :size="16" />
        </button>
      </header>
      <nav class="explorer-tabs"><button type="button" :class="{ active: activeTab === 'files' }" @click="activeTab = 'files'">文件</button><button type="button" :class="{ active: activeTab === 'changes' }" @click="activeTab = 'changes'">变更</button></nav>
      <template v-if="activeTab === 'files'">
        <Toolbar @refresh="loadFileTree('')" />
        <div class="explorer-body">
          <FileTree v-if="tree.length" :nodes="tree" @expand="toggleExpand" @select="selectNode" />
          <div v-else class="empty-files">
          <span class="empty-icon"><IconSymbol name="folder" :size="24" /></span>
          <strong>{{ loading ? '正在读取工作区…' : '没有可显示的文件' }}</strong>
          <p>{{ error || '项目文件会出现在这里。' }}</p>
          </div>
        </div>
        <FilePreview v-if="selectedNode" :node="selectedNode" :content="selectedContent" :loading="loading" />
      </template>
      <WorkspaceDiff v-else />
      <footer><span>本地工作区</span><i /></footer>
    </template>
  </div>
</template>

<style scoped lang="scss">
.file-explorer { display: flex; height: 100%; min-width: 48px; flex-direction: column; background: rgba(247, 248, 251, 0.72); }
.file-explorer.collapsed { align-items: center; padding-top: 9px; }
.collapsed-button { transform: rotate(180deg); }
.explorer-header { display: flex; height: 68px; flex: none; align-items: center; justify-content: space-between; padding: 12px 14px 8px 17px; }
.explorer-header p { margin: 0 0 2px; color: var(--text-tertiary); font-size: 9px; font-weight: 700; letter-spacing: 0.07em; text-transform: uppercase; }
.explorer-header h2 { margin: 0; font-size: 16px; letter-spacing: -0.025em; }
.explorer-header .icon-button { transform: rotate(180deg); }
.explorer-tabs { display: grid; grid-template-columns: 1fr 1fr; gap: 3px; margin: 0 10px 8px; padding: 3px; border-radius: 9px; background: var(--surface-strong); }.explorer-tabs button { height: 27px; border: 0; border-radius: 7px; color: var(--text-tertiary); background: transparent; cursor: pointer; font-size: 9.5px; font-weight: 650; }.explorer-tabs button.active { color: var(--text-primary); background: var(--surface-solid); box-shadow: 0 1px 5px rgba(20,30,45,.1); }
.explorer-body { min-height: 0; flex: 1; overflow: auto; }
.empty-files { display: flex; height: 100%; min-height: 220px; align-items: center; justify-content: center; flex-direction: column; padding: 24px; text-align: center; }
.empty-icon { display: grid; width: 48px; height: 48px; margin-bottom: 13px; place-items: center; border-radius: 15px; color: var(--text-secondary); background: var(--surface-strong); }
.empty-files strong { font-size: 12px; font-weight: 650; }
.empty-files p { max-width: 190px; margin: 5px 0 0; color: var(--text-tertiary); font-size: 10.5px; line-height: 1.5; }
footer { display: flex; height: 38px; flex: none; align-items: center; justify-content: flex-end; gap: 7px; padding: 0 15px; border-top: 1px solid var(--border-color); color: var(--text-tertiary); font-size: 9.5px; }
footer i { width: 5px; height: 5px; border-radius: 50%; background: var(--success); }
@media (prefers-color-scheme: dark) { .file-explorer { background: rgba(27, 28, 33, 0.78); } }
</style>
