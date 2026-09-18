# NanamiGopher 关键时序

> **状态**：Derived
> **来源**：[SystemDesign](SystemDesign.md)、[BackendDesign](BackendDesign.md)、[API](API.md)
> **最后核验**：2026-09-14

时序图不单独定义 endpoint、字段或权限矩阵。

## 1. 发送消息

```mermaid
sequenceDiagram
    actor U as User
    participant UI as Vue UI
    participant G as Go Gateway
    participant P as Python Agent Core
    participant DB as Repository

    U->>UI: 发送消息
    UI->>G: POST conversation/messages + Idempotency-Key
    G->>G: Authenticate + AccessPolicy
    G->>P: gRPC SendMessage(CallContext, request)
    P->>DB: 创建 Message、Task、OutboxEvent
    DB-->>P: commit
    P-->>G: task_id
    G-->>UI: 202 Accepted
    P-->>G: gRPC event stream
    G-->>UI: WebSocket task.started
    opt 模型需要工具或子 Agent
        G-->>UI: reasoning/tool/subagent 活动事件
        UI->>UI: 更新任务活动流，不写入消息气泡
    end
    G-->>UI: WebSocket message.delta/completed
    UI->>UI: 在活动流后渲染最终回复
```

`message.*` 只表示面向用户的回答；模型主动给出的过程说明、工具调用和子 Agent 生命周期分别使用 `reasoning.*`、`tool.*`、`subagent.*`。隐藏思维链不进入事件或界面。

## 2. Native Tool 调用

```mermaid
sequenceDiagram
    participant E as ExecutionEngine
    participant R as ToolRegistry
    participant P as ToolPolicy
    participant T as NativeTool
    participant DB as Repository

    E->>R: resolve(tool_name)
    R-->>E: NativeTool
    E->>P: validate + normalize + allowlist + evaluate
    P-->>E: allow
    E-->>E: 发布 tool.started
    E->>T: execute(context, normalized_args)
    T-->>E: ToolResult
    E->>DB: 保存 ToolCall 状态与事件
```

## 3. MCP Tool 调用

```mermaid
sequenceDiagram
    participant E as ExecutionEngine
    participant R as ToolRegistry
    participant P as ToolPolicy
    participant C as Python MCPClient
    participant S as MCP Server

    E->>R: resolve(tool_name)
    R-->>E: MCPTool
    E->>P: validate + normalize + allowlist + evaluate
    P-->>E: allow
    E->>C: call_tool(server, tool, args)
    C->>S: tools/call over stdio
    S-->>C: MCP result
    C-->>E: ToolResult
```

## 4. 审批

```mermaid
sequenceDiagram
    participant E as ExecutionEngine
    participant DB as Repository
    participant G as Go Gateway
    participant UI as Vue UI

    E->>DB: 创建 Approval，Task/ToolCall → waiting
    E-->>G: task.waiting_approval
    E-->>G: approval.requested
    G-->>UI: WebSocket 通知
    UI->>G: POST approvals/{id}/decision
    G->>G: AccessPolicy
    G->>E: gRPC DecideApproval
    E->>DB: 校验版本、参数 hash、范围、过期时间
    E->>DB: 同事务消费审批并转换任务状态
    E-->>G: approval.decided
    E-->>G: tool.started（仅 allow 后）
    G-->>UI: WebSocket/REST 结果
```

### 4.1 会话模型与速度选择

```mermaid
sequenceDiagram
    participant UI as Vue UI
    participant G as Go Gateway
    participant C as Agent Core
    participant DB as Repository
    participant K as CredentialStore

    UI->>G: PATCH conversation {model_id, response_mode}
    G->>C: UpdateConversationSettings
    C->>DB: 校验 Workspace 模型并持久化会话选择
    UI->>G: POST message
    G->>K: 读取 model-profile.{id}
    G->>C: 同步当前模型凭证并 ProcessMessage
    C->>DB: 读取会话模型与速度档
    C->>C: 构造 Provider 与统一输出预算
```

### 4.2 Workspace 文件与 Diff

文件树、内容预览和 Git Diff 均为 Gateway 只读查询。变更列表只读取一次 Git 状态，用户选中文件后再按需生成该文件 Diff。Gateway 在访问文件系统或执行只读 Git 命令前，先完成 Workspace AccessPolicy 和根目录路径解析；渲染进程不获得 Node 文件系统或 Shell 能力。

## 5. Skill 导入与安装

```mermaid
sequenceDiagram
    participant UI as Client
    participant G as Gateway
    participant P as SkillService
    participant M as MCPManager
    participant S as MCP Server

    UI->>G: skills:import 或 skills:install
    G->>P: gRPC command
    P->>P: 验证来源、hash、manifest、依赖和能力请求
    P-->>UI: 权限预览/确认
    P->>P: 创建 SkillVersion 与 SkillGrant
    P->>M: start(grant)
    M->>S: 启动最小环境进程
    M->>S: initialize + tools/list
    S-->>M: capabilities + tools
    M->>P: 注册 MCPTool
```

## 6. Memory 检索

```mermaid
sequenceDiagram
    participant E as ExecutionEngine
    participant WM as WorkingMemory
    participant CM as ConversationMemory
    participant UM as UserMemory
    participant KB as KnowledgeBase

    E->>WM: 当前任务临时上下文
    E->>CM: 最近消息与摘要
    E->>UM: Workspace/用户相关记忆
    E->>KB: 按需检索外部文档
    WM-->>E: working context
    CM-->>E: messages + summaries
    UM-->>E: attributed memories
    KB-->>E: cited chunks
```

## 7. 断线与恢复

```mermaid
sequenceDiagram
    participant UI as Client
    participant G as Gateway
    participant P as Agent Core

    G--xUI: WebSocket 断开
    Note over P: Task 继续运行
    UI->>G: GET task snapshot
    G->>P: GetTask
    P-->>G: authoritative state
    G-->>UI: snapshot
    UI->>G: WebSocket connect after=last_sequence
    G-->>UI: replay missing events
```

## 8. 取消

```mermaid
sequenceDiagram
    participant UI as Client
    participant G as Gateway
    participant P as TaskManager
    participant E as ExecutionEngine
    participant M as MCPClient

    UI->>G: task:cancel
    G->>P: CancelTask
    P->>E: cancellation signal
    E->>M: cancel/terminate active MCP call
    P->>P: Task → cancelled
    P-->>G: task.cancelled
    G-->>UI: event
```
