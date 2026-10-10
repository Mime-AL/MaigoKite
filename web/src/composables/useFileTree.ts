/**
 * 文件树操作组合式函数
 *
 * 管理文件树的展开、选择和右键菜单操作。
 */

import { onScopeDispose, ref, watch } from 'vue'
import { api, type WorkspaceFileContent } from '@/api/client'
import { useWorkspaceStore } from '@/stores/workspace'

export interface FileTreeNode {
  name: string
  path: string
  type: 'file' | 'directory'
  children?: FileTreeNode[]
  expanded?: boolean
  loaded?: boolean
  loading?: boolean
  size?: number
  modified_at?: string
}

export function useFileTree() {
  const workspace = useWorkspaceStore()
  const tree = ref<FileTreeNode[]>([])
  const selectedNode = ref<FileTreeNode | null>(null)
  const expandedPaths = ref<Set<string>>(new Set())
  const selectedContent = ref<WorkspaceFileContent | null>(null)
  const loading = ref(false)
  const previewLoading = ref(false)
  const previewError = ref<string | null>(null)
  const error = ref<string | null>(null)
  let treeRequest = 0,
    previewRequest = 0

  function toNode(item: Awaited<ReturnType<typeof api.listWorkspaceFiles>>[number]): FileTreeNode {
    return { ...item, children: item.type === 'directory' ? [] : undefined, loaded: false }
  }

  /** 加载文件树 */
  async function loadFileTree(rootPath: string) {
    const request = ++treeRequest
    const folderId = workspace.selectedId
    tree.value = []
    previewRequest++
    selectedNode.value = null
    selectedContent.value = null
    previewLoading.value = false
    previewError.value = null
    expandedPaths.value.clear()
    loading.value = true
    error.value = null
    try {
      const entries = await api.listWorkspaceFiles(rootPath === './' ? '' : rootPath, folderId)
      if (request === treeRequest) tree.value = entries.map(toNode)
    } catch (reason) {
      if (request !== treeRequest) return
      tree.value = []
      error.value = reason instanceof Error ? reason.message : String(reason)
    } finally {
      if (request === treeRequest) loading.value = false
    }
  }

  /** 切换节点展开/收起 */
  async function toggleExpand(node: FileTreeNode) {
    if (node.type === 'directory') {
      const path = node.path
      if (expandedPaths.value.has(path)) {
        expandedPaths.value.delete(path)
        node.expanded = false
      } else {
        expandedPaths.value.add(path)
        node.expanded = true
        if (!node.loaded && !node.loading) {
          const request = treeRequest
          node.loading = true
          error.value = null
          try {
            const entries = await api.listWorkspaceFiles(path, workspace.selectedId)
            if (request !== treeRequest) return
            node.children = entries.map(toNode)
            node.loaded = true
          } catch (reason) {
            if (request === treeRequest)
              error.value = reason instanceof Error ? reason.message : String(reason)
          } finally {
            node.loading = false
          }
        }
      }
    }
  }

  /** 选择节点 */
  async function selectNode(node: FileTreeNode) {
    const request = ++previewRequest
    selectedNode.value = node
    selectedContent.value = null
    previewError.value = null
    previewLoading.value = false
    if (node.type !== 'file') return
    previewLoading.value = true
    try {
      const content = await api.getWorkspaceFile(node.path, workspace.selectedId)
      if (request === previewRequest) selectedContent.value = content
    } catch (reason) {
      if (request === previewRequest)
        previewError.value = reason instanceof Error ? reason.message : String(reason)
    } finally {
      if (request === previewRequest) previewLoading.value = false
    }
  }

  /** 获取展开的子节点 */
  function getExpandedChildren(node: FileTreeNode): FileTreeNode[] {
    if (node.children && expandedPaths.value.has(node.path)) {
      return node.children
    }
    return []
  }

  watch(() => workspace.selectedId, () => void loadFileTree(''), { immediate: true, flush: 'sync' })
  onScopeDispose(() => {
    treeRequest++
    previewRequest++
  })

  return {
    tree,
    selectedNode,
    selectedContent,
    expandedPaths,
    loading,
    previewLoading,
    previewError,
    error,
    loadFileTree,
    toggleExpand,
    selectNode,
    getExpandedChildren,
  }
}
