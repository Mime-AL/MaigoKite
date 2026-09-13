# MCP 集成规范

> NanamiGopher Agent 的 Model Context Protocol (MCP) 集成标准。

---

## 1. MCP 协议概述

### 1.1 什么是 MCP

Model Context Protocol (MCP) 是 NanamiGopher 与外部工具（Skills）通信的标准协议。其核心理念是：**每个 Skill 都是一个独立的 MCP Server**，通过标准化接口暴露工具能力，Agent 通过 MCP 协议自动发现和调用这些工具。

### 1.2 通信方式

MCP 采用 **stdio 通信**模式：

```
┌──────────────┐     stdio (JSON-RPC)      ┌──────────────┐
│  NanamiGopher │ ◄══════════════════════► │  MCP Server   │
│  (Client)     │    stdin / stdout         │  (Skill)      │
└──────────────┘                           └──────────────┘
```

- **stdin**：Client 发送 JSON-RPC 请求
- **stdout**：Server 返回 JSON-RPC 响应
- **stderr**：日志输出（不干扰通信）
- 协议版本：JSON-RPC 2.0

### 1.3 为什么选择 MCP

| 优势 | 说明 |
|------|------|
| 标准化 | 统一的工具发现、调用、错误处理接口 |
| 隔离性 | 每个 Skill 独立进程，崩溃不影响主系统 |
| 可扩展 | 新增 Skill 只需实现 MCP Server，无需修改内核 |
| 跨语言 | 支持 Python、Node.js、Go 等多种语言实现 |

---

## 2. MCP Server 生命周期

### 2.1 生命周期阶段

```
启动 ──► 初始化 ──► 连接 ──► 工具发现 ──► 就绪 ──► 调用 ──► 关闭
                                         │
                                         └── 空闲超时 ──► 自动关闭
```

### 2.2 启动阶段

```python
class MCPClient:
    def __init__(self, skill_name: str, config: MCPConfig):
        self.skill_name = skill_name
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.session_id: Optional[str] = None

    def start(self) -> None:
        """启动 MCP Server 进程。"""
        # 1. 构建启动命令
        cmd = self.config.command.split()
        env = {**os.environ, **self.config.env_vars}

        # 2. 创建子进程
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

        # 3. 发送 initialize 请求
        self._send_initialize()

        # 4. 发送 tools/list 请求
        self._discover_tools()
```

### 2.3 初始化握手

Client 启动后首先发送 JSON-RPC 初始化请求：

```json
// Client → Server
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "clientInfo": {
      "name": "nanamigopher",
      "version": "1.0.0"
    }
  }
}

// Server → Client
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "serverInfo": {
      "name": "file-manager",
      "version": "1.2.0"
    },
    "capabilities": {
      "tools": {
        "listChanged": false
      }
    }
  }
}
```

### 2.4 关闭阶段

```python
    def close(self) -> None:
        """优雅关闭 MCP Server。"""
        if self.process and self.process.poll() is None:
            # 发送 shutdown 请求
            self._send_request("shutdown", {})
            # 发送 exit 通知
            self._send_notification("exit", {})
            # 等待进程退出
            try:
                self.process.wait(timeout=self.config.shutdown_timeout)
            except subprocess.TimeoutExpired:
                # 超时后强制终止
                self.process.kill()
```

---

## 3. MCPToolWrapper 自动发现机制

### 3.1 工具发现流程

```
MCP Client 启动
  │
  ├─ 发送 tools/list 请求
  │
  ├─ 接收 Server 返回的工具列表
  │   [
  │     {
  │       "name": "read_file",
  │       "description": "Read a file from the filesystem...",
  │       "inputSchema": { ... }
  │     },
  │     ...
  │   ]
  │
  ├─ 为每个工具创建 MCPToolWrapper 实例
  │
  ├─ 注册到全局工具注册表
  │
  └─ Agent 可通过统一接口调用 MCP 工具
```

### 3.2 工具注册

```python
class MCPToolRegistry:
    """MCP 工具注册表。"""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def discover_and_register(self, mcp_client: MCPClient) -> None:
        """从 MCP Client 发现并注册所有工具。"""
        tools = mcp_client.list_tools()
        for tool_info in tools:
            wrapper = MCPToolWrapper(
                client=mcp_client,
                name=tool_info.name,
                description=tool_info.description,
                parameters=tool_info.input_schema,
            )
            self._tools[wrapper.name()] = wrapper

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """根据名称获取工具。"""
        return self._tools.get(name)
```

### 3.3 MCPToolWrapper

将 MCP 工具适配为统一的 BaseTool 接口：

```python
class MCPToolWrapper(BaseTool):
    """MCP 工具的统一包装器。"""

    def __init__(self, client: MCPClient, name: str,
                 description: str, parameters: dict):
        self._client = client
        self._name = name
        self._description = description
        self._parameters = parameters

    def name(self) -> str:
        return self._name

    def description(self) -> str:
        return self._description

    def parameters_schema(self) -> dict:
        return self._parameters

    def execute(self, args: dict) -> ToolResult:
        """通过 MCP Client 调用远程工具。"""
        result = self._client.call_tool(self._name, args)
        return ToolResult(
            data=result.content,
            summary=result.summary,
            raw=result.raw,
        )
```

---

## 4. SKILL.md 文件格式规范

### 4.1 SKILL.md 概述

每个 Skill 必须包含一个 `SKILL.md` 文件，位于 Skill 根目录。该文件定义 Skill 的元数据、权限要求和工具接口。

### 4.2 文件格式

```markdown
# Skill 名称

## 描述
简要描述该 Skill 的功能和用途。

## 名称
skill-file-manager

## 版本
1.0.0

## 权限
L2

## 参数
- path: string - 文件路径
- action: string - 操作类型（read/write/delete）

## 入口命令
node server.js

## 环境变量
API_KEY=${API_KEY}

## 依赖
- nodejs >= 18.0.0
- npm >= 9.0.0

## 超时
30s

## 描述（详细）
详细的 Skill 功能说明，包括支持的格式、边界情况等。
```

### 4.3 字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| `名称` | 是 | Skill 的唯一标识符，小写字母加连字符 |
| `版本` | 是 | 语义化版本号 |
| `权限` | 是 | L1-L5 权限等级 |
| `参数` | 是 | 输入参数列表，格式：`参数名: 类型 - 描述` |
| `入口命令` | 是 | 启动 MCP Server 的命令 |
| `环境变量` | 否 | 启动时需要注入的环境变量 |
| `依赖` | 否 | Skill 运行所需的外部依赖 |
| `超时` | 否 | 工具调用超时时间，默认 30s |
| `描述` | 是 | 简短描述（用于工具列表展示） |
| `描述（详细）` | 否 | 详细描述（用于工具详情展示） |

### 4.4 工具发现映射

SKILL.md 中的参数定义会自动映射为 MCP 的 `inputSchema`：

```markdown
## 参数
- path: string - 文件绝对路径
- content: string - 写入的内容
- encoding: string - 文件编码，默认 utf-8
```

映射为：

```json
{
  "type": "object",
  "properties": {
    "path": {
      "type": "string",
      "description": "文件绝对路径"
    },
    "content": {
      "type": "string",
      "description": "写入的内容"
    },
    "encoding": {
      "type": "string",
      "description": "文件编码，默认 utf-8",
      "default": "utf-8"
    }
  },
  "required": ["path", "content"]
}
```

---

## 5. MCP Server 配置

### 5.1 配置结构

```yaml
mcp_servers:
  file-manager:
    command: "node /opt/nanamigopher/skills/file-manager/server.js"
    env:
      NODE_ENV: "production"
    timeout: 30
    max_instances: 3
    retry_delay: 5
    health_check_interval: 60

  web-scraping:
    command: "python /opt/nanamigopher/skills/web-scraping/main.py"
    env:
      PROXY_URL: "${PROXY_URL}"
    timeout: 60
    max_instances: 2
    retry_delay: 10
    health_check_interval: 30

  code-analyzer:
    command: "uvx semgrep --config"
    timeout: 120
    max_instances: 1
    retry_delay: 3
    health_check_interval: 120
```

### 5.2 配置项说明

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `command` | string | - | 启动 MCP Server 的完整命令 |
| `env` | object | `{}` | 环境变量键值对 |
| `timeout` | integer | 30 | 工具调用超时秒数 |
| `max_instances` | integer | 1 | 最大并行实例数 |
| `retry_delay` | integer | 5 | 失败后重试延迟秒数 |
| `health_check_interval` | integer | 60 | 健康检查间隔秒数 |
| `shutdown_timeout` | integer | 10 | 优雅关闭等待时间 |

### 5.3 环境变量注入

环境变量支持引用：

```yaml
env:
  API_KEY: "${API_KEY}"       # 从进程环境继承
  DB_HOST: "db.internal"      # 静态值
  TIMEOUT: "${TIMEOUT:-30}"   # 带默认值的引用
```

---

## 6. 原生 Tool 与 MCP Tool 的统一接口

### 6.1 统一 BaseTool 接口

无论是原生 Tool 还是 MCP Tool，都实现相同的 BaseTool 接口：

```python
class BaseTool(ABC):
    """所有工具的基接口。"""

    @abstractmethod
    def name(self) -> str:
        """工具唯一名称。"""

    @abstractmethod
    def description(self) -> str:
        """工具功能描述（英文）。"""

    @abstractmethod
    def parameters_schema(self) -> dict:
        """工具参数的 JSON Schema。"""

    @abstractmethod
    def execute(self, args: dict) -> Union[ToolResult, ToolResultStream]:
        """执行工具调用。"""

    @abstractmethod
    def permission_level(self) -> PermissionLevel:
        """工具所需的最低权限等级。"""
```

### 6.2 工具注册表

```python
class ToolRegistry:
    """统一工具注册表，管理原生工具和 MCP 工具。"""

    def __init__(self):
        self._native_tools: Dict[str, BaseTool] = {}
        self._mcp_tools: Dict[str, BaseTool] = {}

    def register_native(self, tool: BaseTool) -> None:
        """注册原生工具。"""
        self._native_tools[tool.name()] = tool

    def register_mcp(self, tool: BaseTool) -> None:
        """注册 MCP 工具。"""
        self._mcp_tools[tool.name()] = tool

    def resolve(self, name: str) -> Optional[BaseTool]:
        """根据名称解析工具（先查原生，再查 MCP）。"""
        return self._native_tools.get(name) or self._mcp_tools.get(name)

    def list_all(self) -> List[BaseTool]:
        """列出所有可用工具。"""
        return list(self._native_tools.values()) + list(self._mcp_tools.values())
```

### 6.3 工具调用流程

```
Agent 决定调用工具
  │
  ├─ ToolRegistry.resolve(tool_name)
  │
  ├─ 检查 PermissionManager 权限
  │   ├─ 权限不足 → 拒绝调用
  │   └─ 权限足够 ↓
  │
  ├─ 检查沙箱策略
  │   ├─ 需要沙箱 → 在沙箱中执行
  │   └─ 不需要 ↓
  │
  ├─ 执行工具
  │   ├─ 原生工具 → 直接调用 execute()
  │   └─ MCP 工具 → 通过 MCP Client 调用
  │
  ├─ 收集 ToolResult
  │
  └─ 返回给 Agent
```

---

## 7. 错误处理和重试策略

### 7.1 错误分类

| 错误类型 | HTTP/协议码 | 处理策略 |
|----------|------------|----------|
| 连接失败 | ECONNREFUSED | 重试（指数退避） |
| 超时 | ETIMEDOUT | 切换到备用 Server 或返回错误 |
| 解析错误 | JSONDecodeError | 记录日志，返回原始输出 |
| 工具不存在 | 404 | 返回工具未找到错误 |
| 权限拒绝 | 403 | 返回权限不足错误 |
| 服务端错误 | 5xx | 重试后降级 |

### 7.2 重试策略

```python
class RetryPolicy:
    """重试策略配置。"""

    max_retries: int = 3
    initial_delay: float = 1.0    # 初始延迟（秒）
    max_delay: float = 30.0       # 最大延迟（秒）
    backoff_factor: float = 2.0   # 退避因子
    retryable_errors: set = {
        "connection_error",
        "timeout",
        "server_error",
        "rate_limit",
    }

    def get_delay(self, attempt: int) -> float:
        """计算第 n 次重试的延迟时间。"""
        delay = self.initial_delay * (self.backoff_factor ** attempt)
        return min(delay, self.max_delay)
```

### 7.3 重试流程

```
调用 MCP 工具
  │
  ├─ 成功 → 返回结果
  │
  ├─ 可重试错误 → 等待 delay → 重试
  │   ├─ 重试 1: delay = 1s
  │   ├─ 重试 2: delay = 2s
  │   └─ 重试 3: delay = 4s
  │
  └─ 重试耗尽 → 返回错误
      │
      ├─ 如果是 MCP 工具 → 尝试本地等价工具（如有）
      └─ 报告失败给 Agent
```

### 7.4 健康检查

MCP Client 定期检测 Server 健康状态：

```python
def health_check(self) -> HealthStatus:
    """检查 MCP Server 健康状态。"""
    if self.process is None:
        return HealthStatus.DEAD

    if self.process.poll() is not None:
        return HealthStatus.CRASHED

    try:
        result = self._send_request("ping", {}, timeout=5)
        return HealthStatus.HEALTHY
    except Exception:
        return HealthStatus.UNHEALTHY
```

---

## 附录：MCP 集成 Checklist

- [ ] MCP Server 是否通过 stdio 通信？
- [ ] 工具发现是否通过 tools/list 自动完成？
- [ ] SKILL.md 是否包含所有必需字段？
- [ ] MCPToolWrapper 是否正确适配 BaseTool 接口？
- [ ] 错误重试是否使用指数退避策略？
- [ ] 健康检查是否定期执行？
- [ ] 原生工具和 MCP 工具是否通过统一 ToolRegistry 管理？
- [ ] 环境变量是否正确注入到 MCP Server 进程？
