# NanamiGopher 数据库 ER 图

> 本文档描述了 NanamiGopher 系统的 SQLite 数据库实体关系模型，包含核心业务表、关系定义和字段说明。

---

## ER 图

```mermaid
erDiagram
    USERS ||--o{ CONVERSATIONS : has
    USERS ||--o{ CREDENTIALS : owns
    USERS ||--o{ USER_PREFERENCES : has
    CONVERSATIONS ||--o{ MESSAGES : contains
    CONVERSATIONS ||--o{ TASKS : contains
    TASKS ||--o{ MESSAGES : generates
    TASKS }o--|| SKILLS : uses
    SKILLS ||--o{ SKILL_CREDENTIALS : requires
    CREDENTIALS ||--o{ SKILL_CREDENTIALS : stored_in
    TASKS ||--o{ AUDIT_LOGS : produces
    TASKS ||--o{ WORKFLOW_EXECUTIONS : triggers
    WORKFLOW_EXECUTIONS ||--o{ WORKFLOW_NODES : contains

    USERS {
        uuid id PK
        string username UK
        string email UK
        string password_hash
        string avatar_url
        string role "admin|user"
        int permission_level "L1-L5"
        datetime created_at
        datetime updated_at
    }

    CONVERSATIONS {
        uuid id PK
        uuid user_id FK
        string title
        text description
        datetime last_message_at
        int message_count
        datetime created_at
        datetime updated_at
    }

    MESSAGES {
        uuid id PK
        uuid conversation_id FK
        uuid task_id FK NULL
        uuid sender_id FK
        string role "user|assistant|system"
        text content
        json metadata
        int token_count
        datetime created_at
    }

    TASKS {
        uuid id PK
        uuid conversation_id FK
        uuid creator_id FK
        string status "pending|running|completed|failed|cancelled"
        string mode "manual|accept_edits|plan|auto"
        uuid parent_task_id FK NULL
        int max_steps
        int current_step
        json config
        datetime started_at
        datetime completed_at
        datetime created_at
    }

    SKILLS {
        uuid id PK
        string name UK
        string version
        string description
        text manifest_json "SKILL.md 内容"
        string entry_point
        string execution_type "native|mcp"
        int permission_level
        string author
        datetime created_at
        datetime updated_at
    }

    CREDENTIALS {
        uuid id PK
        uuid user_id FK
        string name
        string provider "openai|anthropic|google|custom"
        string encrypted_value
        json metadata
        datetime expires_at
        datetime created_at
        datetime updated_at
    }

    SKILL_CREDENTIALS {
        uuid id PK
        uuid skill_id FK
        uuid credential_id FK
        string env_key
        datetime created_at
    }

    USER_PREFERENCES {
        uuid id PK
        uuid user_id FK UK
        string theme "light|dark"
        string language "zh-CN|en-US"
        json chat_settings
        json editor_settings
        json notification_settings
        datetime created_at
        datetime updated_at
    }

    AUDIT_LOGS {
        bigint id PK
        uuid actor_id FK
        string action
        string resource_type
        uuid resource_id
        json detail
        string ip_address
        datetime created_at
    }

    WORKFLOW_EXECUTIONS {
        uuid id PK
        uuid task_id FK
        string workflow_name
        string status "running|completed|failed"
        json graph_state
        datetime started_at
        datetime completed_at
        datetime created_at
    }

    WORKFLOW_NODES {
        uuid id PK
        uuid execution_id FK
        string node_id
        string node_type "tool|condition|code|parallel"
        json input_data
        json output_data
        string status "pending|running|completed|failed|skipped"
        float duration_ms
        datetime created_at
        datetime updated_at
    }
```

---

## 表结构详细说明

### 1. users — 用户表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK, UK | 用户唯一标识 |
| username | VARCHAR(64) | NOT NULL, UK | 用户名 |
| email | VARCHAR(255) | NOT NULL, UK | 邮箱地址 |
| password_hash | VARCHAR(255) | NOT NULL | bcrypt 加密密码 |
| avatar_url | VARCHAR(512) | NULL | 头像 URL |
| role | VARCHAR(16) | NOT NULL DEFAULT 'user' | 角色：admin / user |
| permission_level | INTEGER | NOT NULL DEFAULT 1 | 权限等级 L1-L5 |
| created_at | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引：**
- `idx_users_email` ON (email)
- `idx_users_username` ON (username)

---

### 2. conversations — 对话表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK, UK | 对话唯一标识 |
| user_id | UUID | NOT NULL, FK→users.id | 所属用户 |
| title | VARCHAR(255) | NOT NULL DEFAULT '' | 对话标题 |
| description | TEXT | NULL | 对话描述 |
| last_message_at | DATETIME | NULL | 最后一条消息时间 |
| message_count | INTEGER | NOT NULL DEFAULT 0 | 消息总数 |
| created_at | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引：**
- `idx_conversations_user_id` ON (user_id)
- `idx_conversations_created_at` ON (created_at DESC)

---

### 3. messages — 消息表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK, UK | 消息唯一标识 |
| conversation_id | UUID | NOT NULL, FK→conversations.id | 所属对话 |
| task_id | UUID | NULL, FK→tasks.id | 关联任务（可选） |
| sender_id | UUID | NOT NULL, FK→users.id | 发送者 |
| role | VARCHAR(16) | NOT NULL | 角色：user / assistant / system |
| content | TEXT | NOT NULL | 消息正文 |
| metadata | JSON | NULL | 扩展元数据（工具调用、引用等） |
| token_count | INTEGER | NULL | Token 数量统计 |
| created_at | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**索引：**
- `idx_messages_conversation_id` ON (conversation_id)
- `idx_messages_task_id` ON (task_id)
- `idx_messages_role` ON (role)
- `idx_messages_created_at` ON (created_at DESC)
- **FTS5 虚拟表：** `messages_fts(content)` 用于全文检索

---

### 4. tasks — 任务表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK, UK | 任务唯一标识 |
| conversation_id | UUID | NOT NULL, FK→conversations.id | 所属对话 |
| creator_id | UUID | NOT NULL, FK→users.id | 创建者 |
| status | VARCHAR(16) | NOT NULL DEFAULT 'pending' | 状态：pending / running / completed / failed / cancelled |
| mode | VARCHAR(16) | NOT NULL DEFAULT 'manual' | 权限模式：manual / accept_edits / plan / auto |
| parent_task_id | UUID | NULL, FK→tasks.id | 父任务（SubAgent 场景） |
| max_steps | INTEGER | NOT NULL DEFAULT 50 | 最大步数限制 |
| current_step | INTEGER | NOT NULL DEFAULT 0 | 当前步数 |
| config | JSON | NULL | 任务配置（模型、工具列表等） |
| started_at | DATETIME | NULL | 开始时间 |
| completed_at | DATETIME | NULL | 完成时间 |
| created_at | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**索引：**
- `idx_tasks_conversation_id` ON (conversation_id)
- `idx_tasks_status` ON (status)
- `idx_tasks_creator_id` ON (creator_id)

---

### 5. skills — Skill 注册表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK, UK | Skill 唯一标识 |
| name | VARCHAR(128) | NOT NULL, UK | Skill 名称 |
| version | VARCHAR(32) | NOT NULL | 版本号 |
| description | VARCHAR(512) | NOT NULL DEFAULT '' | 简短描述 |
| manifest_json | TEXT | NOT NULL | SKILL.md 完整内容 |
| entry_point | VARCHAR(255) | NULL | 入口命令（MCP 场景） |
| execution_type | VARCHAR(16) | NOT NULL DEFAULT 'native' | 类型：native / mcp |
| permission_level | INTEGER | NOT NULL DEFAULT 1 | 所需权限等级 L1-L5 |
| author | VARCHAR(128) | NULL | 作者 |
| created_at | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP | 注册时间 |
| updated_at | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引：**
- `idx_skills_name` ON (name)
- `idx_skills_execution_type` ON (execution_type)

---

### 6. credentials — 凭证表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK, UK | 凭证唯一标识 |
| user_id | UUID | NOT NULL, FK→users.id | 所属用户 |
| name | VARCHAR(128) | NOT NULL | 凭证名称 |
| provider | VARCHAR(64) | NOT NULL | 提供商：openai / anthropic / google / custom |
| encrypted_value | TEXT | NOT NULL | AES-256 加密的密钥值 |
| metadata | JSON | NULL | 扩展元数据（端点、region 等） |
| expires_at | DATETIME | NULL | 过期时间 |
| created_at | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引：**
- `idx_credentials_user_id` ON (user_id)
- `idx_credentials_provider` ON (provider)

---

### 7. skill_credentials — Skill 与凭证关联表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK, UK | 关联唯一标识 |
| skill_id | UUID | NOT NULL, FK→skills.id | 所需 Skill |
| credential_id | UUID | NOT NULL, FK→credentials.id | 使用的凭证 |
| env_key | VARCHAR(128) | NOT NULL | 环境变量键名 |
| created_at | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**索引：**
- `idx_skill_credential_skill` ON (skill_id)
- `idx_skill_credential_cred` ON (credential_id)
- **联合唯一：** `(skill_id, credential_id)`

---

### 8. user_preferences — 用户偏好表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK, UK | 偏好唯一标识 |
| user_id | UUID | NOT NULL, FK→users.id, UK | 所属用户 |
| theme | VARCHAR(16) | NOT NULL DEFAULT 'dark' | 主题：light / dark |
| language | VARCHAR(16) | NOT NULL DEFAULT 'zh-CN' | 语言 |
| chat_settings | JSON | NULL | 聊天设置（温度、最大 token 等） |
| editor_settings | JSON | NULL | 编辑器设置（缩进、字体等） |
| notification_settings | JSON | NULL | 通知设置 |
| created_at | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP | 更新时间 |

---

### 9. audit_logs — 审计日志表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | BIGINT | PK, UK | 自增主键 |
| actor_id | UUID | NOT NULL, FK→users.id | 操作者 |
| action | VARCHAR(64) | NOT NULL | 操作类型：read/write/delete/install 等 |
| resource_type | VARCHAR(32) | NOT NULL | 资源类型：file/task/skill/credential |
| resource_id | UUID | NOT NULL | 资源标识 |
| detail | JSON | NULL | 详细信息 |
| ip_address | VARCHAR(45) | NULL | 客户端 IP |
| created_at | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP | 操作时间 |

**索引：**
- `idx_audit_actor_id` ON (actor_id)
- `idx_audit_action` ON (action)
- `idx_audit_resource` ON (resource_type, resource_id)
- `idx_audit_created_at` ON (created_at DESC)

---

### 10. workflow_executions — 工作流执行记录表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK, UK | 执行记录唯一标识 |
| task_id | UUID | NOT NULL, FK→tasks.id | 关联任务 |
| workflow_name | VARCHAR(128) | NOT NULL | 工作流名称 |
| status | VARCHAR(16) | NOT NULL DEFAULT 'running' | 状态：running / completed / failed |
| graph_state | JSON | NULL | 当前图状态快照 |
| started_at | DATETIME | NULL | 开始时间 |
| completed_at | DATETIME | NULL | 完成时间 |
| created_at | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP | 创建时间 |

**索引：**
- `idx_workflow_task_id` ON (task_id)
- `idx_workflow_status` ON (status)

---

### 11. workflow_nodes — 工作流节点执行记录表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | UUID | PK, UK | 节点记录唯一标识 |
| execution_id | UUID | NOT NULL, FK→workflow_executions.id | 所属执行 |
| node_id | VARCHAR(128) | NOT NULL | 节点 ID |
| node_type | VARCHAR(16) | NOT NULL | 类型：tool / condition / code / parallel |
| input_data | JSON | NULL | 节点输入 |
| output_data | JSON | NULL | 节点输出 |
| status | VARCHAR(16) | NOT NULL DEFAULT 'pending' | 状态：pending / running / completed / failed / skipped |
| duration_ms | FLOAT | NULL | 执行耗时（毫秒） |
| created_at | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | NOT NULL DEFAULT CURRENT_TIMESTAMP | 更新时间 |

**索引：**
- `idx_workflow_node_execution` ON (execution_id)
- `idx_workflow_node_status` ON (status)
