# NanamiGopher 系统时序图

> 本文档描述了 NanamiGopher 系统中各组件之间的交互时序，涵盖消息处理、工具调用、事件推送、SubAgent 编排、Skill 安装、记忆检索、工作流执行和错误恢复等核心流程。

---

## SEQ-01: 用户发送消息到收到回复的完整流程

```mermaid
sequenceDiagram
    autonumber
    participant U as 用户
    participant FE as Vue 3 前端<br/>(Electron)
    participant GW as Go API Gateway<br/>(:8080)
    participant PY as Python Agent Core<br/>(:8081)
    participant TOOL as Tool
    participant MEM as MemorySystem
    participant LLM as LLM Provider

    U->>FE: 输入消息并发送
    FE->>GW: POST /api/v1/messages {text, conversation_id}
    GW->>GW: PermissionManager 鉴权
    GW->>PY: gRPC TaskManager.create_task()
    PY->>PY: TaskManager 创建任务
    PY->>MEM: MemorySystem.retrieve_context(conversation_id)
    MEM-->>PY: 返回上下文摘要
    PY->>LLM: Chat API (qwen2.5/gpt-4o/claude)
    Note over LLM: 携带系统提示词 + 上下文 + 工具定义
    LLM-->>PY: {content, tool_calls[]}
    alt 需要调用工具
        loop 每个 tool_call
            PY->>TOOL: ExecutionEngine.execute(tool_name, args)
            TOOL-->>PY: ToolResult
            PY->>PY: EventBus.publish("tool.called")
        end
        PY->>LLM: 将 ToolResult 作为上下文再次请求
        LLM-->>PY: 最终回复文本
    else 直接回复
        LLM-->>PY: 回复文本
    end
    PY->>PY: TaskManager 更新任务状态
    PY->>GW: gRPC stream: chunk{role, content, tool_result?}
    Note over GW: EventStream WebSocket 转发
    GW-->>FE: WebSocket: {type: "message_chunk", data}
    FE-->>U: 渲染回复内容
    PY->>PY: EventBus.publish("task.completed")
```

---

## SEQ-02: 工具调用流程

```mermaid
sequenceDiagram
    autonumber
    participant EE as ExecutionEngine
    participant PM as PermissionManager
    participant TOOL as Tool.execute()
    participant SANDBOX as Sandbox
    participant RESULT as ToolResult/Stream
    participant EB as EventBus

    EE->>PM: check_permission(tool_name, action)
    alt L1 低危 (file_read, web_search)
        PM-->>EE: ALLOW
    else L2-L3 中等 (bash, file_write)
        PM-->>EE: MANUAL (等待用户确认)
        Note over EE: 等待用户批准
        EE->>EE: 用户批准后继续
    else L4-L5 高危 (系统级操作)
        PM-->>EE: REJECT / AUTO_APPROVE (AcceptEdits 模式)
    end
    EE->>TOOL: execute(args, context)
    TOOL->>SANDBOX: 沙箱环境初始化
    alt 流式输出 (bash)
        TOOL->>RESULT: ToolResultStream.write(chunk)
        RESULT-->>EE: 实时推送 chunk
    else 同步返回 (file_read, grep)
        TOOL->>RESULT: ToolResult(status, output, error?)
        RESULT-->>EE: 返回完整结果
    end
    TOOL->>SANDBOX: 清理沙箱资源
    EE->>EB: publish("tool.called", {tool, duration, status})
    RESULT-->>EE: 返回给调用方
```

---

## SEQ-03: WebSocket 事件推送流程

```mermaid
sequenceDiagram
    autonumber
    participant FE as 前端 Inspector
    participant GW as Go API Gateway
    participant EB as Python EventBus
    participant PY as Python Agent Core

    FE->>GW: WebSocket 连接 /ws/inspector?token=xxx
    GW->>GW: 验证 token，建立订阅
    GW-->>FE: 101 Switching Protocols

    loop 持续监听
        PY->>EB: publish(event_type, payload)
        alt event.type == "task.started"
            EB->>GW: 推送 task.started
            GW-->>FE: {event: "task.started", data: {task_id}}
        else event.type == "tool.called"
            EB->>GW: 推送 tool.called
            GW-->>FE: {event: "tool.called", data: {tool, args, status}}
        else event.type == "llm.token"
            EB->>GW: 推送 llm.token (流式)
            GW-->>Fe: {event: "llm.token", data: {token, cumulative}}
        else event.type == "task.completed"
            EB->>GW: 推送 task.completed
            GW-->>FE: {event: "task.completed", data: {task_id, result}}
        else event.type == "task.failed"
            EB->>GW: 推送 task.failed
            GW-->>FE: {event: "task.failed", data: {task_id, error}}
        end
    end
```

---

## SEQ-04: SubAgent 并行执行流程

```mermaid
sequenceDiagram
    autonumber
    participant MAIN as 主 Agent
    participant SA1 as SubAgent #1
    participant SA2 as SubAgent #2
    participant SA3 as SubAgent #n
    participant AGG as 流式聚合器
    participant UI as 前端 (折叠卡片)

    MAIN->>MAIN: 分析任务，拆分为子任务
    MAIN->>SA1: 创建 SubAgent (共享上下文)
    MAIN->>SA2: 创建 SubAgent (共享上下文)
    MAIN->>SA3: 创建 SubAgent (共享上下文)
    
    par 并行执行
        SA1->>SA1: 执行子任务 A
        SA2->>SA2: 执行子任务 B
        SA3->>SA3: 执行子任务 C
    end

    loop 流式输出
        SA1-->>AGG: stream chunk A
        SA2-->>AGG: stream chunk B
        SA3-->>AGG: stream chunk C
    end

    AGG->>UI: 实时更新折叠卡片
    Note over UI: 每个 SubAgent 对应一个可展开卡片

    par 等待完成
        SA1-->>MAIN: 完成子任务 A
        SA2-->>MAIN: 完成子任务 B
        SA3-->>MAIN: 完成子任务 C
    end

    MAIN->>MAIN: 汇总所有 SubAgent 结果
    MAIN-->>AGG: 最终聚合结果
    AGG-->>UI: 展示完整回答
```

---

## SEQ-05: Skill 安装流程

```mermaid
sequenceDiagram
    autonumber
    participant U as 用户
    participant FE as 前端
    participant GW as Go API Gateway
    participant SR as SkillRegistry
    participant MCP as MCP Server Manager
    participant SKILL as MCP Server (外部)

    U->>FE: 浏览/搜索可用 Skill
    FE->>GW: GET /api/v1/skills
    GW->>SR: list_skills()
    SR-->>GW: [SkillMetadata]
    GW-->>FE: Skill 列表
    U->>FE: 选择并安装 Skill
    FE->>GW: POST /api/v1/skills/install {name, version}
    GW->>SR: register_skill(skill_config)
    SR->>SR: 解析 SKILL.md / skill.json
    SR->>SR: 验证依赖和权限要求
    SR-->>GW: 注册成功
    GW->>MCP: start_mcp_server(name, command, args)
    MCP->>SKILL: 启动 MCP Server (stdio)
    MCP->>SKILL: MCP initialize() 握手
    SKILL-->>MCP: {capabilities, tools[]}
    MCP->>MCP: 缓存工具定义到 SkillRegistry
    MCP-->>GW: MCP Server 已启动
    GW-->>FE: 安装成功
    FE-->>U: 显示已安装的 Skill 列表
```

---

## SEQ-06: 记忆检索流程

```mermaid
sequenceDiagram
    autonumber
    participant AGENT as Agent Core
    participant MS as MemorySystem
    participant STM as ShortTermMemory
    participant CTX as ConversationMemory
    participant USR as UserMemory
    participant KB as KnowledgeBase
    participant DB as SQLite + FTS5
    participant VDB as VectorStore (ChromaDB)

    AGENT->>MS: retrieve_context(conversation_id, user_id)
    
    MS->>STM: get_recent(conversation_id, limit=20)
    STM->>DB: SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at DESC LIMIT 20
    DB-->>STM: 最近消息列表
    STM-->>MS: 短期记忆 (最近 N 条消息)

    MS->>CTX: get_conversation_summary(conversation_id)
    CTX->>DB: 从对话中提取关键信息
    CTX-->>MS: 对话摘要

    MS->>USR: get_user_profile(user_id)
    USR->>DB: SELECT * FROM user_preferences WHERE user_id=?
    USR-->>MS: 用户偏好和习惯

    MS->>KB: search_knowledge(query, top_k=5)
    KB->>VDB: vector_search(embedding(query))
    VDB-->>KB: 相似文档 ID 列表
    KB->>DB: 获取文档全文 (FTS5 全文检索)
    DB-->>KB: 相关文档内容
    KB-->>MS: 知识检索结果

    MS-->>AGENT: {short_term, conversation_summary, user_profile, knowledge}
```

---

## SEQ-07: 工作流执行流程

```mermaid
sequenceDiagram
    autonumber
    participant USER as 用户
    participant AGENT as Agent Core
    participant WF as 工作流引擎
    participant SKILL as SKILL.md Parser
    participant LG as LangGraph
    participant MCP as MCP 原子工具
    participant STORE as 存储

    USER->>AGENT: 触发工作流 (e.g., "部署应用")
    AGENT->>SKILL: parse_skill("deploy-app/SKILL.md")
    SKILL-->>AGENT: 工作流定义 (nodes + edges)
    AGENT->>WF: 创建工作流实例
    WF->>LG: build_graph(workflow_definition)
    LG-->>WF: 构建完成的状态图
    
    loop 工作流节点执行
        WF->>LG: execute_node(node_id, state)
        alt node 需要外部工具
            LG->>MCP: call_tool(tool_name, params)
            MCP-->>LG: tool_result
        else node 是条件判断
            LG->>LG: evaluate_condition(state)
        else node 是代码执行
            LG->>STORE: save_intermediate_state(state)
            LG->>LG: run_code_block(state)
        end
        LG-->>WF: node_result + updated_state
    end

    WF->>STORE: finalize_workflow(workflow_id, final_state)
    STORE-->>WF: 持久化结果
    WF-->>AGENT: 工作流完成
    AGENT-->>USER: 返回工作流执行结果
```

---

## SEQ-08: 错误恢复流程

```mermaid
sequenceDiagram
    autonumber
    participant EE as ExecutionEngine
    participant TOOL as Tool
    participant RE as ExecutionRecovery
    participant PM as PermissionManager
    participant AGENT as Agent Core

    TOOL->>EE: execute() 返回异常
    alt 临时错误 (超时、网络中断)
        EE->>RE: classify_error(TOOL_TIMEOUT)
        RE->>RE: retry(max_retries=3, delay=exponential_backoff)
        loop 重试
            RE->>TOOL: execute() (第 N 次重试)
            alt 成功
                TOOL-->>RE: 正常结果
                RE-->>EE: 重试成功
            else 仍然失败
                TOOL-->>RE: 异常
            end
        end
    else 权限不足
        EE->>RE: classify_error(PERMISSION_DENIED)
        RE->>PM: request_elevated_permission(tool, action)
        PM-->>RE: APPROVED / REJECTED
        alt 批准
            RE->>TOOL: execute() (重新执行)
            TOOL-->>RE: 正常结果
        else 拒绝
            RE-->>EE: 权限被拒绝
        end
    else 数据损坏 / 不可恢复
        EE->>RE: classify_error(DATA_CORRUPTION)
        RE->>RE: fallback_strategy()
        alt 有回滚点
            RE->>RE: rollback_to_checkpoint()
            RE->>TOOL: execute() (从检查点恢复)
        else 有替代方案
            RE->>RE: select_alternative_tool()
            RE->>ALTERNATIVE: execute()
        else 无法恢复
            RE-->>AGENT: TASK_FAILED (附带错误详情)
            AGENT->>AGENT: 通知用户 + 建议手动处理
        end
    else 跳过策略
        RE->>RE: skip_with_warning()
        RE-->>EE: WARNING (继续后续步骤)
    end
```

---

## 附录：事件类型速查

| 事件名称 | 来源 | 用途 |
|---------|------|------|
| `task.started` | TaskManager | 通知前端任务已开始 |
| `tool.called` | ExecutionEngine | 记录工具调用详情 |
| `llm.token` | LLM Stream | 实时流式推送 Token |
| `task.completed` | TaskManager | 任务完成通知 |
| `task.failed` | ExecutionRecovery | 任务失败通知 |
| `permission.requested` | PermissionManager | 权限审批请求 |
| `skill.installed` | SkillRegistry | Skill 安装完成 |
| `workflow.node.executed` | LangGraph | 工作流节点执行记录 |
