# 项目目录结构

> **版本**: v1.0  
> **日期**: 2026-07-21

---

## 1. 仓库根目录

```
nanamigopher/
├── cmd/                          # Go 可执行程序入口
│   ├── nanamigopher/             # 主程序
│   └── nanamigopher-server/      # 服务端
├── internal/                     # Go 内部包（不对外导出）
│   ├── config/                   # 配置管理
│   ├── permission/               # 权限校验
│   ├── security/                 # 安全过滤
│   └── websocket/                # WebSocket 处理
├── pkg/                          # Go 公共包（可被外部引用）
│   ├── proto/                    # gRPC 协议定义
│   └── middleware/               # HTTP 中间件
├── api/                          # Go API 层
│   ├── handler/                  # HTTP Handler
│   ├── router/                   # 路由配置
│   └── dto/                      # 数据传输对象
├── grpc/                         # Go gRPC 服务实现
│   └── service/
├── python/                       # Python Agent Core
│   ├── agent/                    # Agent 核心模块
│   │   ├── __init__.py
│   │   ├── core.py               # AgentCore 主类
│   │   ├── task_manager.py       # 任务管理
│   │   ├── execution_engine.py   # 执行引擎
│   │   ├── skill_registry.py     # Skill 注册表
│   │   ├── sub_agent_manager.py  # SubAgent 管理
│   │   ├── inspector/            # Inspector 监控
│   │   │   ├── __init__.py
│   │   │   ├── events.py         # 事件模型
│   │   │   └── timeline.py       # 时间线构建
│   │   ├── memory/               # 记忆系统
│   │   │   ├── __init__.py
│   │   │   ├── system.py         # IMemorySystem
│   │   │   ├── short_term.py     # IShortTermMemory
│   │   │   ├── conversation.py   # IConversationMemory
│   │   │   └── user.py           # IUserMemory
│   │   ├── knowledge_base/       # 知识库
│   │   │   ├── __init__.py
│   │   │   ├── store.py          # IDocumentStore
│   │   │   ├── retriever.py      # IRetriever
│   │   │   └── vector_store.py   # IVectorStore
│   │   ├── tools/                # 工具系统
│   │   │   ├── __init__.py
│   │   │   ├── base.py           # BaseTool 接口
│   │   │   ├── native/           # 原生 Tool
│   │   │   │   ├── file_read.py
│   │   │   │   ├── file_write.py
│   │   │   │   ├── file_edit.py
│   │   │   │   ├── bash.py
│   │   │   │   ├── web_search.py
│   │   │   │   ├── web_fetch.py
│   │   │   │   ├── glob.py
│   │   │   │   ├── grep.py
│   │   │   │   ├── todo_write.py
│   │   │   │   └── sleep.py
│   │   │   ├── mcp_wrapper.py    # MCPToolWrapper
│   │   │   ├── tool_registry.py  # ToolRegistry
│   │   │   ├── permission_mgr.py # PermissionManager
│   │   │   └── validator.py      # ToolValidator
│   │   ├── models/               # 模型层
│   │   │   ├── __init__.py
│   │   │   ├── chat_provider.py  # IChatProvider
│   │   │   ├── embedding_provider.py  # IEmbeddingProvider
│   │   │   ├── image_provider.py        # IImageProvider
│   │   │   └── factory.py              # ModelProviderFactory
│   │   ├── security/             # 安全模块
│   │   │   ├── __init__.py
│   │   │   ├── injection_filter.py  # 注入过滤
│   │   │   ├── whitelist.py         # 白名单
│   │   │   └── audit_log.py         # 审计日志
│   │   ├── workflow/             # 工作流引擎
│   │   │   ├── __init__.py
│   │   │   ├── engine.py          # LangGraph 引擎
│   │   │   └── hitl.py            # HITL 人机协同
│   │   └── utils/                # 工具函数
│   ├── tests/                    # 测试
│   │   ├── unit/
│   │   ├── integration/
│   │   ├── security/
│   │   ├── performance/
│   │   └── fixtures/
│   └── requirements.txt
├── web/                          # Vue 3 前端
│   ├── src/
│   │   ├── main.ts               # 入口
│   │   ├── App.vue
│   │   ├── router/               # 路由配置
│   │   ├── stores/               # Pinia 状态管理
│   │   ├── views/                # 页面组件
│   │   ├── components/           # 通用组件
│   │   ├── composables/          # 组合式函数
│   │   ├── types/                # TypeScript 类型
│   │   ├── utils/                # 工具函数
│   │   └── assets/               # 静态资源
│   ├── public/
│   ├── electron/                 # Electron 主进程
│   │   ├── main.ts
│   │   └── preload.ts
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── package.json
├── docs/                         # 项目文档
│   ├── project/                  # 项目基础文档
│   ├── requirements/             # 需求文档
│   ├── design/                   # 设计文档
│   ├── development/              # 开发规范
│   ├── testing/                  # 测试文档
│   ├── deployment/               # 部署文档
│   ├── ops-security/             # 运维安全
│   ├── user-guide/               # 用户指南
│   ├── reference/                # 参考资料
│   ├── agent-capabilities/       # Agent 能力专项
│   └── workflows/                # 业务工作流
├── config/                       # 配置文件
│   ├── config.yaml               # 主配置
│   ├── config.dev.yaml           # 开发环境配置
│   └── config.prod.yaml          # 生产环境配置
├── scripts/                      # 脚本
│   ├── setup.sh                  # 环境初始化
│   ├── run_tests.sh              # 测试运行
│   ├── build.sh                  # 构建脚本
│   └── deploy.sh                 # 部署脚本
├── .github/                      # GitHub Actions
│   └── workflows/
│       ├── ci.yml                # 持续集成
│       └── release.yml           # 发布流程
├── .vscode/                      # VS Code 配置
├── .gitignore
├── .editorconfig
├── Makefile                      # 构建命令
├── go.mod                        # Go 依赖
├── pyproject.toml                # Python 项目配置
├── Dockerfile                    # 容器化配置
├── docker-compose.yml            # 多容器编排
├── README.md                     # 项目说明
└── LICENSE
```

---

## 2. 关键目录说明

### 2.1 Go 后端 (`cmd/`, `internal/`, `pkg/`, `api/`)

| 目录 | 职责 | 说明 |
|------|------|------|
| `cmd/` | 可执行程序入口 | 每个子目录是一个独立的 binary |
| `internal/` | 内部实现 | 不被外部模块引用的代码 |
| `pkg/` | 公共包 | 可被其他项目引用的代码 |
| `api/` | HTTP 层 | Handler、Router、DTO |
| `grpc/` | gRPC 层 | Go ↔ Python 通信 |

### 2.2 Python Agent Core (`python/agent/`)

| 目录 | 职责 | 说明 |
|------|------|------|
| `core.py` | Agent 主类 | 协调所有模块 |
| `task_manager.py` | 任务管理 | 生命周期、调度、状态 |
| `execution_engine.py` | 执行引擎 | 工具调用、Skill 执行 |
| `skill_registry.py` | Skill 注册表 | 注册、发现、版本管理 |
| `memory/` | 记忆系统 | 短期/会话/用户记忆 |
| `knowledge_base/` | 知识库 | 文档存储、检索、向量 |
| `tools/` | 工具系统 | 原生 Tool + MCP Tool |
| `models/` | 模型层 | Chat/Embedding/Image Provider |
| `security/` | 安全模块 | 注入过滤、白名单、审计 |
| `inspector/` | Inspector | 事件模型、时间线 |
| `workflow/` | 工作流 | LangGraph 编排 |

### 2.3 Vue 3 前端 (`web/src/`)

| 目录 | 职责 | 说明 |
|------|------|------|
| `views/` | 页面组件 | 路由级别的页面 |
| `components/` | 通用组件 | 可复用的 UI 组件 |
| `composables/` | 组合式函数 | 跨组件的逻辑复用 |
| `stores/` | Pinia 状态 | 全局状态管理 |
| `router/` | 路由配置 | Vue Router 定义 |
| `types/` | 类型定义 | TypeScript 接口 |

### 2.4 Electron 主进程 (`web/electron/`)

| 文件 | 职责 |
|------|------|
| `main.ts` | 主进程入口，管理窗口生命周期 |
| `preload.ts` | 预加载脚本，暴露 IPC 接口 |

---

## 3. 配置文件说明

### 3.1 主配置 `config/config.yaml`

```yaml
# 应用配置
app:
  name: "NanamiGopher"
  version: "1.0.0"
  environment: "development"  # development | production

# 模型配置
models:
  prefer_local: true
  local_fallback_order:
    - ollama
    - lm_studio
    - vllm
  chat:
    default: "qwen2.5:32b"
    fallback: "gpt-4o"
  embedding:
    provider: "bge"
    bge:
      model: "BGE-M3"
      device: "cpu"

# 权限配置
permissions:
  default_mode: "manual"  # manual | accept_edits | plan | auto
  circuit_breaker:
    enabled: true
    blocked_patterns:
      - "rm -rf /"
      - "dd if="

# 记忆配置
memory:
  storage:
    sqlite_path: "~/.nanamigopher/data/memories.db"
    vector_db: "chromadb"

# 凭证配置
credentials:
  storage: "os_keychain"  # os_keychain | encrypted_file

# Skill 配置
skills:
  scan_directories:
    - "~/.nanamigopher/skills/"
    - "./skills/"

# 可观测性
observability:
  enabled: true
  console_output: true
  langfuse:
    enabled: false
    endpoint: "http://localhost:3000"
```

### 3.2 开发环境配置 `config/config.dev.yaml`

```yaml
app:
  environment: "development"
  debug: true

models:
  prefer_local: true
  chat:
    default: "ollama/qwen2.5:32b"

observability:
  console_output: true
  verbose_logging: true
```

### 3.3 生产环境配置 `config/config.prod.yaml`

```yaml
app:
  environment: "production"
  debug: false

models:
  prefer_local: true
  chat:
    default: "claude-sonnet-4"

observability:
  console_output: false
  langfuse:
    enabled: true
```

---

## 4. 数据存储路径

```
~/.nanamigopher/
├── config.yaml                 # 用户配置
├── data/
│   ├── memories.db             # SQLite 数据库
│   ├── conversations/          # 对话原文
│   ├── skills/                 # 已安装 Skill
│   └── cache/                  # 缓存文件
├── logs/
│   ├── app.log                 # 应用日志
│   └── audit.log               # 审计日志
└── skills/                     # 用户 Skill 目录
```
