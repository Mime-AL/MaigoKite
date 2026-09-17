/**
 * 文件树操作组合式函数
 *
 * 管理文件树的展开、选择和右键菜单操作。
 */

import { ref } from 'vue'
import { api, type WorkspaceFileContent } from '@/api/client'

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
  const tree = ref<FileTreeNode[]>([])
  const selectedNode = ref<FileTreeNode | null>(null)
  const expandedPaths = ref<Set<string>>(new Set())
  const selectedContent = ref<WorkspaceFileContent | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  function toNode(item: Awaited<ReturnType<typeof api.listWorkspaceFiles>>[number]): FileTreeNode {
    return { ...item, children: item.type === 'directory' ? [] : undefined, loaded: false }
  }

  /** 加载文件树 */
  async function loadFileTree(rootPath: string) {
    loading.value = true
    error.value = null
    try {
      tree.value = (await api.listWorkspaceFiles(rootPath === './' ? '' : rootPath)).map(toNode)
    } catch (reason) {
      tree.value = []
      error.value = reason instanceof Error ? reason.message : String(reason)
    } finally { loading.value = false }
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
          node.loading = true
          try {
            node.children = (await api.listWorkspaceFiles(path)).map(toNode)
            node.loaded = true
          } catch (reason) {
            error.value = reason instanceof Error ? reason.message : String(reason)
          } finally { node.loading = false }
        }
      }
    }
  }

  /** 选择节点 */
  async function selectNode(node: FileTreeNode) {
    selectedNode.value = node
    selectedContent.value = null
    if (node.type !== 'file') return
    loading.value = true
    error.value = null
    try { selectedContent.value = await api.getWorkspaceFile(node.path) }
    catch (reason) { error.value = reason instanceof Error ? reason.message : String(reason) }
    finally { loading.value = false }
  }

  /** 获取展开的子节点 */
  function getExpandedChildren(node: FileTreeNode): FileTreeNode[] {
    if (node.children && expandedPaths.value.has(node.path)) {
      return node.children
    }
    return []
  }

  return {
    tree,
    selectedNode,
    selectedContent,
    expandedPaths,
    loading,
    error,
    loadFileTree,
    toggleExpand,
    selectNode,
    getExpandedChildren
  }
}
