# NanamiGopher 数据库设计

> **状态**：Current + Planned（逐节标注）
> **架构版本**：v1
> **最后核验**：2026-09-18
> **权威范围**：当前持久化事实、归属、事务债务和目标演进

具体字段和 SQL 以 `python/agent/repository.py` 为当前实现事实；本文不把目标表写成已经存在的迁移。

## 1. 当前存储边界

- 当前业务数据库只有 SQLite，启用 foreign keys 与 WAL。
- SQLite 保存 Workspace、Membership、会话、消息、任务、事件、ToolCall、审批、设置、审计、Todo 和显式 User Memory。
- 模型与其他非敏感 Workspace 配置保存在 `workspace_settings` JSON 中。
- Secret 值由 Gateway CredentialStore 保存，不进入 SQLite。
- 原始文档、FTS、Embedding、向量索引、PostgreSQL 和对象存储尚未接入。

当前 Repository 是单进程写入模型；多实例并发与 PostgreSQL 不能从接口抽象推断为已支持。

## 2. 当前归属模型

- `workspaces.kind` 支持 `personal / team`，个人与团队使用同一资源表和业务代码。
- 启动时创建 `personal` Workspace 和 `local-user` Owner Membership。
- 会话、偏好、设置、审计、Todo 和 User Memory 都显式带 Workspace 归属。
- Task、ToolCall、Approval 与 TaskEvent 同时保存 Workspace、Conversation 和 Task 关联，用于 API 作用域检查与恢复。
- 当前没有独立 `users` 表、Team 管理 API、邀请或完整身份生命周期；这些属于服务器团队能力。

## 3. 当前表

| 表 | 当前语义与关键字段 |
|---|---|
| `workspaces` | `id / name / kind / created_at / updated_at` |
| `workspace_memberships` | `(workspace_id, user_id)` 主键与 `role`；当前主要用于访问检查 |
| `conversations` | Workspace、标题、`model_id`、权限模式、响应档位和时间 |
| `messages` | Conversation、`role / content / created_at`；没有显式 sequence/token 列 |
| `user_preferences` | `(workspace_id, subject_user_id, key)` 唯一，保存非敏感 JSON |
| `workspace_settings` | `(workspace_id, key)` 唯一，保存非敏感 JSON |
| `tasks` | Workspace/Conversation、输入、状态、最后错误、版本和时间 |
| `task_events` | Task/Conversation、会话内 sequence、类型、payload 和发生时间 |
| `tool_calls` | Task、工具名、参数、结果、摘要、风险、状态和审批 continuation |
| `approvals` | Task/ToolCall、principal、参数 hash、风险、版本、过期和决定时间 |
| `audit_events` | Workspace、actor、action、resource、result、脱敏详情和时间 |
| `todos` | Workspace 内的文本、完成状态和时间 |
| `user_memories` | Workspace + subject user、类别、内容、来源、置信度和时间 |

User Preference 与 User Memory 不合并：前者是显式产品设置，后者是用户可管理的长期信息。当前 User Memory 只有手动 CRUD 和关键词查询，不会自动抽取、Embedding 检索或注入模型上下文。

## 4. 当前状态值

### Task

```text
created, queued, running, waiting_approval, retry_wait,
succeeded, failed, rejected, expired, cancelled, timed_out, interrupted
```

当前运行路径主要使用 `running / waiting_approval / succeeded / failed / cancelled / timed_out / interrupted`；其余值为调度与重试预留。

### ToolCall

```text
proposed, waiting_approval, running, succeeded, failed,
denied, cancelled, timed_out, expired
```

### Approval

```text
pending, consumed, rejected, expired
```

应用层校验状态字符串；当前 Schema 尚无数据库 `CHECK` 约束。Task 与 Approval 具有递增版本，Approval 决定会校验 principal、版本、过期时间和当前参数 hash。

## 5. 当前约束与索引

- `workspace_memberships(workspace_id, user_id)` 主键。
- `task_events(conversation_id, sequence)` 唯一，并按 sequence 查询。
- 一个 ToolCall 通过 `approvals.tool_call_id UNIQUE` 最多关联一个 Approval。
- Workspace 会话、任务、审计、Todo 和 User Memory 有面向当前查询的索引。
- Messages 当前按 `created_at` 查询；同一时间戳的严格稳定排序仍需显式 sequence。
- Tasks 当前没有到 Workspace/Conversation 的数据库外键，归属完整性依赖应用层；这是迁移债务。
- `task_events` sequence 通过当前单进程 SQLite 锁内的 `MAX + 1` 生成；多实例前必须改为数据库安全分配。

## 6. 当前事务边界与架构债务

当前在单个 SQLite 事务中完成：

- 创建 Approval，并把 ToolCall/Task 切换为等待；
- 决定、过期或取消 Approval，并同步更新关联 ToolCall/Task；
- 单次 Repository 方法内部的数据修改。

尚未原子完成：

- 创建用户消息、Task 与首个 TaskEvent；
- Task 状态转换与对应 TaskEvent；
- ToolCall 结果、Task 推进与事件发布。

`EventBus` 当前先写 `task_events` 再实时投递，因此断线可回放，但领域状态和事件不是同一事务。正式 Unit of Work 与 Outbox 是目标方案，不得在当前文档中宣称已经交付。

## 7. 当前迁移方式

- Repository 启动时执行 `CREATE TABLE IF NOT EXISTS`，并用受限 `ALTER TABLE ADD COLUMN` 兼容旧库。
- 当前没有独立、有版本号的迁移工具，也没有自动 rollback。
- 修改表结构必须至少验证空库启动和现存 SQLite 文件升级。
- 活动数据库备份应使用 SQLite backup API 或一致性快照，不能直接复制正在写入的文件。

## 8. Planned 数据模型

以下能力只有在对应迁移、API 和测试同时交付后才能转为 Current：

- `users` 与完整 Team Membership/邀请/角色生命周期；
- `task_runs`、lease、调度队列、retry 与通用 idempotency key；
- Unit of Work、`outbox_events` 与原子领域事件；
- `documents / document_chunks / index_records` 和可重建 FTS/向量索引；
- `skills / skill_versions / skill_grants` 与签名、版本、授权和回滚；
- `workflows / workflow_versions / workflow_runs / workflow_node_runs`；
- `schedules / schedule_runs`；
- Credential Reference 元数据表（Secret 值仍只在 CredentialProvider）；
- PostgreSQL、多实例锁与正式迁移系统。

## 9. Planned 演进不变量

- 所有用户业务数据直接或间接绑定 Workspace。
- 消息和原始文档是事实来源；摘要与索引可删除重建。
- Secret 不进入业务数据库、Memory、TaskEvent 或普通日志。
- 删除权威数据时必须清理或登记清理派生数据。
- PostgreSQL 适配不能改变 Workspace 隔离、UTC 时间、ID 和状态语义。
