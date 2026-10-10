# MaigoKite API 设计

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

文件夹工作区位于既有个人数据范围内，不增加租户或身份系统：

```text
GET  /workspaces/{workspace_id}/folders
POST /workspaces/{workspace_id}/folders
```

POST 仅所有者可用，接受 `root_path` 与可选 `name`，由 Core 校验并登记规范化的实际目录，同目录重复添加返回已有记录。GET 返回 `id / name / root_path`，空 ID 表示启动配置的默认目录。模型、凭证、个人记忆仍以 `workspace_id` 为范围，不以 `folder_id` 隔离。

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

会话包含 `folder_id / archived`；创建可指定 `folder_id`，PATCH 可更新 `title / folder_id / archived`。既有会话迁移后仍使用默认目录且未归档。前端按文件夹与归档状态显示列表；直接进入会话时切换到其归属目录。归档会话拒绝发送消息；未结束的任务禁止移动、归档、删除（409）。DELETE 清理产品任务、消息及 LangGraph checkpoint，不删除工作区文件，保留安全审计。

`files / files/content / changes / changes/diff / runtime-status` 支持可选 `folder_id` 查询参数，Gateway 通过 Core 解析已登记目录，客户端不能直接传任意根目录。Runtime 权限校验与工具上下文使用会话所属目录，不变更共享全局根目录；MCP 进程启动目录和技能加载目录不因切换而变化。

### 3.3 任务、工具调用与审批

```text
GET  /workspaces/{workspace_id}/tasks?conversation_id={conversation_id}
GET  /workspaces/{workspace_id}/tasks/{task_id}
GET  /workspaces/{workspace_id}/tasks/{task_id}/inspection
POST /workspaces/{workspace_id}/tasks/{task_id}/cancel
GET  /workspaces/{workspace_id}/conversations/{conversation_id}/events/history?after={sequence}
GET  /workspaces/{workspace_id}/approvals
GET  /workspaces/{workspace_id}/approvals/{approval_id}
POST /workspaces/{workspace_id}/approvals/{approval_id}/decision
```

任务重试和单条工具调用独立查询尚未注册；任务级工具详情由 `inspection` 提供（见 3.8）。取消操作请求停止任务，并关闭仍待处理的审批；实际停止确认和清理顺序取决于当前执行路径，见 [智能体运行时设计](AgentRuntime.md)。第三方 MCP 调用能否立即被传输方式中止，仍有限制。

审批由智能体核心创建，外部 API 不提供任意创建审批请求的入口。审批决定必须包含目标审批 ID、decision 和审批版本。服务端从已保存的规范化工具调用读取参数，同时验证版本与过期时间；客户端不能在决定时替换参数。

决定请求支持 `{"decision":"deny","version":1,"note":"请只读取文件，不要修改"}`。
`note` 可选，最多 2000 字符；与决定、版本推进、审计在同一事务中保存。GET 单条审批可查询已结束的决定，返回 `note / decided_at`，不再只能查询 pending 列表。一次性 `allow / deny` 语义不变，不新增会话级授权。

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

权限设置请求与响应仅包含 `default_mode`。REST 写入拒绝未知字段（包括旧的 `tool_levels / grants`），不再静默接受无效设置。内部 Proto 的旧 `tool_levels` 字段号 2 和名称均保留为 reserved，Gateway/Core 需一起更新；旧产品库无需删表，旧风险配置不生效，下一次保存只写默认档位。

审批 `deny` 不读取模型凭证、不创建/调用模型，结束当前任务并关闭其剩余待审批操作；仍验证主体、任务状态、参数 hash、版本及过期时间并保存审计。`allow` 保持凭证准备和原生 HITL 恢复路径。这不新增会话级永久授权，也不改变三档自动执行范围。

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

### 3.8 GUI 交互与执行检查接口（2026-10-10）

本节记录本批后端实现，**不表示已通过运行验收或前端已接线**。本批不修改前端，不运行测试、类型检查、lint 或构建，不切换默认 Runtime。

以下路径均以 `/api/v1/workspaces/{workspace_id}` 为前缀，沿用现有工作区访问校验：

| 方法与路径 | 用途与响应 |
|---|---|
| `GET /capabilities` | `{capabilities: {...}}`：当前 Core Runtime 支持的交互能力；缺失键按不支持处理 |
| `GET /tasks/{task_id}/inspection` | `task / tool_calls / approvals / projection / last_sequence`，供任务与工具详情抽屉使用 |
| `GET /questions?conversation_id=...` | `{questions: [...]}`，仍等待回答的问题 |
| `POST /questions/{question_id}/answer` | `{"answer":"用户选择或自由输入","version":1}`；接受后返回 202 |
| `GET /tasks/{task_id}/inputs` | `{inputs: [...]}`，该任务的插话及消费状态 |
| `POST /tasks/{task_id}/inputs` | `{"content":"先不要修改，改为说明方案"}`；必须带 `Idempotency-Key`，返回 202 与 input 记录 |
| `GET /jobs?conversation_id=...` | `{jobs: [...]}`，真实命令进程与已保存的结束结果，最多 100 条命令调用范围内的记录 |
| `POST /jobs/{job_id}/stop` | 终止本 Core 持有的进程句柄并等待退出，返回 204；不是取消整个 Agent 任务 |

**能力边界。** `approval_note / approval_detail / task_inspection / file_change_events / process_list / process_stop` 为本批支持项。
`structured_questions / task_input / structured_plan / context_estimate` 仅在 `agent.runtime: langgraph` 时为 true；legacy 路径不增加第二套 HITL/插话状态机，插话提交返回 501。这些标志表示后端能力，工具仍可能被工作区配置停用。
`model_context_percentage / session_approval / turn_rollback / automatic_memory_events` 当前为 false。回合回滚不在本批需求内；会话授权留待权限简化，不创建临时 Grant 体系。

**任务详情。** `tool_calls` 返回工具名、参数、结果、状态和时间；不暴露 checkpoint、运行时对象或 `continuation_json`。
`projection` 包含 `plan / context / changes / summary / questions / truncated`；问题包含 `options` 数组和已保存回答。快照在同一 Repository 锁内读取。最多 50 条工具调用、50 条审批和最近 100 条相关事件；工具结果、审批、文件差异与问题另外共用约 900 KB 的输出预算，过大条目省略并标记 `truncated`。`last_sequence` 是该任务的事件水位，不是整个会话所有任务的完整快照水位。截断时应补读既有事件历史，不能将省略的内容判为不存在。

**结构化提问。** LangGraph 路径注册 `ask_user_question(title, options)`，选项为 `{label, recommended}`，也允许自由输入。使用原生 `interrupt / Command(resume=...)`，Repository 只保存产品问题、回答和审计。`question.requested` 携带 `question_id / tool_call_id / title / options / version`；`question.answered` 携带 `question_id / answer / version`。等待期间沿用已有任务状态 `waiting_approval`，UI 必须按问题事件/记录区分提问与权限审批，不能把提问渲染成“允许/拒绝”。回答验证工作区、主体、版本及 checkpoint；重复或过期回答返回 409。回答与审计、可见用户历史同事务保存，实际恢复仍看 checkpoint。进程重启恢复未在本批运行验证。

**插话。** 仅接受当前活跃的普通模型任务，不接受 `/tool` 或正在等待交互的任务。content 最多 10000 字符，每任务最多 20 条未消费输入；幂等键最多 128 字节，同键不同内容返回 409。`task.input.queued` 是接收回执；下一模型步骤在原生 middleware 中追加 `HumanMessage`，checkpoint 同步落盘后，再通过 `task.input.consumed` 确认进入模型输入，并保存可见用户消息。`consumed` 不保证 Provider 成功生成回答。尚未开始的旧工具提议会收到未执行结果，让模型读取新输入后重新判断；不抢停已经开始的工具或模型流。若当前回合直接结束而没有下一模型步骤，查询状态为 `not_consumed`，不自动新建回合或重发。客户端按 input ID 合并状态，不能因迟到的 queued 回执把 consumed 状态改回 queued。

**计划与上下文。** 计划直接复用 LangChain `TodoListMiddleware / write_todos`；`plan.updated.items` 是 `{content, status}` 数组，status 为 `pending / in_progress / completed`，只作用于当前任务，不是工作区 TODO。`context.updated` 提供 `estimated_input_tokens / input_budget_tokens / measurement: "estimate"`；`model_context_window / context_percent` 为 null，绝不把产品输入预算冒充模型的实际上下文容量。模型真实计费计数继续通过既有 `model.usage` 提供。

**文件变更。** `file_write / file_edit` 成功后发出任务归属的 `file.changed`：`path / tool_call_id / diff / diff_truncated / added / removed / before_hash / after_hash`。Diff 是单次工具操作前后的证据，不是整个回合净变化，不应将同文件多次修改的行数相加冒充净变化。前后内容各最多读取 256 KB，差异文本最多 64000 字符；二进制、无法读取或行数过多时 `diff_truncated: true`，无法计算的行数/hash 为 null。命令、MCP 或外部程序修改文件不在此事件覆盖内，仍使用现有工作区 Git Diff。发生写入后、事件提交前的崩溃可能缺少该投影；重放已满足内容的写入不会伪造原始 before image。本批不提供文件回滚快照。

**进程。** job ID 使用真实命令的 tool_call ID，只允许停止当前 Core 持有且属于该工作区的句柄，客户端不能提交任意 PID。日志通过 GET 轮询，不是新增日志 WebSocket 协议；`log_tail` 为 stdout/stderr 各约 4000 的尾部片段。POSIX 使用不移动子进程文件偏移的 `pread` 读取；无 `pread` 的平台 `live_logs_available: false`，只提供已有完成输出。仍沿用现有执行超时、进程组终止及平台限制；这不是 detached background scheduler，不保证跨 Core 重启接管进程。

权限拒绝、版本冲突、任务已结束等情况不会以空列表/假成功代替真实写入结果。前端后续需接入这些端点及新的事件映射；Mock 演示通过不等于真实接口已联调通过。

## 4. 命令语义

- 当前审批决定使用版本号防止重复决定和丢失更新。
- `Idempotency-Key` 本批仅用于任务插话；通用幂等写入、ETag、任务重试动作仍是规划中。
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
question.requested
question.answered
task.input.queued
task.input.consumed
plan.updated
context.updated
file.changed
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
