/**
 * 工具类型定义
 *
 * 定义 Agent 工具系统的接口，包括工具元数据、执行上下文和代码更改。
 */

// 工具元数据
interface ToolMetadata {
  name: string
  description: string
  parameters: Record<string, any>  // JSON Schema
  permissions: number  // L1-L5
  category: 'native' | 'mcp'
  streaming: boolean
}

// 工具执行上下文
interface ToolExecutionContext {
  task_id: string
  step_id: string
  trace_id: string
  deadline: Date
  cancellation_token: boolean
  metadata: Record<string, any>
}

// 代码更改
interface CodeChange {
  file_path: string
  status: 'accepted' | 'rejected' | 'pending' | 'modified'
  additions: number
  deletions: number
  diff?: string
}

export {}
