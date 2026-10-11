import { request, workspacePath } from './http'
import { mockConnect } from './mock'
import type { PlanItem } from './events'
export type PermissionMode = 'read_only' | 'workspace' | 'full_access'
export type ResponseMode = 'fast' | 'balanced' | 'thorough'

export interface ToolSetting {
  name: string
  description: string
  source: 'builtin' | 'mcp'
  enabled: boolean
  configurable: boolean
  default_enabled: boolean
}

export interface ToolSettings {
  tools: ToolSetting[]
}

export interface Conversation {
  subagent_model_ids?: string[]
  max_subagent_calls?: number
  max_concurrent_subagents?: number
  folder_id?: string
  archived?: boolean
  id: string
  workspace_id: string
  title: string
  model_id: string
  permission_mode: PermissionMode
  response_mode: ResponseMode
  created_at: string
  updated_at: string
  message_count: number
}
export interface WorkspaceFolder {
  id: string
  name: string
  root_path: string
}

export interface ChatMessage {
  id: string
  conversation_id: string
  role: 'system' | 'user' | 'assistant' | 'tool'
  content: string
  created_at: string
  streaming?: boolean
}

export interface AgentEvent {
  schema_version: number
  event_id: string
  sequence: number
  type: string
  occurred_at?: string
  conversation_id: string
  task_id?: string
  payload: Record<string, unknown> & { content?: string; message?: string; code?: string }
}

export interface Approval {
  id: string
  workspace_id: string
  conversation_id: string
  task_id: string
  tool_call_id: string
  tool_name: string
  arguments: Record<string, unknown>
  resource_scope: string
  risk_level: `L${1 | 2 | 3 | 4 | 5}`
  status: 'pending' | 'approved' | 'consumed' | 'rejected' | 'denied' | 'expired'
  version: number
  expires_at: string
  note?: string
  decided_at?: string
}

export interface AgentQuestion {
  id: string
  workspace_id: string
  conversation_id: string
  task_id: string
  tool_call_id: string
  title: string
  options: { label: string; recommended?: boolean }[]
  status: 'pending' | 'answered' | 'cancelled'
  version: number
  answer?: string
  created_at: string
}

export type AgentActivityKind = 'reasoning' | 'tool' | 'subagent'
export type AgentActivityStatus = 'pending' | 'running' | 'completed' | 'failed' | 'denied'

export interface AgentActivityItem {
  id: string
  task_id: string
  kind: AgentActivityKind
  status: AgentActivityStatus
  title: string
  summary?: string
  detail?: unknown
  hint?: string
  action?: { label: string; to: string }
  sequence: number
  created_at: string
}

export interface AgentActivityGroup {
  task_id: string
  status: 'running' | 'waiting_approval' | 'completed' | 'failed' | 'cancelled'
  items: AgentActivityItem[]
}

export interface PermissionSettings {
  default_mode: PermissionMode
}

export interface AuditEvent {
  id: string
  action: string
  resource: string
  result: string
  details_json: string
  created_at: string
}

export type ChatModelProvider = 'openai' | 'anthropic' | 'openai_compatible' | 'ollama'
export interface DiscoveredChatModel {
  id: string
  name?: string
  owned_by?: string
  context_window?: number
  details?: string
}
export interface ChatModelSettings {
  provider: ChatModelProvider
  model: string
  baseUrl: string
  temperature: number
  maxTokens: number
  timeoutSeconds: number
  credentialConfigured: boolean
}

export interface ChatModelProfile extends ChatModelSettings {
  id: string
  name: string
  isDefault: boolean
}

interface ChatModelWire {
  id?: string
  name?: string
  provider: ChatModelProvider
  model: string
  base_url: string
  temperature: number
  max_tokens: number
  timeout_seconds: number
  credential_configured?: boolean
  is_default?: boolean
}

export interface WorkspaceFileEntry {
  name: string
  path: string
  type: 'file' | 'directory'
  size?: number
  modified_at: string
}

export interface WorkspaceFileContent {
  path: string
  content: string
  binary: boolean
  truncated: boolean
  size: number
  modified_at: string
}

export interface WorkspaceChange {
  path: string
  status: 'modified' | 'added' | 'deleted' | 'renamed' | 'untracked'
  additions: number
  deletions: number
  diff: string
  diff_truncated: boolean
}

export interface CredentialStatus {
  name: string
  configured: boolean
  validated?: boolean
}

export interface CredentialEntry {
  service: string
  configured: boolean
  validated?: boolean
  updated_at?: string
}

export interface UserPreferences {
  assistantName: string
}

export interface RuntimeHealth {
  status: 'ok' | 'degraded'
  agentCore?: string
  version?: string
}

export interface RuntimeServiceStatus {
  status: 'serving' | 'unavailable' | string
  version?: string
}

export interface WorkspaceRuntimeStatus {
  workspaceId: string
  workspaceRoot: string
  workspaceSource: 'configuration' | 'environment' | 'selection'
  environment: string
  gateway: RuntimeServiceStatus
  agentCore: RuntimeServiceStatus
  restart: {
    pending: boolean
    requiredFor: string[]
    hotApplied: string[]
    note: string
  }
}

export type MemoryCategory = 'preference' | 'fact' | 'constraint' | 'project' | 'other'

export interface UserMemory {
  id: string
  workspace_id: string
  subject_user_id: string
  category: MemoryCategory
  content: string
  source_type: string
  source_id: string
  confidence: number
  created_at: string
  updated_at: string
}

export interface MemoryInput {
  category: MemoryCategory
  content: string
  confidence: number
}

export interface WorkspaceDataSummary {
  storage_backend: string
  conversation_count: number
  message_count: number
  memory_count: number
  task_count: number
  audit_event_count: number
}

export interface MCPServerStatus {
  namespace: string
  status: 'running' | 'disabled' | string
  transport: string
  tool_names: string[]
}

export interface MCPConfiguration {
  namespace: string
  transport: 'stdio'
  command: string
  args: string[]
  cwd: string
  enabled: boolean
  env_allowlist: string[]
  secret_env: string[]
  enabled_tools: string[] | null
  disabled_tools: string[]
}
export interface ManagedSkill {
  name: string
  content: string
  enabled: boolean
}
export interface ExtensionConfig {
  revision: number
  mcp_servers: MCPConfiguration[]
  skill_directories: string[]
  skills: ManagedSkill[]
  disabled_skills: string[]
}
export interface ExtensionSettings {
  config: ExtensionConfig
  active_config?: Pick<ExtensionConfig, 'revision' | 'mcp_servers'>
  extension_error?: string
  applied_revision: number
  reload_required: boolean
  reloading: boolean
  runtime_ready: boolean
  servers: MCPServerStatus[]
  skills: (InstalledSkill & { enabled: boolean })[]
  skill_errors: string[]
  management_available?: boolean
}

export interface AgentTask {
  id: string
  workspace_id: string
  conversation_id: string
  title: string
  status:
    | 'created'
    | 'queued'
    | 'running'
    | 'waiting_approval'
    | 'retry_wait'
    | 'succeeded'
    | 'failed'
    | 'cancelled'
    | 'timed_out'
    | 'interrupted'
  input_text: string
  last_error: string
  version: number
  created_at: string
  updated_at: string
}

export interface InstalledSkill {
  name: string
  version: string
  description: string
  kind: 'instruction' | 'workflow'
  source_path: string
  parameters_schema: Record<string, unknown>
}

export interface ConversationSnapshot {
  messages: ChatMessage[]
  tasks: AgentTask[]
  approvals: Approval[]
  questions: AgentQuestion[]
  last_sequence: number
  truncated: boolean
}

export interface TaskInput {
  id: string
  task_id: string
  content: string
  status: 'queued' | 'consumed' | 'not_consumed'
  created_at: string
}

export interface TaskInspection {
  task: AgentTask
  projection: { plan: PlanItem[] | null; truncated: boolean }
  last_sequence: number
}

export interface ProcessJob {
  id: string
  task_id: string
  conversation_id: string
  command: string
  status: string
  log_tail: string
  live: boolean
  live_logs_available: boolean
}

export interface MessageReceipt {
  task_id: string
  status: AgentTask['status'] | 'processing'
  replayed?: boolean
}

function chatModelFromWire(value: ChatModelWire): ChatModelSettings {
  return {
    provider: value.provider,
    model: value.model,
    baseUrl: value.base_url,
    temperature: value.temperature,
    maxTokens: value.max_tokens,
    timeoutSeconds: value.timeout_seconds,
    credentialConfigured: value.credential_configured ?? false,
  }
}

function chatModelToWire(value: ChatModelSettings): Omit<ChatModelWire, 'credential_configured'> {
  return {
    provider: value.provider,
    model: value.model,
    base_url: value.baseUrl,
    temperature: value.temperature,
    max_tokens: value.maxTokens,
    timeout_seconds: value.timeoutSeconds,
  }
}

function chatModelProfileFromWire(value: ChatModelWire): ChatModelProfile {
  return {
    ...chatModelFromWire(value),
    id: value.id || '',
    name: value.name || value.model,
    isDefault: value.is_default ?? false,
  }
}

function chatModelProfileToWire(value: ChatModelProfile): ChatModelWire {
  return {
    ...chatModelToWire(value),
    id: value.id || undefined,
    name: value.name,
    is_default: value.isDefault,
  }
}

const path = workspacePath
function folderQuery(folderId = '') {
  return folderId ? `folder_id=${encodeURIComponent(folderId)}` : ''
}

export const api = {
  async getHealth(): Promise<RuntimeHealth> {
    const body = await request<{
      status: 'ok' | 'degraded'
      agent_core?: string
      version?: string
    }>('/health')
    return { status: body.status, agentCore: body.agent_core, version: body.version }
  },
  async getWorkspaceRuntimeStatus(folderId = ''): Promise<WorkspaceRuntimeStatus> {
    const body = await request<{
      workspace_id: string
      workspace_root: string
      workspace_source: 'configuration' | 'environment' | 'selection'
      environment: string
      gateway: RuntimeServiceStatus
      agent_core: RuntimeServiceStatus
      restart: {
        pending: boolean
        required_for: string[]
        hot_applied: string[]
        note: string
      }
    }>(`${path}/runtime-status?${folderQuery(folderId)}`)
    return {
      workspaceId: body.workspace_id,
      workspaceRoot: body.workspace_root,
      workspaceSource: body.workspace_source,
      environment: body.environment,
      gateway: body.gateway,
      agentCore: body.agent_core,
      restart: {
        pending: body.restart.pending,
        requiredFor: body.restart.required_for || [],
        hotApplied: body.restart.hot_applied || [],
        note: body.restart.note,
      },
    }
  },
  async getUserPreferences(): Promise<UserPreferences> {
    const body = await request<{ assistant_name: string }>(`${path}/preferences`)
    return { assistantName: body.assistant_name }
  },
  async updateUserPreferences(preferences: UserPreferences): Promise<UserPreferences> {
    const body = await request<{ assistant_name: string }>(`${path}/preferences`, {
      method: 'PATCH',
      body: JSON.stringify({ assistant_name: preferences.assistantName }),
    })
    return { assistantName: body.assistant_name }
  },
  async getSettings(): Promise<{ chat: ChatModelSettings }> {
    const body = await request<{ models: { chat: ChatModelWire } }>(`${path}/settings`)
    return { chat: chatModelFromWire(body.models.chat) }
  },
  async updateChatModel(settings: ChatModelSettings): Promise<ChatModelSettings> {
    const body = await request<{ models: { chat: ChatModelWire } }>(`${path}/settings`, {
      method: 'PATCH',
      body: JSON.stringify({ models: { chat: chatModelToWire(settings) } }),
    })
    return chatModelFromWire(body.models.chat)
  },
  async listChatModels(): Promise<{ models: ChatModelProfile[]; defaultModelId: string }> {
    const body = await request<{ models: ChatModelWire[]; default_model_id: string }>(
      `${path}/models`,
    )
    return {
      models: (body.models || []).map(chatModelProfileFromWire),
      defaultModelId: body.default_model_id || '',
    }
  },
  async saveChatModel(
    profile: ChatModelProfile,
    apiKey = '',
    credentialSourceId = '',
  ): Promise<ChatModelProfile> {
    const url = profile.id ? `${path}/models/${encodeURIComponent(profile.id)}` : `${path}/models`
    const body = await request<ChatModelWire>(url, {
      method: profile.id ? 'PUT' : 'POST',
      body: JSON.stringify({
        ...chatModelProfileToWire(profile),
        api_key: apiKey || undefined,
        credential_source_id: !apiKey && credentialSourceId ? credentialSourceId : undefined,
      }),
    })
    return chatModelProfileFromWire(body)
  },
  deleteChatModel(id: string): Promise<void> {
    return request(`${path}/models/${encodeURIComponent(id)}`, { method: 'DELETE' })
  },
  async setDefaultChatModel(
    id: string,
  ): Promise<{ models: ChatModelProfile[]; defaultModelId: string }> {
    const body = await request<{ models: ChatModelWire[]; default_model_id: string }>(
      `${path}/models/${encodeURIComponent(id)}/default`,
      { method: 'POST' },
    )
    return {
      models: body.models.map(chatModelProfileFromWire),
      defaultModelId: body.default_model_id,
    }
  },
  validateChatModel(
    settings: ChatModelSettings | ChatModelProfile,
    apiKey = '',
  ): Promise<{ ok: boolean; message: string; model: string }> {
    const profile = settings as Partial<ChatModelProfile>
    return request(`${path}/models/actions/validate`, {
      method: 'POST',
      body: JSON.stringify({
        chat: {
          ...chatModelToWire(settings),
          id: profile.id || undefined,
          name: profile.name || undefined,
        },
        api_key: apiKey,
      }),
    })
  },
  async discoverChatModels(
    settings: Pick<ChatModelSettings, 'provider' | 'baseUrl'> &
      Partial<Pick<ChatModelProfile, 'id'>>,
    apiKey = '',
    signal?: AbortSignal,
  ): Promise<DiscoveredChatModel[]> {
    const body = await request<{ models: DiscoveredChatModel[] }>(
      `${path}/models/actions/discover`,
      {
        method: 'POST',
        signal,
        body: JSON.stringify({
          id: settings.id || undefined,
          provider: settings.provider,
          base_url: settings.baseUrl,
          api_key: apiKey || undefined,
        }),
      },
    )
    return body.models || []
  },
  async listCredentialReferences(): Promise<CredentialStatus[]> {
    const body = await request<{ engines: CredentialStatus[] }>(`${path}/credential-references`)
    return body.engines || []
  },
  saveCredential(service: string, apiKey: string): Promise<void> {
    return request(`${path}/credential-references`, {
      method: 'POST',
      body: JSON.stringify({ service, api_key: apiKey }),
    })
  },
  deleteCredential(service: string): Promise<void> {
    return request(`${path}/credential-references/${encodeURIComponent(service)}`, {
      method: 'DELETE',
    })
  },
  async listMemories(query = ''): Promise<UserMemory[]> {
    const suffix = query.trim() ? `?q=${encodeURIComponent(query.trim())}` : ''
    const body = await request<{ memories: UserMemory[] }>(`${path}/memories${suffix}`)
    return body.memories || []
  },
  saveMemory(memory: MemoryInput & { id?: string }): Promise<UserMemory> {
    const url = memory.id ? `${path}/memories/${encodeURIComponent(memory.id)}` : `${path}/memories`
    return request(url, {
      method: memory.id ? 'PATCH' : 'POST',
      body: JSON.stringify({
        category: memory.category,
        content: memory.content,
        confidence: memory.confidence,
      }),
    })
  },
  deleteMemory(id: string): Promise<void> {
    return request(`${path}/memories/${encodeURIComponent(id)}`, { method: 'DELETE' })
  },
  getWorkspaceDataSummary(): Promise<WorkspaceDataSummary> {
    return request(`${path}/data-summary`)
  },
  async listMCPServers(): Promise<MCPServerStatus[]> {
    const body = await request<{ servers: MCPServerStatus[] }>(`${path}/mcp-servers`)
    return body.servers || []
  },
  async listSkills(): Promise<InstalledSkill[]> {
    const body = await request<{ skills: InstalledSkill[] }>(`${path}/skills`)
    return body.skills || []
  },
  getExtensions(): Promise<ExtensionSettings> {
    return request(`${path}/extension-settings`)
  },
  saveExtensions(config: ExtensionConfig): Promise<ExtensionSettings> {
    return request(`${path}/extension-settings`, { method: 'PUT', body: JSON.stringify(config) })
  },
  applyExtensions(revision: number, restoreOnly = false): Promise<ExtensionSettings> {
    return request(`${path}/extension-settings/apply`, {
      method: 'POST',
      body: JSON.stringify({ revision, restore_only: restoreOnly }),
    })
  },
  async listTasks(conversationId?: string): Promise<AgentTask[]> {
    const query = conversationId ? `?conversation_id=${encodeURIComponent(conversationId)}` : ''
    const body = await request<{ tasks: AgentTask[] }>(`${path}/tasks${query}`)
    return body.tasks || []
  },
  submitTaskInput(taskId: string, content: string, key: string): Promise<TaskInput> {
    return request(`${path}/tasks/${encodeURIComponent(taskId)}/inputs`, {
      method: 'POST',
      headers: { 'Idempotency-Key': key },
      body: JSON.stringify({ content }),
    })
  },
  async listTaskInputs(taskId: string, signal?: AbortSignal): Promise<TaskInput[]> {
    const body = await request<{ inputs: TaskInput[] }>(
      `${path}/tasks/${encodeURIComponent(taskId)}/inputs`,
      { signal },
    )
    return body.inputs || []
  },
  getTaskInspection(taskId: string, signal?: AbortSignal): Promise<TaskInspection> {
    return request(`${path}/tasks/${encodeURIComponent(taskId)}/inspection`, { signal })
  },
  async listJobs(conversationId: string, signal?: AbortSignal): Promise<ProcessJob[]> {
    const body = await request<{ jobs: ProcessJob[] }>(
      `${path}/jobs?conversation_id=${encodeURIComponent(conversationId)}`,
      { signal },
    )
    return body.jobs || []
  },
  async getCapabilities(): Promise<Record<string, boolean>> {
    const body = await request<{ capabilities: Record<string, boolean> }>(`${path}/capabilities`)
    return body.capabilities || {}
  },
  resumeTask(taskId: string, version: number): Promise<MessageReceipt> {
    return request(`${path}/tasks/${encodeURIComponent(taskId)}/resume`, {
      method: 'POST',
      body: JSON.stringify({ version }),
    })
  },
  cancelTask(taskId: string): Promise<AgentTask> {
    return request(`${path}/tasks/${encodeURIComponent(taskId)}/cancel`, { method: 'POST' })
  },
  async listTaskEvents(
    conversationId: string,
    after = 0,
    signal?: AbortSignal,
  ): Promise<AgentEvent[]> {
    const body = await request<{ events: AgentEvent[] }>(
      `${path}/conversations/${encodeURIComponent(conversationId)}/events/history?after=${after}`,
      { signal },
    )
    return body.events || []
  },
  async listConversations(): Promise<Conversation[]> {
    const body = await request<{ conversations: Conversation[] }>(`${path}/conversations`)
    return body.conversations || []
  },
  async listWorkspaceFolders(): Promise<WorkspaceFolder[]> {
    const body = await request<{ folders?: WorkspaceFolder[] }>(`${path}/folders`)
    return (body.folders || []).map((folder) => ({ ...folder, id: folder.id || '' }))
  },
  async createWorkspaceFolder(rootPath: string, name = ''): Promise<WorkspaceFolder> {
    const folder = await request<WorkspaceFolder>(`${path}/folders`, {
      method: 'POST',
      body: JSON.stringify({ root_path: rootPath, name }),
    })
    return { ...folder, id: folder.id || '' }
  },
  getConversation(id: string): Promise<Conversation> {
    return request(`${path}/conversations/${encodeURIComponent(id)}`)
  },
  deleteConversation(id: string): Promise<void> {
    return request(`${path}/conversations/${encodeURIComponent(id)}`, { method: 'DELETE' })
  },
  createConversation(data: {
    subagent_model_ids?: string[]
    max_subagent_calls?: number
    max_concurrent_subagents?: number
    title?: string
    permission_mode?: PermissionMode
    model_id?: string
    response_mode?: ResponseMode
    folder_id?: string
  }): Promise<Conversation> {
    return request(`${path}/conversations`, { method: 'POST', body: JSON.stringify(data) })
  },
  updateConversationPermission(id: string, permissionMode: PermissionMode): Promise<Conversation> {
    return request(`${path}/conversations/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ permission_mode: permissionMode }),
    })
  },
  updateConversationSettings(
    id: string,
    settings: {
      permission_mode?: PermissionMode
      model_id?: string
      response_mode?: ResponseMode
      title?: string
      folder_id?: string
      archived?: boolean
      max_subagent_calls?: number
      max_concurrent_subagents?: number
      subagent_model_ids?: string[]
    },
  ): Promise<Conversation> {
    return request(`${path}/conversations/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(settings),
    })
  },
  async listMessages(id: string): Promise<ChatMessage[]> {
    const body = await request<{ messages: ChatMessage[] }>(`${path}/conversations/${id}/messages`)
    return body.messages || []
  },
  async getConversationSnapshot(id: string): Promise<ConversationSnapshot> {
    // Snapshot approvals currently use the protobuf JSON shape; keep it out of stores.
    const body = await request<
      Omit<ConversationSnapshot, 'approvals' | 'questions'> & {
        approvals: (Approval & { arguments_json?: string })[]
        questions: (AgentQuestion & { options_json?: string })[]
      }
    >(`${path}/conversations/${encodeURIComponent(id)}/snapshot`)
    return {
      messages: body.messages || [],
      tasks: body.tasks || [],
      questions: (body.questions || []).map(({ options_json, ...question }) => ({
        ...question,
        options: options_json ? JSON.parse(options_json) : question.options || [],
      })),
      approvals: (body.approvals || []).map(({ arguments_json, ...approval }) => ({
        ...approval,
        arguments: arguments_json ? JSON.parse(arguments_json) : approval.arguments || {},
      })),
      last_sequence: Number(body.last_sequence || 0),
      truncated: Boolean(body.truncated),
    }
  },
  sendMessage(id: string, content: string, idempotencyKey: string): Promise<MessageReceipt> {
    return request(`${path}/conversations/${id}/messages`, {
      method: 'POST',
      headers: { 'Idempotency-Key': idempotencyKey },
      body: JSON.stringify({ content }),
    })
  },
  async listApprovals(conversationId?: string): Promise<Approval[]> {
    const query = conversationId ? `?conversation_id=${encodeURIComponent(conversationId)}` : ''
    const body = await request<{ approvals: Approval[] }>(`${path}/approvals${query}`)
    return body.approvals || []
  },
  async listQuestions(conversationId?: string): Promise<AgentQuestion[]> {
    const query = conversationId ? `?conversation_id=${encodeURIComponent(conversationId)}` : ''
    const body = await request<{ questions: AgentQuestion[] }>(`${path}/questions${query}`)
    return body.questions || []
  },
  answerQuestion(id: string, answer: string, version: number): Promise<{ task_id: string }> {
    return request(`${path}/questions/${encodeURIComponent(id)}/answer`, {
      method: 'POST',
      body: JSON.stringify({ answer, version }),
    })
  },
  decideApproval(
    id: string,
    decision: 'allow' | 'deny',
    version: number,
    note?: string,
  ): Promise<{ task_id: string }> {
    return request(`${path}/approvals/${encodeURIComponent(id)}/decision`, {
      method: 'POST',
      body: JSON.stringify({ decision, version, note }),
    })
  },
  getPermissionSettings(): Promise<PermissionSettings> {
    return request(`${path}/permissions`)
  },
  getToolSettings(): Promise<ToolSettings> {
    return request(`${path}/tool-settings`)
  },
  updateToolSettings(enabled: Record<string, boolean>): Promise<ToolSettings> {
    return request(`${path}/tool-settings`, { method: 'PATCH', body: JSON.stringify({ enabled }) })
  },
  updatePermissionSettings(settings: PermissionSettings): Promise<PermissionSettings> {
    return request(`${path}/permissions`, { method: 'PATCH', body: JSON.stringify(settings) })
  },
  async listAuditEvents(): Promise<AuditEvent[]> {
    const body = await request<{ events: AuditEvent[] }>(`${path}/audit-events`)
    return body.events || []
  },
  async listWorkspaceFiles(relativePath = '', folderId = ''): Promise<WorkspaceFileEntry[]> {
    const body = await request<{ entries: WorkspaceFileEntry[] }>(
      `${path}/files?path=${encodeURIComponent(relativePath)}&${folderQuery(folderId)}`,
    )
    return body.entries || []
  },
  getWorkspaceFile(relativePath: string, folderId = ''): Promise<WorkspaceFileContent> {
    return request(
      `${path}/files/content?path=${encodeURIComponent(relativePath)}&${folderQuery(folderId)}`,
    )
  },
  async listWorkspaceChanges(folderId = ''): Promise<{
    changes: WorkspaceChange[]
    git: boolean
    truncated: boolean
  }> {
    return request(`${path}/changes?${folderQuery(folderId)}`)
  },
  async getWorkspaceDiff(filePath: string, folderId = ''): Promise<WorkspaceChange> {
    return request(
      `${path}/changes/diff?path=${encodeURIComponent(filePath)}&${folderQuery(folderId)}`,
    )
  },
  connectEvents(conversationId: string, onEvent: (event: AgentEvent) => void): WebSocket {
    if (import.meta.env.VITE_MOCK === '1') return mockConnect(conversationId, onEvent)
    const configured = import.meta.env.VITE_WS_URL
    const host = location.protocol === 'file:' ? '127.0.0.1:8080' : location.host
    const base = configured || `${location.protocol === 'https:' ? 'wss' : 'ws'}://${host}`
    const socket = new WebSocket(
      `${base}${path}/events?conversation_id=${encodeURIComponent(conversationId)}`,
    )
    socket.onmessage = ({ data }) => {
      try {
        const event: unknown = JSON.parse(String(data))
        if (event && typeof event === 'object' && 'type' in event && 'payload' in event)
          onEvent(event as AgentEvent)
      } catch {
        /* A malformed frame must not interrupt reconnection/replay. */
      }
    }
    return socket
  },
}
