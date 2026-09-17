# NanamiGopher ER 图

> **状态**：Derived
> **来源**：[Database.md](Database.md)
> **最后核验**：2026-09-14

字段、约束和迁移以 Database 与实际 migration 为准；本文档不维护第二套字段表。

```mermaid
erDiagram
    USERS ||--o{ MEMBERSHIPS : joins
    WORKSPACES ||--o{ MEMBERSHIPS : contains
    WORKSPACES ||--o{ CONVERSATIONS : owns
    CONVERSATIONS ||--o{ MESSAGES : contains
    CONVERSATIONS ||--o{ TASKS : starts
    TASKS ||--o{ TASK_RUNS : attempts
    TASK_RUNS ||--o{ TOOL_CALLS : invokes
    TOOL_CALLS ||--o| APPROVALS : requires

    WORKSPACES ||--o{ MEMORIES : owns
    USERS ||--o{ MEMORIES : subject
    WORKSPACES ||--o{ DOCUMENTS : owns
    DOCUMENTS ||--o{ DOCUMENT_CHUNKS : splits
    DOCUMENT_CHUNKS ||--o{ INDEX_RECORDS : indexes

    SKILLS ||--o{ SKILL_VERSIONS : publishes
    WORKSPACES ||--o{ SKILL_GRANTS : installs
    SKILL_VERSIONS ||--o{ SKILL_GRANTS : grants
    WORKSPACES ||--o{ CREDENTIAL_REFERENCES : owns

    WORKSPACES ||--o{ WORKFLOWS : owns
    WORKFLOWS ||--o{ WORKFLOW_VERSIONS : versions
    WORKFLOW_VERSIONS ||--o{ WORKFLOW_RUNS : runs
    TASKS ||--o| WORKFLOW_RUNS : executes
    WORKFLOW_RUNS ||--o{ WORKFLOW_NODE_RUNS : contains

    WORKSPACES ||--o{ SCHEDULES : owns
    SCHEDULES ||--o{ SCHEDULE_RUNS : triggers
    TASKS ||--o| SCHEDULE_RUNS : executes

    WORKSPACES ||--o{ AUDIT_EVENTS : scopes
    TASKS ||--o{ OUTBOX_EVENTS : emits
```

## 关系说明

- Workspace 是业务数据的统一归属边界。
- Message 是会话事实；Working Memory 不作为重复消息表。
- TaskRun 表示一次执行尝试，ToolCall 属于具体尝试。
- Approval 绑定 ToolCall，不是独立可任意创建的业务资源。
- DocumentChunk 是向量与全文索引的稳定来源。
- CredentialReference 不包含 Secret 值。
