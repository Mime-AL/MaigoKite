# MaigoKite API 设计

> **状态**：当前有效
> **架构版本**：v1
> **基线核验**：2026-09-18；后续增量的验证范围见 [交付路线与状态](../project/Roadmap.md)。
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
GET  /workspaces/{workspace_id}/folders/browse
POST /workspaces/{workspace_id}/folders
DELETE /workspaces/{workspace_id}/folders/{folder_id}
```

POST 仅所有者可用，接受 `root_path` 与可选 `name`，由 Core 校验并登记规范化的实际目录，同目录重复添加返回已有记录。GET 返回 `id / name / root_path`，空 ID 表示启动配置的默认目录。模型、凭证、个人记忆仍以 `workspace_id` 为范围，不以 `folder_id` 隔离。

`DELETE folders/{folder_id}` 仅 owner 可用，Gateway/Core 均检查身份；成功返回 204。只删除文件夹登记，不读取或删除磁盘文件、消息、任务、checkpoint、模型或记忆。关联对话（含归档）在同一 SQLite 事务中移至默认目录，撤销原目录下的复用审批授权，并写入 `workspace_folder.deleted` 审计；之后的文件操作使用默认目录。默认空 ID 不可删除（400），不存在或不属于当前个人范围的登记为 404。存在未结束任务、仍在清理的 Runtime run、运行进程或最新可恢复 interrupted 任务时返回 409；整项操作失败，不部分迁移。磁盘目录已消失不影响移除登记。界面提供二次确认并同步已载入对话的目录归属，迟到的旧列表不重新显示被移除的工作区。

`folders/browse` 为本机 Web 文件夹选择器提供目录列表，要求 owner 且请求直接连接地址为 loopback（不信任转发头来判定本机）。可选 `path` 为已有绝对目录，省略时从网关进程用户的主目录开始；`show_hidden=true` 包含点开头目录。响应为 `{path, parent, home, root, entries: [{name, path}], truncated}`，根目录的 parent 为空。只枚举目录，不返回文件或读取内容；每次最多扫描 5000 项、返回 500 个文件夹，不缓存响应。注册路径仍调用上述 POST，由 Core 做最终校验。它不是工作区文件预览接口，也不是远程设备文件选择协议；Gateway/Core 必须共享文件系统，反向代理不应将此本机专用入口公开到远程。

手机访问为规划中，范围以 [手机远程访问](RemoteAccess.md) 为准。配对设备关联同一个个人主体；首版复用会话、任务、审批和 UI Event DTO，仅开放明确列出的远程资源。配对、会话和撤销的具体契约在实施时补充，本文不将它们列成已存在的端点。

### 3.2 会话与消息

```text
GET    /workspaces/{workspace_id}/conversations
POST   /workspaces/{workspace_id}/conversations
POST   /workspaces/{workspace_id}/conversations/{conversation_id}/fork
GET    /workspaces/{workspace_id}/conversations/{conversation_id}
PATCH  /workspaces/{workspace_id}/conversations/{conversation_id}
DELETE /workspaces/{workspace_id}/conversations/{conversation_id}
GET    /workspaces/{workspace_id}/conversations/{conversation_id}/messages
POST   /workspaces/{workspace_id}/conversations/{conversation_id}/messages
GET    /workspaces/{workspace_id}/conversations/{conversation_id}/snapshot
```

发送消息返回已创建的 `task_id`；增量结果通过事件流提供。

`POST .../fork` 需 `Idempotency-Key`（1–128 个无空格可打印 ASCII 字符），body 为 `{}` 或
`{"message_id":"msg_..."}`。省略消息 ID 时选择最新持久消息；分岔点须为助手回复，源会话有活动/待审批任务时返回 409。
201 返回新 `Conversation`，含 `forked_from_conversation_id / forked_from_message_id`。同源会话同键同参数返回原分岔；换参数使用旧键返回 409。
分岔复制该点之前的 user/assistant 消息，最多 500 条/2 MiB，超限返回 400 而非静默裁剪；创建与消息复制同事务提交。
模型、思考设置、目录和子 Agent 限额沿用源会话；完全访问及旧自动模式降为工作区权限。审批授权、任务、checkpoint、工具事件、队列和文件均不复制，也不调用模型。
分岔的首次执行沿用现有产品历史导入入口，不恢复源任务；文件仍共享，源会话删除不删除分岔。GUI 从已保存助手回复下方的「⋯ → 从此处分叉新对话」传入该回复的 `message_id`，不再由会话管理默认从末尾分岔；不是逐节点执行 Fork 或文件回滚。
请求键只在本次页面内保留；刷新后先查看会话列表，不保证找回原键。分岔删除后不保留去重墓碑。

发送消息可带 `Idempotency-Key`（1–128 个无空格可打印 ASCII 字符）。键按工作区、会话、主体隔离，内容指纹覆盖 content 与 attachments；新请求返回 202，相同键/相同内容返回原任务的 200 `{task_id, conversation_id, status, replayed: true}` 和 `Idempotency-Replayed: true`，不同内容返回 409。返回旧任务不会重新发模型请求、写消息或广播历史事件；中断/失败任务也不会因重发键自动恢复。相同文本的新操作必须用新键。省略键保持旧行为；GUI 已为每次逻辑提交生成键，网络/5xx 错误时保留原键，用户点击确认才重试。4xx 明确拒绝会释放键；成功回执后刷新失败不等于提交失败。键仅保留在当前页面会话内，刷新页面后应先查询任务记录，不保证找回原键。服务端的键随任务保留，删除会话/任务后不再保留去重记录。最新 GUI 接线未验收。

`snapshot` 返回 `messages / tasks / approvals / questions / last_sequence / truncated`，其中 approvals/questions 只含待处理项，嵌套审批和问题沿用 protobuf JSON（`arguments_json / options_json`），客户端 API 边界将审批参数和问题选项转换为界面 DTO。在单 Core 的同一个 Repository 锁内读取，每类最多 200 条最新记录并按时间返回，条目合用约 900 KB 序列化预算；省略时明确 `truncated: true`。这解决多个列表分开读取的观察窗口，不提供跨进程一致性或完整事件快照。GUI 已先订阅并缓冲，再取快照、补拉历史并按 event_id 合并；快照水位内的活动卡片与未完成回复仍回放，但不得覆盖较新的任务状态或重新触发排队发送。待审批/待回答卡片直接使用真实快照水位，不制造伪事件。`truncated` 会提示较早记录可能不完整，客户端不能因缺少某个待处理 ID 就关闭对应卡片。接线不等同于断线恢复验收。

会话包含 `folder_id / archived`；创建可指定 `folder_id`，PATCH 可更新 `title / folder_id / archived`。既有会话迁移后仍使用默认目录且未归档。前端按文件夹与归档状态显示列表；直接进入会话时切换到其归属目录。归档会话拒绝发送消息；未结束的任务禁止移动、归档、删除（409）。DELETE 清理产品任务、消息及 LangGraph checkpoint，不删除工作区文件，保留安全审计。

归档仅禁止新执行，不禁止相同幂等键/内容查询已存在的提交回执。幂等请求中的会话若已删除，返回 404，不悄悄新建会话。`snapshot` 的空列表返回 `[]`，不返回 `null`。

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
GET  /workspaces/{workspace_id}/approval-authorizations?conversation_id={conversation_id}
DELETE /workspaces/{workspace_id}/approvals/{approval_id}/authorization
```

任务重试和单条工具调用独立查询尚未注册；任务级工具详情由 `inspection` 提供（见 3.8）。取消操作请求停止任务，并关闭仍待处理的审批；实际停止确认和清理顺序取决于当前执行路径，见 [智能体运行时设计](AgentRuntime.md)。第三方 MCP 调用能否立即被传输方式中止，仍有限制。

审批由智能体核心创建，外部 API 不提供任意创建审批请求的入口。审批决定必须包含目标审批 ID、decision 和审批版本。服务端从已保存的规范化工具调用读取参数，同时验证版本与过期时间；客户端不能在决定时替换参数。

决定请求支持 `{"decision":"deny","version":1,"note":"请只读取文件，不要修改"}`。
`note` 可选，最多 2000 字符；与决定、版本推进、审计在同一事务中保存。GET 单条审批可查询已结束的决定，返回 `note / decided_at`，不再只能查询 pending 列表。

允许请求可携带 `scope`：`{"decision":"allow","version":1,"scope":"session"}`。缺省为 `once`；另支持 `task / session`，仅可选择审批响应的 `allowed_scopes`。`deny` 只接受 `once`。响应增加服务端生成的 `reuse_scope`（只读）、`authorization_scope / authorization_expires_at / authorization_revoked_at`；客户端不得提交自定义 scope 规则。L5/MCP/沙箱外命令不支持复用。

授权列表返回 `{"authorizations":[...]}`，项包括 `approval_id / conversation_id / task_id / scope / expires_at / resource`；撤销返回 204。两接口要求 owner 且校验主体，不删除原审批审计；任务/会话授权最长 8 小时。每次执行重新核对权限和回执，详见 [工具权限](../agent-capabilities/security/tool-permission.md#窄范围复用)。

GUI 审批卡已接 scope 选择，只展示该审批版本允许的选项；会话管理接授权列表与撤销。快照额外解析 `reuse_scope_json` 为同一 DTO。完全访问显式确认后发送 `danger_full_access`，旧自动模式仅保留显示，不冒充完全访问。本次没有运行交互验收。

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

运行清单与个人配置分开：

```text
GET /workspaces/{workspace_id}/skills
GET /workspaces/{workspace_id}/mcp-servers
GET /workspaces/{workspace_id}/extension-settings
PUT /workspaces/{workspace_id}/extension-settings
POST /workspaces/{workspace_id}/extension-settings/apply
```

`skills` 返回实际启用的声明式技能元数据，`mcp-servers` 返回实际加载的 stdio Server 状态和工具名，不把期望启用当作已经连接。

三个 `extension-settings` 接口只允许个人工作区 owner（Core 同时要求 `workspace_id=personal`）。GET/PUT/apply 返回同一个快照：`config / active_config / applied_revision / reload_required / reloading / runtime_ready / servers / skills / skill_errors / extension_error`。其中 skills 包括停用的已扫描元数据；config 是期望配置，active_config 仅含上次生效配置的 `revision / mcp_servers`，不重复返回 Skill 正文；extension_error 提示应用或资源清理失败。应用新版本要求 Skill 扫描成功且所有启用 MCP 已连接；已应用的 revision 不保证连接持续健康，仍须检查逐项状态。`runtime_ready=false` 时不宣称聊天链可运行。

PUT 完整替换 `config`（2 MiB 上限）：`revision / mcp_servers / skill_directories / skills / disabled_skills`，校验通过后递增 revision，写现有 `workspace_settings` 并记审计，不操作运行中的进程。MCP 项包括 `namespace / transport=stdio / command / args / cwd / enabled / env_allowlist / secret_env / enabled_tools / disabled_tools`；托管 Skill 项包括 `name / content / enabled`，每个 Markdown 最大 256 KiB。只接受声明字段，不接受原始 env/secret 值。

apply 默认接受 `{"revision": <保存后的版本>}`，应用新配置。Gateway 按 `secret_env` 从现有密钥链读取引用 `mcp.<namespace>.<ENV_NAME>`，经内部 RPC 瞬时传值。Core 拒绝旧版本、重复应用或仍有运行/待审批/待回答的任务（409）；无效配置 400，非 owner 403。

同一接口接受 `{"revision": <active_config.revision>, "restore_only": true}`，只恢复已生效配置的 MCP 连接、复用已加载 Skill；允许等待审批/回答，不允许活动运行，不应用尚未生效的编辑。新聊天、回答、任务恢复和批准入口均先准备已生效配置的凭证与连接；缺凭证或恢复失败时不准入本次执行，也不消费审批决定。批准 MCP 工具时还检查对应连接，成功后仍由 Core 校验审批 hash/version/策略。拒绝审批无需恢复 MCP 连接。

配置或进程异常有逐项状态，不能用 HTTP 200 推断全部连接成功；基础 Runtime 准备失败返回错误并保留原聊天入口，已断开的 MCP 另行恢复。Core 持有应用任务到清理完成，调用方断线不提前开放新运行；请求超时后先 GET 查看 reloading/结果，不盲目重发 apply。

凭证沿用 3.6 的 POST/PUT/DELETE 接口；值不进入扩展配置/GET/审计。更新/删除凭证不改活动进程环境，下次 apply/恢复连接时生效。卸载配置不删除程序、目录或凭证。当前只支持本地 stdio 与 Markdown/目录技能，不是技能包安装、版本授权或 Grant 平台，扩展边界见 [技能](../agent-capabilities/skills/skill-lifecycle.md)。

本次配置与管理接口是源码接入状态，未运行新增链路测试；只读列表或此前 MCP SDK 的验收不能代替它。

### 3.6 设置、模型和凭证引用

```text
GET   /workspaces/{workspace_id}/settings
PATCH /workspaces/{workspace_id}/settings
GET   /workspaces/{workspace_id}/tool-settings
PATCH /workspaces/{workspace_id}/tool-settings
GET   /workspaces/{workspace_id}/models
GET   /workspaces/{workspace_id}/models/{model_id}/thinking
GET   /workspaces/{workspace_id}/models/{model_id}/context
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

**模型窗口查询。** `models/{model_id}/context` 由 Gateway 恢复当前配置的凭证，再调用
Core 的 `GetChatModelContext`。与执行路径复用同一个容量解析函数和 Core 所有的模型客户端；
不生成消息、不创建任务、不自动加载模型、不修改配置。返回 `model_id / model_key / model_name`、
`model_context_window / capacity_source / capacity_status / capacity_checked_at`，以及
`input_budget_tokens / output_reserved_tokens / safety_margin_tokens / compaction_trigger_tokens`。
窗口未知时，窗口、输入预算和容量压缩阈值均为 null；不把旧的 32000 产品默认值冒充容量。
容量已知时，预算为窗口减输出预留和安全余量，不再对所有模型套用 32000 上限。
此接口不返回对话用量，客户端必须从当前会话的执行回执取得用量，不能借用其他会话。
本次接口和恢复链路为源码接入状态，未运行测试或真实 Provider 验收。

**会话思考控制。** `models/{model_id}/thinking` 返回 `kind: effort | toggle | unavailable`、
`options: string[]`、`default`、`source` 和 `reason`；列表由 Core 确认，前端不按模型名称猜测。
`default` 为空表示默认值未知，不等于关闭思考。查询只读取能力资料，不发生成请求、不自动加载模型。
Gateway 在读取能力、保存显式思考设置之前，沿用 OS 凭证存储恢复所选模型的 Core 内存凭证，
不启动 MCP/Skill，不返回 Secret。

创建/PATCH 会话接受 `thinking: string`；PATCH 省略保持原值，`""` 恢复服务默认（不发送推理参数）。
模型变更且未指定 thinking 时自动清空；非法档位由 Core 拒绝，活跃或等待批准的任务不允许更改。
GET/List 返回相同字段；protobuf JSON 省略空值时客户端按 `""` 解读。
旧 `response_mode` 暂留作兼容字段，但不再改变输出 token 预算，也不被转换为推理强度。

当前控制范围：OpenAI 使用原生 SDK `profile.reasoning_effort_levels`（原始 GPT-5 使用官方档位修正），
Claude 使用已确认的自适应思考型号及官方 effort 档位，Ollama 查询 `/api/show.thinking`，
LM Studio 查询 `/api/v1/models.capabilities.reasoning`。OpenAI/LM Studio 的强度参数复用 SDK Responses，
Claude 使用 adaptive + effort，Ollama 使用原生 reasoning/think；不自建 Provider 协议。
LM Studio 仅原生 API 暴露的 on/off 尚不映射到兼容接口，返回 `native_control_only`；
未知兼容服务、旧版缺少元数据或未接入的预算型控制返回不可调节，保持服务默认。

模型目录支持多选及手动追加 ID；每个选中模型保存为既有的独立配置，共享本次填写的服务连接信息。前端使用稳定配置 ID，串行调用现有 `PUT models/{model_id}`，避免配置目录的读改写发生并发覆盖；部分失败保留已保存项和草稿，重试更新同一 ID，不承诺跨配置事务。

模型保存请求可携带 `credential_source_id`，由 Gateway 从同工作区、同接口协议、同规范化基础地址的已保存配置复用密钥；来源无效时在写入前拒绝。显式提交 `api_key` 优先，密钥仍按目标模型 ID 存储，不回传前端。此字段不建立新的 Provider 注册表或共享密钥域。

模型 API 管理工作区的聊天模型配置集合，并保证最多一个默认模型。`models/actions/validate` 使用提交的草稿配置做一次最小模型调用，不保存草稿。`models/actions/discover` 根据模型提供方与基础地址查询服务端模型目录：OpenAI、Anthropic 和兼容端点使用 `/models`，Ollama 使用 `/api/tags`。

目录发现优先使用本次草稿中的 Key。仅当模型提供方与基础地址同已保存配置完全匹配时，才读取该配置的凭证存储引用。结果和敏感凭证都不持久化。目录请求禁用重定向、系统代理和链路本地地址，防止 Key 被转发到非预期端点。

设置写入、目录发现、连接验证和凭证管理只允许工作区所有者。模型凭证按模型配置 ID 隔离（`model-profile.{id}`）。保存后，网关将凭证同步到智能体核心内存；发送消息前，再次从 OS 凭证存储同步当前会话选择的配置。修改模型提供方/基础地址会使旧凭证失效。敏感凭证不进入领域数据库或事件。

联网搜索凭证使用 `tavily`、`google` 引用名。网关保存或删除引用时通过内部 gRPC 同步智能体核心，并在每次消息任务开始前重新同步，以覆盖核心服务重启场景。搜索失败事件只携带稳定错误码、用户提示和设置路由，不携带敏感凭证。

`GET/PATCH /workspaces/{workspace_id}/permissions` 管理默认执行模式：`read_only / workspace / danger_full_access`；不向普通客户端暴露逐工具风险矩阵。`PATCH conversations/{conversation_id}` 可修改当前会话的 `model_id`、`thinking` 和 `permission_mode`（旧 `response_mode` 仅保留兼容）。服务端验证模型属于当前工作区；L1–L5 风险、参数升级和 hard-deny 由 ToolPolicy 内部维护。

2026-10-11 兼容约定：旧 `full_access` 请求仍被接受，但规范化为 `workspace_auto`，保留原工作区限制而非自动提权；历史会话、YAML/环境变量与默认设置同样处理。前端要把 `workspace_auto` 显示为兼容的“旧版受限自动”，不作为新的完全访问档位。真正完全访问须显式提交 `{"permission_mode":"danger_full_access"}` 或 `{"default_mode":"danger_full_access"}`，界面接入时应明确告知将取消工作区沙箱与逐项审批。设置默认仅影响后续新会话。

创建/PATCH 会话还接受 `max_subagent_calls`（0–32，默认 0 关闭）和 `max_concurrent_subagents`（1–8，默认 1；启用时不能超过前者）。省略字段保留旧值，`0` 不当作省略。GET/List 返回会话设置；Go JSON 可能省略值为 0 的字段，客户端以 0 解读。Core 在持久化事务内校验组合；新任务原子快照限额，运行中修改仅影响后续回合。`capabilities.subagents` 表示支持此接口/执行入口，不绕过工具停用设置和共享模型调用预算。执行限制见 [运行时设计第 7 节](AgentRuntime.md#7-技能子任务与工作流边界)。

`capabilities.subagent_model_selection` 表示支持多模型子 Agent。创建/PATCH 会话接受 `subagent_model_ids: string[]`，最多 32 个、不重复、必须是同工作区已配置模型 ID。PATCH 省略保留旧值，`[]` 清空额外选择（仍可跟随父模型）；GET/List 返回相同字段，空值被 Go JSON 省略时按 `[]` 解读。gRPC PATCH 使用 `ModelIdList subagent_models` 的 message presence 区分省略/清空。Task 返回准入时保存的 `subagent_model_ids`，供重启后的凭证准备使用；不是另一份执行状态。

权限设置请求与响应仅包含 `default_mode`。REST 写入拒绝未知字段（包括旧的 `tool_levels / grants`），不再静默接受无效设置。内部 Proto 的旧 `tool_levels` 字段号 2 和名称均保留为 reserved，Gateway/Core 需一起更新；旧产品库无需删表，旧风险配置不生效，下一次保存只写默认档位。

审批 `deny` 只拒绝当前操作，不取消整轮或关闭其他待审批操作。Gateway 尽力准备模型凭证供后续续接，但凭证不可用不能阻止拒绝保存，也不为被拒绝的操作启动 MCP。决定仍验证主体、任务状态、参数 hash、版本及过期时间并保存审计；后续续接失败通过 `task.failed` 报告。`allow` 继续使用凭证准备和原生 HITL 恢复路径。授权有期限且可撤销，不存在永久会话授权或独立审核 Agent；批次续接语义见 3.8。

`preferences` 是当前主体在工作区中的用户级偏好。`assistant_name`（1–32 个字符）用于界面称呼，只修改当前个人主体的显示偏好，不改变工作区名称。

`runtime-status` 是工作区所有者可见的只读投影，返回规范化工作区根目录及来源、网关/智能体核心状态和版本、即时生效项与需重启项。它不修改部署配置，也不声称能够检测运行期间手工编辑的外部 YAML。

### 3.7 工作区文件与变更

```text
GET /workspaces/{workspace_id}/files?path={relative_path}
GET /workspaces/{workspace_id}/files/content?path={relative_file}
POST /workspaces/{workspace_id}/files?path={relative_parent}&folder_id={registered_folder_id}
POST /workspaces/{workspace_id}/files/open-folder?path={relative_folder}&folder_id={registered_folder_id}
GET /workspaces/{workspace_id}/changes
GET /workspaces/{workspace_id}/changes/diff?path={relative_file}
```

GET 接口是受工作区根目录约束的只读投影，拒绝绝对路径、`..` 穿越和逃逸根目录的符号链接。预览限制为 512 KiB，变更列表最多 200 项。差异在用户选中文件后懒加载，限制为 256 KiB；响应同时返回截断状态。`changes` 在非 Git 工作区返回 `git: false`，不执行写入或暂存操作。文件查询与操作均按 `folder_id` 解析已登记的目录，缺省为默认工作区，不接受调用方指定任意根目录。

POST 接口为用户显式文件操作，限工作区所有者；不作为 Agent 工具、审批续接或自动执行入口：

- `POST /files` 正文为 `{"name":"notes.md","type":"file"}` 或 `{"name":"notes","type":"directory"}`。只在已存在的相对父目录创建一个空文件或文件夹，不递归创建路径、不覆盖、不写正文。成功返回 201 与 `name / path / type / size / modified_at` 文件树条目；同名返回 409 `ALREADY_EXISTS`，非法名称 / 路径返回 400，权限失败返回 403。拒绝路径分隔符、控制字符、保留名称以及 `.git` 路径。复用系统相对目录句柄创建能力，防止校验后替换符号链接或 junction 令写入逃逸；现有 `x/sys` 依赖版本不变。
- `POST /files/open-folder` 另外要求直接连接地址为本机 loopback。只可打开工作区内已存在目录；Gateway 以固定文件管理器程序加路径参数启动，不经 shell。快速成功返回 204；启动器仍在运行时返回 202 `{"launched":true}`，仅表示启动已接受，不保证窗口已打开；启动或快速退出失败返回 503 `OPEN_FAILED`。Electron 优先使用已有 `openPath` IPC，不调用此接口。

这两项源码已接线，尚未执行运行验收；使用新接口需重启 Gateway。

### 3.8 GUI 交互与执行检查接口（2026-10-10）

本节以 2026-10-10 的后端接口为基线，包含后续 GUI 接线说明。最初批次未修改前端，也未运行测试、类型检查、lint 或构建；不能用这份历史记录推断当前界面缺少接口。各项当前验证范围见 [交付路线与状态](../project/Roadmap.md)，未验收项仍单独标注。

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
| `POST /jobs/{job_id}/input` | `{"text":"一行输入\n","eof":false}`；向获批的交互式命令发送最多 4096 字节，或以空 text/eof=true 关闭输入；确认后返回 204，不自动重试 |
| `POST /tasks/{task_id}/resume` | 工作区所有者显式恢复被进程中断的文件任务，正文 `{"version":当前任务版本}`；确认接受后返回 202，不代表完成 |

**能力边界。** `approval_note / approval_detail / task_inspection / file_change_events / process_list / process_stop` 为本批支持项。
2026-10-11 增加 `process_input`，每个 job 返回 `stdin_available`。GUI 必须同时检查进程 live、stdin_available 和能力标志，不能把历史记录当成可操作进程。输入正文不保存到审计或对话，响应丢失不代表未送达；进程自行回显的输出仍可能包含输入。当前是有超时的标准管道，不提供 PTY 或断线后恢复进程。
`structured_questions / task_input / structured_plan / context_estimate` 在 Core 的唯一 LangGraph Runtime 就绪时为 true；关闭或未就绪时不对外宣称可执行。这些标志表示后端能力，工具仍可能被工作区配置停用。
`session_approval / task_approval / approval_authorization_revocation / permission_boundary_v2 / conversation_fork` 在 Runtime 就绪时为 true，表示支持上述新接口/语义，不代表前端已完成联调或主机沙箱可用。`auto_review / model_context_percentage / turn_rollback / automatic_memory_events` 为 false。回合回滚和审核 Agent 不在本批范围。

**显式任务恢复。** `task_resume` 在 Runtime 就绪时为 true，表示提供受限恢复入口，不表示所有 interrupted 任务均可重放。Gateway 先按现有凭证入口补齐 Core 的进程内模型密钥，再调用流式 gRPC `ResumeTask(workspace_id, task_id, principal_id, version)`。Core 只接受所有者、最新版本、最新会话回合、无活跃运行、未归档且存在未完成 checkpoint 的 `interrupted` 任务；等待审批的任务继续使用 Approval API，不走这个接口。旧任务无 checkpoint 也按不可恢复处理；状态/版本/checkpoint 不满足返回 409，越权返回 403，任务不在工作区内返回 404。

首版恢复只接受保留的 checkpoint 中工具调用均为 `file_read / file_write` 的任务，以及这两种直接 `/tool` 命令。保留历史若包含旧回合的其他工具也会保守拒绝；命令、Browser、MCP 等不自动重放。恢复不等于重新授权：未批准的调用仍暂停等待，已批准的调用仍核对当前策略及审批 hash/version。文件内容匹配时可零写入核对；不同内容可能被再次覆盖，接口不提供外部编辑冲突保护、回滚或 exactly-once 保证。调用者应先检查目标文件，确认重放意图。

接受事件 `task.resumed` 使用既有 AgentEvent DTO 和持久 event_id/sequence/occurred_at，payload 包含 `execution_resumed: true` 与本次 `trace_id`。Gateway 收到该请求的确认才返回 202，后续事件透传原 WS 通道；并发拒绝请求不会冒领其他恢复请求的事件。执行与订阅分离：断线不取消；用户停止与 Core shutdown 都取消并等待同一根任务。UI 不接触 checkpoint/continuation，不新增前端状态机。当前批次只补后端接口与样例，验收状态见 [交付路线与状态](../project/Roadmap.md)。

**任务详情。** `tool_calls` 返回工具名、参数、结果、状态和时间；不暴露 checkpoint、运行时对象或 `continuation_json`。
`projection` 包含 `plan / context / changes / summary / questions / usage / truncated`；问题包含 `options` 数组和已保存回答。快照在同一 Repository 锁内读取。最多 50 条工具调用、50 条审批和最近 100 条相关事件；工具结果、审批、文件差异与问题另外共用约 900 KB 的输出预算，过大条目省略并标记 `truncated`。`usage` 独立汇总该任务全部已保存的用量事件，不受最近 100 条活动限制；按 purpose 返回 `calls / failed_calls / reported_calls / tokens`，另有 `compactions`。它仅汇总已有回执，不将缺失字段填零，不计算价格；cached/reasoning 不额外加到总 token。`last_sequence` 是该任务的事件水位，不是整个会话所有任务的完整快照水位。截断时应补读既有事件历史，不能将省略的内容判为不存在。

**结构化提问。** LangGraph 路径注册 `ask_user_question(title, options)`，选项为 `{label, recommended}`，也允许自由输入。使用原生 `interrupt / Command(resume=...)`，Repository 只保存产品问题、回答和审计。`question.requested` 携带 `question_id / tool_call_id / title / options / version`；`question.answered` 携带 `question_id / answer / version`。等待期间沿用已有任务状态 `waiting_approval`，UI 必须按问题事件/记录区分提问与权限审批，不能把提问渲染成“允许/拒绝”。回答验证工作区、主体、版本及 checkpoint；重复或过期回答返回 409。回答与审计、可见用户历史同事务保存，实际恢复仍看 checkpoint。进程重启恢复未在本批运行验证。

GUI 的收件箱与活动卡片已接入问题选项、自由文本及“回答并继续”。提交当前展示的 version；
成功、冲突或网络失败后重读快照和持久事件，不用 HTTP 202 冒充执行完成，也不自动重复回答。
普通聊天输入不隐式充当问题回答：运行中 Enter 通过 `/tasks/{task_id}/inputs` 引导，
Alt+Enter 显式加入下一回合待发列表；等待审批或提问时只能稍后发送，或就地处理卡片。
驳回理由通过 Approval API 的 note 保存并交给模型。`deny` 只拒绝该操作，`scope` 必须为 `once`；任务继续或等待同批下一项审批，不发布 `task.cancelled`。批次审阅完成后，被拒绝调用通过既有 `tool.failed`（`error_code=APPROVAL_REJECTED`）投影，产品工具状态为 `denied`。续接失败另发 `task.failed`，拒绝决定仍有效；显式 cancel 才停止整轮。
阶段 3a 的补充输入、计划恢复与运行抽屉已进行真实 Gateway/Core 验收，见
[UI 设计的阶段 3a 记录](agent-ui-design.md#10-阶段-3a--数据链路)。
该验收不代表审批/回答的跨进程恢复通过；Mock 未实现问题续接，返回空问题列表。

**插话。** 仅接受当前活跃的普通模型任务，不接受 `/tool` 或正在等待交互的任务。content 最多 10000 字符，每任务最多 20 条未消费输入；幂等键最多 128 字节，同键不同内容返回 409。`task.input.queued` 是接收回执；下一模型步骤在原生 middleware 中追加 `HumanMessage`，包含该输入的模型调用成功返回后才保存可见用户消息并发出 `task.input.consumed`。预算拒绝、失败和取消不冒充已消费；Provider 可能已收到但响应丢失的情况仍不能确认，`not_consumed` 不是“服务端一定没收到”的证明。`consumed` 也不保证后续工具或整个任务成功。尚未开始的旧工具提议会收到未执行结果，让模型读取新输入后重新判断；不抢停已经开始的工具或模型流。若当前回合结束前未确认消费，查询状态为 `not_consumed`，不自动新建回合或重发。客户端按 input ID 合并状态，不能因迟到的 queued 回执把 consumed 状态改回 queued。

**计划与上下文。** 计划直接复用 LangChain `TodoListMiddleware / write_todos`；`plan.updated.items` 是 `{content, status}` 数组，status 为 `pending / in_progress / completed`，只作用于当前任务，不是工作区 TODO。`context.updated` 提供 `call_id / model_name / estimated_input_tokens / input_budget_tokens / measurement`；本地估算为 `estimate`，显式超限回执提供的输入计数为 `provider`，沿用 `estimated_input_tokens` 字段兼容现有消费者，不表示计费成功。`model_context_window / context_percent` 在容量已知时有值，否则为 null，绝不把产品预算冒充模型窗口。

容量附加字段：`capacity_source` 包括 `lmstudio.loaded_instance / ollama.loaded_instance / ollama.model_info / model_profile / provider_metadata / provider_error / models.dev / sdk_profile / route_config / route_default / null`，分别表示加载实例、Ollama 模型资料、显式模型覆盖、当前服务资料、拒绝回执、当前路由目录/SDK 资料、YAML 路由默认值、内置路由假定值和未知。目录是资料上限，不冒充实际加载窗口；未知远端路由默认容量为 262,144，`route_default` 对应 `capacity_status=assumed`，不是实测。`capacity_status` 还可为 `known / cached / unknown / model_catalog_unavailable / metadata_unavailable / unsupported_metadata / unauthorized / not_loaded / model_not_found / ambiguous_instance`；`capacity_checked_at` 为 UTC 解析/观测时间。`output_reserved_tokens / safety_margin_tokens / compaction_trigger_tokens` 分别是输出预留、估算余量和自动压缩阈值，均不是已消耗 token。`purpose` 区分 `response / summary`。压缩前和正式调用前均可发布，预检的 `context_*` call ID 不是模型调用次数，只有 `model.call.started` 才代表请求开始；不能对多个 `context.updated` 求和。模型真实计费计数继续通过既有 `model.usage` 提供。

容量未知时不按产品默认预算触发模型压力压缩，也不发布伪造阈值。明确的服务端超限错误可以
触发一次强制原生摘要，再重试一次；只在尚无可见 Token、历史实际缩减且当前输入保留时进行。
摘要使用 LangGraph `TAG_NOSTREAM`，不进入回复正文；公开的 `ExtendedModelResponse / Command`
将替换历史与新回复一起提交 checkpoint，UI 只投影新回复，不重复历史工具操作。
恢复失败、没有可压缩历史、已输出内容或取消时不重复调用、不提交失败摘要。
固定指令和工具定义本身超预算的失败带 `reason=fixed_overhead_exceeded`，显示输入预算不足，
不称为历史摘要失败。现有 `context.max_tokens` 只作未知容量下恢复工作的预算，不能声明服务端窗口。

模型配置使用可选 `context_window`（正的安全整数；省略/0 表示没有模型覆盖），从设置页获取的服务目录按精确模型 ID 保存，经既有 REST / protobuf / Repository 传递，无数据库增列。换服务或换模型不能沿用另一模型的容量。Runtime 使用 Core 已拥有的官方 SDK 查询当前服务 `/models`，读取精确模型项的 `context_window / context_length / contextWindow / max_model_len`；只有本地 OpenAI-compatible 服务才尝试 LM Studio 加载实例接口。models.dev/SDK 资料只适用于已识别的当前路由，不跨厂商匹配模型 ID；自定义 Anthropic/OpenAI 协议地址不等于官方路由。无资料的远端接入使用 `models.routes[].default_context_window`，未配置时采用 262,144 的 `assumed` 回退，本地/Ollama 无默认云端回退。输出上限与旧产品预算仍不冒充窗口。持久容量记录增加内部 `capacity_policy / catalog_route`，旧跨厂商缓存失效；前端缓存换版本，历史目录容量不得覆盖新路由观测，用量保留。`context.updated` 保持 `model_id / model_key`：后者为 `[provider, normalized_base_url, model, context_window_or_null]` 的紧凑 JSON，仅用于配置关联，不含密钥。前端同时匹配配置 ID 与该关联值；旧事件缺少关联值时不把历史容量套到当前配置，新请求发布新的观测。路由配置由现有 YAML 读取，不新增 REST/protobuf 字段或设置系统。

压缩状态通过 `context.compaction.started / failed / skipped` 与既有 `context.compacted` 发布。started 带 `before_tokens / input_budget_tokens / model_context_window / measurement`；failed 带 `message / error_type / model_context_window` 且保留原历史；skipped 的 `reason=no_compressible_history` 不代表完成压缩。前端按事件投影独立压缩状态，不从普通“思考中”推断；窗口仪表保留 measurement、容量来源、获取状态与观测时间，未知窗口只显示已有 Token 计数/估算、不绘制占用比例。聊天过程与底部显示压缩失败原因，关闭窗口用量显示不隐藏失败反馈。本次前端接入未运行测试或真实服务验收，后端没有手动压缩接口，界面不提供该按钮。

用量汇总中，旧记录若缺少 `call_id` 或调用开始回执，`calls / failed_calls` 返回 null（未知），不能显示为“0 次调用”。已收到的 token 小计和 `reported_calls` 仍可查询，但不是完整账单或调用次数的估计。

**文件变更。** `file_write / file_edit` 成功后发出任务归属的 `file.changed`：`path / tool_call_id / diff / diff_truncated / added / removed / before_hash / after_hash`。Diff 是单次工具操作前后的证据，不是整个回合净变化，不应将同文件多次修改的行数相加冒充净变化。前后内容各最多读取 256 KB，差异文本最多 64000 字符；二进制、无法读取或行数过多时 `diff_truncated: true`，无法计算的行数/hash 为 null。命令、MCP 或外部程序修改文件不在此事件覆盖内，仍使用现有工作区 Git Diff。发生写入后、事件提交前的崩溃可能缺少该投影；重放已满足内容的写入不会伪造原始 before image。同字节核对成功的 `file_write` 仍通过标准工具投影返回结果：`tool.completed.data` 含 `reconciled: true / bytes_written: 0 / size_bytes`，`file.changed` 含可选 `reconciled: true`，并以 `before_hash: null / diff_truncated: true` 表示原始差异不可恢复，不表示产生了新的磁盘写入。本批不提供文件回滚快照。

**进程。** job ID 使用真实命令的 tool_call ID，只允许停止当前 Core 持有且属于该工作区的句柄，客户端不能提交任意 PID。日志通过 GET 轮询，不是新增日志 WebSocket 协议；`log_tail` 为 stdout/stderr 各约 4000 的尾部片段。POSIX 使用不移动子进程文件偏移的 `pread` 读取；无 `pread` 的平台 `live_logs_available: false`，只提供已有完成输出。仍沿用现有执行超时、进程组终止及平台限制；这不是 detached background scheduler，不保证跨 Core 重启接管进程。

权限拒绝、版本冲突、任务已结束等情况不会以空列表/假成功代替真实写入结果。前端后续需接入这些端点及新的事件映射；Mock 演示通过不等于真实接口已联调通过。

## 4. 命令语义

- 当前审批决定使用版本号防止重复决定和丢失更新。
- `Idempotency-Key` 用于任务插话和可选的聊天提交；不扩展为通用幂等写入框架。ETag、任务重试动作仍是规划中。
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
model.call.started
model.call.failed
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
subagent.queued
subagent.started
subagent.progress
subagent.completed
subagent.failed
subagent.cancelled
approval.requested
approval.decided
question.requested
question.answered
task.input.queued
task.input.consumed
plan.updated
context.updated
context.compaction.started
context.compaction.failed
context.compaction.skipped
context.compacted
context.history
file.changed
```

`message.*` 只承载用户可见的最终回答。模型主动输出的简短过程说明使用 `reasoning.*`，工具与子智能体生命周期分别使用 `tool.*` 和 `subagent.*`；三者均通过 `task_id` 关联任务，不写入消息资源。系统不传输模型隐藏思维链。

`subagent.*` 的 `subagent_id` 对应父任务的 `delegate` 工具调用 ID，不是独立产品 task。queued 带 `used/limit/task/label/requested_model_id`；started 带 `task` 和实际 `model_id/name/provider/model/label`，progress 带相同模型身份及只读工具名/参数，completed 带摘要和模型身份，failed 带安全错误信息与请求 ID。前端将进度/结果映射到同一 delegate 活动；原 `tool.completed/failed` 投影继续保留，父任务终态保持不变。子 Agent 模型事件的 `purpose=subagent`、`subagent_id` 及实际模型身份用于用量归属，不复用主回复的 `message.delta`。

`model.usage` 是可选的观测事件，不写入消息，也不表示任务完成。`payload.usage` 保存 Provider/SDK 提供的数值，例如 `input_tokens / output_tokens / total_tokens / cache_read_tokens / cache_creation_tokens / cache_miss_tokens / reasoning_tokens`；缺失缓存字段表示未提供。旧路径可能保留 `prompt_tokens / completion_tokens`。新路径同时覆盖主模型与摘要，通过 `purpose: response | summary`、`call_id` 区分；`model.call.started/failed` 记录调用次数和无完整结果的调用。SDK 内部重试与未返回的服务端用量无法据此补齐，因此不是完整账单。`context.compacted` 只给近似压缩前后/摘要 token 数和目标上限；`context.history` 标记 checkpoint 或可见历史导入，`execution_resumed: false` 表示开启新回合而非重放旧执行。未知事件类型不得阻断客户端的 sequence 推进。

重复聊天提交的 gRPC `task.accepted / code: MESSAGE_REPLAY` 只是传输回执，Gateway 转为 HTTP 200，不持久化、不广播为 UI 事件，也不向前端泄漏 LangGraph 类型。

客户端按 `event_id` 去重，按 `sequence` 检测缺口。断线不取消任务。Gateway 在同一订阅注册锁内，先排入 `{"type":"stream.ready","payload":{}}`，再允许实时事件入队。该帧是传输控制消息，不属于产品事件，不分配 `event_id / sequence`，不写活动区。

客户端收到 `stream.ready` 后才通过 REST `events/history?after=` 连续分页重放（每页最多 1000 条），期间缓冲实时事件；回放成功再释放缓冲。历史游标只由已确认的 HTTP 历史推进，不能用较新的实时序号或会话快照跳过活动历史。补拉失败则重连，不先释放越过缺口的实时事件；注册确认超过 10 秒同样重连。慢订阅者被断开后沿用这一恢复路径。

这提供“注册屏障 → 历史补拉 → 实时缓冲”的衔接，不是跨数据库/WebSocket 原子事务或新的 Event Sourcing。Core 持久日志是事件身份的唯一来源；Gateway 不再为缺身份的错误或业务事件发明 ID/序列，转发异常只触发重连。Gateway 与 Web 需一起更新，旧 Gateway 不会发送注册确认。后端注册顺序、身份保持和超过 1000 条历史的定向验收范围见 [交付路线与状态](../project/Roadmap.md)；本次不包含浏览器 GUI E2E。

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
