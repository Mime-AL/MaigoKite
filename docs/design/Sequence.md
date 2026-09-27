# NanamiGopher 关键时序

> **状态**：Derived
> **来源**：[SystemDesign](SystemDesign.md)、[BackendDesign](BackendDesign.md)、[API](API.md)
> **最后核验**：2026-09-18

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
    UI->>G: POST conversation/messages
    G->>G: Authenticate + AccessPolicy
    G->>P: gRPC ProcessMessage(request)
    P->>DB: 创建 Message 与 Task
    P->>DB: append task.started，分配 event_id/sequence
    P-->>G: gRPC event stream
    G-->>UI: 202 Accepted(task_id)
    G-->>UI: WebSocket task.started（沿用持久 ID/sequence）
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

## 3.1 Browser Tool 调用

```mermaid
sequenceDiagram
    participant E as ExecutionEngine
    participant P as ToolPolicy
    participant B as BrowserRuntime
    participant C as Chromium

    E->>P: evaluate browser action + target/path
    alt open/snapshot 可自动执行
        P-->>E: allow
    else fill/click/press 需要批准
        P-->>E: approval_required
    end
    E->>B: action(session_id, arguments)
    B->>B: 校验公开 HTTP(S) / Workspace 截图路径
    B->>C: Playwright command
    C-->>B: 页面状态
    B-->>E: 结构化快照/结果
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

## 5. Skill 发现（Current）

```mermaid
sequenceDiagram
    participant C as Agent Core
    participant F as Skill Directories
    participant R as SkillRegistry
    participant UI as Client

    C->>F: 扫描 */SKILL.md
    C->>C: 校验路径、大小和 YAML metadata
    C->>R: 注册 instruction/workflow Skill
    C->>R: 注册 skill list/read Tool
    UI->>C: GET skills（经 Gateway）
    C-->>UI: 实际加载清单
```

安装、签名、版本回滚和 Workspace Grant 属于 Planned，不得从此 Current 流程推断已经实现。

## 6. Memory 检索（Planned）

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
    UI->>G: GET conversation events/history?after=sequence
    G->>P: ListTaskEvents
    P-->>G: persisted events
    G-->>UI: replay and rebuild activity
    UI->>G: WebSocket connect
    G-->>UI: live events with the same durable IDs
```

当前客户端在 WebSocket 建立后按最后 sequence 再补拉一次，并按 event ID 去重，因此普通连接窗口可恢复。历史读取与订阅仍不是服务端原子操作，且单页上限为 1000；目标协议是连接携带 `after_sequence`，由 Gateway 分页补发后注册实时订阅。

Core 重启时：具备持久 continuation 且不依赖易失资源的 `waiting_approval` 保持等待；Browser session 相关审批会被拒绝并转为 `interrupted`。其他非终态任务若没有安全 continuation，也转为 `interrupted` 并产生事件。

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
    E->>E: 标记 cancellation token
    P->>P: Task / pending Approval / ToolCall → cancelled
    P-->>G: task.cancelled
    G-->>UI: event
```

模型流和原生 Tool 在边界检查取消。第三方 MCP 是否能立即中止取决于其 transport/实现；完整取消与超时契约仍是 Phase 1 发布阻塞项。
