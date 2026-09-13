/**
 * 文件树操作组合式函数
 *
 * 管理文件树的展开、选择和右键菜单操作。
 */

import { ref } from 'vue'

export interface FileTreeNode {
  name: string
  path: string
  type: 'file' | 'directory'
  children?: FileTreeNode[]
  expanded?: boolean
}

export function useFileTree() {
  const tree = ref<FileTreeNode[]>([])
  const selectedNode = ref<FileTreeNode | null>(null)
  const expandedPaths = ref<Set<string>>(new Set())

  /** 加载文件树 */
  async function loadFileTree(rootPath: string) {
    // TODO: 调用 API 获取文件系统数据
    tree.value = []
  }

  /** 切换节点展开/收起 */
  function toggleExpand(node: FileTreeNode) {
    if (node.type === 'directory') {
      const path = node.path
      if (expandedPaths.value.has(path)) {
        expandedPaths.value.delete(path)
      } else {
        expandedPaths.value.add(path)
      }
    }
  }

  /** 选择节点 */
  function selectNode(node: FileTreeNode) {
    selectedNode.value = node
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
    expandedPaths,
    loadFileTree,
    toggleExpand,
    selectNode,
    getExpandedChildren
  }
}
