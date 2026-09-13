# NanamiGopher — Agent 快速上手指南

> 本文档是给 AI Agent（如 Claude、Cursor、Devin 等）的阅读材料，帮助新 Agent 快速理解项目全貌并上手开发。
>
> **阅读顺序**：先读本章概览 → 再读 `docs/project/Vision.md` 了解产品定位 → 然后读 `docs/design/Architecture.md` 了解架构 → 最后根据需要翻阅各模块详细设计。

---

## 1. 项目一句话描述

**NanamiGopher** 是一个中文优先的通用 AI Agent 工作助手，采用 **Go + Python 混合架构** + **Electron + Vue 3 桌面端**，支持本地模型和云端 API 混合调用，通过 MCP 协议可扩展任意工具。

---

## 2. 技术栈总览

| 层级 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 前端 | Vue 3 + Vite + TypeScript | 3.4+ / 5+ / 5+ | 响应式 UI |
| 桌面容器 | Electron | 28+ | 桌面应用打包 |
| API 网关 | Go (Gin) | 1.22+ | HTTP/gRPC/WebSocket 服务 |
| Agent 核心 | Python (LangChain) | 3.11+ | Agent 推理、工具调用、记忆管理 |
| 向量数据库 | ChromaDB | 0.5+ | 语义检索 |
| 结构化存储 | SQLite | 3.35+ | 元数据、配置、记忆 |
| 通信协议 | gRPC + WebSocket + MCP stdio | — | 跨进程通信 |
| 样式框架 | Tailwind CSS + SCSS | 3+ | 样式 |

---

## 3. 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│  用户界面: Electron + Vue 3 (桌面应用)                           │
│  - 三栏布局: 左侧导航栏 + 中间工作区 + 右侧文件管理器            │
│  - 12 个页面: 总览/对话/Inspector/设置/搜索/定时任务/浏览器等   │
└────────────────────────┬────────────────────────────────────────┘
                         │ WebSocket / HTTP
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Go API Gateway (端口 8080)                                      │
│  - HTTP/gRPC 路由分发                                            │
│  - WebSocket 实时推送                                            │
│  - MCP Server 生命周期管理                                       │
│  - 安全过滤 + 权限校验                                           │
│  - 凭证管理 (系统密钥链)                                         │
└────────────────────────┬────────────────────────────────────────┘
                         │ gRPC (端口 8081)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  Python Agent Core                                               │
│                                                                  │
│  执行流:                                                         │
│  ITaskManager → ExecutionEngine → ISkillRegistry → Skill → Sandbox│
│                                                                  │
│  核心模块:                                                       │
│  - Cross-Cutting: ConfigManager, EventBus, Recovery, Observability│
│  - Memory: IMemorySystem (ShortTerm/Conversation/User)           │
│  - Knowledge: IKnowledgeBase (DocumentStore/Retriever/VectorStore)│
│  - Models: IChatProvider / IEmbeddingProvider / IImageProvider   │
│  - Inspector: 事件收集 + 时间线构建                              │
│  - Workflow: DSL 引擎 + HITL 人机协同                            │
└────────────────────────┬────────────────────────────────────────┘
                         │ MCP stdio
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  MCP Server 集群 (动态进程)                                      │
│  - 每个 Skill 是一个独立的 MCP Server 进程                       │
│  - 按需启动，用后回收                                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. 项目目录结构

```
nanamigopher/                          # 仓库根目录
├── cmd/gateway/main.go                # Go 入口
├── internal/                          # Go 内部包
│   ├── api/                           # HTTP Handler + Router
│   ├── grpc/                          # gRPC 服务
│   ├── websocket/                     # WebSocket Hub
│   ├── mcp/                           # MCP Server 管理
│   ├── security/                      # 安全过滤
│   ├── observability/                 # 可观测性
│   ├── credentialstore/               # 跨平台密钥链
│   └── config/                        # 配置加载
├── python/                            # Python Agent Core
│   └── agent/
│       ├── core.py                    # AgentCore 主类
│       ├── task_manager.py            # 任务管理
│       ├── execution_engine.py        # 执行引擎
│       ├── skill_registry.py          # Skill 注册表
│       ├── context_manager.py         # 上下文窗口
│       ├── event_bus.py               # 事件总线
│       ├── recovery.py                # 错误恢复
│       ├── observability.py           # 可观测性
│       ├── config_manager.py          # 配置管理
│       ├── sub_agent_manager.py       # SubAgent 管理
│       ├── memory/                    # 记忆系统
│       ├── knowledge_base/            # 知识库
│       ├── tools/                     # 工具系统
│       │   ├── base.py                # BaseTool 接口
│       │   ├── native/                # 原生 Tool (8个)
│       │   ├── mcp_wrapper.py         # MCP 工具封装
│       │   ├── tool_registry.py       # 工具注册表
│       │   ├── permission_mgr.py      # 权限管理
│       │   └── validator.py           # 参数校验
│       ├── models/                    # 模型层
│       ├── inspector/                 # Inspector 事件+时间线
│       ├── security/                  # 安全模块
│       ├── workflow/                  # 工作流引擎
│       └── utils/                     # 工具函数
├── web/                               # Vue 3 前端
│   ├── src/
│   │   ├── main.ts                    # 入口
│   │   ├── App.vue                    # 根组件
│   │   ├── router/                    # 路由 (12 页面)
│   │   ├── stores/                    # Pinia Store
│   │   ├── views/                     # 页面组件
│   │   ├── components/                # 组件
│   │   │   ├── layout/                # 三栏布局
│   │   │   ├── sidebar/               # 左侧导航
│   │   │   ├── chat-area/             # 对话面板
│   │   │   ├── file-explorer/         # 文件管理器
│   │   │   ├── inspector/             # Inspector 组件
│   │   │   └── common/                # 通用组件
│   │   ├── composables/               # 组合式函数
│   │   ├── types/                     # TypeScript 类型
│   │   ├── utils/                     # 工具函数
│   │   ├── assets/styles/             # 样式
│   │   └── electron/                  # Electron 主进程
│   ├── electron/                      # Electron 主进程
│   ├── vite.config.ts
│   └── package.json
├── docs/                              # 项目文档 (44+ 文件)
├── config/                            # 配置文件
├── scripts/                           # 运维脚本
├── Dockerfile                         # 容器化
├── docker-compose.yml                 # 多容器编排
├── Makefile                           # 构建命令
├── go.mod                             # Go 依赖
├── pyproject.toml                     # Python 配置
└── README.md
```

---

## 5. 核心设计决策

### 5.1 四层工具架构

| 层级 | 说明 | 示例 |
|------|------|------|
| **Layer 0: Runtime 内核** | 不是 Tool，是基础设施 | TaskManager, ExecutionEngine, Planner, MemorySystem 等 |
| **Layer 1: 高频原生 Tool** | Python 直接实现，不走 MCP | file_read, file_write, file_edit, glob, grep, bash, todo_write, sleep |
| **Layer 2: 低频原生 Tool** | Python 直接实现 | web_search, web_fetch, image_generate(可选) |
| **Layer 3: MCP Tool** | SKILL.md 导入的 Skill | browser, ocr, code_executor, 自定义 Skill |

**关键原则**：
- 高频工具（每分钟可能调用几百次）必须原生实现，避免 MCP stdio 通信开销（10-50ms）
- 所有工具实现统一 `BaseTool` 接口
- 工具返回统一 `ToolResult` 结构（Data + Summary + Raw + Metadata）

### 5.2 记忆 vs 知识库分离

- **IMemorySystem** = Agent 内部状态（对话历史、用户偏好、会话上下文）
- **IKnowledgeBase** = Agent 外部知识（文档、FAQ、知识库）
- 两者物理存储也不同：Memory 用 SQLite，Knowledge 用 VectorDB

### 5.3 模型接口分离

- `IChatProvider` — 有上下文、流式输出、tool calling
- `IEmbeddingProvider` — 批处理、固定维度、和向量库绑定
- `IImageProvider` — 异步任务、文件输出
- 统一通过 `ModelProviderFactory` 创建，但接口不合并

### 5.4 执行流

```
ITaskManager (创建/调度/状态/重试/取消)
    ↓ 调用
ExecutionEngine (执行单步/调用Skill/调用Sandbox)
    ↓ 查找
ISkillRegistry (注册/发现/版本/依赖)
    ↓ 找到
Skill 实例
    ↓ 执行
Sandbox Runtime (LocalSandbox → DockerSandbox)
```

### 5.5 三栏布局

- **左侧导航栏**：可收起/展开（64px/240px），包含总览/新建对话/搜索/定时任务/浏览器/包管理/Skill管理/每日回顾/长期计划/归档/设置
- **中间工作区**：自适应宽度，显示当前页面内容
- **右侧文件管理器**：可收起/展开（48px/320px），包含文件树/搜索/预览/操作
- 分隔线可拖拽调整宽度，状态持久化到 localStorage

---

## 6. 开发工作流

### 6.1 启动开发服务器

```bash
# 一键启动所有服务
./scripts/dev.sh

# 或分别启动
# 终端 1: Go API Gateway
go run cmd/gateway/main.go

# 终端 2: Python Agent Core
cd python && python -m agent.core

# 终端 3: 前端开发服务器
cd web && pnpm dev
```

### 6.2 构建

```bash
# 构建所有模块
make build

# 构建 Docker 镜像
make docker-build

# 运行测试
make test
```

### 6.3 代码规范

- **Go**: `gofmt` + `goimports` + `staticcheck`
- **Python**: `ruff check` + `ruff format` + `mypy`
- **Vue/TS**: `eslint --fix` + `prettier --write`
- 提交信息遵循 Conventional Commits

---

## 7. 关键文件索引

| 你想做什么 | 先看哪个文件 |
|-----------|-------------|
| 了解产品定位 | `docs/project/Vision.md` |
| 了解系统架构 | `docs/design/Architecture.md` |
| 了解后端实现 | `docs/design/BackendDesign.md` |
| 了解前端实现 | `docs/design/FrontendDesign.md` |
| 了解数据库设计 | `docs/design/Database.md` |
| 了解 API 接口 | `docs/design/API.md` |
| 了解工具系统 | `python/agent/tools/base.py` |
| 了解记忆系统 | `python/agent/memory/system.py` |
| 了解模型路由 | `python/agent/models/router.py` |
| 了解 Inspector | `python/agent/inspector/events.py` |
| 了解配置结构 | `config/config.yaml` |
| 了解编码规范 | `docs/development/CodingStyle.md` |
| 了解 Git 规范 | `docs/development/GitWorkflow.md` |
| 了解部署方案 | `docs/deployment/Docker.md` |

---

## 8. 常见任务速查

### 8.1 添加一个新原生 Tool

1. 在 `python/agent/tools/native/` 下创建 `your_tool.py`
2. 继承 `BaseTool` 实现 `name()`, `description()`, `parameters_schema()`, `execute()`
3. 在 `python/agent/tools/tool_registry.py` 中注册
4. 在 `docs/design/BackendDesign.md` 的工具列表中补充

### 8.2 添加一个新前端页面

1. 在 `web/src/views/` 下创建 `YourPage.vue`
2. 在 `web/src/router/index.ts` 中添加路由
3. 在 `web/src/components/sidebar/NavMenu.vue` 中添加导航项
4. 在 `web/src/stores/` 中创建对应的 Pinia Store（如需）

### 8.3 添加一个新的 MCP Server

1. 创建目录 `skills/your-skill/`
2. 编写 `SKILL.md`（frontmatter + 使用说明）
3. 编写 MCP Server 入口脚本（stdio 协议）
4. 在 `config/config.yaml` 的 `skills.scan_directories` 中添加目录
5. Agent 启动时自动扫描并注册

### 8.4 修改配置

1. 编辑 `config/config.yaml`（或对应环境的配置文件）
2. Go 端结构体在 `internal/config/models.go` 等文件中定义
3. Python 端在 `python/agent/config_manager.py` 中读取
4. 重启服务生效（Phase 3 支持热重载）

---

## 9. 开发阶段里程碑

| 阶段 | 周期 | 目标 | 关键交付物 |
|------|------|------|-----------|
| **Phase 1** | Week 1-2 | MVP | Go Gateway + Python Agent + 8 个原生 Tool + 基础对话 |
| **Phase 2** | Week 3-6 | 核心体验 | 多对话 + 流式输出 + 本地模型 + Browser/OCR + Electron |
| **Phase 3** | Week 7-12 | 高级编排 | DSL 工作流 + SubAgent + Inspector + 长期记忆 + Plugin 热加载 |
| **Phase 4** | Week 13-16 | 生产就绪 | 安全加固 + Skill 市场 + Team 功能 + CI/CD |

---

## 10. 注意事项

1. **不要自问自答** — 遇到不确定的设计决策，通过 AskUserQuestion 工具向用户提问
2. **先读文档再写代码** — 每个模块的实现必须参照对应的设计文档
3. **保持文档同步** — 代码变更后，同步更新 `docs/` 下的设计文档
4. **更新记忆文件** — 每次对话结束前更新 `memory/long-term.md` 和当日 `memory/YYYY-MM-DD.md`
5. **PRD 是唯一真理** — 如有设计冲突，以 `outputs/prd.md` 为准
6. **中文优先** — 用户界面、文档、注释优先使用中文
7. **不要使用 emoji** — 用户界面中不使用 emoji，仅使用 Unicode 符号或纯文本
8. **三栏布局是最终设计** — 前端布局必须是左侧导航 + 中间工作区 + 右侧文件管理器

---

*本文档基于 NanamiGopher 项目所有设计文档自动生成，最后更新: 2026-07-21*
