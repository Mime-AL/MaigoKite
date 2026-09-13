/**
 * Inspector 类型定义
 *
 * 定义 Inspector 监控页面的数据结构，包括时间线节点和维度配置。
 */

// 时间线节点
interface TimelineNode {
  id: string
  type: 'task' | 'tool' | 'llm' | 'event' | 'exception' | 'subagent'
  timestamp: Date
  data: Record<string, any>
  children?: TimelineNode[]
}

// 维度配置
interface DimensionConfig {
  key: string
  label: string
  visible: boolean
  icon: string
}

export {}
