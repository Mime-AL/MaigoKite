/**
 * API 类型定义
 *
 * 用于前端与后端交互的数据结构，包括会话、消息、工具调用、任务、Inspector 等核心实体。
 */

// ==================== 会话 ====================

interface Session {
  id: string
  title: string
  messages: Message[]
  status: 'active' | 'paused' | 'completed' | 'failed' | 'timeout'
  createdAt: Date
  updatedAt: Date
  tokenCount: number
  toolCallCount: number
}

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  metadata?: Record<string, any>
}

// ==================== 工具调用 ====================

interface ToolCall {
  id: string
  tool_name: string
  arguments: Record<string, any>
  status: 'pending' | 'running' | 'completed' | 'failed'
  result?: ToolResult
  error?: string
  started_at: Date
  finished_at?: Date
}

interface ToolResult {
  data: Record<string, any>
  summary: string
  raw: string | null
  metadata: Record<string, any>
}

// ==================== 步骤 & 任务 ====================

interface Step {
  id: string
  title: string
  status: 'todo' | 'running' | 'completed' | 'failed'
  tool_calls: ToolCall[]
  started_at: Date
  finished_at?: Date
}

interface Task {
  id: string
  session_id: string
  title: string
  steps: Step[]
  status: 'queued' | 'running' | 'paused' | 'completed' | 'failed' | 'timeout'
  created_at: Date
  updated_at: Date
}

// ==================== Inspector ====================

interface InspectorEvent {
  event_type: string
  task_id: string
  timestamp: Date
  data: Record<string, any>
}

interface InspectorCard {
  id: string
  session_title: string
  status: 'active' | 'completed' | 'failed' | 'paused' | 'timeout'
  run_duration: string
  current_step: string
  token_count: number
  tool_call_count: number
  events: InspectorEvent[]
  sub_agents: SubAgentStatus[]
}

interface SubAgentStatus {
  id: string
  title: string
  status: 'created' | 'running' | 'streaming' | 'completed' | 'failed' | 'destroyed'
  result?: string
  error?: string
  started_at: Date
  finished_at?: Date
}

// ==================== 文件 & Skill ====================

interface FileNode {
  name: string
  path: string
  type: 'file' | 'directory'
  children?: FileNode[]
  modified_at?: Date
  size?: number
}

interface Skill {
  name: string
  version: string
  description: string
  tools: string[]
  mcp_server?: string
  permissions: number  // L1-L5
  enabled: boolean
  installed_at: Date
}

// ==================== 记忆 ====================

interface MemoryEntry {
  id: string
  type: 'short_term' | 'conversation' | 'user_preference' | 'fact'
  content: string
  metadata: Record<string, any>
  created_at: Date
}

// ==================== 凭证 ====================

export interface CredentialEntry {
  service: string
  configured: boolean
  validated?: boolean
  updated_at?: string
}

// ==================== 模型配置 ====================

interface BGEConfig {
  model: string
  device: string
}

export type ChatModelProvider = 'openai' | 'anthropic' | 'openai_compatible' | 'ollama'

export interface ChatModelConfig {
  provider: ChatModelProvider
  model: string
  baseUrl: string
  temperature: number
  maxTokens: number
  timeoutSeconds: number
  credentialConfigured: boolean
}

interface EmbeddingConfig {
  provider: string
  bge: BGEConfig
}

export interface ModelConfig {
  chat: ChatModelConfig
  embedding: EmbeddingConfig
}

// ==================== 搜索引擎 ====================

interface SearchEngineProvider {
  enabled: boolean
  apiKey?: string
  cx?: string  // Google Custom Search CX
}

export interface SearchEngineConfig {
  default: string
  providers: {
    tavily: SearchEngineProvider
    google: SearchEngineProvider
    duckduckgo: SearchEngineProvider
  }
}

// ==================== 应用配置 ====================

export interface AppConfig {
  name: string
  version: string
  environment?: string
  theme?: string
  language?: string
}

// ==================== 设置页面 API 响应 ====================

interface SettingsResponse {
  app: AppConfig
  models: ModelConfig
  credentials: Record<string, CredentialEntry>
  search_engines: SearchEngineConfig
  permissions: { defaultMode: string; circuitBreakerEnabled: boolean }
  observability: Record<string, unknown>
  inspector: Record<string, unknown>
}

export {}
