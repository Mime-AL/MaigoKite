# NanamiGopher 数据库设计文档

> **版本**: v1.0  
> **日期**: 2026-07-15  
> **数据库**: SQLite 3 (Phase 1) → ChromaDB/Qdrant (Phase 3+)

---

## 1. 数据库选型

| 数据类型 | 存储方案 | 说明 |
|---------|---------|------|
| 元数据 | SQLite 3 | 配置、权限、Skill 注册表 |
| 记忆数据 | SQLite 3 | 会话历史、用户记忆 |
| 向量数据 | ChromaDB (默认) / Qdrant (可选) | 语义检索 |
| 全文检索 | SQLite FTS5 | 关键词搜索 |
| 文件存储 | 本地文件系统 | 对话原文、Skill 文件 |

---

## 2. SQLite 表结构

### 2.1 会话管理

```sql
-- 会话表
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    title TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_archived BOOLEAN DEFAULT 0,
    permission_mode TEXT DEFAULT 'manual',
    model_id TEXT
);

-- 短期记忆表（当前对话完整上下文）
CREATE TABLE IF NOT EXISTS short_term_memories (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT CHECK(role IN ('user', 'assistant', 'system')) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES conversations(id) ON DELETE CASCADE
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_short_term_session ON short_term_memories(session_id);
CREATE INDEX IF NOT EXISTS idx_short_term_created ON short_term_memories(created_at);
```

### 2.2 用户记忆

```sql
-- 用户记忆表（偏好、事实、任务）
CREATE TABLE IF NOT EXISTS user_memories (
    id TEXT PRIMARY KEY,
    type TEXT CHECK(type IN ('preference', 'fact', 'task')) NOT NULL,
    content TEXT NOT NULL,
    tags TEXT,                     -- JSON 数组: ["python", "project-x"]
    importance_score REAL DEFAULT 0.5,  -- 0.0-1.0
    is_pinned BOOLEAN DEFAULT 0,   -- 用户标记保留
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_user_mem_type ON user_memories(type);
CREATE INDEX IF NOT EXISTS idx_user_mem_tags ON user_memories(tags);
CREATE INDEX IF NOT EXISTS idx_user_mem_expiry ON user_memories(expires_at);
CREATE INDEX IF NOT EXISTS idx_user_mem_pinned ON user_memories(is_pinned);
```

### 2.3 Skill 注册表

```sql
-- Skill 表
CREATE TABLE IF NOT EXISTS skills (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    version TEXT NOT NULL,
    description TEXT,
    mode TEXT CHECK(mode IN ('self_contained', 'directory')) NOT NULL,
    namespace TEXT NOT NULL,
    entry_point TEXT,              -- SKILL.md 路径
    executable TEXT,               -- MCP Server 启动命令
    dependencies TEXT,             -- JSON 数组: ["file-reader", "code-executor"]
    permission_level INTEGER DEFAULT 2,  -- L1-L5
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Skill 命名空间隔离表
CREATE TABLE IF NOT EXISTS skill_namespaces (
    skill_name TEXT NOT NULL,
    namespace TEXT NOT NULL,
    PRIMARY KEY (skill_name, namespace),
    FOREIGN KEY (skill_name) REFERENCES skills(name) ON DELETE CASCADE
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_skills_namespace ON skills(namespace);
CREATE INDEX IF NOT EXISTS idx_skills_active ON skills(is_active);
```

### 2.4 权限配置

```sql
-- 权限规则表
CREATE TABLE IF NOT EXISTS permission_rules (
    id TEXT PRIMARY KEY,
    rule_name TEXT UNIQUE NOT NULL,
    pattern TEXT NOT NULL,         -- 正则表达式
    severity TEXT CHECK(severity IN ('allow', 'ask', 'deny')) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 权限模式配置
CREATE TABLE IF NOT EXISTS permission_modes (
    id TEXT PRIMARY KEY,
    mode_name TEXT UNIQUE NOT NULL,  -- manual, accept_edits, plan, auto
    l1_action TEXT DEFAULT 'allow',
    l2_action TEXT DEFAULT 'allow',
    l3_action TEXT DEFAULT 'ask',
    l4_action TEXT DEFAULT 'ask',
    l5_action TEXT DEFAULT 'deny',
    is_default BOOLEAN DEFAULT 0
);

-- 初始化默认权限模式
INSERT INTO permission_modes (mode_name, l1_action, l2_action, l3_action, l4_action, l5_action, is_default)
VALUES ('manual', 'allow', 'allow', 'ask', 'ask', 'deny', 1);

INSERT INTO permission_modes (mode_name, l1_action, l2_action, l3_action, l4_action, l5_action, is_default)
VALUES ('accept_edits', 'allow', 'allow', 'ask', 'allow', 'deny', 0);

INSERT INTO permission_modes (mode_name, l1_action, l2_action, l3_action, l4_action, l5_action, is_default)
VALUES ('plan', 'allow', 'allow', 'ask', 'ask', 'deny', 0);

INSERT INTO permission_modes (mode_name, l1_action, l2_action, l3_action, l4_action, l5_action, is_default)
VALUES ('auto', 'allow', 'allow', 'allow', 'allow', 'deny', 0);
```

### 2.5 配置管理

```sql
-- 配置表（键值对）
CREATE TABLE IF NOT EXISTS app_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 初始化默认配置
INSERT INTO app_config (key, value, description) VALUES
    ('app.name', 'NanamiGopher', '应用名称'),
    ('app.version', '1.0.0', '应用版本'),
    ('permissions.default_mode', 'manual', '默认权限模式'),
    ('models.prefer_local', 'true', '优先使用本地模型'),
    ('memory.retention.days', '30', '记忆保留天数'),
    ('memory.retention.max_entries', '1000', '最大记忆条目数');
```

### 2.6 审计日志

```sql
-- 安全审计日志表
CREATE TABLE IF NOT EXISTS security_audit_log (
    id TEXT PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_type TEXT CHECK(event_type IN (
        -- 安全过滤事件
        'injection_blocked',
        'whitelist_hit',
        'length_truncated',
        -- 权限事件
        'permission_denied',
        'permission_escalation_attempt',
        -- 凭证事件
        'credential_access',
        -- 工具执行事件
        'tool_executed',
        'tool_failed',
        'tool_cancelled',
        -- 沙箱事件
        'sandbox_escape_attempt',
        -- MCP 生命周期事件
        'mcp_server_started',
        'mcp_server_stopped'
    )) NOT NULL,
    source TEXT CHECK(source IN ('user_input', 'rag_result', 'search', 'tool_return')) NOT NULL,
    matched_rule TEXT,
    severity TEXT CHECK(severity IN ('block', 'warn', 'info')),
    confidence REAL,
    action_taken TEXT,
    input_summary TEXT,
    sanitized_length INTEGER
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON security_audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_event ON security_audit_log(event_type);
```

---

## 3. 向量数据库设计

### 3.1 ChromaDB 集合

```python
# Phase 3+ 使用 ChromaDB
import chromadb

client = chromadb.Client()

# 知识库集合
knowledge_collection = client.get_or_create_collection(
    name="agent_knowledge",
    metadata={"hnsw:space": "cosine"}
)

# 记忆集合
memory_collection = client.get_or_create_collection(
    name="agent_memory",
    metadata={"hnsw:space": "cosine"}
)
```

### 3.2 文档结构

```python
# 知识库文档
{
    "id": "doc_001",
    "document": "Python 官方文档内容...",
    "metadata": {
        "title": "Python 教程",
        "source": "https://docs.python.org",
        "tags": ["python", "tutorial"],
        "created_at": "2026-07-15T10:00:00Z"
    }
}

# 记忆文档
{
    "id": "mem_001",
    "document": "用户偏好使用 Python 进行后端开发",
    "metadata": {
        "type": "preference",
        "tags": ["python", "backend"],
        "importance": 0.8,
        "created_at": "2026-07-15T10:00:00Z",
        "expires_at": "2026-08-15T10:00:00Z"
    }
}
```

---

## 4. 文件存储结构

```
~/.nanamigopher/
├── config.yaml                    # 全局配置
├── data/
│   ├── memories.db               # SQLite 数据库
│   ├── conversations/            # 对话原文
│   │   ├── sess_001.json
│   │   └── sess_002.json
│   ├── skills/                   # Skill 文件
│   │   ├── web-search/
│   │   │   └── SKILL.md
│   │   └── data-analysis/
│   │       ├── SKILL.md
│   │       └── mcp_server.py
│   └── checkpoints/              # 工作流断点
│       └── workflow_001.json
├── logs/
│   ├── security.json             # 安全审计日志
│   └── app.log                   # 应用日志
└── cache/                        # 缓存目录
    └── embeddings/               # Embedding 缓存
```

---

## 5. 数据关系图

```
┌─────────────────┐       ┌─────────────────┐
│  conversations  │       │  short_term_    │
│                 │1───*   │  memories       │
│  id (PK)        │       │  id (PK)        │
│  title          │       │  session_id(FK) │
│  created_at     │       │  role           │
│  updated_at     │       │  content        │
│  is_archived    │       │  created_at     │
└─────────────────┘       └─────────────────┘

┌─────────────────┐       ┌─────────────────┐
│  user_memories  │       │  skills         │
│                 │       │                 │
│  id (PK)        │       │  id (PK)        │
│  type           │       │  name (UK)      │
│  content        │       │  version        │
│  tags           │       │  mode           │
│  importance     │       │  namespace      │
│  is_pinned      │       │  dependencies   │
│  created_at     │       │  permission_    │
│  expires_at     │       │    level        │
└─────────────────┘       └─────────────────┘

┌─────────────────┐       ┌─────────────────┐
│ permission_     │       │  security_      │
│  modes          │       │  audit_log      │
│                 │       │                 │
│  id (PK)        │       │  id (PK)        │
│  mode_name      │       │  timestamp      │
│  l1_action      │       │  event_type     │
│  l2_action      │       │  source         │
│  l3_action      │       │  matched_rule   │
│  l4_action      │       │  severity       │
│  l5_action      │       │  action_taken   │
│  is_default     │       └─────────────────┘
└─────────────────┘
```

---

## 6. 迁移策略

### 6.1 Phase 1 → Phase 2

```sql
-- 新增 FTS5 虚拟表（全文检索）
CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
    title,
    content,
    tags,
    unpinned=1,
    content='knowledge_documents',
    content_rowid='rowid'
);
```

### 6.2 Phase 2 → Phase 3

```sql
-- 新增工作流表
CREATE TABLE IF NOT EXISTS workflows (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    version TEXT NOT NULL,
    dsl_json TEXT NOT NULL,        -- JSON 格式的 DSL 定义
    status TEXT CHECK(status IN ('draft', 'active', 'archived')) DEFAULT 'draft',
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 新增工作流执行记录
CREATE TABLE IF NOT EXISTS workflow_executions (
    id TEXT PRIMARY KEY,
    workflow_id TEXT NOT NULL,
    status TEXT CHECK(status IN ('running', 'completed', 'failed', 'suspended')) NOT NULL,
    checkpoint_data TEXT,          -- JSON 格式的 Checkpoint 数据
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (workflow_id) REFERENCES workflows(id)
);
```

---

## 7. 备份与恢复

### 7.1 备份策略

```bash
#!/bin/bash
# 每日自动备份
BACKUP_DIR="$HOME/.nanamigopher/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 备份 SQLite 数据库
cp "$HOME/.nanamigopher/data/memories.db" "$BACKUP_DIR/memories_$TIMESTAMP.db"

# 备份配置文件
cp "$HOME/.nanamigopher/config.yaml" "$BACKUP_DIR/config_$TIMESTAMP.yaml"

# 压缩备份
tar -czf "$BACKUP_DIR/backup_$TIMESTAMP.tar.gz" -C "$BACKUP_DIR" "memories_$TIMESTAMP.db" "config_$TIMESTAMP.yaml"

# 清理 30 天前的备份
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete
```

### 7.2 恢复策略

```bash
# 从备份恢复
BACKUP_FILE="backup_20260715_100000.tar.gz"
tar -xzf "$BACKUP_DIR/$BACKUP_FILE" -C "$BACKUP_DIR/tmp/"

# 恢复数据库
cp "$BACKUP_DIR/tmp/memories_*.db" "$HOME/.nanamigopher/data/memories.db"

# 恢复配置
cp "$BACKUP_DIR/tmp/config_*.yaml" "$HOME/.nanamigopher/config.yaml"
```

---

## 8. 性能优化

### 8.1 SQLite 优化

```sql
-- 启用 WAL 模式（提高并发写入性能）
PRAGMA journal_mode=WAL;

-- 设置缓存大小（64MB）
PRAGMA cache_size=-64000;

-- 启用外键约束
PRAGMA foreign_keys=ON;

-- 优化查询性能
PRAGMA synchronous=NORMAL;
PRAGMA temp_store=MEMORY;
```

### 8.2 索引策略

| 表 | 字段 | 索引类型 | 说明 |
|----|------|---------|------|
| short_term_memories | session_id | B-Tree | 按会话查询 |
| short_term_memories | created_at | B-Tree | 按时间排序 |
| user_memories | type | B-Tree | 按类型过滤 |
| user_memories | tags | B-Tree | 按标签搜索 |
| user_memories | expires_at | B-Tree | 过期清理 |
| security_audit_log | timestamp | B-Tree | 按时间查询 |
| security_audit_log | event_type | B-Tree | 按事件过滤 |

---

## 9. 安全性

### 9.1 数据加密

```sql
-- SQLite 加密（使用 SQLCipher）
-- 需要在编译时启用加密支持
PRAGMA key = 'your_encryption_key';
PRAGMA cipher_compatibility = 4;
```

### 9.2 敏感数据脱敏

```python
# 审计日志中的敏感信息脱敏
def sanitize_input(input_text: str, max_length: int = 100) -> str:
    """脱敏用户输入"""
    # 去除 API Key、密码等敏感信息
    sanitized = re.sub(r'(api[_-]?key|password|token)\s*[:=]\s*\S+', r'\1: ***', input_text, flags=re.IGNORECASE)
    # 截断过长输入
    return sanitized[:max_length] + "..." if len(sanitized) > max_length else sanitized
```

---

## 10. 附录

### 10.1 ER 图

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ conversations│────<│short_term_   │     │user_memories │
│              │     │memories      │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
       │                                    │
       │                                    │
┌──────▼──────┐                      ┌─────▼──────┐
│permissions_ │                      │   skills   │
│  modes      │                      │            │
└─────────────┘                      └────────────┘
       │                                    │
       │                                    │
┌──────▼────────────────────────────────────▼──────┐
│              security_audit_log                   │
└──────────────────────────────────────────────────┘
```

### 10.2 数据字典

| 表名 | 字段名 | 类型 | 约束 | 说明 |
|------|--------|------|------|------|
| conversations | id | TEXT | PK | 会话唯一标识 |
| conversations | title | TEXT | - | 会话标题 |
| conversations | created_at | TIMESTAMP | DEFAULT | 创建时间 |
| short_term_memories | id | TEXT | PK | 记忆唯一标识 |
| short_term_memories | session_id | TEXT | FK | 关联会话 |
| short_term_memories | role | TEXT | CHECK | 角色（user/assistant/system） |
| short_term_memories | content | TEXT | NOT NULL | 记忆内容 |
| user_memories | id | TEXT | PK | 记忆唯一标识 |
| user_memories | type | TEXT | CHECK | 类型（preference/fact/task） |
| user_memories | content | TEXT | NOT NULL | 记忆内容 |
| user_memories | tags | TEXT | - | JSON 标签数组 |
| user_memories | importance_score | REAL | DEFAULT 0.5 | 重要程度 |
| user_memories | is_pinned | BOOLEAN | DEFAULT 0 | 是否标记保留 |
| skills | id | TEXT | PK | Skill 唯一标识 |
| skills | name | TEXT | UK, NOT NULL | Skill 名称 |
| skills | version | TEXT | NOT NULL | 版本号 |
| skills | namespace | TEXT | NOT NULL | 命名空间 |
| skills | dependencies | TEXT | - | JSON 依赖数组 |
