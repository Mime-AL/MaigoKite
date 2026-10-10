/**
 * 布局状态 Store
 *
 * 管理三栏布局的宽度和收起状态，
 * 数据持久化到 localStorage。
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'

// 布局常量
const storagePrefix = import.meta.env.VITE_MOCK === '1' ? 'demo_' : ''
const LAYOUT_KEYS = {
  SIDEBAR_COLLAPSED: storagePrefix + 'layout_sidebar_collapsed',
  SIDEBAR_WIDTH: storagePrefix + 'layout_sidebar_width',
  FILE_EXPLORER_COLLAPSED: storagePrefix + 'layout_explorer_collapsed',
  FILE_EXPLORER_WIDTH: storagePrefix + 'layout_explorer_width',
}

const DEFAULT_SIDEBAR_WIDTH = 240
const MIN_SIDEBAR_WIDTH = 200
const MAX_SIDEBAR_WIDTH = 400

const DEFAULT_EXPLORER_WIDTH = 380
const MIN_EXPLORER_WIDTH = 280
// Right panel is bounded by the viewport and chat space, not a fixed pixel ceiling.
const MAX_EXPLORER_WIDTH = Infinity

export const panelWidths = {
  left: { min: MIN_SIDEBAR_WIDTH, max: MAX_SIDEBAR_WIDTH, default: DEFAULT_SIDEBAR_WIDTH },
  right: { min: MIN_EXPLORER_WIDTH, max: MAX_EXPLORER_WIDTH, default: DEFAULT_EXPLORER_WIDTH },
} as const

function savedWidth(key: string, side: keyof typeof panelWidths): number {
  const bounds = panelWidths[side]
  const stored: unknown = loadFromStorage(key, bounds.default)
  // Old layouts stored the collapsed rail width instead of the expanded width.
  return typeof stored === 'number' && Number.isFinite(stored) && stored >= bounds.min
    ? Math.min(bounds.max, stored)
    : bounds.default
}

function loadFromStorage<T>(key: string, fallback: T): T {
  try {
    const stored = localStorage.getItem(key)
    return stored !== null ? (JSON.parse(stored) as T) : fallback
  } catch {
    return fallback
  }
}

export const useLayoutStore = defineStore('layout', () => {
  const sidebarCollapsed = ref(
    loadFromStorage<boolean>(LAYOUT_KEYS.SIDEBAR_COLLAPSED, false) === true,
  )
  const sidebarWidth = ref(savedWidth(LAYOUT_KEYS.SIDEBAR_WIDTH, 'left'))
  const fileExplorerCollapsed = ref(
    loadFromStorage<boolean>(LAYOUT_KEYS.FILE_EXPLORER_COLLAPSED, false) === true,
  )
  const fileExplorerWidth = ref(savedWidth(LAYOUT_KEYS.FILE_EXPLORER_WIDTH, 'right'))

  /** 仅在交互完成后持久化，避免拖拽期间同步阻塞每一帧。 */
  function persistLayout() {
    try {
      localStorage.setItem(LAYOUT_KEYS.SIDEBAR_COLLAPSED, JSON.stringify(sidebarCollapsed.value))
      localStorage.setItem(LAYOUT_KEYS.SIDEBAR_WIDTH, JSON.stringify(sidebarWidth.value))
      localStorage.setItem(
        LAYOUT_KEYS.FILE_EXPLORER_COLLAPSED,
        JSON.stringify(fileExplorerCollapsed.value),
      )
      localStorage.setItem(LAYOUT_KEYS.FILE_EXPLORER_WIDTH, JSON.stringify(fileExplorerWidth.value))
    } catch {
      // 禁用本地存储时布局仍在当前会话内可用。
    }
  }

  /** 切换侧边栏收起/展开 */
  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
    persistLayout()
  }

  /** 切换文件管理器收起/展开 */
  function toggleFileExplorer() {
    fileExplorerCollapsed.value = !fileExplorerCollapsed.value
    persistLayout()
  }

  /** 设置侧边栏宽度（拖拽时使用） */
  function setSidebarWidth(width: number) {
    if (!Number.isFinite(width)) return
    sidebarWidth.value = Math.max(MIN_SIDEBAR_WIDTH, Math.min(MAX_SIDEBAR_WIDTH, width))
  }

  /** 设置文件管理器宽度（拖拽时使用） */
  function setFileExplorerWidth(width: number) {
    if (!Number.isFinite(width)) return
    fileExplorerWidth.value = Math.max(MIN_EXPLORER_WIDTH, Math.min(MAX_EXPLORER_WIDTH, width))
  }

  function resetPanelWidth(side: keyof typeof panelWidths) {
    if (side === 'left') setSidebarWidth(panelWidths.left.default)
    else setFileExplorerWidth(panelWidths.right.default)
    persistLayout()
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
    resetPanelWidth,
    persistLayout,
  }
})
