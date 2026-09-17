/**
 * 布局状态 Store
 *
 * 管理三栏布局的宽度和收起状态，
 * 数据持久化到 localStorage。
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'

// 布局常量
const LAYOUT_KEYS = {
  SIDEBAR_COLLAPSED: 'layout_sidebar_collapsed',
  SIDEBAR_WIDTH: 'layout_sidebar_width',
  FILE_EXPLORER_COLLAPSED: 'layout_explorer_collapsed',
  FILE_EXPLORER_WIDTH: 'layout_explorer_width'
}

const DEFAULT_SIDEBAR_WIDTH = 240
const MIN_SIDEBAR_WIDTH = 64
const MAX_SIDEBAR_WIDTH = 400

const DEFAULT_EXPLORER_WIDTH = 320
const MIN_EXPLORER_WIDTH = 48
const MAX_EXPLORER_WIDTH = 600

function loadFromStorage<T>(key: string, fallback: T): T {
  try {
    const stored = localStorage.getItem(key)
    return stored !== null ? (JSON.parse(stored) as T) : fallback
  } catch {
    return fallback
  }
}

export const useLayoutStore = defineStore('layout', () => {
  const sidebarCollapsed = ref(loadFromStorage(LAYOUT_KEYS.SIDEBAR_COLLAPSED, false))
  const sidebarWidth = ref(
    sidebarCollapsed.value ? MIN_SIDEBAR_WIDTH : loadFromStorage(LAYOUT_KEYS.SIDEBAR_WIDTH, DEFAULT_SIDEBAR_WIDTH)
  )
  const fileExplorerCollapsed = ref(loadFromStorage(LAYOUT_KEYS.FILE_EXPLORER_COLLAPSED, false))
  const fileExplorerWidth = ref(
    fileExplorerCollapsed.value
      ? MIN_EXPLORER_WIDTH
      : loadFromStorage(LAYOUT_KEYS.FILE_EXPLORER_WIDTH, DEFAULT_EXPLORER_WIDTH)
  )

  /** 仅在交互完成后持久化，避免拖拽期间同步阻塞每一帧。 */
  function persistLayout() {
    try {
      localStorage.setItem(LAYOUT_KEYS.SIDEBAR_COLLAPSED, JSON.stringify(sidebarCollapsed.value))
      localStorage.setItem(LAYOUT_KEYS.SIDEBAR_WIDTH, JSON.stringify(sidebarWidth.value))
      localStorage.setItem(LAYOUT_KEYS.FILE_EXPLORER_COLLAPSED, JSON.stringify(fileExplorerCollapsed.value))
      localStorage.setItem(LAYOUT_KEYS.FILE_EXPLORER_WIDTH, JSON.stringify(fileExplorerWidth.value))
    } catch {
      // 禁用本地存储时布局仍在当前会话内可用。
    }
  }

  /** 切换侧边栏收起/展开 */
  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
    if (sidebarCollapsed.value) {
      sidebarWidth.value = MIN_SIDEBAR_WIDTH
    } else {
      sidebarWidth.value = DEFAULT_SIDEBAR_WIDTH
    }
    persistLayout()
  }

  /** 切换文件管理器收起/展开 */
  function toggleFileExplorer() {
    fileExplorerCollapsed.value = !fileExplorerCollapsed.value
    if (fileExplorerCollapsed.value) {
      fileExplorerWidth.value = MIN_EXPLORER_WIDTH
    } else {
      fileExplorerWidth.value = DEFAULT_EXPLORER_WIDTH
    }
    persistLayout()
  }

  /** 设置侧边栏宽度（拖拽时使用） */
  function setSidebarWidth(width: number) {
    sidebarWidth.value = Math.max(MIN_SIDEBAR_WIDTH, Math.min(MAX_SIDEBAR_WIDTH, width))
  }

  /** 设置文件管理器宽度（拖拽时使用） */
  function setFileExplorerWidth(width: number) {
    fileExplorerWidth.value = Math.max(MIN_EXPLORER_WIDTH, Math.min(MAX_EXPLORER_WIDTH, width))
  }

  return {
    sidebarCollapsed,
    sidebarWidth,
    fileExplorerCollapsed,
    fileExplorerWidth,
    toggleSidebar,
    toggleFileExplorer,
    setSidebarWidth,
    setFileExplorerWidth,
    persistLayout,
  }
})
