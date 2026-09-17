# NanamiGopher 组件图

> **状态**：Derived
> **来源**：[SystemDesign.md](SystemDesign.md)
> **最后核验**：2026-09-14

本文档只提供总体架构的图形视图；职责和约束以 SystemDesign 与 ADR 为准。

## 1. 逻辑组件

```mermaid
flowchart TB
    subgraph Client[客户端]
        Vue[Vue UI]
        Electron[Electron Host]
    end

    subgraph Edge[Go API Gateway]
        REST[REST]
        WS[WebSocket]
        Auth[Authentication]
        Access[AccessPolicy]
        GRPCClient[gRPC Client]
    end

    subgraph Core[Python Agent Core]
        Session[Session Service]
        Task[TaskManager]
        Engine[ExecutionEngine]
        ToolPolicy[ToolPolicy]
        Registry[ToolRegistry]
        Memory[Memory System]
        Knowledge[Knowledge Base]
        Model[Model Router]
        Event[EventBus]
        MCPClient[MCP Client]
    end

    subgraph Tools[工具]
        Native[Native Tools]
        MCP[MCP Servers]
    end

    subgraph Storage[存储]
        DB[(Relational DB)]
        Blob[(Document Store)]
        Index[(FTS / Vector Index)]
        Secret[(Credential Provider)]
    end

    Vue --> REST
    Vue <--> WS
    Electron --> Vue
    REST --> Auth --> Access --> GRPCClient
    GRPCClient --> Session
    GRPCClient --> Task
    Task --> Engine --> ToolPolicy --> Registry
    Registry --> Native
    Registry --> MCPClient --> MCP
    Engine --> Memory
    Engine --> Knowledge
    Engine --> Model
    Engine --> Event --> WS
    Session --> DB
    Task --> DB
    Memory --> DB
    Knowledge --> Blob
    Knowledge --> Index
    MCPClient -. scoped secret .-> Secret
```

## 2. 桌面部署

```mermaid
flowchart TB
    Electron[Electron Supervisor]
    Electron --> Renderer[Vue Renderer]
    Electron --> Go[Go Gateway]
    Electron --> Python[Python Agent Core]
    Go -->|gRPC| Python
    Python --> MCP[MCP child processes]
    Python --> SQLite[(SQLite)]
    Python --> LocalIndex[(Local vector/FTS index)]
```

## 3. 服务器部署

```mermaid
flowchart LR
    Browser --> Ingress --> Go[Go Gateway]
    Go -->|authenticated gRPC| Python[Python Agent Core]
    Python --> MCP[MCP Workers]
    Python --> DB[(PostgreSQL)]
    Python --> Index[(Vector Index)]
    Go --> Identity[OIDC/JWT Provider]
    Python -. secret reference .-> Vault[Vault/KMS]
```

## 4. 依赖约束

- UI 只依赖公开 API 和事件契约。
- Go 不依赖具体 Tool 或 MCP Server 实现。
- Python ToolRegistry 是所有工具调用的唯一入口。
- MCP Server 不直接访问业务数据库。
- 派生索引不拥有原始文档或消息。
