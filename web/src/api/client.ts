export type PermissionMode = 'read_only' | 'workspace' | 'full_access'
export type ResponseMode = 'fast' | 'balanced' | 'thorough'

export interface Conversation {
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
  workspaceSource: 'configuration' | 'environment'
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

const workspaceId = 'personal'
const localGateway = location.protocol === 'file:' ? 'http://127.0.0.1:8080' : ''
const apiBase = import.meta.env.VITE_API_BASE_URL || localGateway
const path = `/api/v1/workspaces/${workspaceId}`

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${url}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  })
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {
      error?: string | { message?: string }
    } | null
    const message = typeof body?.error === 'string' ? body.error : body?.error?.message
    if (response.status === 404 && !message) {
      throw new Error('Gateway 未提供该接口，请重启应用或重新运行 make dev 以加载最新运行时。')
    }
    throw new Error(message || `Request failed (${response.status})`)
  }
  return response.status === 204 ? (undefined as T) : response.json()
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
  async getWorkspaceRuntimeStatus(): Promise<WorkspaceRuntimeStatus> {
    const body = await request<{
      workspace_id: string
      workspace_root: string
      workspace_source: 'configuration' | 'environment'
      environment: string
      gateway: RuntimeServiceStatus
      agent_core: RuntimeServiceStatus
      restart: {
        pending: boolean
        required_for: string[]
        hot_applied: string[]
        note: string
      }
    }>(`${path}/runtime-status`)
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
  async saveChatModel(profile: ChatModelProfile, apiKey = ''): Promise<ChatModelProfile> {
    const url = profile.id ? `${path}/models/${encodeURIComponent(profile.id)}` : `${path}/models`
    const body = await request<ChatModelWire>(url, {
      method: profile.id ? 'PUT' : 'POST',
      body: JSON.stringify({ ...chatModelProfileToWire(profile), api_key: apiKey || undefined }),
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
  ): Promise<DiscoveredChatModel[]> {
    const body = await request<{ models: DiscoveredChatModel[] }>(
      `${path}/models/actions/discover`,
      {
        method: 'POST',
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
  async listConversations(): Promise<Conversation[]> {
    const body = await request<{ conversations: Conversation[] }>(`${path}/conversations`)
    return body.conversations || []
  },
  createConversation(data: {
    title?: string
    permission_mode?: PermissionMode
    model_id?: string
    response_mode?: ResponseMode
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
    settings: { permission_mode?: PermissionMode; model_id?: string; response_mode?: ResponseMode },
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
  sendMessage(id: string, content: string): Promise<{ task_id: string }> {
    return request(`${path}/conversations/${id}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content }),
    })
  },
  async listApprovals(conversationId?: string): Promise<Approval[]> {
    const query = conversationId ? `?conversation_id=${encodeURIComponent(conversationId)}` : ''
    const body = await request<{ approvals: Approval[] }>(`${path}/approvals${query}`)
    return body.approvals || []
  },
  decideApproval(
    id: string,
    decision: 'allow' | 'deny',
    version: number,
  ): Promise<{ task_id: string }> {
    return request(`${path}/approvals/${encodeURIComponent(id)}/decision`, {
      method: 'POST',
      body: JSON.stringify({ decision, version }),
    })
  },
  getPermissionSettings(): Promise<PermissionSettings> {
    return request(`${path}/permissions`)
  },
  updatePermissionSettings(settings: PermissionSettings): Promise<PermissionSettings> {
    return request(`${path}/permissions`, { method: 'PATCH', body: JSON.stringify(settings) })
  },
  async listAuditEvents(): Promise<AuditEvent[]> {
    const body = await request<{ events: AuditEvent[] }>(`${path}/audit-events`)
    return body.events || []
  },
  async listWorkspaceFiles(relativePath = ''): Promise<WorkspaceFileEntry[]> {
    const body = await request<{ entries: WorkspaceFileEntry[] }>(
      `${path}/files?path=${encodeURIComponent(relativePath)}`,
    )
    return body.entries || []
  },
  getWorkspaceFile(relativePath: string): Promise<WorkspaceFileContent> {
    return request(`${path}/files/content?path=${encodeURIComponent(relativePath)}`)
  },
  async listWorkspaceChanges(): Promise<{
    changes: WorkspaceChange[]
    git: boolean
    truncated: boolean
  }> {
    return request(`${path}/changes`)
  },
  async getWorkspaceDiff(filePath: string): Promise<WorkspaceChange> {
    return request(`${path}/changes/diff?path=${encodeURIComponent(filePath)}`)
  },
  connectEvents(conversationId: string, onEvent: (event: AgentEvent) => void): WebSocket {
    const configured = import.meta.env.VITE_WS_URL
    const host = location.protocol === 'file:' ? '127.0.0.1:8080' : location.host
    const base = configured || `${location.protocol === 'https:' ? 'wss' : 'ws'}://${host}`
    const socket = new WebSocket(
      `${base}${path}/events?conversation_id=${encodeURIComponent(conversationId)}`,
    )
    socket.onmessage = ({ data }) => onEvent(JSON.parse(String(data)) as AgentEvent)
    return socket
  },
}
