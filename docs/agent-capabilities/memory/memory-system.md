# 记忆系统设计

> **状态**：Current
> **架构版本**：v1
> **最后核验**：2026-09-14
> **权威范围**：记忆分类、职责、生命周期与检索规则

数据实体见 [Database](../../design/Database.md)，模型选择见 [Model Routing](../models/model-routing.md)。

## 1. 边界

```text
Memory System                         Knowledge Base
├── Working Memory                    ├── Document Store
├── Conversation Memory               ├── Chunking / Indexing
└── User Memory                       └── Retrieval

Agent 运行和用户相关信息               用户导入或授权接入的外部资料
```

Memory 不保存凭证；Knowledge Base 不替代对话消息或用户记忆。

## 2. 事实与派生数据

| 数据 | 类型 | 是否可重建 |
|---|---|---|
| Message | 权威事实 | 否 |
| Document 原文 | 权威事实 | 否 |
| User Memory | 经确认或可追溯的领域数据 | 取决于来源 |
| Working Context | 派生运行状态 | 是 |
| Conversation Summary | 派生数据 | 是 |
| Document Chunk | 派生数据 | 是 |
| Embedding / FTS / Vector Index | 派生索引 | 是 |

任何派生记录都必须保存 source ID 和生成版本，不能成为原始内容的唯一副本。

## 3. Working Memory

Working Memory 保存当前任务执行所需的临时信息：

- 当前用户请求和近期消息视图。
- 当前计划、工具结果摘要和未提交中间状态。
- deadline、cancellation、token budget 等执行上下文。

接口能力：

```text
append(entry)
snapshot()
trim(budget)
clear(task_id)
```

约束：

- 作用域是 `workspace_id + task_id`。
- 默认随任务终态清理；崩溃恢复所需内容进入 Task checkpoint。
- 容量按 token/字节控制，不按任意 priority 删除原始 Message。
- 不直接保存 Embedding；语义检索属于持久化 Memory 或 Knowledge Base。

## 4. Conversation Memory

Conversation Memory 从持久化 Message 构建模型上下文：

```text
System/Policy Context
+ Conversation Summary
+ Recent Messages
+ Relevant Tool Result Summaries
+ User Memory
+ Optional Knowledge Retrieval
```

接口能力：

```text
list_messages(conversation_id, cursor)
build_context(conversation_id, token_budget)
summarize(conversation_id, through_sequence)
invalidate_summary(conversation_id)
```

约束：

- Message 顺序以数据库 sequence 为准。
- Summary 保存覆盖的 message sequence、模型和 Prompt 版本。
- Summary 不能覆盖未包含在其 source range 中的新消息。
- 删除或编辑源消息后，相关 Summary 必须失效并重建。

## 5. User Memory

User Memory 保存对后续任务有用的偏好、事实或长期约束。

每条记忆至少包含：

```text
id
workspace_id
subject_user_id（可选）
type
content
source_type + source_id
confidence
visibility
created_at / updated_at / expires_at
status
```

接口能力：

```text
propose(memory, source)
confirm(memory_id)
update(memory_id, patch)
forget(memory_id)
search(scope, query, limit)
```

约束：

- 自动提取产生 `proposed` 记忆；敏感或高影响信息需用户确认。
- 每条记忆必须可追溯到来源或明确标记为用户直接输入。
- API Key、Token、密码、私钥不允许进入 User Memory。
- Personal Memory 不得被 Team Workspace 查询，除非用户明确共享。
- 用户可以查看、修改、导出和删除自己的记忆。

## 6. Knowledge Base

Knowledge Base 管理用户授权的外部文档：

```text
Document
→ immutable content version
→ chunks
→ keyword/vector indexes
→ retrieval results with citations
```

接口能力：

```text
add_document(workspace, content, metadata)
delete_document(document_id)
get_document(document_id)
search(workspace, query, filters, limit)
rebuild_index(workspace, version)
```

约束：

- 文档内容先持久化，再异步创建索引。
- 检索结果必须携带 document/chunk ID 和版本。
- 索引不可用时允许降级到关键词检索或返回明确错误。
- 删除文档后级联清理 chunk、FTS、Embedding 和缓存。

## 7. 检索策略

```text
构建任务上下文
├── 总是读取：近期 Message、有效 Summary
├── 按需读取：User Memory
└── 明确需要外部资料时：Knowledge Base
```

推荐流水线：

1. 解析 Workspace、用户和会话作用域。
2. 过滤过期、删除、不可见或来源失效的数据。
3. 关键词与向量召回。
4. 合并去重并按相关性、时效和可信度排序。
5. 在 token budget 内组装上下文。
6. 保留来源引用，避免把检索内容提升为系统指令。

## 8. 生命周期

| 对象 | 清理/失效条件 |
|---|---|
| Working Memory | 任务终态、TTL、显式取消 |
| Message | 用户删除、Workspace 保留策略 |
| Summary | 源消息变化、Prompt/模型策略升级 |
| User Memory | 用户遗忘、过期、来源撤销、Workspace 删除 |
| Document | 用户删除、来源撤销、保留策略 |
| Index | 源数据删除、Embedding/Chunk版本变化 |

清理必须是可审计流程。删除权威数据与清理派生索引通过事务事件协调。

## 9. 存储适配

Memory 依赖 Repository，不在领域逻辑中判断部署模式：

- 本地：SQLite + 本地内容存储 + 可选本地向量索引。
- 服务器：PostgreSQL + 对象存储 + 可选独立向量服务。

两种实现必须保持相同的 Workspace 隔离、排序、删除和版本语义。

## 10. 可观测性与安全

- 记录检索来源数量、耗时、token 使用和索引版本。
- 日志不记录完整用户记忆或文档内容。
- 检索内容按不可信数据处理，经过内容边界和 Prompt 注入防护。
- Memory 写入、共享、导出和删除产生审计事件。

## 11. 验收清单

- [ ] Working、Conversation、User Memory 职责不重叠。
- [ ] 所有查询强制 Workspace 作用域。
- [ ] Summary 和 Index 可由权威数据重建。
- [ ] 删除能够清理所有派生副本。
- [ ] User Memory 可追溯、可修改、可遗忘。
- [ ] Secret 不进入 Memory、Prompt 日志或向量索引。
