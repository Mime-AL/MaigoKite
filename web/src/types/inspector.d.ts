/**
 * Inspector 类型定义
 *
 * 定义 Inspector 监控页面的数据结构，包括时间线节点和维度配置。
 */

// 时间线节点
export interface TimelineNode {
  id: string
  type: 'task' | 'tool' | 'llm' | 'event' | 'exception' | 'subagent'
  timestamp: Date
  data: Record<string, any>
  children?: TimelineNode[]
}

// 维度配置
export interface DimensionConfig {
  key: string
  label: string
  visible: boolean
  icon: string
}

export type Dimension = string

export interface InspectorCard {
  session_id: string
  title: string
  status: 'running' | 'completed' | 'failed' | 'paused'
  current_step?: string
  running_duration_sec?: number
  total_duration_sec?: number
  token_count?: number
  tool_call_count?: number
}

export {}
