# NanamiGopher 配置指南

本指南详细说明 NanamiGopher 的各项配置选项，帮助您根据需求定制工作流和安全策略。

---

## 目录

1. [配置文件概述](#配置文件概述)
2. [模型配置](#模型配置)
3. [存储配置](#存储配置)
4. [权限模式配置](#权限模式配置)
5. [工具配置](#工具配置)
6. [Skill 管理配置](#skill-管理配置)
7. [安全配置](#安全配置)
8. [快捷键自定义](#快捷键自定义)

---

## 配置文件概述

NanamiGopher 使用 `config.yaml` 作为主要配置文件，位于数据目录下的 `config/` 子目录中。

- **macOS**：`~/.local/share/NanamiGopher/config/config.yaml`
- **Windows**：`%APPDATA%\NanamiGopher\config\config.yaml`
- **Linux**：`~/.config/NanamiGopher/config/config.yaml`

您也可以通过图形界面（设置面板）修改大部分配置项，这些修改会自动同步到 `config.yaml`。

---

## 模型配置

NanamiGopher 支持灵活的模型配置，包括 Chat Model、Embedding 和 Image Generation。

### 基本结构

```yaml
models:
  chat:
    provider: openai              # 模型提供商
    model_name: gpt-4o            # 模型名称
    api_key: ""                   # API Key（留空则使用环境变量 NANAMIGOPHER_OPENAI_API_KEY）
    base_url: ""                  # 自定义 API 地址（用于兼容 OpenAI 格式的本地/第三方服务）
    temperature: 0.7              # 生成温度（0.0-2.0）
    max_tokens: 4096              # 最大生成 token 数
    timeout: 60                   # 请求超时秒数

  embedding:
    provider: local               # 嵌入模型提供商
    model_name: bge-m3            # 默认使用本地 BGE-M3
    dimensions: 1024              # 向量维度
    batch_size: 64                # 批量处理大小

  image_generation:
    enabled: false                # 是否启用图像生成
    provider: ""                  # 图像生成提供商（如 openai, stable-diffusion）
    model_name: ""                # 图像生成模型名称
    size: "1024x1024"             # 图像尺寸
```

### 支持的 Chat Model 提供商

| 提供商 | provider 值 | 备注 |
|--------|-------------|------|
| OpenAI | `openai` | 默认配置，支持 GPT-4o、GPT-4 Turbo 等 |
| Anthropic | `anthropic` | 支持 Claude 系列模型 |
| 本地 Ollama | `ollama` | 需要本地运行 Ollama 服务 |
| 本地 vLLM | `vllm` | 需要本地部署 vLLM 推理服务 |
| 自定义 OpenAI 兼容 | `openai-compatible` | 设置 base_url 即可接入任意兼容服务 |

### 切换模型

在图形界面中：设置 > 模型配置 > Chat Model，从下拉列表中选择目标模型。

命令行方式切换：

```bash
# 查看当前配置
nanamigopher models show

# 切换到 gpt-4o
nanamigopher models set-chat gpt-4o

# 切换到本地 Ollama 模型
nanamigopher models set-chat ollama/llama3
```

### Embedding 模型

默认使用本地的 BGE-M3 Embedding 模型，无需额外配置。如需更换：

```yaml
models:
  embedding:
    provider: local
    model_name: bge-m3          # 或更换为其他本地模型
    # provider: openai           # 也可使用 OpenAI 的 text-embedding-3-large
    # model_name: text-embedding-3-large
```

---

## 存储配置

NanamiGopher 采用本地优先的数据存储策略，使用 SQLite 存储结构化数据，ChromaDB 存储向量数据。

### 基本结构

```yaml
storage:
  # 根数据目录
  data_dir: "~/.local/share/nanamigopher/data"

  # SQLite 配置
  sqlite:
    db_path: "sqlite.db"        # 数据库文件名
    journal_mode: WAL           # 日志模式，推荐 WAL 以获得更好的并发性能
    sync_mode: NORMAL           # 同步模式

  # ChromaDB 配置
  chromadb:
    enabled: true               # 是否启用 ChromaDB
    path: "chroma_data"         # 本地持久化路径
    collection_name: "default"  # 默认集合名称
    distance_metric: "cosine"   # 距离度量方式：cosine / l2 / ip

  # 向量数据库切换（可选）
  vector_db:
    backend: chromadb           # 当前后端：chromadb / qdrant / milvus
    # 如果使用 Qdrant
    # backend: qdrant
    # url: "http://localhost:6333"
    # api_key: ""
    # 如果使用 Milvus
    # backend: milvus
    # uri: "http://localhost:19530"
```

### 存储迁移

从一种向量数据库迁移到另一种：

```bash
# 导出所有向量数据
nanamigopher storage export --output ./vector_backup.json

# 修改 config.yaml 中的 vector_db.backend

# 导入数据到新后端
nanamigopher storage import --input ./vector_backup.json
```

### 数据备份

```bash
# 备份整个数据目录
tar czf nanamigopher-backup-$(date +%Y%m%d).tar.gz ~/.local/share/nanamigopher/

# 仅备份 SQLite 数据库
cp ~/.local/share/nanamigopher/data/sqlite.db ~/backup/
```

---

## 权限模式配置

权限模式决定了 NanamiGopher 在执行操作时的自主程度。

### 基本结构

```yaml
permissions:
  mode: manual                  # 权限模式：manual / accept_edits / plan / auto
  # 工具权限分级（L1-L5）
  tool_levels:
    l1_safe:                    # L1：只读、无副作用操作
      enabled: true
      auto_approve: true
    l2_low_risk:                # L2：低风险的写操作
      enabled: true
      auto_approve: false
    l3_medium_risk:             # L3：中等风险操作
      enabled: true
      auto_approve: false
    l4_high_risk:               # L4：高风险操作
      enabled: true
      auto_approve: false
    l5_critical:                # L5：关键操作（网络、系统级别）
      enabled: true
      auto_approve: false
```

### 四种权限模式详解

#### Manual（手动确认）

- 每次工具调用前都会弹出确认对话框
- 适合新手用户或对安全性要求极高的场景
- 所有操作都需要用户显式批准

#### AcceptEdits（接受编辑）

- 文件读写操作自动批准
- 终端命令和网络请求仍需确认
- 适合日常开发辅助场景

#### Plan（仅规划）

- 不会执行任何实际操作
- 只会生成执行计划和步骤说明
- 适合方案讨论和任务规划

#### Auto（完全自动）

- 所有操作自动执行，无需确认
- 仅在 L5 级别（关键操作）会弹出确认
- 适合高级用户和自动化工作流

### 工具权限 L1-L5 分级说明

| 级别 | 名称 | 说明 | 示例操作 |
|------|------|------|----------|
| L1 | 安全 | 只读、无副作用 | 读取文件、列出目录、搜索文本 |
| L2 | 低风险 | 低风险的写操作 | 创建文件、修改文件内容、todo 写入 | |
| L3 | 中等风险 | 可能影响多个文件的操作 | 批量编辑、复杂 bash 命令 |
| L4 | 高风险 | 系统级或网络操作 | 安装软件包、修改系统配置 |
| L5 | 关键 | 不可逆或危险操作 | 删除文件/目录、网络请求 |

---

## 工具配置

NanamiGopher Phase 1 提供了 10 个核心工具，每个工具都可以进行参数配置。

### 基本结构

```yaml
tools:
  # 文件读取
  file_read:
    enabled: true
    max_file_size: 1048576      # 最大读取文件大小（字节），默认 1MB
    allowed_extensions: []      # 允许读取的文件扩展名，空表示全部允许

  # 文件写入
  file_write:
    enabled: true
    max_file_size: 1048576      # 最大写入文件大小（字节），默认 1MB
    auto_backup: true           # 写入前是否自动备份原文件
    backup_dir: ".nanamigopher/backups"  # 备份目录

  # 文件编辑
  file_edit:
    enabled: true
    max_diff_size: 50           # 最大差异行数，超出需要用户确认
    syntax_check: true          # 编辑后是否进行语法检查

  # Bash 终端
  bash:
    enabled: true
    timeout: 30                 # 命令超时时间（秒）
    max_output_lines: 1000      # 最大输出行数
    allowed_commands: []        # 允许的命令白名单，空表示全部允许
    blocked_commands:           # 禁止的命令黑名单
      - "rm -rf /"
      - "mkfs"
      - "dd if="

  # 网页搜索
  web_search:
    enabled: true
    engine: duckduckgo          # 搜索引擎：duckduckgo / google / bing
    max_results: 10             # 最大搜索结果数
    timeout: 15                 # 搜索超时时间（秒）

  # 网页抓取
  web_fetch:
    enabled: true
    timeout: 30                 # 页面加载超时时间（秒）
    max_content_length: 524288  # 最大内容长度（字节），默认 512KB
    user_agent: "NanamiGopher/1.0"  # 请求 User-Agent
    follow_redirects: true      # 是否跟随重定向

  # 文件匹配（Glob）
  glob:
    enabled: true
    max_matches: 100            # 最大匹配数量
    case_sensitive: false       # 是否区分大小写

  # 全局搜索（Grep）
  grep:
    enabled: true
    max_matches: 100            # 最大匹配数量
    include_hidden: false       # 是否搜索隐藏文件
    ignore_patterns:            # 忽略的文件/目录模式
      - "node_modules"
      - ".git"
      - "__pycache__"
      - "*.min.js"

  # 任务列表
  todo_write:
    enabled: true
    max_items: 100              # 最大任务项数
    auto_archive_days: 30       # 超过多少天的完成任务自动归档

  # 睡眠/延迟
  sleep:
    enabled: true
    max_duration: 3600          # 最大睡眠时长（秒），默认 1 小时
```

### 工具白名单配置

如果您希望限制某些工具的使用，可以配置白名单：

```yaml
tools:
  whitelist:
    enabled: true
    allowed_tools:
      - file_read
      - file_write
      - bash
      - web_search
```

---

## Skill 管理配置

NanamiGopher 的 Skill 体系基于 MCP（Model Context Protocol）Server 构建，每个 Skill 通过 `SKILL.md` 文件定义其行为和能力。

### 基本结构

```yaml
skills:
  # Skill 目录
  directory: "~/.nanamigopher/skills"

  # 自动加载
  auto_load: true

  # 加载超时
  load_timeout: 10

  # 全局 Skill 设置
  global_settings:
    max_concurrent_skills: 5    # 同时运行的最大 Skill 数
    cache_enabled: true         # 是否缓存 Skill 元数据
    cache_ttl: 3600             # 缓存过期时间（秒）
```

### SKILL.md 文件格式

每个 Skill 目录中必须包含一个 `SKILL.md` 文件，格式如下：

```markdown
# Skill 名称

## 描述
简短描述 Skill 的功能和用途。

## 触发条件
什么情况下应该使用这个 Skill（自然语言描述）。

## 参数
- param1: 参数1的描述
- param2: 参数2的描述

## 使用示例
示例 1：...
示例 2：...

## 注意事项
使用此 Skill 时的限制和注意事项。
```

### Skill 安装

通过图形界面：设置 > Skill 管理 > 安装 Skill，输入 Skill 的 Git 仓库地址或本地路径。

通过命令行：

```bash
# 从 Git 仓库安装
nanamigopher skills install https://github.com/user/my-skill

# 从本地目录安装
nanamigopher skills install /path/to/local-skill

# 安装后自动加载
nanamigopher skills install --auto-load <source>
```

### Skill 连接配置（MCP Server）

对于基于 MCP Server 的 Skill，可以配置连接参数：

```yaml
skills:
  mcp_servers:
    - name: my-server
      transport: stdio            # 传输方式：stdio / http
      command: "npx"
      args: ["-y", "@modelcontextprotocol/server-filesystem"]
      env:
        SERVER_DIR: "/path/to/allowed/dir"
      timeout: 30
      retries: 3
```

### Skill 优先级

当多个 Skill 都可能响应同一个请求时，使用优先级决定调用顺序：

```yaml
skills:
  priority_order:
    - "git-helper"
    - "code-review"
    - "documentation"
```

---

## 安全配置

NanamiGopher 提供了多层次的安全机制，保护您的数据和操作安全。

### 基本结构

```yaml
security:
  # 沙箱模式
  sandbox:
    enabled: false                # 是否启用沙箱隔离
    mode: "network-isolated"     # 沙箱模式：none / network-isolated / full
    # network-isolated：隔离网络访问
    # full：完全隔离（仅允许白名单内的操作）

  # 命令白名单
  command_whitelist:
    enabled: false
    allowed_patterns:
      - "ls *"
      - "cat *"
      - "grep *"

  # 凭证存储
  credentials:
    storage: "keychain"           # 存储方式：keychain / encrypted-file / env
    # keychain：使用系统密钥链（macOS Keychain / Windows Credential Manager / libsecret）
    # encrypted-file：加密存储在本地文件中
    # env：仅从环境变量读取，不存储
    file_path: "~/.nanamigopher/credentials.enc"  # 加密文件路径（当 storage=encrypted-file 时）

  # 网络限制
  network:
    allow_outbound: true          # 是否允许出站网络请求
    allow_inbound: false          # 是否允许入站连接
    blocked_domains: []           # 阻止的域名列表
    allowed_domains: []           # 允许的域名列表（为空表示不限制）

  # 审计日志
  audit_log:
    enabled: true
    path: "audit.log"             # 日志文件路径
    rotation_size_mb: 50          # 日志轮转大小（MB）
    retention_days: 90            # 日志保留天数
```

### 沙箱模式详解

| 模式 | 说明 | 适用场景 |
|------|------|----------|
| none | 不启用沙箱 | 个人开发环境 |
| network-isolated | 隔离网络访问，允许本地文件系统操作 | 处理敏感代码时 |
| full | 完全隔离，仅允许白名单操作 | 高安全要求的生产环境 |

### 凭证加密

使用加密文件存储凭证时，需要设置主密码：

```bash
# 设置主密码
nanamigopher security set-master-password

# 更改主密码
nanamigopher security update-master-password

# 清除已存储的凭证
nanamigopher security clear-credentials
```

---

## 快捷键自定义

NanamiGopher 支持自定义快捷键，以满足个人的操作习惯。

### 默认快捷键

| 快捷键 | 功能 |
|--------|------|
| `Ctrl+B` | 切换左侧导航栏（显示/收起） |
| `Ctrl+Shift+F` | 切换右侧文件管理器（显示/收起） |
| `Ctrl+N` | 新建对话 |
| `Ctrl+Shift+N` | 新建定时任务 |
| `Ctrl+Shift+S` | 打开搜索面板 |
| `Ctrl+P` | 快速切换模型 |
| `Ctrl+Shift+P` | 命令面板 |
| `Esc` | 取消当前操作 / 关闭弹窗 |
| `Ctrl+Enter` | 发送对话消息 |

### 自定义快捷键

通过图形界面：设置 > 快捷键，找到对应功能并修改按键组合。

通过配置文件：

```yaml
shortcuts:
  toggle_sidebar:
    - "Ctrl+B"
    - "Cmd+B"                     # macOS 上 Cmd+B 也有效
  toggle_file_manager:
    - "Ctrl+Shift+F"
  new_conversation:
    - "Ctrl+N"
  search:
    - "Ctrl+Shift+S"
  quick_model_switch:
    - "Ctrl+P"
  command_palette:
    - "Ctrl+Shift+P"
  send_message:
    - "Ctrl+Enter"
```

### 冲突检测

修改快捷键时，系统会自动检测与其他应用程序的冲突。如果检测到冲突，会在设置面板中显示警告提示。

```bash
# 检查快捷键冲突
nanamigopher shortcuts check-conflicts
```
