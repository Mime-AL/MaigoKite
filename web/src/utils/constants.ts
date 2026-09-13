/**
 * 常量定义
 *
 * 项目中使用的硬编码常量集中管理。
 */

/** API 基础地址 */
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080'

/** WebSocket 地址 */
export const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8080/ws'

/** 布局常量 */
export const LAYOUT = {
  SIDEBAR: {
    COLLAPSED_WIDTH: 64,
    EXPANDED_WIDTH: 240,
    DEFAULT_WIDTH: 240,
    MIN_WIDTH: 48,
    MAX_WIDTH: 400
  },
  FILE_EXPLORER: {
    COLLAPSED_WIDTH: 48,
    EXPANDED_WIDTH: 320,
    DEFAULT_WIDTH: 320,
    MIN_WIDTH: 48,
    MAX_WIDTH: 600
  }
} as const

/** 路由名称映射 */
export const ROUTE_NAMES: Record<string, string> = {
  overview: '总览',
  chat: '对话',
  inspector: 'Inspector',
  settings: '设置',
  search: '搜索',
  scheduledTasks: '定时任务',
  browser: '浏览器',
  packages: '包管理',
  skills: 'Skill 管理',
  dailyReview: '每日回顾',
  longTermPlan: '长期计划',
  archive: '归档'
} as const

/** WebSocket 事件类型 */
export const WS_EVENTS = {
  TASK_STARTED: 'task.started',
  TASK_COMPLETED: 'task.completed',
  TASK_FAILED: 'task.failed',
  TOOL_CALLED: 'tool.called',
  LLM_TOKEN: 'llm.token',
  STEP_STATUS: 'step.status'
} as const
