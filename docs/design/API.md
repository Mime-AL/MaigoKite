# NanamiGopher API 设计

> **状态**：Current
> **架构版本**：v1
> **最后核验**：2026-09-18
> **权威范围**：REST 资源、gRPC 服务、WebSocket 事件及兼容规则

最终机器契约应分别由 OpenAPI、Proto 和事件 Schema 表达；本文档说明稳定资源与行为，不复制生成代码。

## 1. 协议边界

| 边界 | 协议 | 服务端 |
|---|---|---|
| UI → Gateway | HTTPS REST | Go Gateway |
| UI ↔ Gateway | WSS | Go Gateway |
| Gateway → Agent Core | gRPC | Python Agent Core |
| Agent Core ↔ MCP Server | MCP stdio | MCP Server |

## 2. 通用调用上下文

外部请求经过 Gateway 认证后形成可信上下文：

```text
request_id
trace_id
principal_id
workspace_id
client_version
deadline
```

- 外部客户端不得在请求体中覆盖 `principal_id`。
- `workspace_id` 可来自路径或请求头，但必须经过 Membership 校验。
- 资源不存在和无权访问应按安全策略返回一致外观，避免枚举。

## 3. REST 资源

统一前缀：`/api/v1`。

### 3.1 身份与 Workspace

当前版本没有独立的 `/me`、Workspace CRUD 或成员管理 REST。所有已注册资源都位于 `/workspaces/{workspace_id}` 下，由本地访问中间件与 Agent Core Membership 检查共同约束。以下是团队部署目标，尚未注册：

```text
GET    /me
GET    /workspaces
POST   /workspaces
GET    /workspaces/{workspace_id}
GET    /workspaces/{workspace_id}/members
POST   /workspaces/{workspace_id}/members
DELETE /workspaces/{workspace_id}/members/{user_id}
```

### 3.2 会话与消息

```text
GET    /workspaces/{workspace_id}/conversations
POST   /workspaces/{workspace_id}/conversations
GET    /workspaces/{workspace_id}/conversations/{conversation_id}
PATCH  /workspaces/{workspace_id}/conversations/{conversation_id}
DELETE /workspaces/{workspace_id}/conversations/{conversation_id}
GET    /workspaces/{workspace_id}/conversations/{conversation_id}/messages
POST   /workspaces/{workspace_id}/conversations/{conversation_id}/messages
```

发送消息返回已创建的 `task_id`；增量结果通过事件流提供。

### 3.3 任务、工具调用与审批

```text
GET  /workspaces/{workspace_id}/tasks?conversation_id={conversation_id}
GET  /workspaces/{workspace_id}/tasks/{task_id}
POST /workspaces/{workspace_id}/tasks/{task_id}/cancel
GET  /workspaces/{workspace_id}/conversations/{conversation_id}/events/history?after={sequence}
GET  /workspaces/{workspace_id}/approvals
POST /workspaces/{workspace_id}/approvals/{approval_id}/decision
```

任务重试和 ToolCall 独立查询尚未注册。取消终止任务并拒绝该任务仍 pending 的审批；第三方 MCP 调用能否立即被 transport 中止仍有限制。

审批由 Agent Core 创建，外部 API 不提供任意创建审批请求的入口。审批决定必须包含目标审批 ID、decision 和审批版本；参数从服务端保存的规范化 ToolCall 读取，客户端不能在决定时替换参数，服务端同时验证版本与过期时间。

### 3.4 Memory 与 Knowledge（Phase 2 In Progress）

当前已注册的 User Memory 契约：

```text
GET    /workspaces/{workspace_id}/memories
POST   /workspaces/{workspace_id}/memories
PATCH  /workspaces/{workspace_id}/memories/{memory_id}
DELETE /workspaces/{workspace_id}/memories/{memory_id}
GET    /workspaces/{workspace_id}/data-summary
```

`GET memories?q=` 当前执行大小写不敏感的关键词查询。所有 Memory 操作使用认证主体作为 `subject_user_id`，客户端不能指定其他用户；写入、修改或删除与对应审计事件在同一数据库事务提交。`data-summary` 仅 Workspace Owner 可读，返回权威数据计数，不返回内容。

以下 Knowledge/索引端点仍是目标契约，尚未注册：

```text
GET    /workspaces/{workspace_id}/documents
POST   /workspaces/{workspace_id}/documents
GET    /workspaces/{workspace_id}/documents/{document_id}
DELETE /workspaces/{workspace_id}/documents/{document_id}
POST   /workspaces/{workspace_id}/indexes:rebuild
```

### 3.5 Skill 与 MCP

当前已注册以下只读运行清单：

```text
GET /workspaces/{workspace_id}/skills
GET /workspaces/{workspace_id}/mcp-servers
```

`skills` 返回从配置目录实际加载的本地声明式 Skill 元数据；`mcp-servers` 返回 Agent Core 实际加载的部署级 stdio Server、状态和工具名。二者都不是安装或 Grant 管理接口。

以下端点是目标契约，当前尚未注册：

```text
POST   /workspaces/{workspace_id}/skills:import
POST   /workspaces/{workspace_id}/skills:install
GET    /workspaces/{workspace_id}/skills/{skill_id}
PATCH  /workspaces/{workspace_id}/skills/{skill_id}
DELETE /workspaces/{workspace_id}/skills/{skill_id}
```

- `import` 接收本地包或目录归档。
- `install` 接收受支持的注册源和不可变版本引用。
- 二者共用验证、权限预览和 SkillGrant 创建流程。

### 3.6 设置、模型和凭证引用

```text
GET   /workspaces/{workspace_id}/settings
PATCH /workspaces/{workspace_id}/settings
GET   /workspaces/{workspace_id}/models
POST  /workspaces/{workspace_id}/models
PUT   /workspaces/{workspace_id}/models/{model_id}
DELETE /workspaces/{workspace_id}/models/{model_id}
POST  /workspaces/{workspace_id}/models/{model_id}/default
POST  /workspaces/{workspace_id}/models/actions/validate
POST  /workspaces/{workspace_id}/models/actions/discover
GET   /workspaces/{workspace_id}/credential-references
POST  /workspaces/{workspace_id}/credential-references
PUT   /workspaces/{workspace_id}/credential-references/{credential_id}
DELETE /workspaces/{workspace_id}/credential-references/{credential_id}
GET   /workspaces/{workspace_id}/preferences
PATCH /workspaces/{workspace_id}/preferences
GET   /workspaces/{workspace_id}/runtime-status
```

读取凭证只返回引用和元数据，不返回 Secret 值。

Phase 1 中，模型 API 管理 Workspace 的 Chat 模型配置集合，并保证最多一个默认模型；`models/actions/validate` 使用提交的草稿配置做一次最小模型调用，不保存草稿。`models/actions/discover` 根据 Provider 与 Base URL 查询服务端模型目录：OpenAI、Anthropic 和兼容端点使用 `/models`，Ollama 使用 `/api/tags`。它优先使用本次草稿中的 Key；仅当 Provider 与 Base URL 同已保存配置完全匹配时，才读取该配置的 CredentialStore 引用。结果和 Secret 都不持久化。目录请求禁用重定向、系统代理和链路本地地址，防止 Key 被转发到非预期端点。

设置写入、目录发现、连接验证和凭证管理只允许 Workspace Owner。模型凭证按模型配置 ID 隔离（`model-profile.{id}`），保存后由 Gateway 同步到 Agent Core 内存，发送消息前再次从 OS CredentialStore 同步当前会话选择的配置。修改 Provider/Base URL 会使旧凭证失效，Secret 不进入领域数据库或事件。

联网搜索凭证使用 `tavily`、`google` 引用名。Gateway 保存或删除引用时通过内部 gRPC 同步 Agent Core，并在每次消息任务开始前重新同步，以覆盖 Core 重启场景。搜索失败事件只携带稳定错误码、用户提示和设置路由，不携带 Secret。

Phase 1 另提供 `GET/PATCH /workspaces/{workspace_id}/permissions` 管理三档默认执行模式：`read_only / workspace / full_access`；不向普通客户端暴露逐工具风险矩阵。`PATCH conversations/{conversation_id}` 可修改当前会话的 `model_id`、`response_mode` 和 `permission_mode`。服务端验证模型属于当前 Workspace；L1–L5 风险、参数升级和 hard-deny 由 ToolPolicy 内部维护。

`preferences` 是当前主体在 Workspace 中的用户级偏好。Phase 1 支持 `assistant_name`（1–32 个字符），用于界面称呼；团队成员只修改自己的显示偏好，不会改变 Workspace 全局名称。

`runtime-status` 是 Workspace Owner 可见的只读投影，返回规范化 Workspace 根目录及来源、Gateway/Agent Core 状态和版本、即时生效项与需重启项。它不修改部署配置，也不声称能够检测运行期间手工编辑的外部 YAML。

### 3.7 Workspace 文件与变更

```text
GET /workspaces/{workspace_id}/files?path={relative_path}
GET /workspaces/{workspace_id}/files/content?path={relative_file}
GET /workspaces/{workspace_id}/changes
GET /workspaces/{workspace_id}/changes/diff?path={relative_file}
```

这些接口是受 Workspace 根目录约束的只读投影：拒绝绝对路径、`..` 穿越和逃逸根目录的符号链接；预览限制为 512 KiB，变更列表最多 200 项，Diff 在用户选中文件后懒加载并限制为 256 KiB，截断状态随响应返回。`changes` 在非 Git Workspace 返回 `git: false`，不执行写入或暂存操作。

## 4. 命令语义

- 当前审批决定使用版本号防止重复决定和丢失更新。
- 通用 `Idempotency-Key`、ETag、任务 retry 动作仍是 Planned，客户端当前不得假设已经支持。
- 取消、审批和重试使用显式动作，不伪装成普通字段 PATCH。

## 5. gRPC 服务

Python Agent Core 当前由一个 `AgentService` 提供 ProcessMessage、Conversation、Task、TaskEvent、Approval、Model、Skill/MCP 等 RPC。下面的按领域拆分是未来契约目标，并非当前 Proto：

```protobuf
service AgentCommandService {
  rpc SendMessage(SendMessageRequest) returns (SendMessageResponse);
  rpc CancelTask(CancelTaskRequest) returns (TaskResponse);
  rpc RetryTask(RetryTaskRequest) returns (TaskResponse);
  rpc DecideApproval(DecideApprovalRequest) returns (ApprovalResponse);
}

service AgentQueryService {
  rpc GetTask(GetTaskRequest) returns (TaskResponse);
  rpc ListMessages(ListMessagesRequest) returns (ListMessagesResponse);
  rpc SearchMemories(SearchMemoriesRequest) returns (SearchMemoriesResponse);
}

service AgentEventService {
  rpc Subscribe(SubscribeRequest) returns (stream AgentEvent);
}
```

目标领域服务将统一使用 `CallContext`；当前单体 Proto 仍在各请求上直接携带 `workspace_id`、`principal_id` 等必要字段。Proto 中字段一旦发布不得重编号，删除字段必须 `reserved`。

当前 Proto 使用自定义 `Health` RPC，Gateway 对外提供 HTTP `/health`。切换到标准 gRPC Health Checking 属于后续兼容性改造，不能按已实现能力部署探针。

## 6. WebSocket 事件

连接：

```text
GET /api/v1/workspaces/{workspace_id}/events?conversation_id={conversation_id}
```

事件信封：

```json
{
  "schema_version": 1,
  "event_id": "evt_...",
  "sequence": 42,
  "type": "task.started",
  "occurred_at": "2026-09-14T00:00:00Z",
  "conversation_id": "conv_...",
  "task_id": "task_...",
  "payload": {}
}
```

稳定事件类型：

```text
message.delta
message.completed
task.started
task.waiting_approval
task.succeeded
task.failed
task.cancelled
task.interrupted
reasoning.started
reasoning.delta
reasoning.completed
tool.proposed
tool.started
tool.completed
tool.failed
subagent.started
subagent.progress
subagent.completed
subagent.failed
approval.requested
approval.decided
```

`message.*` 只承载用户可见的最终回答。模型主动输出的简短过程说明使用 `reasoning.*`，工具与子 Agent 生命周期分别使用 `tool.*` 和 `subagent.*`；三者均通过 `task_id` 关联任务，不写入 Message 资源。系统不传输模型隐藏思维链。

客户端按 `event_id` 去重，按 `sequence` 检测缺口。断线不取消任务；当前先通过 REST `events/history?after=` 重放，建立 WebSocket 后再按最新 sequence 补拉一次，覆盖普通连接窗口。原子 `after_sequence` WebSocket 握手和历史分页仍是 Planned。

## 7. 错误模型

```json
{
  "error": {
    "code": "APPROVAL_EXPIRED",
    "message": "审批已过期",
    "request_id": "req_...",
    "retryable": false,
    "details": {}
  }
}
```

稳定类别：Validation、Unauthenticated、AccessDenied、NotFound、Conflict、ApprovalRequired、ToolDenied、RateLimited、Timeout、DependencyUnavailable、Internal。

错误消息不得包含 Secret、原始系统提示、内部路径或未脱敏工具输出。

## 8. 版本策略

- REST 主版本位于路径。
- Event 使用 `schema_version`。
- Proto 遵循字段兼容规则。
- Breaking change 必须新增版本并记录 ADR。
- Markdown 示例通过机器 Schema 校验，避免与实现漂移。
