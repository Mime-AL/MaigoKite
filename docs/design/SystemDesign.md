# NanamiGopher 系统设计文档

> **版本**: v1.2  
> **日期**: 2026-07-21  
> **定位**: 基于 Go + Python 混合架构的通用 AI Agent 系统

---

## 1. 系统概述

### 1.1 产品定位

NanamiGopher 是一个通用 AI Agent 助手，面向个人用户（也可兼容团队协作）。它具备以下特征：

- **本地优先**：核心功能完全本地运行，保护用户隐私
- **模型灵活**：支持开源本地模型 + 各大厂商 API 混合调用
- **可扩展**：通过 SKILL.md 标准动态加载新技能
- **透明可控**：用户全程可见 Agent 的思考过程和工具调用，拥有最终控制权
- **三栏布局**：左侧固定导航 + 中间工作区 + 右侧文件管理器

### 1.2 核心设计原则

1. **用户始终在环**（Human-in-the-loop）：关键操作需用户确认
2. **本地优先**：所有数据默认存储在本地
3. **渐进增强**：基础功能离线可用，联网后能力扩展
4. **透明可信**：Agent 的思考和操作对用户可见
5. **可插拔扩展**：通过 Skill 体系无限扩展能力

### 1.3 架构分层理念

```
┌─────────────────────────────────────────────────────────────┐
│              Agent Framework vs Agent Application             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Agent Framework（平台能力）                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ • Tool 系统（四层架构：原生 + MCP）                    │  │
│  │ • Memory 系统（会话历史 + RAG）                        │  │
│  │ • Model 系统（IChatProvider / IEmbeddingProvider）     │  │
│  │ • Security 系统（过滤 + 白名单）                      │  │
│  │ • CredentialStore（凭证管理）                          │  │
│  │ • Permission 系统（L1-L5 分级）                       │  │
│  │ • Inspector（执行监控）                                │  │
│  └──────────────────────────────────────────────────────┘  │
│           │                                                 │
│           ▼                                                 │
│  Agent Application（业务工作流）                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ • Boss 直聘工作流（浏览器自动化 + OCR + 评分）         │  │
│  │ • 竞品分析工作流                                       │  │
│  │ • 自动化报表工作流                                     │  │
│  │ • 更多...（通过 Plugin/Skill 扩展）                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. 整体架构

### 2.1 架构图

```
┌──────────────────────────────────────────────────────────────────────┐
│                        用户界面层 (Frontend)                          │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │           Electron 桌面应用（Phase 1）→ 后续评估迁移 Tauri       │  │
│  │  ┌──────────────┐  ┌──────────────────────────────────────┐    │  │
│  │  │  Vue 3 + Vite│  │  三栏布局：导航栏 + 工作区 + 文件管理器│    │  │
│  │  └──────────────┘  └──────────────────────────────────────┘    │  │
│  └────────────────────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────────────┤
│             │  WebSocket / HTTP                              │  gRPC  │
│  ┌──────────┴──────────────────────────────────────────────────────┐  │
│  │           Go API Gateway (端口 8080)                             │  │
│  │  ┌──────────────────────────────────────────────────────────┐   │  │
│  │  │  • 路由分发      • 权限校验      • 会话管理                │   │  │
│  │  │  • 事件推送      • MCP Server 管理 • 错误聚合              │   │  │
│  │  │  • 前端事件流 (WebSocket)       • 可观测性 (Metrics)       │   │  │
│  │  │  • Inspector 监控 (WebSocket + REST API)                  │   │  │
│  │  │  • 工具分发 (Native Tool Dispatch + MCP Client)            │   │  │
│  │  └──────────────────────────────────────────────────────────┘   │  │
│  └────────────────────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────────────┤
│                     │  HTTP/gRPC                                     │
│  ┌──────────────────┴──────────────────────────────────────────────┐ │
│  │      Python Agent Core (端口 8081)                               │ │
│  │  ┌──────────────────────────────────────────────────────────┐   │ │
│  │  │  Cross-Cutting Services                                   │   │ │
│  │  │  • IConfigManager    • IEventBus    • IExecutionRecovery  │   │ │
│  │  │  • IObservability   （Phase1: ConsoleObserver）           │   │ │
│  │  └──────────────────────────────────────────────────────────┘   │ │
│  │  ┌──────────────────────────────────────────────────────────┐   │ │
│  │  │  ITaskManager                                             │   │ │
│  │  │  （创建/调度/状态/重试/取消 + 并发控制预留）               │   │ │
│  │  └─────────────────────┬────────────────────────────────────┘   │ │
│  │                        │ 调用                                    │ │
│  │  ┌─────────────────────▼────────────────────────────────────┐   │ │
│  │  │  ExecutionEngine                                          │   │ │
│  │  │  （执行单步/调用工具注册表/权限校验/生命周期管理）          │   │ │
│  │  └─────────────────────┬────────────────────────────────────┘   │ │
│  │                        │ 查找                                    │ │
│  │  ┌─────────────────────▼────────────────────────────────────┐   │ │
│  │  │  Tool Registry（统一管理原生 Tool + MCP Tool）             │ │   │ │
│  │  │  ┌──────────────────────────────────────────────────┐   │   │ │
│  │  │  │ Layer 0: Runtime 内核 (非 Tool)                    │   │   │ │
│  │  │  │ TaskManager │ ExecutionEngine │ Planner │ ...     │   │   │ │
│  │  │  └──────────────────────────────────────────────────┘   │   │ │
│  │  │  ┌──────────────────────────────────────────────────┐   │   │ │
│  │  │  │ Layer 1: 高频原生 Tool (Python 直接实现)            │   │   │ │
│  │  │  │ file_read │ file_write │ file_edit │ glob │ grep │   │   │ │
│  │  │  │ bash │ todo_write │ sleep                        │   │   │ │
│  │  │  └──────────────────────────────────────────────────┘   │   │ │
│  │  │  ┌──────────────────────────────────────────────────┐   │   │ │
│  │  │  │ Layer 2: 低频原生 Tool (Python 直接实现)            │   │   │ │
│  │  │  │ web_search │ web_fetch                            │   │   │ │
│  │  │  └──────────────────────────────────────────────────┘   │   │ │
│  │  │  ┌──────────────────────────────────────────────────┐   │   │ │
│  │  │  │ Layer 3: MCP Tool (SKILL.md 导入)                 │   │   │ │
│  │  │  │ browser │ ocr │ code_executor │ custom skills    │   │   │ │
│  │  │  └──────────────────────────────────────────────────┘   │   │ │
│  │  │  统一接口: BaseTool → execute(context, args) → ToolResult│   │ │
│  │  └──────────────────────────────────────────────────────────┘   │ │
│  │  ┌──────────────────────────────────────────────────────────┐   │ │
│  │  │  IMemorySystem                                            │   │ │
│  │  │  ├── IShortTermMemory                                      │   │ │
│  │  │  ├── IConversationMemory                                   │   │ │
│  │  │  └── IUserMemory                                           │   │ │
│  │  └──────────────────────────────────────────────────────────┘   │ │
│  │  ┌──────────────────────────────────────────────────────────┐   │ │
│  │  │  IKnowledgeBase                                           │   │ │
│  │  │  ├── IDocumentStore                                        │   │ │
│  │  │  ├── IRetriever                                            │   │ │
│  │  │  └── IVectorStore                                          │   │ │
│  │  └──────────────────────────────────────────────────────────┘   │ │
│  │  ┌──────────────────────────────────────────────────────────┐   │ │
│  │  │  ModelRegistry → ModelProviderFactory                     │   │ │
│  │  │  ├── IChatProvider                                       │   │ │
│  │  │  ├── IEmbeddingProvider                                  │   │ │
│  │  │  └── IImageProvider                                      │   │ │
│  │  └──────────────────────────────────────────────────────────┘   │ │
│  │  ┌──────────────────────────────────────────────────────────┐   │ │
│  │  │  SubAgentManager（单对话内并行执行单元）                   │   │ │
│  │  └──────────────────────────────────────────────────────────┘   │ │
│  │  ┌──────────────────────────────────────────────────────────┐   │ │
│  │  │  Inspector（执行监控：EventBus → WebSocket → 前端渲染）   │   │ │
│  │  └──────────────────────────────────────────────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────────────┤
│                     │  stdio / MCP                                   │
│  ┌──────────────────┴──────────────────────────────────────────────┐ │
│  │         MCP Server 集群（仅 Layer 3 Skill 化工具）               │ │
│  │  • Browser Server (Playwright)   • OCR Server (PaddleOCR)       │ │
│  │  • CodeExecutor Server           • Custom Skill Servers         │ │
│  │  （SKILL.md 导入，自动发现工具）                                 │ │
│  └────────────────────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────────────┤
│                     │  Model API                                     │
│  ┌──────────────────┴──────────────────────────────────────────────┐ │
│  │         模型层 (Model Layer)                                     │ │
│  │  ┌─────────┐ ┌──────────┐ ┌────────────┐ ┌──────────────────┐   │ │
│  │  │ Ollama  │ │ vLLM/    │ │ LM Studio  │ │ 云端 API         │   │ │
│  │  │ :11434  │ │ llama.cpp│ │ :1234      │ │ OpenAI/Claude    │   │ │
│  │  └─────────┘ └──────────┘ └────────────┘ └──────────────────┘   │ │
│  └────────────────────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────────────┤
│                     │  Storage Layer                                 │
│  ┌──────────────────┴──────────────────────────────────────────────┐ │
│  │  • SQLite: 元数据、配置、权限规则（IMemorySystem/IConfigManager） │   │
│  │  • ChromaDB/Qdrant: 向量存储（IKnowledgeBase）                   │   │
│  │  • 文件系统: 对话原文、Skill 文件、缓存（IStorage）               │   │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 技术栈清单

| 层级 | 技术选型 | 说明 |
|------|---------|------|
| 前端框架 | Vue 3 + Vite | 桌面端 UI 组件库 |
| 桌面容器 | Electron 28+（Phase 1） | 后续评估迁移 Tauri |
| API 网关 | Go 1.22+ (Gin) | 高性能服务层 |
| Agent 核心 | Python 3.11+ | 接口抽象 + 运行时 |
| 工作流引擎 | LangGraph（仅复杂工作流） | Phase 3 引入 |
| 工具协议 | MCP (Model Context Protocol) | stdio 通信（仅 Layer 3） |
| 向量数据库 | ChromaDB (默认) / Qdrant (可选) | 语义检索 |
| 结构化存储 | SQLite 3 | 元数据、配置 |
| 模型适配 | IModelProvider 抽象 | 统一模型接口 |
| 本地模型 | Ollama / vLLM / LM Studio | 三种都支持 |
| 通信协议 | gRPC (Go↔Python) + WebSocket (前端↔Go) | 实时双向通信 |
| 序列化 | JSON Schema (MCP) + Protobuf (gRPC) | 高效数据传输 |
| 可观测性 | OpenTelemetry + Langfuse (Phase 3) | 链路追踪 |
| 事件总线 | InMemoryEventBus (Phase 1) → Redis Pub/Sub (Phase 3) | 事件驱动 |

---

## 3. 进程模型

```
进程结构:

┌─────────────────────────────────────────────────────┐
│ 进程 1: Electron/Tauri 桌面应用                      │
│   • 前端渲染 (Vue 3)                                 │
│   • WebSocket 连接到 Go API Gateway                  │
│   • 端口: 随机                                       │
├─────────────────────────────────────────────────────┤
│ 进程 2: Go API Gateway                              │
│   • HTTP/REST API                                    │
│   • gRPC 到 Python Agent                             │
│   • WebSocket 流式推送                               │
│   • 端口: 8080                                       │
├─────────────────────────────────────────────────────┤
│ 进程 3: Python Agent Core                           │
│   • 四层工具架构（原生 + MCP）                        │
│   • 向量数据库客户端 (ChromaDB/Qdrant)               │
│   • 模型适配层                                       │
│   • 端口: 8081 (gRPC)                               │
├─────────────────────────────────────────────────────┤
│ 进程 4-N: MCP Server（仅 Layer 3，按需启停）         │
│   • 每个 Skill 一个 stdio 进程                       │
│   • 通过 SKILL.md 导入，自动发现工具                 │
│   • 端口: N/A (stdio)                                │
├─────────────────────────────────────────────────────┤
│ 进程 N+1: 向量数据库 (可选独立部署)                   │
│   • ChromaDB / Qdrant                                │
│   • 端口: 8000 (Chroma) / 6333 (Qdrant)             │
└─────────────────────────────────────────────────────┘
```

---

## 4. 通信协议

### 4.1 Go ↔ Python 通信

```
通信协议选择:

gRPC (Agent 控制):
  • 会话管理 (创建/切换/删除)
  • 模型路由决策
  • 权限校验请求
  • 错误上报
  • 流式控制信号

WebSocket (实时推送):
  • 前端 ↔ Go API
  • 流式输出推送
  • 步骤状态实时更新
  • Inspector 事件推送
```

### 4.2 MCP stdio 通信（仅 Layer 3）

```
Agent (MCP Client)          MCP Server (Skill 进程)
     │                            │
     │── tools/list ─────────────►│  发现可用工具
     │◄── [{name, description, schema}] │
     │                            │
     │── tools/call ─────────────►│  调用工具
     │   {name: "browser_navigate",│
     │    arguments: {url}}       │
     │◄── {content: "..."}       │  返回结果
     │                            │
     │── (stderr) ─────────────►│  错误信息
     │                            │
     │── 进程退出 ◄──────────────│  Skill 完成
```

---

## 5. 核心模块设计

### 5.1 四层工具架构（核心设计）

这是本系统的核心设计决策之一，决定了工具的组织和调用方式。

```
Layer 0: Runtime 内核（非 Tool，直接编译进 Python Agent Core）
  TaskManager │ ExecutionEngine │ Planner │ ContextManager
  MemorySystem │ EventBus │ ConfigManager │ Recovery
  ModelProvider │ SkillRegistry │ Observability
  
  原因: ExecutionEngine 不可能通过 MCP 调自己，会造成循环依赖。
  这些是 Agent 的基础设施，不是工具。

Layer 1: 高频原生 Tool（Python 直接实现，不走 MCP）
  file_read │ file_write │ file_edit │ glob │ grep
  bash │ todo_write │ sleep
  
  原因: 这些工具每分钟可能被调用几百次。
  MCP 方式的额外开销（10-50ms）在高频率下不可接受。
  例如：读文件 → grep → 读文件 → 编辑 → 保存
  如果全部走 MCP，累积浪费数秒。

Layer 2: 低频原生 Tool（Python 直接实现，不走 MCP）
  web_search │ web_fetch
  
  原因: 调用频率较低，但仍与本地环境耦合（需要 DuckDuckGo/HTTP 库）。
  做成原生避免了 MCP 进程管理的复杂性。

Layer 3: MCP Tool（SKILL.md 导入的 Skill，走 MCP 协议）
  browser │ ocr │ code_executor │ data_analysis │ ...
  
  原因: 这些是 Skill 化的工具，需要标准化接口。
  单次调用耗时秒级，MCP 开销占比很小。
  用户可通过 SKILL.md 自定义扩展。
```

### 5.2 统一 Tool 接口

所有工具（原生 + MCP）都实现统一接口：

```python
# python/agent/tools/base.py

class BaseTool(ABC):
    """所有工具的基类"""
    
    @abstractmethod
    def name(self) -> str:
        """工具名，snake_case 命名"""
        pass
    
    @abstractmethod
    def description(self) -> str:
        """详细英文描述，供 LLM 理解何时调用"""
        pass
    
    @abstractmethod
    def parameters_schema(self) -> dict:
        """JSON Schema 定义参数"""
        pass
    
    @abstractmethod
    async def execute(
        self,
        context: 'ExecutionContext',
        arguments: dict
    ) -> Union['ToolResult', 'ToolResultStream']:
        """
        执行工具
        
        返回:
          - ToolResult: 一次性返回完整结果（file_read 等）
          - ToolResultStream: 流式返回结果（bash 等）
        """
        pass


class ExecutionContext:
    """工具执行上下文（所有 Tool 共享）"""
    
    def __init__(
        self,
        deadline: datetime,
        cancellation_token: asyncio.Event = None,
        trace_id: str = "",
        task_id: str = "",
        step_id: str = "",
        metadata: dict = None
    ):
        self.deadline = deadline
        self.cancellation_token = cancellation_token or asyncio.Event()
        self.trace_id = trace_id
        self.task_id = task_id
        self.step_id = step_id
        self.metadata = metadata or {}
    
    def is_cancelled(self) -> bool:
        return self.cancellation_token.is_set()
    
    def is_timed_out(self) -> bool:
        return datetime.now() > self.deadline


class ToolResult:
    """工具返回结果（所有工具统一格式）"""
    
    def __init__(
        self,
        data: dict,
        summary: str,
        raw: str = None,
        metadata: dict = None
    ):
        self.data = data              # 业务数据（ExecutionEngine 消费）
        self.summary = summary         # 人类可读摘要（LLM 消费）
        self.raw = raw                 # 原始输出（需要时引用）
        self.metadata = metadata or {} # 元数据（耗时、token 等）


class ToolResultStream(AsyncIterator[str]):
    """流式返回结果的迭代器"""
    pass
```

### 5.3 消费分层

```
ToolResult 分层消费:

  ExecutionEngine  → 消费 data（结构化数据，用于后续处理）
  LLM              → 消费 summary（人类可读摘要，用于生成回答）
  用户/UI          → 消费 raw（原始输出，用于展示详情）

示例 (file_read):
  data: {"content": "import os...", "lines": 42}
  summary: "Read 42 lines from /path/to/file.py"
  raw: "import os..."
  metadata: {"duration_ms": 2, "bytes_read": 1024}
```

### 5.4 生命周期管理

```
ExecutionEngine 负责:
  • 创建 ExecutionContext（设置 deadline、trace_id）
  • 定期检查 cancellation_token
  • 取消时调用 context.cancellation_token.set() 通知所有持有该 context 的 Tool
  • 超时后取消执行
  • 异常捕获和重试决策

Tool 只负责:
  • 定期检查 context.is_cancelled()
  • 尽快退出被取消的执行
  • 不自己创建计时器
  • 不自己管理重试
```

### 5.5 工具权限控制

```python
# python/agent/tools/permission_manager.py

class PermissionLevel(IntEnum):
    L1 = 1  # 只读操作
    L2 = 2  # 只读 Shell
    L3 = 3  # Shell 命令
    L4 = 4  # 文件修改
    L5 = 5  # 危险操作

class PermissionMode(IntEnum):
    MANUAL = 1
    ACCEPT_EDITS = 2
    PLAN = 3
    AUTO = 4

# 权限矩阵
PERMISSION_MATRIX = {
    PermissionMode.MANUAL: {
        PermissionLevel.L1: "allow",
        PermissionLevel.L2: "allow",
        PermissionLevel.L3: "ask",
        PermissionLevel.L4: "ask",
        PermissionLevel.L5: "deny",
    },
    # ... 其他模式
}

# 工具权限映射
TOOL_PERMISSION_MAP = {
    "file_read": PermissionLevel.L1,
    "file_write": PermissionLevel.L4,
    "file_edit": PermissionLevel.L4,
    "bash": PermissionLevel.L3,
    "web_search": PermissionLevel.L3,
    "web_fetch": PermissionLevel.L3,
    "glob": PermissionLevel.L1,
    "grep": PermissionLevel.L1,
    "todo_write": PermissionLevel.L1,
    "sleep": PermissionLevel.L1,
}

class PermissionManager:
    """统一权限管理器（所有工具共用）"""
    
    def check(self, tool_name: str, level: PermissionLevel) -> str:
        """检查工具权限，返回 allow/ask/deny"""
        return PERMISSION_MATRIX[self.mode][level]
```

### 5.6 工具注册与发现

```python
# python/agent/tools/tool_registry.py

class ToolRegistry:
    """工具注册表（统一管理原生 Tool + MCP Tool）"""
    
    def __init__(self, permission_manager: PermissionManager):
        self._tools: Dict[str, BaseTool] = {}
        self._permission_mgr = permission_manager
    
    def register(self, tool: BaseTool):
        """注册原生 Tool"""
        self._tools[tool.name()] = tool
    
    def register_mcp_tools(self, mcp_tools: List[MCPTool]):
        """批量注册 MCP Tool（自动发现）"""
        for mcp_tool in mcp_tools:
            self._tools[mcp_tool.name()] = mcp_tool
    
    def get(self, name: str) -> BaseTool:
        """获取工具"""
        return self._tools.get(name)
    
    def list(self) -> List[Dict]:
        """列出所有工具（供 LLM 发现）"""
        return [
            {
                "name": t.name(),
                "description": t.description(),
                "parameters": t.parameters_schema()
            }
            for t in self._tools.values()
        ]
    
    def check_permission(self, tool_name: str) -> str:
        """检查工具权限"""
        level = TOOL_PERMISSION_MAP.get(tool_name, PermissionLevel.L1)
        return self._permission_mgr.check(tool_name, level)
```

### 5.7 MCP Tool 自动发现

```python
# python/agent/tools/mcp_wrapper.py

class MCPTool(BaseTool):
    """MCP 工具包装器（自动发现 MCP Server 的工具）"""
    
    def __init__(self, mcp_client, server_name: str, tool_info: dict):
        self._mcp_client = mcp_client
        self._server_name = server_name
        self._tool_name = tool_info["name"]
        self._description = tool_info["description"]
        self._schema = tool_info["inputSchema"]
    
    async def execute(self, context: ExecutionContext, arguments: dict) -> ToolResult:
        result = await self._mcp_client.call_tool(
            name=self._tool_name,
            arguments=arguments
        )
        return ToolResult(
            data={"raw": result},
            summary=result.content[0].text if result.content else "",
            raw=str(result)
        )


class MCPToolDiscovery:
    """MCP 工具自动发现"""
    
    async def discover(self, mcp_client, server_name: str) -> List[MCPTool]:
        """发现 MCP Server 的所有工具"""
        tools_response = await mcp_client.list_tools()
        tools = []
        for tool_info in tools_response.tools:
            tools.append(MCPTool(
                mcp_client=mcp_client,
                server_name=server_name,
                tool_info={
                    "name": tool_info.name,
                    "description": tool_info.description,
                    "inputSchema": tool_info.inputSchema
                }
            ))
        return tools
```

### 5.8 Phase 1 工具清单

| # | 工具名 | 类型 | 权限 | 说明 |
|---|--------|------|------|------|
| 1 | `file_read` | 原生 L1 | L1 | 读取文件内容 |
| 2 | `file_write` | 原生 L1 | L4 | 写入文件内容 |
| 3 | `file_edit` | 原生 L1 | L4 | 精确替换文件内容 |
| 4 | `bash` | 原生 L1 | L3 | 执行 Shell 命令（流式输出）|
| 5 | `web_search` | 原生 L2 | L3 | 网络搜索（DuckDuckGo）|
| 6 | `web_fetch` | 原生 L2 | L3 | 抓取 URL 内容转 Markdown |
| 7 | `glob` | 原生 L1 | L1 | 文件通配搜索 |
| 8 | `grep` | 原生 L1 | L1 | 文本搜索 |
| 9 | `todo_write` | 原生 L1 | L1 | Todo 列表管理（Phase 2 实现）|
| 10 | `sleep` | 原生 L1 | L1 | 延时等待（Phase 2 实现）|

---

## 6. 核心模块详细设计

### 6.0 横切关注点 (Cross-Cutting Services)

```python
# 配置管理
class IConfigManager:
    def get(self, key: str) -> Any: ...
    def set(self, key: str, value: Any): ...
    def get_section(self, name: str) -> dict: ...
    def reload(self): ...

# 事件总线
class IEventBus:
    def publish(self, event: Event): ...
    def subscribe(self, event_type: str, handler: Callable): ...

# 错误恢复
class IExecutionRecovery:
    def handle_failure(self, task_id: str, error: Exception) -> str:
        # 返回: "retry" | "fallback" | "rollback" | "skip"

# 可观测性
class IObservability:
    def log(self, event: str): ...
    def trace(self, task_id: str, data: dict): ...
    def metric(self, name: str, value: float): ...
```

Phase 1 实现：`IEventBus` → `InMemoryEventBus`，`IObservability` → `ConsoleObserver`。

### 6.1 任务管理 (ITaskManager)

```
ITaskManager 职责:
  • 创建任务 (create_task)
  • 调度任务 (schedule)
  • 取消任务 (cancel)
  • 重试任务 (retry)
  • 获取状态 (get_status)
  • 并发控制预留 (Phase 2+)

任务生命周期:
  CREATED → QUEUED → RUNNING → COMPLETED
                         ↓
                       FAILED → RETRY → RUNNING
                         ↓
                       TIMEOUT → TERMINATED
```

### 6.2 执行引擎 (ExecutionEngine)

```
ExecutionEngine 职责:
  • 执行单步操作
  • 调用 ToolRegistry 查找工具
  • 权限校验
  • 生命周期管理（超时、取消、追踪）
  • 返回执行结果

调用链:
  ITaskManager → ExecutionEngine → ToolRegistry → BaseTool.execute()
```

### 6.3 Skill 注册表 (ISkillRegistry)

```
ISkillRegistry 职责:
  • register(skill) - 注册 Skill
  • unregister(name) - 卸载 Skill
  • resolve(name) - 查找 Skill 实例
  • list() - 列出所有 Skill
  • get_version(name) - 获取版本
  • check_dependency(name) - 检查依赖

Phase 1 合并实现，Phase 3 拆分为:
  • SkillCatalog (有哪些 Skill)
  • DependencyResolver (能否一起运行)
```

### 6.4 记忆系统 (IMemorySystem)

```
IMemorySystem 包含:
  ├── IShortTermMemory - 当前对话完整上下文
  ├── IConversationMemory - 历史对话摘要
  └── IUserMemory - 用户偏好和事实性知识

与 IKnowledgeBase 的区别:
  • Memory = Agent 内部状态 (对话、偏好)
  • KnowledgeBase = Agent 外部知识 (文档、FAQ)
```

### 6.5 知识库 (IKnowledgeBase)

```
IKnowledgeBase 包含:
  ├── IDocumentStore - 文档存储 (PDF/MD/HTML)
  ├── IRetriever - 语义搜索 + 关键词搜索
  └── IVectorStore - 向量存储 (ChromaDB/Qdrant)

Embedding Provider 抽象:
  • IEmbeddingProvider (工厂模式)
    ├── BGEProvider (本地默认)
    ├── OpenAIProvider (云端可选)
    └── GTEProvider (扩展)

切换方式: config.yaml 配置 provider 名称
```

### 6.6 模型提供商 (ModelProviderFactory)

```
ModelRegistry (配置管理):
  • 默认模型配置（由用户在设置页面配置）
  • 备用模型配置
  • Embedding 模型配置
  ↓
ModelProviderFactory (实例创建):
  • create("chat") → IChatProvider
  • create("embedding") → IEmbeddingProvider
  • create("image") → IImageProvider

接口分离:
  • IChatProvider.chat(messages, tools, stream)
  • IEmbeddingProvider.embed(texts)
  • IImageProvider.generate_image(prompt)
```

### 6.7 存储层 (IStorage)

```
IStorage 接口:
  • put(key, value) - 写入
  • get(key) - 读取
  • delete(key) - 删除
  • list(prefix) - 列出

Phase 1 实现:
  • SQLiteStorage (元数据、配置、记忆)
  • FileStorage (对话原文、Skill 文件)

Phase 3 扩展:
  • CloudStorage (加密云同步)
```

### 6.8 单对话 SubAgent 编排

```
与 §3.12 工作流引擎的定位区分:
  • SubAgent = 单对话内的临时并行执行单元（按需创建，完成后销毁）
  • 工作流 = 长期可复用的 Skill（通过 SKILL.md 导入）

执行模型 - 流式聚合:
  主 Agent 拆解任务
      ↓
  并行创建 SubAgent（最多 N 个）
      ↓
  SubAgent 实时输出结果 → 主 Agent 逐步聚合
      ↓
  所有 SubAgent 完成后 → 主 Agent 综合生成最终回答

通信方式 - 共享上下文:
  ┌─────────────────────────────────────────────┐
  │ 主 Agent 上下文（只读）                       │
  │  SubAgent-A: 可读取全量，写入自己的结果键      │
  │  SubAgent-B: 可读取全量，写入自己的结果键      │
  │  规则: 单写锁、50KB 上限、5 分钟过期          │
  └─────────────────────────────────────────────┘

SubAgent 生命周期状态机:
  CREATED → RUNNING → STREAMING → COMPLETED → DESTROYED
                                  ↓
                                FAILED → RETRY → STREAMING

超时降级策略:
  • 默认: Retry + Degrade（Phase 1）
  • 超时阈值: 5 分钟/SubAgent
  • 降级: 返回部分结果 + 标记"未完成"

UI 呈现 - 折叠卡片:
  步骤面板: 显示每个 SubAgent 状态和进度
  结果区:   折叠为卡片，用户可展开查看详情

Phase 1 接口预留: ISubAgentManager
  • create_subagent(session_id, task, parent_context)
  • submit_result(subagent_id, result)
  • get_status(subagent_id)
  • destroy(subagent_id)
```

### 6.9 Agent Execution Inspector 监控页面

```
定位: 独立监控页面，实时展示 Agent 运行过程

页面布局:
  ┌───────────────────────────────────────────────────┐
  │  Inspector 监控页面                                │
  │                                                   │
  │  ┌─ 活动卡片 ─────────────────────────────────┐   │
  │  │ [活动] 帮我分析这个项目                      │   │
  │  │ 运行中 · 2分35秒 · 正在执行: 搜索知识        │   │
  │  │ Token: 1,234 · 调用: 3次                    │   │
  │  │ [暂停] [停止] [工具详情]                     │   │
  │  │ ┌─ 展开的时间线（可自定义维度）────────────┐ │   │
  │  │ │ 任务分解 · 工具链路 · 模型信息           │ │   │
  │  │ │ 事件流 · 异常处理 · SubAgent             │ │   │
  │  │ └─────────────────────────────────────────┘ │   │
  │  └─────────────────────────────────────────────┘   │
  │                                                   │
  │  ┌─ 完成卡片 ─────────────────────────────────┐   │
  │  │ [完成] 帮我搜索最新 AI 新闻                  │   │
  │  │ 已完成 · 运行 15秒 · Token: 567              │   │
  │  └─────────────────────────────────────────────┘   │
  │                                                   │
  │  ┌─ 失败卡片 ─────────────────────────────────┐   │
  │  │ [失败] 帮我部署网站                         │   │
  │  │ 失败 · Docker 构建超时 · Retry: 2次         │   │
  │  └─────────────────────────────────────────────┘   │
  └───────────────────────────────────────────────────┘

数据流:
  EventBus (Python Agent Core)
      │  publish(task.started / tool.called / llm.token ...)
      ▼
  WebSocket Server (Go API Gateway)
      │  实时推送事件
      ▼
  Inspector 前端组件 (Vue 3)
      │  渲染时间线
      ▼
  Timeline Renderer (可自定义显示维度)

交互能力:
  • 停止任务 — 立即终止对话执行
  • 暂停/恢复 — 暂停当前执行，稍后恢复
  • 查看工具详情 — 弹出工具调用参数和返回值
  • 查看模型详情 — 弹出模型名称、Token 消耗、响应时间
  • 自定义维度 — 勾选/取消时间线中显示的维度
  • 保存设置 — 维度偏好保存到本地配置

断线重连:
  • 默认: WebSocket 实时推送
  • 断线后: 自动切换 HTTP 轮询（每 3 秒）
  • 重连后: 恢复 WebSocket 推送

记录保存（可选）:
  • 用户可在设置中选择是否保存 Inspector 记录
  • 保存后: 对话结束后 Inspector 数据持久化到 SQLite
  • 查看: 可在 Inspector 页面回放历史对话的执行过程
```

---

## 7. 安全架构

### 7.1 安全过滤架构

```
输入 → 长度截断(Gatekeeper) → 正则模式匹配 → 向量语义拦截(可选) → 放行

第一层：长度截断 (Gatekeeper)
  • 单条输入 > 4096 tokens:
    1. 先截断到 4096 tokens
    2. 再做正则检测
    3. 记录截断日志

第二层：正则模式匹配
  • block 级 → 直接拦截
  • warn 级 → 仅记录日志

第三层：向量语义拦截（可选）
  • 相似度 > 0.95 → 直接拦截
  • 0.85 ≤ 相似度 ≤ 0.95 → 正则二次检测
  • 相似度 < 0.85 → 放行

白名单机制（降级因子）:
  • 命中白名单关键词 + block 级规则 → 降级为 warn
  • 不跳过任何安全层
```

### 7.2 权限分级

| 级别 | 操作类型 | 示例 | 默认行为 |
|------|---------|------|---------|
| **L1** | 只读操作 | Read, Grep, Glob | 直接执行 |
| **L2** | 只读 Shell | ls, pwd, git status | 直接执行 |
| **L3** | Shell 命令 | npm run, python | 弹窗确认 |
| **L4** | 文件修改 | Edit, Write | 弹窗确认 |
| **L5** | 危险操作 | rm -rf, curl | 严格确认 + 熔断器 |

### 7.3 凭证管理

```
API Key 生命周期:
  1. 用户配置 → 粘贴 API Key → 验证
  2. 验证通过 → 存入操作系统密钥链 (Keychain/DPAPI)
  3. MCP Server 启动 → Go 后端从密钥链读取 → 注入 env
  4. MCP Server 通过 env 获取 Key，不经过网络传输

重要设计原则:
  • 所有模型配置、API Key 均由用户在设置页面自行配置
  • 配置文件（config.yaml / config.dev.yaml）不写死任何具体模型或 Key
  • 配置文件只保留结构定义，值为 null 或空字符串
```

---

## 8. 配置管理

### 8.1 配置加载流程

```
配置加载顺序（优先级从低到高）:
  1. config.yaml（主配置模板，只定义结构）
  2. config.{env}.yaml（环境覆盖，如 config.dev.yaml）
  3. 环境变量（最高优先级）
  4. 用户设置页面配置（运行时动态覆盖）
```

### 8.2 配置结构

```yaml
# config.yaml（主配置模板）
app:
  name: "NanamiGopher"
  version: "1.0.0"

models:
  prefer_local: true
  local_fallback_order: [ollama, lm_studio, vllm]
  # 注意: 不写死具体模型名，由用户在设置页面配置

permissions:
  default_mode: "manual"

memory:
  storage:
    sqlite_path: "~/.nanamigopher/data/memories.db"
    vector_db: "chromadb"

credentials:
  storage: "os_keychain"

skills:
  scan_directories:
    - "~/.nanamigopher/skills/"

observability:
  tracing:
    enabled: false
    provider: "console"
```

---

## 9. 开发路线图

### 9.1 四阶段规划

| 阶段 | 周期 | 目标 | 交付物 |
|------|------|------|--------|
| **Phase 1** | 2 周 | Agent Framework MVP | 平台能力 + 2 个 Example |
| **Phase 2** | 4 周 | 核心体验完善 | 可用日常助手 |
| **Phase 3** | 6 周 | 高级编排能力 | 工业级工作流引擎 |
| **Phase 4** | 4 周 | 生产就绪 | 安全/性能/Skill Market |

### 9.2 LangGraph 重新定位

```
普通对话:
  用户消息 → Go Gateway → Python Agent → Tool Call → LLM → 回答
  (不需要 LangGraph)

复杂工作流 (如 Boss 直聘):
  用户请求 → Go Gateway → Python Agent → LangGraph StateGraph → 多节点编排
  (需要 LangGraph)

定位:
  LangChain = LLM 适配层（所有 Agent 都用）
  LangGraph = 工作流引擎（仅复杂场景用）
```

---

## 10. 附录

### 10.1 术语表

| 术语 | 全称 | 说明 |
|------|------|------|
| MCP | Model Context Protocol | Anthropic 推出的工具标准协议 |
| RAG | Retrieval-Augmented Generation | 检索增强生成 |
| HITL | Human-in-the-Loop | 人机协同 |
| DSL | Domain Specific Language | 领域特定语言 |
| stdio | Standard I/O | 标准输入输出进程通信 |
| gRPC | Google Remote Procedure Call | 高性能 RPC 框架 |

### 10.2 参考资料

- [MCP Specification](https://modelcontextprotocol.io/)
- [LangChain Documentation](https://python.langchain.com/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [Coze Studio Architecture](https://github.com/coze-dev)

---

*本文档基于 PRD 设计，所有接口和模块均经过 grill-me 确认。*
