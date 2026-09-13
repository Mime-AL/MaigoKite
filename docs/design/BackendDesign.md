# NanamiGopher 后端设计文档

> **版本**: v1.1  
> **日期**: 2026-07-15  
> **技术栈**: Go 1.22+ (Gin) + Python 3.11+ (LangChain)

---

## 1. 项目结构

### 1.1 Go API Gateway 项目结构

```
nanamigopher/
├── cmd/
│   └── gateway/
│       └── main.go             # Go 服务入口
├── internal/
│   ├── api/                    # HTTP 路由和 Handler
│   │   ├── router.go           # 路由注册
│   │   ├── session_handler.go  # 会话管理
│   │   ├── message_handler.go  # 消息收发
│   │   ├── memory_handler.go   # 记忆管理
│   │   ├── skill_handler.go    # Skill 管理
│   │   ├── permission_handler.go # 权限管理
│   │   ├── credential_handler.go # 凭证管理
│   │   ├── inspector_handler.go  # Inspector 监控
│   │   └── approval_handler.go   # 审批管理
│   ├── grpc/                   # gRPC 服务
│   │   ├── server.go           # gRPC 服务器
│   │   ├── agent_client.go     # Python Agent 客户端
│   │   └── pb/                 # Protobuf 定义
│   │       └── agent.proto
│   ├── websocket/              # WebSocket 推送
│   │   ├── hub.go              # 连接管理
│   │   ├── broadcaster.go      # 消息广播
│   │   └── inspector_ws.go     # Inspector 专用 WS
│   ├── mcp/                    # MCP Server 管理
│   │   ├── manager.go          # 管理器
│   │   ├── server.go           # MCP Server 封装
│   │   └── health_checker.go   # 健康检查
│   ├── credentialstore/        # 跨平台密钥链
│   │   ├── store.go            # 接口定义
│   │   ├── keychain_darwin.go  # macOS
│   │   ├── dpapi_windows.go    # Windows
│   │   └── libsecret_linux.go  # Linux
│   ├── security/               # 安全过滤
│   │   ├── gatekeeper.go       # 长度截断
│   │   ├── regex_filter.go     # 正则检测
│   │   ├── whitelist.go        # 白名单
│   │   ├── vector_filter.go    # 向量拦截（可选）
│   │   └── audit_logger.go     # 审计日志
│   ├── observability/          # 可观测性
│   │   ├── console_observer.go # Phase 1: 控制台输出
│   │   ├── tracer.go           # 链路追踪
│   │   └── metrics.go          # 指标收集
│   └── config/                 # 配置管理
│       ├── loader.go           # 配置加载
│       └── manager.go          # 配置管理
├── pkg/                        # 公共包
│   ├── logger/                 # 日志
│   ├── errors/                 # 错误定义
│   └── utils/                  # 工具函数
├── proto/                      # Protobuf 定义
│   └── agent.proto
├── config/
│   └── config.yaml             # 配置文件
├── go.mod
└── go.sum
```

### 1.2 Python Agent Core 项目结构

```
agent-core/
├── main.py                     # Python 服务入口
├── agent/
│   ├── runtime/                # Agent 运行时
│   │   ├── engine.py           # ExecutionEngine
│   │   ├── task_manager.py     # ITaskManager 实现
│   │   ├── context_manager.py  # IContextManager 实现
│   │   └── recovery.py         # IExecutionRecovery 实现
│   ├── memory/                 # 记忆系统
│   │   ├── system.py           # IMemorySystem 实现
│   │   ├── short_term.py       # IShortTermMemory
│   │   ├── conversation.py     # IConversationMemory
│   │   ├── user_memory.py      # IUserMemory
│   │   └── extraction.py       # 智能摘要提取
│   ├── knowledge/              # 知识库
│   │   ├── base.py             # IKnowledgeBase 实现
│   │   ├── document_store.py   # IDocumentStore
│   │   ├── retriever.py        # IRetriever
│   │   └── vector_store.py     # IVectorStore
│   ├── embedding/              # Embedding 抽象
│   │   ├── provider.py         # IEmbeddingProvider 接口
│   │   ├── bge_provider.py     # BGEProvider
│   │   ├── openai_provider.py  # OpenAIProvider
│   │   └── factory.py          # EmbeddingFactory
│   ├── models/                 # 模型抽象
│   │   ├── chat_provider.py    # IChatProvider 接口
│   │   ├── image_provider.py   # IImageProvider 接口
│   │   ├── registry.py         # ModelRegistry
│   │   └── router.py           # 模型路由
│   ├── skills/                 # Skill 管理
│   │   ├── registry.py         # ISkillRegistry 实现
│   │   ├── loader.py           # Skill 加载器
│   │   └── namespace.py        # 命名空间管理
│   ├── mcp/                    # MCP 客户端
│   │   ├── client.py           # MCP Client 封装
│   │   ├── tool_caller.py      # 工具调用
│   │   └── discovery.py        # 工具发现
│   ├── workflow/               # 工作流引擎（Phase 3）
│   │   ├── dsl_parser.py       # DSL 解析
│   │   ├── graph_builder.py    # LangGraph 图构建
│   │   ├── checkpoint.py       # Checkpoint 管理
│   │   └── stealth.py          # Stealth Runtime
│   ├── security/               # Agent 端安全
│   │   ├── sanitizer.py        # 输入清洗
│   │   └── prompt_guard.py     # Prompt 注入防护
│   └── observability/          # 可观测性
│       ├── observer.py         # IObservability 接口
│       ├── console.py          # ConsoleObserver
│       └── otel_exporter.py    # OpenTelemetry 导出
├── tools/                      # MCP Server 实现
│   ├── file_reader/
│   │   └── server.py
│   ├── code_executor/
│   │   └── server.py
│   ├── web_search/
│   │   └── server.py
│   └── browser/                # Playwright（Phase 2）
│       └── server.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── golden_dataset/
├── requirements.txt
└── pyproject.toml
```

---

## 2. Go API Gateway 详细设计

### 2.1 入口与启动流程

```go
// cmd/gateway/main.go
package main

import (
    "context"
    "log"
    "os"
    "os/signal"
    "syscall"
    
    "nanamigopher/internal/api"
    "nanamigopher/internal/config"
    "nanamigopher/internal/grpc"
    "nanamigopher/internal/mcp"
    "nanamigopher/internal/observability"
    "nanamigopher/internal/websocket"
)

func main() {
    // 1. 加载配置
    cfg, err := config.Load("config.yaml")
    if err != nil {
        log.Fatalf("Failed to load config: %v", err)
    }
    
    // 2. 初始化可观测性
    obs := observability.NewConsoleObserver(cfg.Observability)
    obs.Log("INFO", "Starting NanamiGopher Gateway")
    
    // 3. 启动 Python Agent Core（子进程）
    agentProc, err := startAgentCore(cfg)
    if err != nil {
        log.Fatalf("Failed to start agent core: %v", err)
    }
    defer agentProc.Kill()
    
    // 4. 初始化 gRPC 客户端
    grpcClient := grpc.NewAgentClient(agentProc, cfg.GRPC)
    
    // 5. 初始化 MCP Server 管理器
    mcpMgr := mcp.NewManager(cfg.MCP, grpcClient)
    
    // 6. 初始化 WebSocket Hub
    wsHub := websocket.NewHub()
    
    // 7. 启动 HTTP 服务器
    router := api.NewRouter(cfg, grpcClient, wsHub, mcpMgr)
    server := &http.Server{
        Addr:    fmt.Sprintf(":%d", cfg.HTTP.Port),
        Handler: router,
    }
    
    // 8. 优雅关闭
    go func() {
        sigCh := make(chan os.Signal, 1)
        signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
        <-sigCh
        obs.Log("INFO", "Shutting down...")
        ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
        defer cancel()
        server.Shutdown(ctx)
    }()
    
    if err := server.ListenAndServe(); err != nil {
        log.Fatal(err)
    }
}
```

### 2.2 路由与 Handler

```go
// internal/api/router.go
package api

import (
    "github.com/gin-gonic/gin"
    "nanamigopher/internal/config"
    "nanamigopher/internal/grpc"
    "nanamigopher/internal/mcp"
    "nanamigopher/internal/websocket"
)

type Router struct {
    engine     *gin.Engine
    cfg        *config.Config
    grpcClient *grpc.AgentClient
    wsHub      *websocket.Hub
    mcpMgr     *mcp.Manager
}

func NewRouter(cfg *config.Config, grpcClient *grpc.AgentClient, wsHub *websocket.Hub, mcpMgr *mcp.Manager) *gin.Engine {
    r := &Router{
        engine:     gin.Default(),
        cfg:        cfg,
        grpcClient: grpcClient,
        wsHub:      wsHub,
        mcpMgr:     mcpMgr,
    }
    r.registerRoutes()
    return r.engine
}

func (r *Router) registerRoutes() {
    v1 := r.engine.Group("/api/v1")
    
    // 会话管理
    sessions := v1.Group("/sessions")
    {
        sessions.POST("", r.sessionHandler.Create)
        sessions.GET("", r.sessionHandler.List)
        sessions.GET("/:id", r.sessionHandler.Get)
        sessions.DELETE("/:id", r.sessionHandler.Delete)
        sessions.POST("/:id/switch", r.sessionHandler.Switch)
        sessions.POST("/:id/messages", r.sessionHandler.SendMessage)
        sessions.GET("/:id/stream", r.wsHub.HandleStream)  // WebSocket
    }
    
    // 记忆管理
    memories := v1.Group("/memories")
    {
        memories.GET("", r.memoryHandler.List)
        memories.POST("/search", r.memoryHandler.Search)
        memories.PUT("/:id", r.memoryHandler.Update)
        memories.DELETE("/batch", r.memoryHandler.BatchDelete)
    }
    
    // Skill 管理
    skills := v1.Group("/skills")
    {
        skills.GET("", r.skillHandler.List)
        skills.POST("/import", r.skillHandler.Import)
        skills.DELETE("/:id", r.skillHandler.Uninstall)
        skills.GET("/:id/deps", r.skillHandler.Dependencies)
    }
    
    // 权限管理
    perms := v1.Group("/permissions")
    {
        perms.GET("", r.permissionHandler.Get)
        perms.PUT("", r.permissionHandler.Update)
        perms.POST("/mode", r.permissionHandler.SwitchMode)
    }
    
    // 凭证管理（通用 CRUD，type 区分 model / search / custom）
    creds := v1.Group("/credentials")
    {
        creds.POST("", r.credentialHandler.Create)
        creds.GET("", r.credentialHandler.List)      // ?type=model|search|custom
        creds.GET("/:id", r.credentialHandler.Get)
        creds.PUT("/:id", r.credentialHandler.Update)
        creds.DELETE("/:id", r.credentialHandler.Delete)
    }
    
    // 模型管理
    models := v1.Group("/models")
    {
        models.GET("", r.modelHandler.List)
        models.POST("/route", r.modelHandler.Route)
    }
    
    // Inspector 监控
    inspector := v1.Group("/inspector")
    {
        inspector.GET("/cards", r.inspectorHandler.Cards)
        inspector.GET("/sessions/:id/timeline", r.inspectorHandler.Timeline)
        inspector.POST("/sessions/:id/stop", r.inspectorHandler.Stop)
        inspector.POST("/sessions/:id/pause", r.inspectorHandler.Pause)
        inspector.GET("/sessions/:id/settings", r.inspectorHandler.Settings)
        inspector.PUT("/sessions/:id/settings", r.inspectorHandler.UpdateSettings)
        inspector.WS("/sessions/:id/ws", r.inspectorHandler.HandleWS)
    }
    
    // 审批管理
    approvals := v1.Group("/approvals")
    {
        approvals.POST("", r.approvalHandler.Create)
        approvals.GET("/:id", r.approvalHandler.Get)
        approvals.PUT("/:id/decision", r.approvalHandler.Decide)
        approvals.GET("/history", r.approvalHandler.History)
    }
    
    // 接管管理
    takeovers := v1.Group("/takeovers")
    {
        takeovers.POST("/raise", r.takeoverHandler.Raise)
        takeovers.POST("/:id/accept", r.takeoverHandler.Accept)
        takeovers.POST("/:id/release", r.takeoverHandler.Release)
    }
    
    // 可观测性
    observability := v1.Group("/observability")
    {
        observability.GET("/traces/:trace_id", r.obsHandler.GetTrace)
        observability.GET("/traces/:trace_id/spans", r.obsHandler.GetSpans)
        observability.POST("/benchmarks/run", r.obsHandler.RunBenchmark)
        observability.GET("/benchmarks/results", r.obsHandler.BenchmarkResults)
        observability.GET("/metrics", r.obsHandler.Metrics)
    }
}
```

### 2.3 会话管理 Handler

```go
// internal/api/session_handler.go
package api

import (
    "net/http"
    "github.com/gin-gonic/gin"
    "nanamigopher/internal/grpc"
    "nanamigopher/internal/websocket"
)

type SessionHandler struct {
    grpcClient *grpc.AgentClient
    wsHub      *websocket.Hub
}

// Create 创建新会话
func (h *SessionHandler) Create(c *gin.Context) {
    var req grpc.CreateSessionRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
        return
    }
    
    resp, err := h.grpcClient.CreateSession(c.Request.Context(), &req)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }
    
    c.JSON(http.StatusOK, resp)
}

// List 列出所有会话
func (h *SessionHandler) List(c *gin.Context) {
    resp, err := h.grpcClient.ListSessions(c.Request.Context(), &grpc.Empty{})
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }
    
    c.JSON(http.StatusOK, resp)
}

// SendMessage 发送消息
func (h *SessionHandler) SendMessage(c *gin.Context) {
    sessionId := c.Param("id")
    
    var req grpc.MessageRequest
    if err := c.ShouldBindJSON(&req); err != nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
        return
    }
    
    // 调用 Python Agent
    stream, err := h.grpcClient.ProcessMessage(c.Request.Context(), &req)
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }
    
    // 转发流式响应到 WebSocket
    h.wsHub.Broadcast(sessionId, stream)
    
    c.JSON(http.StatusOK, gin.H{"status": "streaming"})
}

// Delete 删除会话
func (h *SessionHandler) Delete(c *gin.Context) {
    sessionId := c.Param("id")
    
    _, err := h.grpcClient.DeleteSession(c.Request.Context(), &grpc.SessionRequest{
        SessionId: sessionId,
    })
    if err != nil {
        c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
        return
    }
    
    c.JSON(http.StatusOK, gin.H{"status": "deleted"})
}
```

### 2.4 WebSocket Hub

```go
// internal/websocket/hub.go
package websocket

import (
    "encoding/json"
    "sync"
    "github.com/gorilla/websocket"
)

// Hub 管理所有 WebSocket 连接
type Hub struct {
    // sessionId -> 连接集合
    clients    map[string]map[*Client]bool
    register   chan *Client
    unregister chan *Client
    broadcast  chan *BroadcastMessage
    mu         sync.RWMutex
}

type Client struct {
    conn *websocket.Conn
    send chan []byte
}

type BroadcastMessage struct {
    SessionID string
    Event     StreamEvent
}

type StreamEvent struct {
    Type    string          `json:"type"`    // step_start, step_complete, message_chunk, error
    Data    json.RawMessage `json:"data"`    // 事件数据
    Timestamp int64         `json:"timestamp"`
}

func NewHub() *Hub {
    return &Hub{
        clients:    make(map[string]map[*Client]bool),
        register:   make(chan *Client),
        unregister: make(chan *Client),
        broadcast:  make(chan *BroadcastMessage),
    }
}

func (h *Hub) Run() {
    for {
        select {
        case client := <-h.register:
            h.registerClient(client)
        case client := <-h.unregister:
            h.unregisterClient(client)
        case msg := <-h.broadcast:
            h.broadcastMessage(msg)
        }
    }
}

func (h *Hub) registerClient(client *Client) {
    h.mu.Lock()
    defer h.mu.Unlock()
    
    if h.clients[client.SessionID] == nil {
        h.clients[client.SessionID] = make(map[*Client]bool)
    }
    h.clients[client.SessionID][client] = true
}

func (h *Hub) unregisterClient(client *Client) {
    h.mu.Lock()
    defer h.mu.Unlock()
    
    if clients, ok := h.clients[client.SessionID]; ok {
        delete(clients, client)
        if len(clients) == 0 {
            delete(h.clients, client.SessionID)
        }
    }
    close(client.send)
}

func (h *Hub) broadcastMessage(msg *BroadcastMessage) {
    h.mu.RLock()
    defer h.mu.RUnlock()
    
    if clients, ok := h.clients[msg.SessionID]; ok {
        data, _ := json.Marshal(msg.Event)
        for client := range clients {
            select {
            case client.send <- data:
            default:
                close(client.send)
                delete(clients, client)
            }
        }
    }
}
```

### 2.5 MCP Server 管理器

```go
// internal/mcp/manager.go
package mcp

import (
    "context"
    "fmt"
    "os/exec"
    "sync"
    "nanamigopher/pkg/credentialstore"
)

// MCPServer 代表一个 MCP Server 进程
type MCPServer struct {
    name       string
    command    string
    args       []string
    env        []string
    cmd        *exec.Cmd
    stdin      *io.WriteCloser
    stdout     *io.ReadCloser
    stderr     *io.ReadCloser
    healthURL  string
    isRunning  bool
    mu         sync.Mutex
}

// Manager 管理所有 MCP Server 的生命周期
type Manager struct {
    creds credentialstore.CredentialStore
    servers map[string]*MCPServer
    config *MCPConfig
    mu     sync.RWMutex
}

func NewManager(cfg *MCPConfig, creds credentialstore.CredentialStore) *Manager {
    return &Manager{
        creds:   creds,
        servers: make(map[string]*MCPServer),
        config:  cfg,
    }
}

// StartServer 启动 MCP Server 进程
func (m *Manager) StartServer(engine string) error {
    m.mu.Lock()
    defer m.mu.Unlock()
    
    engineCfg, ok := m.config.Engines[engine]
    if !ok {
        return fmt.Errorf("engine %s not configured", engine)
    }
    
    // 1. 从密钥链读取 API Key（如果需要）
    var env []string
    if engineCfg.EnvKeyName != "" {
        apiKey, err := m.creds.Get("search", engine)
        if err != nil {
            return fmt.Errorf("API Key not configured for %s: %w", engine, err)
        }
        env = append(env, fmt.Sprintf("%s=%s", engineCfg.EnvKeyName, apiKey))
    }
    
    // 2. 启动进程
    cmd := exec.Command(engineCfg.Command, engineCfg.Args...)
    cmd.Env = append(os.Environ(), env...)
    
    stdin, err := cmd.StdinPipe()
    if err != nil {
        return err
    }
    stdout, err := cmd.StdoutPipe()
    if err != nil {
        return err
    }
    stderr, err := cmd.StderrPipe()
    if err != nil {
        return err
    }
    
    if err := cmd.Start(); err != nil {
        return err
    }
    
    server := &MCPServer{
        name:    engine,
        command: engineCfg.Command,
        args:    engineCfg.Args,
        env:     env,
        cmd:     cmd,
        stdin:   &stdin,
        stdout:  &stdout,
        stderr:  &stderr,
        isRunning: true,
    }
    
    m.servers[engine] = server
    return nil
}

// StopServer 停止 MCP Server 进程
func (m *Manager) StopServer(engine string) {
    m.mu.Lock()
    defer m.mu.Unlock()
    
    if server, ok := m.servers[engine]; ok {
        server.mu.Lock()
        defer server.mu.Unlock()
        
        if server.isRunning {
            server.cmd.Process.Kill()
            server.isRunning = false
        }
        delete(m.servers, engine)
    }
}

// RestartServer 重启 MCP Server（用于 API Key 更新）
func (m *Manager) RestartServer(engine string) error {
    m.StopServer(engine)
    return m.StartServer(engine)
}

// IsHealthy 检查 MCP Server 健康状态
func (m *Manager) IsHealthy(engine string) bool {
    m.mu.RLock()
    defer m.mu.RUnlock()
    
    server, ok := m.servers[engine]
    if !ok {
        return false
    }
    
    // 检查进程是否存活
    if server.cmd.ProcessState != nil && server.cmd.ProcessState.Exited() {
        return false
    }
    
    // 如果有健康检查端点，发起 HTTP 请求
    if server.healthURL != "" {
        resp, err := http.Get(server.healthURL)
        if err != nil {
            return false
        }
        defer resp.Body.Close()
        return resp.StatusCode == http.StatusOK
    }
    
    return true
}
```

### 2.6 凭证管理

```go
// internal/credentialstore/store.go
package credentialstore

// CredentialStore 跨平台密钥链接口
type CredentialStore interface {
    // Save 存储凭证
    Save(service, username, secret string) error
    
    // Get 读取凭证
    Get(service, username string) (string, error)
    
    // Delete 删除凭证
    Delete(service, username string) error
    
    // List 列出某服务的所有凭证
    List(service string) ([]string, error)
}

// Manager 凭证管理器
type Manager struct {
    store CredentialStore
}

func NewManager(store CredentialStore) *Manager {
    return &Manager{store: store}
}

// SaveSearchKey 保存搜索引擎 API Key
func (m *Manager) SaveSearchKey(engine, apiKey string) error {
    return m.store.Save("search", engine, apiKey)
}

// GetSearchKey 读取搜索引擎 API Key
func (m *Manager) GetSearchKey(engine string) (string, error) {
    return m.store.Get("search", engine)
}

// ValidateAndSave 验证并保存 API Key
func (m *Manager) ValidateAndSave(engine, apiKey string) error {
    // 1. 验证 Key 有效性
    if err := m.validateAPIKey(engine, apiKey); err != nil {
        return fmt.Errorf("invalid API key: %w", err)
    }
    
    // 2. 保存到密钥链
    return m.store.Save("search", engine, apiKey)
}

func (m *Manager) validateAPIKey(engine, apiKey string) error {
    // 根据不同引擎调用对应的验证 API
    switch engine {
    case "tavily":
        return validateTavily(apiKey)
    case "google":
        return validateGoogle(apiKey)
    default:
        return fmt.Errorf("unknown engine: %s", engine)
    }
}
```

---

## 3. Python Agent Core 详细设计

### 3.1 入口与启动流程

```python
# main.py
import asyncio
import logging
from agent.runtime.engine import ExecutionEngine
from agent.runtime.task_manager import TaskManager
from agent.memory.system import MemorySystem
from agent.knowledge.base import KnowledgeBase
from agent.skills.registry import SkillRegistry
from agent.models.router import ModelRouter
from agent.mcp.client import MCPClient
from agent.security.sanitizer import InputSanitizer
from agent.observability.observer import IObservability

logger = logging.getLogger(__name__)

class AgentCore:
    """Agent 核心运行时"""
    
    def __init__(self, config: dict, observability: IObservability):
        self.config = config
        self.obs = observability
        
        # 初始化各模块
        self.memory_system = MemorySystem(config)
        self.knowledge_base = KnowledgeBase(config)
        self.skill_registry = SkillRegistry(config)
        self.model_router = ModelRouter(config)
        self.mcp_client = MCPClient(config)
        self.execution_engine = ExecutionEngine(
            config=config,
            memory_system=self.memory_system,
            knowledge_base=self.knowledge_base,
            skill_registry=self.skill_registry,
            model_router=self.model_router,
            mcp_client=self.mcp_client,
            observability=self.obs,
        )
        # TaskManager 依赖 ExecutionEngine，必须在 engine 构造之后注入
        self.task_manager = TaskManager(config, engine=self.execution_engine)
        self.sanitizer = InputSanitizer(config.security)
    
    async def process_message(self, session_id: str, message: str) -> AsyncIterator[str]:
        """处理用户消息，流式返回结果"""
        # 1. 安全过滤
        sanitized = self.sanitizer.filter(message)
        
        # 2. 创建任务
        task = self.task_manager.create_task(
            session_id=session_id,
            user_message=sanitized,
        )
        
        # 3. 执行任务
        async for chunk in self.execution_engine.execute(task):
            yield chunk
        
        # 4. 任务完成，提取记忆
        self.memory_system.extract_after_completion(task)

async def main():
    config = load_config("config.yaml")
    obs = ConsoleObserver(config.observability)
    agent = AgentCore(config, obs)
    
    # 启动 gRPC 服务
    await agent.run_grpc_server(port=8081)

if __name__ == "__main__":
    asyncio.run(main())
```

### 3.2 TaskManager 实现

```python
# agent/runtime/task_manager.py
from enum import Enum
from typing import Optional
import uuid
import time

class TaskStatus(Enum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Task:
    """任务对象"""
    
    def __init__(self, task_id: str, session_id: str, user_message: str):
        self.task_id = task_id
        self.session_id = session_id
        self.user_message = user_message
        self.status = TaskStatus.CREATED
        self.created_at = time.time()
        self.started_at: Optional[float] = None
        self.completed_at: Optional[float] = None
        self.steps: list[dict] = []
        self.error: Optional[str] = None
        self.metadata: dict = {}

class TaskManager:
    """任务管理器 - 负责创建、调度、状态保存、重试和取消"""
    
    def __init__(self, config: dict, engine: "ExecutionEngine"):
        self.config = config
        self.engine = engine
        self.tasks: dict[str, Task] = {}
        self.queue: asyncio.Queue = asyncio.Queue()
        self.max_concurrent = config.get("max_concurrent_tasks", 5)
        self.current_count = 0
        self.lock = asyncio.Lock()
    
    def create_task(self, session_id: str, user_message: str) -> Task:
        """创建新任务"""
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        task = Task(task_id, session_id, user_message)
        self.tasks[task_id] = task
        return task
    
    async def schedule(self, task: Task) -> bool:
        """调度任务执行"""
        async with self.lock:
            if self.current_count >= self.max_concurrent:
                return False  # 达到并发上限
            
            self.current_count += 1
            task.status = TaskStatus.QUEUED
            await self.queue.put(task)
            return True
    
    async def run_loop(self):
        """任务调度循环"""
        while True:
            task = await self.queue.get()
            task.status = TaskStatus.RUNNING
            task.started_at = time.time()
            
            try:
                # 执行任务（复用 AgentCore 注入的 ExecutionEngine 单例）
                await self.engine.execute(task)
                task.status = TaskStatus.COMPLETED
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
            finally:
                task.completed_at = time.time()
                async with self.lock:
                    self.current_count -= 1
                self.queue.task_done()
    
    async def cancel(self, task_id: str) -> bool:
        """取消任务"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        if task.status in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
            return False
        
        task.status = TaskStatus.CANCELLED
        # 通知 ExecutionEngine 停止执行
        return True
    
    async def retry(self, task_id: str) -> Optional[Task]:
        """重试失败的任务"""
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        if task.status != TaskStatus.FAILED:
            return None
        
        # 创建新任务，复用原始消息
        new_task = self.create_task(task.session_id, task.user_message)
        await self.schedule(new_task)
        return new_task
    
    def get_status(self, task_id: str) -> Optional[dict]:
        """获取任务状态"""
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        return {
            "task_id": task.task_id,
            "session_id": task.session_id,
            "status": task.status.value,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "error": task.error,
            "steps": task.steps,
        }
```

### 3.3 ExecutionEngine 实现

```python
# agent/runtime/engine.py
from typing import AsyncIterator, Optional
from agent.memory.system import MemorySystem
from agent.knowledge.base import KnowledgeBase
from agent.skills.registry import SkillRegistry
from agent.models.router import ModelRouter
from agent.mcp.client import MCPClient
from agent.observability.observer import IObservability

class ExecutionEngine:
    """执行引擎 - 负责执行单步、调用 Skill、调用 Sandbox"""
    
    def __init__(
        self,
        config: dict,
        memory_system: MemorySystem,
        knowledge_base: KnowledgeBase,
        skill_registry: SkillRegistry,
        model_router: ModelRouter,
        mcp_client: MCPClient,
        observability: IObservability,
    ):
        self.config = config
        self.memory = memory_system
        self.knowledge = knowledge_base
        self.skills = skill_registry
        self.models = model_router
        self.mcp = mcp_client
        self.obs = observability
        self.sandbox = LocalSandbox()  # Phase 1: 本地执行，Phase 3: Docker
    
    async def execute(self, task) -> AsyncIterator[str]:
        """执行任务，流式返回结果"""
        task_id = task.task_id
        
        # 1. 追踪开始
        span = self.obs.trace(task_id, {"action": "task_start"})
        
        # 2. 检索记忆
        context = await self._build_context(task)
        
        # 3. 模型路由决策
        model = self.models.route(task.user_message, context)
        
        # 4. 构建 Prompt
        prompt = self._build_prompt(task, context, model)
        
        # 5. 调用 LLM（流式）
        async for chunk in self._call_llm(model, prompt, task_id):
            yield chunk
        
        # 6. 提取记忆
        self.memory.extract(task)
        
        # 7. 追踪结束
        span.end()
    
    async def _build_context(self, task) -> dict:
        """构建上下文"""
        # 1. 短期记忆（当前对话历史）
        short_term = self.memory.short_term.get_history(task.session_id)
        
        # 2. 用户记忆（偏好、事实）
        user_memories = self.memory.user.search(task.user_message)
        
        # 3. 知识库检索（可选）
        kb_results = []
        if self._need_knowledge(task.user_message):
            kb_results = await self.knowledge.search(task.user_message)
        
        return {
            "short_term": short_term,
            "user_memories": user_memories,
            "kb_results": kb_results,
        }
    
    def _build_prompt(self, task, context, model) -> str:
        """构建 Prompt"""
        prompt = f"""你是 NanamiGopher，一个有用的 AI 助手。

【用户记忆】
{self._format_memories(context['user_memories'])}

【知识库检索结果】
{self._format_kb_results(context['kb_results'])}

【对话历史】
{self._format_history(context['short_term'])}

【用户消息】
{task.user_message}
"""
        return prompt
    
    async def _call_llm(self, model, prompt: str, task_id: str) -> AsyncIterator[str]:
        """调用 LLM，流式返回"""
        # 1. 工具发现
        tools = self.skills.list_available()
        
        # 2. 调用模型
        async for chunk in model.chat_stream(
            messages=[{"role": "user", "content": prompt}],
            tools=tools,
            stream=True,
        ):
            # 3. 追踪 Token
            self.obs.metric(task_id, "tokens_output", len(chunk))
            yield chunk
            
            # 4. 检查是否需要调用工具
            if self._needs_tool_call(chunk):
                tool_result = await self._execute_tool(chunk, task_id)
                yield f"\n[工具调用结果] {tool_result}"
    
    async def _execute_tool(self, tool_call, task_id: str) -> str:
        """执行工具调用"""
        tool_name = tool_call.tool_name
        arguments = tool_call.arguments
        
        # 1. 权限检查
        skill = self.skills.resolve(tool_name)
        if not self._check_permission(skill.permission_level):
            return f"权限不足: 需要 L{skill.permission_level} 权限"
        
        # 2. 通过 MCP 调用工具
        result = await self.mcp.call_tool(
            namespace=skill.namespace,
            name=tool_name,
            arguments=arguments,
        )
        
        # 3. 追踪
        self.obs.metric(task_id, "tool_calls", 1)
        
        return result.content
    
    def _check_permission(self, required_level: int) -> bool:
        """检查权限（简化版）"""
        # 实际实现需要读取当前权限模式
        return True
    
    def _need_knowledge(self, message: str) -> bool:
        """判断是否需要知识库检索"""
        # 简单启发式：消息长度 > 100 或包含特定关键词
        return len(message) > 100
```

### 3.4 IMemorySystem 实现

```python
# agent/memory/system.py
from abc import ABC, abstractmethod
from typing import Optional

class IShortTermMemory(ABC):
    """短期记忆接口 - 当前对话的完整上下文"""
    
    @abstractmethod
    def add_message(self, session_id: str, role: str, content: str) -> None:
        """添加消息到短期记忆"""
        pass
    
    @abstractmethod
    def get_history(self, session_id: str, limit: int = 50) -> list[dict]:
        """获取对话历史"""
        pass
    
    @abstractmethod
    def clear(self, session_id: str) -> None:
        """清空短期记忆"""
        pass

class IConversationMemory(ABC):
    """会话记忆接口 - 历史对话摘要"""
    
    @abstractmethod
    def add_summary(self, session_id: str, summary: str) -> None:
        """添加会话摘要"""
        pass
    
    @abstractmethod
    def search(self, query: str, limit: int = 10) -> list[dict]:
        """搜索历史摘要"""
        pass
    
    @abstractmethod
    def delete(self, session_id: str) -> None:
        """删除会话记忆"""
        pass

class IUserMemory(ABC):
    """用户记忆接口 - 用户偏好和事实"""
    
    @abstractmethod
    def add_preference(self, user_id: str, key: str, value: str) -> None:
        """添加用户偏好"""
        pass
    
    @abstractmethod
    def add_fact(self, user_id: str, fact: str, tags: list[str]) -> None:
        """添加事实性知识"""
        pass
    
    @abstractmethod
    def search(self, query: str, limit: int = 10) -> list[dict]:
        """搜索用户记忆"""
        pass
    
    @abstractmethod
    def delete(self, memory_id: str) -> None:
        """删除记忆"""
        pass
    
    @abstractmethod
    def pin(self, memory_id: str) -> None:
        """标记保留"""
        pass
    
    @abstractmethod
    def unpin(self, memory_id: str) -> None:
        """取消保留"""
        pass

class MemorySystem:
    """记忆系统实现"""
    
    def __init__(self, config: dict):
        self.short_term = SQLiteShortTermMemory(config)
        self.conversation = SQLiteConversationMemory(config)
        self.user = SQLiteUserMemory(config)
        self.embedding_provider = self._create_embedding_provider(config)
        self.knowledge_base = None  # 引用 IKnowledgeBase
    
    def _create_embedding_provider(self, config: dict):
        """创建 Embedding Provider"""
        from agent.embedding.factory import EmbeddingFactory
        return EmbeddingFactory.create(
            config.memory.embedding.provider,
            **config.memory.embedding.get(config.memory.embedding.provider, {})
        )
    
    def extract(self, task) -> None:
        """对话结束后提取记忆"""
        # 1. 生成摘要
        summary = self._generate_summary(task)
        
        # 2. 提取偏好
        preferences = self._extract_preferences(task)
        
        # 3. 提取事实
        facts = self._extract_facts(task)
        
        # 4. 存储
        self.conversation.add_summary(task.session_id, summary)
        for pref in preferences:
            self.user.add_preference(task.session_id, pref.key, pref.value)
        for fact in facts:
            self.user.add_fact(task.session_id, fact.content, fact.tags)
    
    def _generate_summary(self, task) -> str:
        """生成对话摘要"""
        # 调用 LLM 生成摘要
        # 简化版：直接返回用户消息
        return task.user_message
    
    def _extract_preferences(self, task) -> list:
        """提取用户偏好"""
        # 通过 LLM 分析对话，提取偏好
        return []
    
    def _extract_facts(self, task) -> list:
        """提取事实性知识"""
        # 通过 LLM 分析对话，提取事实
        return []
    
    def cleanup_expired(self) -> int:
        """清理过期的记忆"""
        count = 0
        
        # 双重条件触发
        total_count = self.conversation.count() + self.user.count()
        if total_count > self.config.memory.retention.auto_cleanup.max_entries:
            # 检查是否有超过阈值的记忆
            expired = self.conversation.find_expired(days=30)
            expired += self.user.find_expired(days=30)
            
            for mem in expired:
                if not mem.is_pinned:
                    self.conversation.delete(mem.id)
                    count += 1
        
        return count
```

### 3.5 IKnowledgeBase 实现

```python
# agent/knowledge/base.py
from abc import ABC, abstractmethod
from typing import Optional

class IDocumentStore(ABC):
    """文档存储接口"""
    
    @abstractmethod
    def add(self, doc_id: str, title: str, content: str, metadata: dict) -> None:
        """添加文档"""
        pass
    
    @abstractmethod
    def get(self, doc_id: str) -> Optional[dict]:
        """获取文档"""
        pass
    
    @abstractmethod
    def delete(self, doc_id: str) -> None:
        """删除文档"""
        pass
    
    @abstractmethod
    def list(self, tags: Optional[list[str]] = None) -> list[dict]:
        """列出文档"""
        pass

class IVectorStore(ABC):
    """向量存储接口"""
    
    @abstractmethod
    def add(self, doc_id: str, embedding: list[float]) -> None:
        """添加向量"""
        pass
    
    @abstractmethod
    def search(self, query_embedding: list[float], top_k: int = 10) -> list[dict]:
        """向量相似度搜索"""
        pass
    
    @abstractmethod
    def delete(self, doc_id: str) -> None:
        """删除向量"""
        pass

class IRetriever(ABC):
    """检索器接口"""
    
    @abstractmethod
    async def search(self, query: str, top_k: int = 10) -> list[dict]:
        """语义搜索"""
        pass
    
    @abstractmethod
    async def hybrid_search(self, query: str, top_k: int = 10) -> list[dict]:
        """混合搜索（语义 + 关键词）"""
        pass

class KnowledgeBase:
    """知识库实现"""
    
    def __init__(self, config: dict):
        self.document_store = self._create_document_store(config)
        self.vector_store = self._create_vector_store(config)
        self.retriever = HybridRetriever(
            document_store=self.document_store,
            vector_store=self.vector_store,
            embedding_provider=self._create_embedding_provider(config),
        )
    
    def _create_document_store(self, config: dict) -> IDocumentStore:
        """创建文档存储"""
        # SQLite 存储文档元数据
        return SQLiteDocumentStore(config)
    
    def _create_vector_store(self, config: dict) -> IVectorStore:
        """创建向量存储"""
        if config.memory.vector_db == "chromadb":
            return ChromaDBVectorStore(config.chromadb)
        elif config.memory.vector_db == "sqlite":
            return SQLiteVectorStore(config.sqlite)
        else:
            raise ValueError(f"Unknown vector db: {config.memory.vector_db}")
    
    def _create_embedding_provider(self, config: dict):
        """创建 Embedding Provider"""
        from agent.embedding.factory import EmbeddingFactory
        return EmbeddingFactory.create(
            config.memory.embedding.provider,
            **config.memory.embedding.get(config.memory.embedding.provider, {})
        )
    
    async def search(self, query: str, top_k: int = 10) -> list[dict]:
        """搜索知识库"""
        return await self.retriever.hybrid_search(query, top_k)
    
    async def add_document(self, doc_id: str, title: str, content: str, tags: list[str] = None) -> None:
        """添加文档到知识库"""
        # 1. 存储文档
        self.document_store.add(doc_id, title, content, {"tags": tags or []})
        
        # 2. 生成 embedding
        embedding = self._embedding_provider.embed(content)
        
        # 3. 存储向量
        self.vector_store.add(doc_id, embedding)
```

### 3.6 Embedding Provider 抽象

```python
# agent/embedding/provider.py
from abc import ABC, abstractmethod

class IEmbeddingProvider(ABC):
    """Embedding Provider 接口"""
    
    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """单条文本 embedding"""
        pass
    
    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量 embedding"""
        pass

# agent/embedding/bge_provider.py
class BGEProvider(IEmbeddingProvider):
    """BGE-M3 Embedding Provider"""
    
    def __init__(self, model: str = "BGE-M3", device: str = "cpu"):
        from FlagEmbedding import BGEM3FlagModel
        self.model = BGEM3FlagModel(model_name=model, use_gpu=device == "cuda")
        self.device = device
    
    def embed(self, text: str) -> list[float]:
        result = self.model.encode([text])
        return result["dense_vecs"][0].tolist()
    
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        results = self.model.encode(texts)
        return results["dense_vecs"].tolist()

# agent/embedding/openai_provider.py
class OpenAIProvider(IEmbeddingProvider):
    """OpenAI Embedding Provider"""
    
    def __init__(self, model: str = "text-embedding-3-small", api_key: str = None):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model
    
    def embed(self, text: str) -> list[float]:
        response = self.client.embeddings.create(
            model=self.model,
            input=text
        )
        return response.data[0].embedding
    
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(
            model=self.model,
            input=texts
        )
        return [item.embedding for item in response.data]

# agent/embedding/factory.py
class EmbeddingFactory:
    """Embedding Provider 工厂"""
    
    _providers = {
        "bge": BGEProvider,
        "openai": OpenAIProvider,
    }
    
    @classmethod
    def create(cls, provider_name: str, **kwargs) -> IEmbeddingProvider:
        """创建 Embedding Provider"""
        provider_class = cls._providers.get(provider_name)
        if not provider_class:
            raise ValueError(f"Unknown embedding provider: {provider_name}")
        return provider_class(**kwargs)
```

### 3.7 Model Provider 抽象

```python
# agent/models/chat_provider.py
from abc import ABC, abstractmethod
from typing import AsyncIterator

class IChatProvider(ABC):
    """Chat Model Provider 接口"""
    
    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] = None,
        temperature: float = 0.7,
    ) -> dict:
        """非流式聊天"""
        pass
    
    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict],
        tools: list[dict] = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """流式聊天"""
        pass

# agent/models/image_provider.py
from abc import ABC, abstractmethod

class IImageProvider(ABC):
    """Image Model Provider 接口"""
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        size: str = "1024x1024",
        n: int = 1,
    ) -> list[str]:
        """生成图片，返回 URL 列表"""
        pass

# agent/models/registry.py
class ModelRegistry:
    """模型注册表 - 管理模型配置"""
    
    def __init__(self, config: dict):
        self.config = config
        self.providers = {}
        self._load_providers()
    
    def _load_providers(self):
        """加载模型提供商"""
        from agent.models.openai_chat import OpenAIChatProvider
        from agent.models.ollama_chat import OllamaChatProvider
        
        self.providers["openai"] = OpenAIChatProvider(
            api_key=self.config.models.cloud_providers.openai.api_key
        )
        self.providers["ollama"] = OllamaChatProvider(
            base_url=self.config.models.local_fallback_order[0]
        )
    
    def get_chat_provider(self, model_name: str) -> IChatProvider:
        """获取 Chat Provider"""
        if model_name.startswith("gpt"):
            return self.providers["openai"]
        elif model_name.startswith("ollama"):
            return self.providers["ollama"]
        else:
            raise ValueError(f"Unknown model: {model_name}")

# agent/models/router.py
class ModelRouter:
    """模型路由器 - 根据任务复杂度选择模型"""
    
    def __init__(self, config: dict, registry: ModelRegistry):
        self.config = config
        self.registry = registry
        self.routing_strategy = config.model_routing.strategy
    
    # 推理深度关键词（Phase 1 启发式匹配，Phase 2 替换为轻量分类器）
    REASONING_KEYWORDS = (
        "分析", "推理", "为什么", "证明", "步骤", "设计", "对比", "权衡", "规划",
        "analyze", "reason", "why", "prove", "design", "compare", "trade-off", "plan",
    )

    def route(self, message: str, context: dict = None) -> IChatProvider:
        """路由决策"""
        context = context or {}
        
        # 1. 评估复杂度（5 维度加权评分）
        complexity = self._assess_complexity(message, context)
        
        # 2. 选择模型池
        if complexity == "simple":
            model_pool = self.config.model_routing.simple
        elif complexity == "standard":
            model_pool = self.config.model_routing.standard
        else:
            model_pool = self.config.model_routing.complex
        
        # 3. 语言类型不参与复杂度评分，仅在模型选择阶段生效
        if self._detect_language(message) == "zh":
            for model in model_pool:
                if model.startswith("qwen"):
                    return self.registry.get_chat_provider(model)
        
        # 4. 优先本地模型
        if self.config.model_routing.prefer_local:
            for model in model_pool:
                if model.startswith("ollama"):
                    return self.registry.get_chat_provider(model)
        
        # 5. 返回默认模型
        return self.registry.get_chat_provider(model_pool[0])
    
    def _detect_language(self, message: str) -> str:
        """检测消息主要语言"""
        return "zh" if any("一" <= ch <= "鿿" for ch in message) else "en"
    
    def _assess_complexity(self, message: str, context: dict) -> str:
        """评估任务复杂度（5 维度加权评分）"""
        # 维度 1：指令长度 (20%)
        length_score = min(len(message) / 1000, 1.0)
        
        # 维度 2：工具调用数 (25%) —— 由上游 planner 预判并写入 context
        tool_count = len(context.get("tool_hints", []))
        tool_score = min(tool_count / 5, 1.0)
        
        # 维度 3：推理深度 (30%) —— Phase 1 关键词启发式
        hits = sum(1 for kw in self.REASONING_KEYWORDS if kw in message)
        reasoning_score = min(hits / 3, 1.0)
        
        # 维度 4：语言类型 (15%) —— 不参与评分，见 route()
        
        # 维度 5：预算约束 (10%)
        budget_score = {
            "minimal": 0.0,
            "normal": 0.5,
            "unlimited": 1.0,
        }.get(context.get("budget", "normal"), 0.5)
        
        # 语言类型 15% 不参与评分，将其余权重归一化到 1.0
        weights = {"length": 0.20, "tool": 0.25, "reasoning": 0.30, "budget": 0.10}
        total_weight = sum(weights.values())
        score = (
            length_score * weights["length"]
            + tool_score * weights["tool"]
            + reasoning_score * weights["reasoning"]
            + budget_score * weights["budget"]
        ) / total_weight
        
        if score < 0.25:
            return "simple"
        elif score < 0.60:
            return "standard"
        else:
            return "complex"
```

### 3.8 ISkillRegistry 实现

```python
# agent/skills/registry.py
import json
import yaml
from pathlib import Path
from typing import Optional

class Skill:
    """Skill 对象"""
    
    def __init__(self, name: str, version: str, description: str,
                 namespace: str, entry_point: str, executable: str = None,
                 dependencies: list[str] = None, permission_level: int = 2):
        self.name = name
        self.version = version
        self.description = description
        self.namespace = namespace
        self.entry_point = entry_point
        self.executable = executable
        self.dependencies = dependencies or []
        self.permission_level = permission_level
        self.is_active = True

class SkillRegistry:
    """Skill 注册表 - 包含 register/unresolve/list/getVersion/checkDependency"""
    
    def __init__(self, config: dict):
        self.config = config
        self.skills: dict[str, Skill] = {}
        self.db = SQLiteSkillDB(config)
        self._load_builtin_skills()
    
    def _load_builtin_skills(self):
        """加载内置 Skill"""
        builtin_skills = [
            Skill(
                name="file_reader",
                version="1.0",
                description="读取文件内容",
                namespace="builtin/filesystem",
                entry_point="tools/file_reader/server.py",
                permission_level=1,
            ),
            Skill(
                name="code_executor",
                version="1.0",
                description="执行代码",
                namespace="builtin/executor",
                entry_point="tools/code_executor/server.py",
                permission_level=3,
            ),
            Skill(
                name="web_search",
                version="1.0",
                description="网络搜索",
                namespace="builtin/search",
                entry_point="tools/web_search/server.py",
                permission_level=3,
            ),
        ]
        for skill in builtin_skills:
            self.register(skill)
    
    def register(self, skill: Skill) -> None:
        """注册 Skill"""
        # 1. 检查依赖
        if not self._check_dependencies(skill):
            raise ValueError(f"Missing dependencies for {skill.name}")
        
        # 2. 存储
        self.skills[skill.name] = skill
        self.db.save(skill)
    
    def unregister(self, name: str) -> None:
        """卸载 Skill"""
        if name in self.skills:
            del self.skills[name]
            self.db.delete(name)
    
    def resolve(self, name: str) -> Optional[Skill]:
        """解析 Skill（通过名称或命名空间）"""
        if name in self.skills:
            return self.skills[name]
        
        # 通过命名空间查找
        for skill in self.skills.values():
            if skill.namespace.endswith(name):
                return skill
        
        return None
    
    def list(self) -> list[Skill]:
        """列出所有 Skill"""
        return list(self.skills.values())
    
    def get_version(self, name: str) -> Optional[str]:
        """获取 Skill 版本"""
        skill = self.resolve(name)
        return skill.version if skill else None
    
    def check_dependency(self, name: str) -> bool:
        """检查 Skill 依赖是否满足"""
        skill = self.resolve(name)
        if not skill:
            return False
        
        for dep in skill.dependencies:
            if self.resolve(dep) is None:
                return False
        
        return True
    
    def _check_dependencies(self, skill: Skill) -> bool:
        """检查依赖是否满足"""
        return self.check_dependency(skill.name)
    
    def import_skill(self, skill_dir: Path) -> Skill:
        """从目录导入 Skill（SKILL.md + 配套目录）"""
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            raise ValueError(f"SKILL.md not found in {skill_dir}")
        
        # 解析 SKILL.md
        with open(skill_md) as f:
            frontmatter = yaml.safe_load(f)
        
        skill = Skill(
            name=frontmatter["name"],
            version=frontmatter.get("version", "1.0"),
            description=frontmatter.get("description", ""),
            namespace=f"custom/{frontmatter['name']}",
            entry_point=str(skill_md),
            executable=skill_dir,
            dependencies=frontmatter.get("dependencies", []),
            permission_level=2,
        )
        
        self.register(skill)
        return skill
```

### 3.9 Sandbox 实现

```python
# agent/runtime/sandbox.py
from abc import ABC, abstractmethod
import subprocess
import tempfile
import os

class ISandbox(ABC):
    """沙箱接口 - Skill 无感知执行环境"""
    
    @abstractmethod
    def execute(self, skill, args: dict) -> dict:
        """执行 Skill"""
        pass

class LocalSandbox(ISandbox):
    """本地沙箱 - Phase 1 使用"""
    
    def execute(self, skill, args: dict) -> dict:
        """在本地执行 Skill（MCP JSON-RPC over stdio）"""
        request = json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": skill.name, "arguments": args},
            "id": 1,
        })

        proc = subprocess.run(
            [skill.executable],
            input=request,
            capture_output=True,
            text=True,
            timeout=30,
        )

        # 解析 MCP 响应
        try:
            response = json.loads(proc.stdout)
        except json.JSONDecodeError:
            return {"error": "invalid MCP response", "stderr": proc.stderr}

        if "error" in response:
            return {"error": response["error"], "stderr": proc.stderr}

        return response.get("result", {})

class DockerSandbox(ISandbox):
    """Docker 沙箱 - Phase 3 使用"""
    
    def __init__(self, image: str = "nanamigopher/skill-runner"):
        self.image = image
    
    def execute(self, skill, args: dict) -> dict:
        """在 Docker 容器中执行 Skill"""
        # 创建临时目录挂载
        with tempfile.TemporaryDirectory() as tmpdir:
            # 写入 Skill 代码和参数
            with open(os.path.join(tmpdir, "args.json"), "w") as f:
                json.dump(args, f)
            
            # 启动容器执行
            result = subprocess.run([
                "docker", "run", "--rm",
                "-v", f"{tmpdir}:/data",
                self.image,
                "/data/args.json",
            ], capture_output=True, text=True, timeout=120)
            
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
```

### 3.10 IContextManager 实现

```python
# agent/runtime/context_manager.py
class IContextManager:
    """上下文窗口管理器接口"""
    
    def build_context(self, messages: list[dict], max_tokens: int = 4096) -> list[dict]:
        """构建上下文，处理截断/压缩"""
        pass

class ContextManager(IContextManager):
    """上下文窗口管理器实现"""
    
    def __init__(self, config: dict):
        self.config = config
        self.max_tokens = config.get("context_max_tokens", 4096)
    
    def build_context(self, messages: list[dict], max_tokens: int = None) -> list[dict]:
        """构建上下文
        
        策略:
        1. 如果总 token 数 <= max_tokens，直接返回
        2. 否则，保留最近的 N 条消息，使总 token 数 <= max_tokens
        3. 如果仍然超限，对最早的消息进行摘要压缩
        """
        if max_tokens is None:
            max_tokens = self.max_tokens
        
        # 1. 估算总 token 数
        total_tokens = self._estimate_tokens(messages)
        
        if total_tokens <= max_tokens:
            return messages
        
        # 2. 滑动窗口截断
        truncated = self._slide_window(messages, max_tokens)
        
        # 3. 如果仍然超限，摘要压缩
        if self._estimate_tokens(truncated) > max_tokens:
            truncated = self._summarize_early_messages(truncated, max_tokens)
        
        return truncated
    
    def _estimate_tokens(self, messages: list[dict]) -> int:
        """估算 token 数（简化版）"""
        total = 0
        for msg in messages:
            total += len(msg.get("content", "")) // 4  # 粗略估算
        return total
    
    def _slide_window(self, messages: list[dict], max_tokens: int) -> list[dict]:
        """滑动窗口截断"""
        result = []
        tokens = 0
        
        for msg in reversed(messages):
            msg_tokens = self._estimate_tokens([msg])
            if tokens + msg_tokens <= max_tokens:
                result.append(msg)
                tokens += msg_tokens
        
        return list(reversed(result))
    
    def _summarize_early_messages(self, messages: list[dict], max_tokens: int) -> list[dict]:
        """摘要压缩早期消息"""
        # 保留最后一条用户消息和最近几条
        keep_last = 5
        early_messages = messages[:-keep_last]
        late_messages = messages[-keep_last:]
        
        if not early_messages:
            return late_messages
        
        # 调用 LLM 生成摘要
        summary = self._generate_summary(early_messages)
        
        return [{"role": "system", "content": f"[早期对话摘要]\n{summary}"}] + late_messages
    
    def _generate_summary(self, messages: list[dict]) -> str:
        """生成对话摘要"""
        # 调用 LLM 生成摘要
        # 简化版：直接拼接
        return "\n".join([msg.get("content", "") for msg in messages[:3]])
```

### 3.11 IExecutionRecovery 实现

```python
# agent/runtime/recovery.py
from enum import Enum

class RecoveryStrategy(Enum):
    RETRY = "retry"
    FALLBACK = "fallback"
    ROLLBACK = "rollback"
    SKIP = "skip"

class IExecutionRecovery:
    """执行恢复接口"""
    
    def handle_failure(self, task_id: str, error: Exception) -> RecoveryStrategy:
        """处理失败，返回恢复策略"""
        pass

class ExecutionRecovery(IExecutionRecovery):
    """执行恢复实现"""
    
    def __init__(self, config: dict):
        self.config = config
        self.max_retries = config.get("retry_max_attempts", 2)
        self.backoff_multiplier = config.get("retry_backoff_multiplier", 2)
    
    def handle_failure(self, task_id: str, error: Exception) -> RecoveryStrategy:
        """处理失败"""
        error_type = type(error).__name__
        
        # 1. 网络错误 → 重试
        if "timeout" in error_type.lower() or "connection" in error_type.lower():
            return RecoveryStrategy.RETRY
        
        # 2. 工具不存在 → 回退
        if "not found" in str(error).lower():
            return RecoveryStrategy.FALLBACK
        
        # 3. 权限错误 → 跳过
        if "permission" in error_type.lower():
            return RecoveryStrategy.SKIP
        
        # 4. 未知错误 → 回退
        return RecoveryStrategy.FALLBACK
    
    async def retry_with_backoff(self, func, *args, **kwargs):
        """带指数退避的重试"""
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                
                if attempt < self.max_retries:
                    # 指数退避
                    delay = self.backoff_multiplier ** attempt
                    await asyncio.sleep(delay)
        
        raise last_error
```

### 3.12 IObservability 实现

```python
# agent/observability/observer.py
from abc import ABC, abstractmethod
import time
import logging

class IObservability(ABC):
    """可观测性接口"""
    
    @abstractmethod
    def log(self, event: str, level: str = "info") -> None:
        """记录日志"""
        pass
    
    @abstractmethod
    def trace(self, task_id: str, data: dict) -> "TraceSpan":
        """创建追踪 Span"""
        pass
    
    @abstractmethod
    def metric(self, name: str, value: float) -> None:
        """记录指标"""
        pass

class TraceSpan:
    """追踪 Span"""
    
    def __init__(self, task_id: str, operation_name: str, observer: IObservability):
        self.task_id = task_id
        self.operation_name = operation_name
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.attributes: dict = {}
        self.observer = observer
    
    def set_attribute(self, key: str, value):
        """设置属性"""
        self.attributes[key] = value
    
    def end(self):
        """结束 Span"""
        self.end_time = time.time()
        duration = (self.end_time - self.start_time) * 1000  # ms
        self.observer.metric(f"duration.{self.operation_name}", duration)
        self.observer.log(f"Span {self.operation_name} completed in {duration:.2f}ms")

class ConsoleObserver(IObservability):
    """控制台观察者 - Phase 1 使用"""
    
    def __init__(self, config: dict):
        self.logger = logging.getLogger("nanamigopher")
        self.config = config
    
    def log(self, event: str, level: str = "info") -> None:
        """记录日志到控制台"""
        getattr(self.logger, level)(event)
    
    def trace(self, task_id: str, data: dict) -> TraceSpan:
        """创建追踪 Span"""
        span = TraceSpan(task_id, data.get("operation", "unknown"), self)
        for key, value in data.items():
            if key != "operation":
                span.set_attribute(key, value)
        return span
    
    def metric(self, name: str, value: float) -> None:
        """记录指标到控制台"""
        self.logger.info(f"METRIC: {name} = {value}")

# Phase 3: LangfuseObserver
class LangfuseObserver(IObservability):
    """Langfuse 观察者 - Phase 3 使用"""
    
    def __init__(self, config: dict):
        from langfuse import Langfuse
        self.langfuse = Langfuse(
            secret_key=config.observability.langfuse.secret_key,
            public_key=config.observability.langfuse.public_key,
            host=config.observability.langfuse.host,
        )
    
    def log(self, event: str, level: str = "info") -> None:
        self.langfuse.log(event, level=level)
    
    def trace(self, task_id: str, data: dict) -> TraceSpan:
        trace = self.langfuse.trace(name=task_id, input=data)
        return LangfuseTraceSpan(trace, self)
    
    def metric(self, name: str, value: float) -> None:
        self.langfuse.metric(name=name, value=value)
```

---

## 4. 数据流设计

### 4.1 用户请求链路

```
用户输入
  │
  ▼
Vue 3 前端 (electron-app/src/)
  │
  │ WebSocket (ws://localhost:8080/api/v1/sessions/:id/stream)
  ▼
Go API Gateway (internal/api/message_handler.go)
  │
  │ gRPC (AgentService.ProcessMessage)
  ▼
Python Agent Core (agent/main.py → ExecutionEngine.execute())
  │
  ├── 1. 安全过滤 (InputSanitizer)
  │     └── 正则检测 + 长度截断
  │
  ├── 2. 构建上下文 (ContextManager.build_context())
  │     ├── 短期记忆 (IMemorySystem.short_term.get_history())
  │     ├── 用户记忆 (IMemorySystem.user.search())
  │     └── 知识库检索 (IKnowledgeBase.search())
  │
  ├── 3. 模型路由 (ModelRouter.route())
  │     └── 选择 IChatProvider
  │
  ├── 4. 调用 LLM (IChatProvider.chat_stream())
  │     ├── OpenAI / Ollama / Claude
  │     └── 流式返回 chunks
  │
  ├── 5. 工具调用 (MCPClient.call_tool())
  │     ├── 权限检查 (PermissionChecker)
  │     ├── 通过 stdio 调用 MCP Server
  │     └── 返回工具结果
  │
  └── 6. 记忆提取 (MemorySystem.extract())
        ├── 生成对话摘要
        ├── 提取用户偏好
        └── 存储到 IMemorySystem
  │
  ▼
Go API Gateway (internal/websocket/hub.go)
  │
  │ WebSocket 推送
  ▼
Vue 3 前端 (渲染消息)
```

### 4.2 事件推送链路

```
Python Agent Core (ExecutionEngine)
  │
  │ IObservability.trace() / IObservability.metric()
  ▼
ConsoleObserver (Phase 1) / LangfuseObserver (Phase 3)
  │
  │ 输出到日志 / 发送到 Langfuse
  ▼
Go API Gateway (internal/websocket/hub.go)
  │
  │ 监听 Python 进程 stdout
  ▼
WebSocket 推送
  │
  │ StreamEvent { type, data, timestamp }
  ▼
Vue 3 前端 (InspectorView / ChatView)
```

### 4.3 审批流程数据流

```
Python Agent Core (ExecutionEngine)
  │
  │ 检测到需要审批的操作
  ▼
gRPC: ApprovalRequest { request_id, action, preview, timeout }
  │
  ▼
Go API Gateway (internal/api/approval_handler.go)
  │
  │ 持久化到 SQLite
  │ 推送 WebSocket 事件到前端
  ▼
Vue 3 前端 (ApprovalDialog)
  │
  │ 用户点击 [批准] / [拒绝]
  ▼
gRPC: ApprovalDecision { request_id, decision, selected_items }
  │
  ▼
Go API Gateway → Python Agent Core
  │
  │ 恢复执行
  ▼
ExecutionEngine 继续执行
```

---

## 5. 配置管理

### 5.1 配置加载器

```go
// internal/config/loader.go
package config

import (
    "fmt"
    "os"
    "path/filepath"

    "gopkg.in/yaml.v3"
)

// Config 全局配置结构
type Config struct {
    App        AppConfig        `yaml:"app"`
    Models     ModelsConfig     `yaml:"models"`
    Memory     MemoryConfig     `yaml:"memory"`
    Security   SecurityConfig   `yaml:"security"`
    Skills     SkillsConfig     `yaml:"skills"`
    MCP        MCPConfig        `yaml:"mcp"`
    Observability ObservabilityConfig `yaml:"observability"`
    GRPC       GRPCConfig       `yaml:"grpc"`
    HTTP       HTTPConfig       `yaml:"http"`
}

// Load 加载配置文件
func Load(path string) (*Config, error) {
    // 1. 检查文件是否存在
    if _, err := os.Stat(path); os.IsNotExist(err) {
        // 使用默认配置
        return DefaultConfig(), nil
    }
    
    // 2. 读取文件
    data, err := os.ReadFile(path)
    if err != nil {
        return nil, fmt.Errorf("read config file: %w", err)
    }
    
    // 3. 解析 YAML
    var cfg Config
    if err := yaml.Unmarshal(data, &cfg); err != nil {
        return nil, fmt.Errorf("parse config: %w", err)
    }
    
    // 4. 环境变量覆盖
    cfg.applyEnvOverrides()
    
    // 5. 验证配置
    if err := cfg.Validate(); err != nil {
        return nil, fmt.Errorf("validate config: %w", err)
    }
    
    return &cfg, nil
}

// Reload 热重载配置（Phase 3）
func (cfg *Config) Reload(path string) error {
    newCfg, err := Load(path)
    if err != nil {
        return err
    }
    
    // 应用新配置
    *cfg = *newCfg
    return nil
}
```

### 5.2 配置结构体

```go
// internal/config/models.go
package config

// AppConfig 应用配置
type AppConfig struct {
    Name    string `yaml:"name"`
    Version string `yaml:"version"`
    Theme   string `yaml:"theme"`
}

// ModelsConfig 模型配置
type ModelsConfig struct {
    PreferLocal        bool     `yaml:"prefer_local"`
    LocalFallbackOrder []string `yaml:"local_fallback_order"`
    CloudProviders     struct {
        OpenAI struct {
            DefaultModel  string `yaml:"default_model"`
            FallbackModels []string `yaml:"fallback_models"`
        } `yaml:"openai"`
        Anthropic struct {
            DefaultModel  string `yaml:"default_model"`
            FallbackModels []string `yaml:"fallback_models"`
        } `yaml:"anthropic"`
    } `yaml:"cloud_providers"`
    Routing struct {
        Strategy            string `yaml:"strategy"`
        ComplexityThreshold struct {
            Simple   int `yaml:"simple"`
            Standard int `yaml:"standard"`
            Complex  int `yaml:"complex"`
        } `yaml:"complexity_threshold"`
    } `yaml:"routing"`
}

// MemoryConfig 记忆配置
type MemoryConfig struct {
    Storage struct {
        VectorDB    string `yaml:"vector_db"`
        SQLitePath  string `yaml:"sqlite_path"`
    } `yaml:"storage"`
    Embedding struct {
        Provider string            `yaml:"provider"`
        Local    map[string]string `yaml:"local"`
        OpenAI   map[string]string `yaml:"openai"`
    } `yaml:"embedding"`
    Retention struct {
        AutoCleanup struct {
            Enabled    bool `yaml:"enabled"`
            MaxEntries int  `yaml:"max_entries"`
            MaxSizeMB  int  `yaml:"max_size_mb"`
            AgeDays    int  `yaml:"age_days"`
            Trigger    string `yaml:"trigger"`
        } `yaml:"auto_cleanup"`
        Extraction struct {
            IncludeSummary    bool `yaml:"include_summary"`
            IncludePreferences bool `yaml:"include_preferences"`
            IncludeFacts      bool `yaml:"include_facts"`
        } `yaml:"extraction"`
    } `yaml:"retention"`
}

// SecurityConfig 安全配置
type SecurityConfig struct {
    PromptInjection struct {
        Enabled       bool     `yaml:"enabled"`
        RegexPatterns string   `yaml:"regex_patterns"`
        VectorBlock   struct {
            Enabled            bool    `yaml:"enabled"`
            SimilarityThreshold float64 `yaml:"similarity_threshold"`
            FallbackThreshold  float64 `yaml:"fallback_threshold"`
        } `yaml:"vector_block"`
        LengthLimit struct {
            MaxTokens int    `yaml:"max_tokens"`
            Strategy  string `yaml:"strategy"`
        } `yaml:"length_limit"`
        Whitelist struct {
            GlobalKeywords []string `yaml:"global_keywords"`
            UserKeywords   []string `yaml:"user_keywords"`
            UserRegex      []string `yaml:"user_regex"`
        } `yaml:"whitelist"`
    } `yaml:"prompt_injection"`
    AuditLog struct {
        Enabled        bool   `yaml:"enabled"`
        Storage        string `yaml:"storage"`
        Path           string `yaml:"path"`
        RetentionDays  int    `yaml:"retention_days"`
        MaskInputSummary bool `yaml:"mask_input_summary"`
    } `yaml:"audit_log"`
}

// SkillsConfig Skill 配置
type SkillsConfig struct {
    ScanDirectories []string `yaml:"scan_directories"`
    NamespaceIsolation bool   `yaml:"namespace_isolation"`
    DependencyResolution string `yaml:"dependency_resolution"`
    Workflow struct {
        Engine         string `yaml:"engine"`
        MaxGraphDepth  int    `yaml:"max_graph_depth"`
        Checkpoint     struct {
            Enabled bool   `yaml:"enabled"`
            Storage string `yaml:"storage"`
            Path    string `yaml:"path"`
        } `yaml:"checkpoint"`
        Timeout struct {
            NodeExecution string `yaml:"node_execution"`
            TotalWorkflow string `yaml:"total_workflow"`
        } `yaml:"timeout"`
    } `yaml:"workflow"`
}

// MCPConfig MCP 配置
type MCPConfig struct {
    Servers map[string]struct {
        Command      string   `yaml:"command"`
        Args         []string `yaml:"args"`
        EnvKeyName   string   `yaml:"env_key_name"`
        AutoInstall  bool     `yaml:"auto_install"`
        HealthCheck  string   `yaml:"health_check"`
    } `yaml:"servers"`
}

// ObservabilityConfig 可观测性配置
type ObservabilityConfig struct {
    Tracing struct {
        Enabled     bool    `yaml:"enabled"`
        Provider    string  `yaml:"provider"`
        SampleRate  float64 `yaml:"sample_rate"`
        RetentionDays int   `yaml:"retention_days"`
    } `yaml:"tracing"`
    Benchmark struct {
        Enabled          bool   `yaml:"enabled"`
        GoldenDatasetPath string `yaml:"golden_dataset_path"`
        AutoRunOnDeploy  bool   `yaml:"auto_run_on_deploy"`
        Schedule         string `yaml:"schedule"`
    } `yaml:"benchmark"`
}

// GRPCConfig gRPC 配置
type GRPCConfig struct {
    Port     int `yaml:"port"`
    Timeout  int `yaml:"timeout"`
}

// HTTPConfig HTTP 配置
type HTTPConfig struct {
    Port int `yaml:"port"`
}
```

### 5.3 配置验证

```go
// internal/config/validator.go
package config

func (cfg *Config) Validate() error {
    // 验证模型配置
    if cfg.Models.PreferLocal && len(cfg.Models.LocalFallbackOrder) == 0 {
        return fmt.Errorf("prefer_local is true but no local models configured")
    }
    
    // 验证记忆配置
    if cfg.Memory.Retention.AutoCleanup.Enabled {
        if cfg.Memory.Retention.AutoCleanup.MaxEntries <= 0 {
            return fmt.Errorf("max_entries must be positive")
        }
        if cfg.Memory.Retention.AutoCleanup.AgeDays <= 0 {
            return fmt.Errorf("age_days must be positive")
        }
    }
    
    // 验证安全配置
    if cfg.Security.PromptInjection.Enabled {
        if cfg.Security.PromptInjection.LengthLimit.MaxTokens <= 0 {
            return fmt.Errorf("max_tokens must be positive")
        }
    }
    
    return nil
}
```

---

## 6. 错误处理

### 6.1 错误分级

```go
// pkg/errors/errors.go
package errors

// ErrorLevel 错误级别
type ErrorLevel string

const (
    ErrorP0 ErrorLevel = "P0" // 严重
    ErrorP1 ErrorLevel = "P1" // 一般
    ErrorP2 ErrorLevel = "P2" // 轻微
)

// AppError 应用错误
type AppError struct {
    Level     ErrorLevel `json:"level"`
    Code      string     `json:"code"`
    Message   string     `json:"message"`
    Suggestion string   `json:"suggestion,omitempty"`
    Retryable bool       `json:"retryable,omitempty"`
    Cause     error      `json:"-"`
}

func (e *AppError) Error() string {
    return e.Message
}

func (e *AppError) Unwrap() error {
    return e.Cause
}

// 错误码定义
const (
    ErrModelAllFailed    = "MODEL_ALL_FAILED"     // P0: 所有模型失败
    ErrNetworkTimeout    = "NETWORK_TIMEOUT"      // P1: 网络超时
    ErrToolCallFailed    = "TOOL_CALL_FAILED"     // P1: 工具调用失败
    ErrPermissionDenied  = "PERMISSION_DENIED"    // P1: 权限拒绝
    ErrPartialFailure    = "PARTIAL_FAILURE"      // P2: 部分失败
    ErrCancelled         = "CANCELLED"            // P2: 用户取消
)
```

### 6.2 错误处理中间件

```go
// internal/api/middleware/error_handler.go
package middleware

import (
    "github.com/gin-gonic/gin"
    "nanamigopher/pkg/errors"
)

// ErrorHandler 全局错误处理中间件
func ErrorHandler() gin.HandlerFunc {
    return func(c *gin.Context) {
        c.Next()
        
        if len(c.Errors) > 0 {
            for _, err := range c.Errors {
                appErr, ok := err.Err.(*errors.AppError)
                if !ok {
                    // 未知错误，记录日志
                    c.JSON(500, gin.H{
                        "error": "internal_error",
                        "message": "服务器内部错误",
                    })
                    return
                }
                
                // 根据错误级别返回不同响应
                switch appErr.Level {
                case errors.ErrorP0:
                    c.JSON(500, gin.H{
                        "error": appErr.Code,
                        "message": appErr.Message,
                        "suggestion": appErr.Suggestion,
                    })
                case errors.ErrorP1:
                    c.JSON(400, gin.H{
                        "error": appErr.Code,
                        "message": appErr.Message,
                        "suggestion": appErr.Suggestion,
                        "retryable": appErr.Retryable,
                    })
                case errors.ErrorP2:
                    c.JSON(207, gin.H{
                        "error": appErr.Code,
                        "message": appErr.Message,
                    })
                }
            }
        }
    }
}
```

### 6.3 重试策略

```go
// internal/api/middleware/retry.go
package middleware

import (
    "time"
    "github.com/cenkalti/backoff/v4"
)

// RetryWithBackoff 带指数退避的重试
func RetryWithBackoff(operation func() error, maxRetries int) error {
    b := backoff.NewExponentialBackOff()
    b.Multiplier = 2
    b.MaxElapsedTime = 30 * time.Second
    b.MaxInterval = 10 * time.Second
    
    retry := backoff.NewRetryOperation(b, maxRetries)
    
    return backoff.Retry(operation, retry)
}

// 使用示例
func (h *SessionHandler) SendMessage(c *gin.Context) {
    var retryErr error
    
    err := RetryWithBackoff(func() error {
        resp, err := h.grpcClient.ProcessMessage(c.Request.Context(), &req)
        if err != nil {
            retryErr = err
            return err
        }
        return nil
    }, 2)
    
    if retryErr != nil {
        c.JSON(http.StatusInternalServerError, gin.H{
            "error": "TOOL_CALL_FAILED",
            "message": "工具调用失败（已重试 2 次）",
        })
        return
    }
}
```

---

## 7. 安全机制

### 7.1 安全过滤管道

```go
// internal/security/gatekeeper.go
package security

import (
    "strings"
)

// Gatekeeper 长度截断守卫
type Gatekeeper struct {
    maxTokens int
}

func NewGatekeeper(maxTokens int) *Gatekeeper {
    return &Gatekeeper{maxTokens: maxTokens}
}

// Filter 长度截断
func (g *Gatekeeper) Filter(input string) (string, bool) {
    // 估算 token 数（简化：每 4 字符 ≈ 1 token）
    estimatedTokens := len(input) / 4
    
    if estimatedTokens <= g.maxTokens {
        return input, false  // 无需截断
    }
    
    // 截断到最大 token 数
    truncated := input[:g.maxTokens*4]
    return truncated, true  // 已截断
}

// internal/security/regex_filter.go
package security

import (
    "regexp"
)

// Pattern 注入攻击正则模式
type Pattern struct {
    Name     string
    Regex    *regexp.Regexp
    Severity string // "block" | "warn"
}

// RegexFilter 正则过滤器
type RegexFilter struct {
    patterns []Pattern
}

func NewRegexFilter() *RegexFilter {
    return &RegexFilter{
        patterns: []Pattern{
            {
                Name:     "ignore_instructions",
                Regex:    regexp.MustCompile(`(?i)(ignore\s+(all\s+)?(previous\s+)?(system\s+)?instructions?)`),
                Severity: "block",
            },
            {
                Name:     "system_prompt_leak",
                Regex:    regexp.MustCompile(`(?i)(tell\s+me\s+your\s+(system\s+)?prompt|reveal\s+your\s+instructions)`),
                Severity: "block",
            },
            {
                Name:     "role_escape",
                Regex:    regexp.MustCompile(`(?i)(daniel|do\s+anything|DAN\s+mode|jailbreak)`),
                Severity: "block",
            },
            // ... 更多模式
        },
    }
}

// Check 检查输入是否命中正则模式
func (f *RegexFilter) Check(input string) []Match {
    var matches []Match
    
    for _, pattern := range f.patterns {
        if pattern.Regex.MatchString(input) {
            matches = append(matches, Match{
                PatternName: pattern.Name,
                Severity:    pattern.Severity,
            })
        }
    }
    
    return matches
}

// internal/security/whitelist.go
package security

// Whitelist 白名单
type Whitelist struct {
    GlobalKeywords []string
    UserKeywords   []string
    UserRegex      []*regexp.Regexp
}

// IsWhitelisted 检查是否命中白名单
func (w *Whitelist) IsWhitelisted(input string) bool {
    // 检查关键词
    allKeywords := append(w.GlobalKeywords, w.UserKeywords...)
    for _, keyword := range allKeywords {
        if strings.Contains(strings.ToLower(input), strings.ToLower(keyword)) {
            return true
        }
    }
    
    // 检查正则
    for _, regex := range w.UserRegex {
        if regex.MatchString(input) {
            return true
        }
    }
    
    return false
}

// internal/security/filter_pipeline.go
package security

// Match 匹配结果
type Match struct {
    PatternName string
    Severity    string
}

// FilterPipeline 安全过滤管道
type FilterPipeline struct {
    gatekeeper  *Gatekeeper
    regexFilter *RegexFilter
    whitelist   *Whitelist
    auditLogger *AuditLogger
}

func NewFilterPipeline(cfg *Config) *FilterPipeline {
    return &FilterPipeline{
        gatekeeper:  NewGatekeeper(cfg.LengthLimit.MaxTokens),
        regexFilter: NewRegexFilter(),
        whitelist:   &Whitelist{
            GlobalKeywords: cfg.Whitelist.GlobalKeywords,
            UserKeywords:   cfg.Whitelist.UserKeywords,
            UserRegex:      parseRegex(cfg.Whitelist.UserRegex),
        },
        auditLogger: NewAuditLogger(cfg.AuditLog),
    }
}

// Filter 执行完整过滤管道
func (p *FilterPipeline) Filter(input string) (string, []AuditEntry) {
    var entries []AuditEntry
    
    // 第 1 步: 长度截断
    truncated, wasTruncated := p.gatekeeper.Filter(input)
    if wasTruncated {
        entries = append(entries, AuditEntry{
            Event: "length_truncated",
            Severity: "info",
        })
    }
    
    // 第 2 步: 正则检测
    matches := p.regexFilter.Check(truncated)
    for _, match := range matches {
        if match.Severity == "block" {
            // 检查白名单
            if p.whitelist.IsWhitelisted(truncated) {
                // 降级为 warn
                entries = append(entries, AuditEntry{
                    Event: "whitelist_hit",
                    Pattern: match.PatternName,
                    Severity: "warn",
                })
            } else {
                // 拦截
                entries = append(entries, AuditEntry{
                    Event: "injection_blocked",
                    Pattern: match.PatternName,
                    Severity: "block",
                })
                return "", entries  // 返回空字符串，表示拦截
            }
        }
    }
    
    // 第 3 步: 向量拦截（可选）
    // if cfg.VectorBlock.Enabled {
    //     if p.vectorFilter.Block(truncated) {
    //         entries = append(entries, AuditEntry{...})
    //         return "", entries
    //     }
    // }
    
    return truncated, entries
}
```

### 7.2 权限校验

```go
// internal/api/middleware/permission.go
package middleware

import (
    "net/http"
    "github.com/gin-gonic/gin"
)

// PermissionMiddleware 权限校验中间件
func PermissionMiddleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        // 1. 获取当前权限模式
        mode := c.GetString("permission_mode")  // 从 session 中获取
        
        // 2. 获取操作级别
        operationLevel := c.GetInt("operation_level")
        
        // 3. 检查是否允许
        if !isAllowed(mode, operationLevel) {
            c.JSON(http.StatusForbidden, gin.H{
                "error": "PERMISSION_DENIED",
                "message": "权限不足，需要升级权限模式",
                "suggestion": "请在设置中切换权限模式",
            })
            c.Abort()
            return
        }
        
        c.Next()
    }
}

func isAllowed(mode string, level int) bool {
    // Manual: L1/L2 直接允许，L3/L4/L5 需要确认
    // AcceptEdits: L1/L2/L4 直接允许，L3/L5 需要确认
    // Auto: L1-L4 直接允许，L5 需要确认
    switch mode {
    case "manual":
        return level <= 2
    case "accept_edits":
        return level <= 2 || level == 4
    case "auto":
        return level <= 4
    default:
        return level <= 2
    }
}
```

### 7.3 XML 标签隔离

```go
// internal/security/prompt_guard.go
package security

import (
    "strings"
)

// PromptGuard 提示词守卫 - XML 标签隔离
type PromptGuard struct{}

func (g *PromptGuard) Isolate(source string, content string) string {
    // 根据数据来源添加 XML 标签
    tag := g.getTag(source)
    return fmt.Sprintf("<%s>\n%s\n</%s>", tag, content, tag)
}

func (g *PromptGuard) getTag(source string) string {
    switch source {
    case "user_input":
        return "user_input"
    case "memory":
        return "memory_context"
    case "search":
        return "search_results"
    case "tool_output":
        return "tool_output"
    default:
        return "unknown"
    }
}

// BuildSafePrompt 构建安全的 Prompt
func (g *PromptGuard) BuildSafePrompt(systemPrompt string, userInput string, memory string, search string) string {
    prompt := fmt.Sprintf(`<system>
%s
</system>

<user_input>
%s
</user_input>

<memory_context>
%s
</memory_context>

<search_results>
%s
</search_results>`,
        systemPrompt,
        userInput,
        memory,
        search,
    )
    return prompt
}
```

---

## 8. 接口预留清单（Phase 1 定义，Phase 2/3 实现）

| 接口 | Phase 1 | Phase 2 | Phase 3 | 说明 |
|------|---------|---------|---------|------|
| `IConfigManager` | ✅ 完整实现 | | | 配置管理 |
| `IMemorySystem` | ✅ 完整实现 | | | 记忆系统 |
| `IKnowledgeBase` | ✅ 完整实现 | | | 知识库 |
| `IContextManager` | ✅ 基础截断 | 摘要压缩 | 智能压缩 | 上下文窗口管理 |
| `IModelProvider` | ✅ 完整实现 | | | 模型抽象 |
| `ISkillRegistry` | ✅ 完整实现 | | | Skill 注册/版本/依赖 |
| `ITaskManager` | ✅ 完整实现 | 并发控制 | 高级调度 | 任务生命周期 |
| `IEventBus` | InMemory | | Redis Pub/Sub | 事件总线 |
| `IExecutionRecovery` | ✅ 完整实现 | | | 错误恢复 |
| `ISandbox` | LocalSandbox | | DockerSandbox | 执行环境 |
| `IStorage` | ✅ 完整实现 | | 云存储 | 存储抽象 |
| `IObservability` | ConsoleObserver | | Langfuse/Prometheus | 可观测性 |

---

*本文档基于 PRD 设计，所有接口和模块均经过 grill-me 确认。*
