# NanamiGopher API 设计

> **状态**：当前有效
> **架构版本**：v1
> **最后核验**：2026-09-18
> **权威范围**：REST 资源、gRPC 服务、WebSocket 事件及兼容规则

最终机器契约应分别由 OpenAPI、Proto 和事件 Schema 表达；本文档说明稳定资源与行为，不复制生成代码。

## 1. 协议边界

| 边界 | 协议 | 服务端 |
|---|---|---|
| UI → 网关 | HTTPS REST | Go 网关 |
| UI ↔ 网关 | WSS | Go 网关 |
| 网关 → 智能体核心 | gRPC | Python 智能体核心 |
| 智能体核心 ↔ MCP Server | MCP stdio | MCP Server |

## 2. 通用调用上下文

外部请求应经过网关身份/资源校验形成可信上下文。以下是目标关联字段；当前请求仅携带部分主体/工作区字段，request/trace/deadline 尚未统一传播：

```text
request_id
trace_id
principal_id
workspace_id
client_version
deadline
```

- 外部客户端不得在请求体中覆盖 `principal_id`。
- `workspace_id` 可来自路径或请求头，但必须经过成员关系校验。
- 资源不存在和无权访问时，应按安全策略返回形式一致的响应，避免资源枚举。

## 3. REST 资源

统一前缀：`/api/v1`。

### 3.1 身份与工作区

当前版本没有独立的 `/me`、工作区 CRUD 或成员管理 REST。所有已注册资源都位于 `/workspaces/{workspace_id}` 下，受本地访问中间件与智能体核心成员关系检查共同约束。网关当前固定映射到 `local-user`，这不构成远程设备认证。团队身份、工作区 CRUD 与成员管理已移出当前路线，不在本文保留未注册接口草案。

手机访问为规划中，范围以 [手机远程访问](RemoteAccess.md) 为准。配对设备关联同一个个人主体；首版复用会话、任务、审批和 UI Event DTO，仅开放明确列出的远程资源。配对、会话和撤销的具体契约在实施时补充，本文不将它们列成已存在的端点。

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

任务重试和工具调用独立查询尚未注册。取消操作请求停止任务，并关闭仍待处理的审批；实际停止确认和清理顺序取决于当前执行路径，见 [智能体运行时设计](AgentRuntime.md)。第三方 MCP 调用能否立即被传输方式中止，仍有限制。

审批由智能体核心创建，外部 API 不提供任意创建审批请求的入口。审批决定必须包含目标审批 ID、decision 和审批版本。服务端从已保存的规范化工具调用读取参数，同时验证版本与过期时间；客户端不能在决定时替换参数。

### 3.4 用户记忆与数据摘要

当前已注册的用户记忆契约：

```text
GET    /workspaces/{workspace_id}/memories
POST   /workspaces/{workspace_id}/memories
PATCH  /workspaces/{workspace_id}/memories/{memory_id}
DELETE /workspaces/{workspace_id}/memories/{memory_id}
GET    /workspaces/{workspace_id}/data-summary
```

`GET memories?q=` 当前执行大小写不敏感的关键词查询。所有记忆操作都使用认证主体作为 `subject_user_id`，客户端不能指定其他用户。写入、修改或删除操作与对应审计事件在同一数据库事务中提交。`data-summary` 仅工作区所有者可读，返回权威数据计数，不返回内容。

文档导入、检索和索引重建接口尚未注册；只有能力闭环时再定义契约，范围见 [记忆与检索](../agent-capabilities/memory/memory-system.md)。

### 3.5 技能与 MCP

当前已注册以下只读运行清单：

```text
GET /workspaces/{workspace_id}/skills
GET /workspaces/{workspace_id}/mcp-servers
```

`skills` 返回从配置目录实际加载的本地声明式技能元数据；`mcp-servers` 返回智能体核心实际加载的部署级 stdio Server、状态和工具名。二者都不是安装或 Grant 管理接口。

技能包导入、安装、启停与版本授权 API 尚未实现；不保留与当前路径相似的假接口清单，扩展门槛见 [技能](../agent-capabilities/skills/skill-lifecycle.md)。

### 3.6 设置、模型和凭证引用

```text
GET   /workspaces/{workspace_id}/settings
PATCH /workspaces/{workspace_id}/settings
GET   /workspaces/{workspace_id}/tool-settings
PATCH /workspaces/{workspace_id}/tool-settings
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

`tool-settings` 仅工作区所有者可读写。GET 返回实际注册工具的 `name / description / source /
enabled / configurable / default_enabled`；PATCH 请求为 `{"enabled":{"web_search":true,"sleep":false}}`，
按工具名合并选择并返回完整目录。未知工具、非布尔值和尝试开启启动配置已停用的工具均被拒绝。
选择保存到既有 Workspace 设置，不修改 YAML、不授予权限、不启动新 MCP 服务；可见性与审批是独立边界。
新增启用项在新任务/恢复生效，停用限制后续调用，不撤销已开始的副作用。

读取凭证只返回引用和元数据，不返回敏感凭证值。

阶段 1 中，模型 API 管理工作区的聊天模型配置集合，并保证最多一个默认模型。`models/actions/validate` 使用提交的草稿配置做一次最小模型调用，不保存草稿。`models/actions/discover` 根据模型提供方与基础地址查询服务端模型目录：OpenAI、Anthropic 和兼容端点使用 `/models`，Ollama 使用 `/api/tags`。

目录发现优先使用本次草稿中的 Key。仅当模型提供方与基础地址同已保存配置完全匹配时，才读取该配置的凭证存储引用。结果和敏感凭证都不持久化。目录请求禁用重定向、系统代理和链路本地地址，防止 Key 被转发到非预期端点。

设置写入、目录发现、连接验证和凭证管理只允许工作区所有者。模型凭证按模型配置 ID 隔离（`model-profile.{id}`）。保存后，网关将凭证同步到智能体核心内存；发送消息前，再次从 OS 凭证存储同步当前会话选择的配置。修改模型提供方/基础地址会使旧凭证失效。敏感凭证不进入领域数据库或事件。

联网搜索凭证使用 `tavily`、`google` 引用名。网关保存或删除引用时通过内部 gRPC 同步智能体核心，并在每次消息任务开始前重新同步，以覆盖核心服务重启场景。搜索失败事件只携带稳定错误码、用户提示和设置路由，不携带敏感凭证。

阶段 1 另提供 `GET/PATCH /workspaces/{workspace_id}/permissions` 管理三档默认执行模式：`read_only / workspace / full_access`；不向普通客户端暴露逐工具风险矩阵。`PATCH conversations/{conversation_id}` 可修改当前会话的 `model_id`、`response_mode` 和 `permission_mode`。服务端验证模型属于当前工作区；L1–L5 风险、参数升级和 hard-deny 由 ToolPolicy 内部维护。

`preferences` 是当前主体在工作区中的用户级偏好。阶段 1 支持 `assistant_name`（1–32 个字符），用于界面称呼；只修改当前个人主体的显示偏好，不改变工作区名称。

`runtime-status` 是工作区所有者可见的只读投影，返回规范化工作区根目录及来源、网关/智能体核心状态和版本、即时生效项与需重启项。它不修改部署配置，也不声称能够检测运行期间手工编辑的外部 YAML。

### 3.7 工作区文件与变更

```text
GET /workspaces/{workspace_id}/files?path={relative_path}
GET /workspaces/{workspace_id}/files/content?path={relative_file}
GET /workspaces/{workspace_id}/changes
GET /workspaces/{workspace_id}/changes/diff?path={relative_file}
```

这些接口是受工作区根目录约束的只读投影，拒绝绝对路径、`..` 穿越和逃逸根目录的符号链接。预览限制为 512 KiB，变更列表最多 200 项。差异在用户选中文件后懒加载，限制为 256 KiB；响应同时返回截断状态。`changes` 在非 Git 工作区返回 `git: false`，不执行写入或暂存操作。

## 4. 命令语义

- 当前审批决定使用版本号防止重复决定和丢失更新。
- 通用 `Idempotency-Key`、ETag、任务重试动作仍是规划中，客户端当前不得假设已经支持。
- 取消、审批和重试使用显式动作，不伪装成普通字段 PATCH。

## 5. gRPC 服务

Python 核心服务当前由一个 `AgentService` 提供消息、会话、任务、事件、审批、模型与技能/MCP 等 RPC。准确方法和字段以 `proto/agent.proto` 为准；不预设为了分层另拆三套领域服务。

当前各请求直接携带 `workspace_id`、`principal_id` 等必要字段，统一 `CallContext` 尚未完成。Proto 字段发布后不得重编号，删除字段必须 `reserved`；绑定生成入口见 [开发指南](../development/DevelopmentGuide.md)。

当前 Proto 使用自定义 `Health` RPC，网关对外提供 HTTP `/health`。切换到标准 gRPC Health Checking 属于后续兼容性改造，不能按已实现能力部署探针。

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
model.usage
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

`message.*` 只承载用户可见的最终回答。模型主动输出的简短过程说明使用 `reasoning.*`，工具与子智能体生命周期分别使用 `tool.*` 和 `subagent.*`；三者均通过 `task_id` 关联任务，不写入消息资源。系统不传输模型隐藏思维链。

`model.usage` 是可选的观测事件，不写入消息，也不表示任务完成。`payload.usage` 只包含模型提供方实际提供的数值，例如 `input_tokens`、`output_tokens`、`total_tokens`、`cache_read_tokens`、`cache_creation_tokens`、`reasoning_tokens`；缺失字段表示未提供。旧模型提供方可能保留 `prompt_tokens`/`completion_tokens` 命名。当前计数覆盖主模型请求，不包含自动摘要的全部成本，不能作为完整账单。未知事件类型不得阻断客户端的 sequence 推进。

客户端按 `event_id` 去重，按 `sequence` 检测缺口。断线不取消任务。当前客户端先通过 REST `events/history?after=` 重放；建立 WebSocket 后，再按最新 sequence 补拉一次，覆盖普通连接窗口。原子 `after_sequence` WebSocket 握手和历史分页仍是规划中。

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

错误消息不得包含敏感凭证、原始系统提示、内部路径或未脱敏工具输出。

## 8. 版本策略

- REST 主版本位于路径。
- Event 使用 `schema_version`。
- Proto 遵循字段兼容规则。
- Breaking change 必须新增版本并记录 ADR。
- Markdown 示例应接受机器契约校验；当前没有完整自动文档校验流水线，不能把要求写成已通过。
