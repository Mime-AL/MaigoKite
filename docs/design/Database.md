# NanamiGopher 数据库设计

> **状态**：Current
> **架构版本**：v1
> **最后核验**：2026-09-14
> **权威范围**：逻辑数据模型、归属、约束、事务和迁移原则

具体字段和 SQL 以数据库迁移为实现事实；[ERDiagram](ERDiagram.md) 是本文档的派生视图。

## 1. 存储边界

| 数据 | 权威存储 | 说明 |
|---|---|---|
| Workspace、会话、任务、审批、记忆元数据 | 关系数据库 | 事务事实来源 |
| 原始消息 | 关系数据库 | 不可由摘要替代 |
| 原始文档 | 关系数据库元数据 + 内容存储 | 内容寻址或受控文件路径 |
| FTS、Embedding、向量 | 派生索引 | 可重建，不是唯一事实来源 |
| Secret 值 | CredentialProvider | 不进入业务数据库 |
| 日志与指标 | 可观测性存储 | 不作为业务状态来源 |

本地模式默认 SQLite；服务器模式可使用 PostgreSQL。业务层通过 Repository 与 Unit of Work 访问，不依赖具体方言。

## 2. 归属模型

- 每个 User 自动拥有一个 Personal Workspace。
- Team Workspace 通过 Membership 关联多个 User。
- 所有用户产生的业务资源必须直接或间接关联 `workspace_id`。
- `created_by` 记录创建者，不替代 Workspace 归属。
- 查询必须在 Workspace 作用域内执行。

## 3. 核心实体

### 3.1 身份与空间

| 实体 | 关键约束 |
|---|---|
| users | 稳定 ID；认证标识唯一；状态可禁用 |
| workspaces | type 为 personal/team；名称和生命周期状态 |
| memberships | workspace_id + user_id 唯一；角色和状态受约束 |
| user_preferences | workspace_id + subject_user_id + key 唯一；保存用户级非敏感偏好 |
| workspace_settings | workspace_id + key 唯一；只保存非敏感配置 JSON 与更新时间；Phase 1 的模型配置集合使用 `models.chat.catalog` |

### 3.2 会话与执行

| 实体 | 关键约束 |
|---|---|
| conversations | 属于 Workspace；记录创建者、模型配置 ID、响应速度档、权限模式和归档状态 |
| messages | 属于 Conversation；保存 role、内容、token 和顺序 |
| tasks | 属于 Workspace/Conversation；保存权威状态和版本 |
| task_runs | 记录每次尝试、lease、开始/结束和错误 |
| tool_calls | 关联 TaskRun；保存能力、参数摘要、结果和幂等键 |
| approvals | 关联 ToolCall；绑定参数 hash、范围、过期和决定 |

消息与 Working Memory 不共用一张表。Working Memory 是运行时派生状态，持久化消息是事实来源。

### 3.3 Memory 与知识

| 实体 | 关键约束 |
|---|---|
| memories | Workspace、可选 subject_user、类型、来源、置信度、过期时间 |
| documents | Workspace、内容引用、hash、MIME、版本和状态 |
| document_chunks | 关联文档版本；保存稳定 chunk ID 和文本 |
| index_records | 关联 source/chunk、Provider、模型版本和索引状态 |

用户偏好配置与 User Memory 分离：前者是显式设置，后者是带来源的 Agent 记忆。

### 3.4 Skill、凭证和工作流

| 实体 | 关键约束 |
|---|---|
| skills | 全局不可变标识和发布者 |
| skill_versions | 内容 hash、manifest、版本和信任状态唯一 |
| skill_grants | Workspace 安装状态、能力授权和配置 |
| credential_references | Secret 外部引用、归属、范围和过期信息 |
| workflows | Workspace 中的逻辑工作流 |
| workflow_versions | 不可变定义与版本 |
| workflow_runs | 关联 Task，保存 checkpoint 和终态 |
| workflow_node_runs | 节点级尝试和输出引用 |
| schedules | Workspace 调度规则、时区、状态和继承策略 |
| schedule_runs | 触发时间、关联任务、结果和重试次数 |

### 3.5 审计与事件

| 实体 | 关键约束 |
|---|---|
| audit_events | actor、action、resource、outcome、trace 和不可变时间 |
| outbox_events | 与业务事务同时写入；发布后记录状态和尝试次数 |

审计日志不保存原始 Secret、完整认证头或未经脱敏的工具参数。

## 4. 状态约束

### Task

```text
created, queued, running, waiting_approval, retry_wait,
succeeded, failed, rejected, expired, cancelled, timed_out
```

### ToolCall

```text
created, waiting_approval, running, succeeded, failed,
denied, cancelled, timed_out
```

### Approval

```text
pending, approved, rejected, expired, consumed
```

状态转换通过领域服务执行并使用乐观锁版本，禁止任意字符串更新。

## 5. 关键约束与索引

- `memberships(workspace_id, user_id)` 唯一。
- `messages(conversation_id, sequence)` 唯一。
- `tool_calls(task_run_id, idempotency_key)` 在非空时唯一。
- 同一 ToolCall 同时最多有一个 pending Approval。
- `skill_versions(skill_id, version)` 与内容 hash 受唯一约束。
- 资源列表索引以 `workspace_id` 为首列。
- 任务索引覆盖 Workspace、状态和调度/创建时间。
- 过期清理索引覆盖 `expires_at`。

JSON 字段只保存结构不稳定的扩展数据；需要过滤、关联或约束的字段必须显式建模。

## 6. 事务边界

必须原子提交的操作：

- 创建消息、Task 和首个 OutboxEvent。
- Task 状态转换与对应事件。
- 创建 Approval 并将 ToolCall/Task 设为等待。
- 消费 Approval 并恢复或终止 Task。
- 保存 ToolCall 结果并推进任务。
- 删除原始实体并登记派生索引清理任务。

向量索引更新不参与主事务，通过 Outbox/Job 异步处理。

## 7. SQLite 与 PostgreSQL

共同约束：

- 应用生成 UUID/ULID，不依赖自增语义。
- 时间统一存 UTC。
- 布尔值、JSON、大小写比较和 NULL 排序通过适配层规范化。
- 迁移在两种数据库上分别测试。

SQLite：

- 适用于本地单实例。
- 启用 foreign keys、WAL 和 busy timeout。
- 备份使用 SQLite backup API 或一致性快照，不直接复制活动文件。

PostgreSQL：

- 适用于服务器和多实例。
- 使用连接池、事务隔离和必要的行锁/skip locked。
- 可额外启用数据库级租户保护，但应用层 Workspace 检查仍保留。

## 8. 全文与向量索引

- FTS 索引来源是 messages 或 document_chunks 等已存在的权威表。
- 每条向量记录包含 workspace、source ID、chunk ID、Provider、模型和版本。
- 更换切分或 Embedding 版本时创建新索引版本，再原子切换读流量。
- 删除源数据后必须清理 FTS、向量和缓存。
- 支持从原始数据执行全量重建。

## 9. 迁移

- 所有 Schema 变更使用有序迁移，不在应用启动代码中散落建表 SQL。
- 迁移必须支持空库安装和受支持版本升级。
- 破坏性迁移采用 expand → migrate → contract。
- 发布前在 SQLite 与 PostgreSQL 执行迁移、回滚或恢复演练。
- ER 图和数据字典从迁移/模型生成，禁止独立维护字段副本。

## 10. 保留、删除和备份

- Workspace 删除采用可恢复标记、保留期和最终清理流程。
- 用户可分别删除 Conversation、Memory 和 Document。
- 删除权威数据会调度派生索引清理。
- 审计数据按合规周期保留，并与普通业务删除策略区分。
- 备份与恢复流程见 [Backup](../ops-security/Backup.md)。
