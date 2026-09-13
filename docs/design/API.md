# NanamiGopher 接口文档

> **版本**: v1.1  
> **日期**: 2026-07-15  
> **协议**: REST API + gRPC + WebSocket + MCP

---

## 1. API 概览

| 协议 | 用途 | 端口 | 说明 |
|------|------|------|------|
| REST API | 会话/记忆/Skill 管理 | 8080 | Go API Gateway |
| gRPC | Agent 控制 | 8081 | Go ↔ Python |
| WebSocket | 流式响应 | 8080 | 前端 ↔ Go |
| MCP stdio | 工具调用 | N/A | Python ↔ MCP Server |

---

## 2. REST API (Go API Gateway)

### 2.1 会话管理

#### 创建新对话

```
POST /api/v1/sessions
Content-Type: application/json

{
  "title": "新项目分析",
  "model_id": "gpt-4o",
  "permission_mode": "manual"
}

Response 201:
{
  "id": "sess_20260715_001",
  "title": "新项目分析",
  "created_at": "2026-07-15T10:00:00Z",
  "updated_at": "2026-07-15T10:00:00Z"
}
```

#### 列出所有对话

```
GET /api/v1/sessions

Response 200:
{
  "sessions": [
    {
      "id": "sess_20260715_001",
      "title": "新项目分析",
      "created_at": "2026-07-15T10:00:00Z",
      "is_archived": false
    }
  ]
}
```

#### 获取对话详情

```
GET /api/v1/sessions/:id

Response 200:
{
  "id": "sess_20260715_001",
  "title": "新项目分析",
  "created_at": "2026-07-15T10:00:00Z",
  "updated_at": "2026-07-15T10:00:00Z",
  "is_archived": false,
  "permission_mode": "manual",
  "model_id": "gpt-4o",
  "message_count": 15
}
```

#### 删除对话

```
DELETE /api/v1/sessions/:id

Response 204: No Content
```

#### 切换对话

```
POST /api/v1/sessions/:id/switch

Response 200:
{
  "id": "sess_20260715_001",
  "title": "新项目分析",
  "switched_at": "2026-07-15T10:05:00Z"
}
```

### 2.2 消息交互

#### 发送消息

```
POST /api/v1/sessions/:id/messages
Content-Type: application/json

{
  "content": "帮我分析一下这个项目的依赖关系",
  "attachments": [
    {
      "type": "file",
      "path": "/path/to/package.json"
    }
  ]
}

Response 202:
{
  "message_id": "msg_001",
  "status": "processing"
}
```

#### 流式响应（WebSocket）

```
WS /api/v1/sessions/:id/stream

连接成功后接收事件:

// 步骤开始
{"type": "step_start", "data": {"step": "reading_file", "status": "running"}}

// 步骤完成
{"type": "step_complete", "data": {"step": "reading_file", "status": "completed"}}

// 消息片段（流式输出）
{"type": "message_chunk", "data": {"content": "好的，让我来分析一下..."}}

// 错误
{"type": "error", "data": {"level": "P1", "code": "TOOL_FAILED", "message": "文件读取失败", "suggestion": "请检查文件路径"}}
```

### 2.3 记忆管理

#### 列出记忆

```
GET /api/v1/memories?type=favorite&tag=python&page=1&per_page=20

Response 200:
{
  "memories": [
    {
      "id": "mem_001",
      "type": "preference",
      "content": "用户偏好使用 Python 进行后端开发",
      "tags": ["python", "backend"],
      "importance_score": 0.8,
      "is_pinned": true,
      "created_at": "2026-07-15T10:00:00Z"
    }
  ],
  "total": 42,
  "page": 1,
  "per_page": 20
}
```

#### 搜索记忆

```
POST /api/v1/memories/search
Content-Type: application/json

{
  "query": "Python 后端开发",
  "type": "preference",
  "tags": ["python"],
  "top_k": 10,
  "use_vector_search": true
}

Response 200:
{
  "results": [
    {
      "id": "mem_001",
      "content": "用户偏好使用 Python 进行后端开发",
      "similarity": 0.95,
      "type": "preference"
    }
  ]
}
```

#### 更新记忆

```
PUT /api/v1/memories/:id
Content-Type: application/json

{
  "content": "用户偏好使用 Python 和 Go 进行后端开发",
  "tags": ["python", "go", "backend"],
  "is_pinned": true
}

Response 200:
{
  "id": "mem_001",
  "updated_at": "2026-07-15T10:05:00Z"
}
```

#### 批量删除

```
DELETE /api/v1/memories/batch
Content-Type: application/json

{
  "ids": ["mem_001", "mem_002", "mem_003"]
}

Response 200:
{
  "deleted_count": 3
}
```

### 2.4 Skill 管理

#### 列出所有 Skill

```
GET /api/v1/skills?namespace=builtin

Response 200:
{
  "skills": [
    {
      "id": "skill_001",
      "name": "web-search",
      "version": "1.0.0",
      "description": "通过网络搜索获取实时信息",
      "namespace": "builtin",
      "permission_level": 2,
      "is_active": true
    }
  ]
}
```

#### 导入 Skill

```
POST /api/v1/skills/import
Content-Type: multipart/form-data

file: SKILL.md
mode: self_contained  // 或 directory

Response 201:
{
  "id": "skill_002",
  "name": "data-analysis",
  "version": "1.0.0",
  "status": "imported"
}
```

#### 卸载 Skill

```
DELETE /api/v1/skills/:id

Response 204: No Content
```

#### 查看 Skill 依赖

```
GET /api/v1/skills/:id/deps

Response 200:
{
  "skill_name": "data-analysis",
  "dependencies": [
    {
      "name": "file-reader",
      "version": "1.0.0",
      "installed": true
    },
    {
      "name": "code-executor",
      "version": "1.0.0",
      "installed": true
    },
    {
      "name": "visualization",
      "version": "1.0.0",
      "installed": false
    }
  ]
}
```

### 2.5 权限管理

#### 获取当前权限配置

```
GET /api/v1/permissions

Response 200:
{
  "current_mode": "manual",
  "modes": [
    {"name": "manual", "is_default": true},
    {"name": "accept_edits", "is_default": false},
    {"name": "plan", "is_default": false},
    {"name": "auto", "is_default": false}
  ],
  "circuit_breaker": {
    "enabled": true,
    "blocked_patterns": ["rm -rf /", "dd if="]
  }
}
```

#### 更新权限配置

```
PUT /api/v1/permissions
Content-Type: application/json

{
  "default_mode": "accept_edits",
  "circuit_breaker": {
    "enabled": true,
    "blocked_patterns": ["rm -rf /"]
  }
}

Response 200:
{
  "updated_at": "2026-07-15T10:05:00Z"
}
```

#### 切换权限模式

```
POST /api/v1/permissions/mode
Content-Type: application/json

{
  "mode": "auto"
}

Response 200:
{
  "previous_mode": "manual",
  "current_mode": "auto",
  "switched_at": "2026-07-15T10:05:00Z"
}
```

### 2.6 凭证管理

凭证采用通用 CRUD 模型，通过 `type` 字段区分用途（`model` / `search` / `custom`）。凭证明文仅写入 OS 密钥链，API 层不回传 `api_key`。

#### 创建凭证

```
POST /api/v1/credentials
Content-Type: application/json

{
  "type": "model",
  "service": "openai",
  "api_key": "sk-xxxxx"
}

Response 201:
{
  "id": "cred_001",
  "type": "model",
  "service": "openai",
  "configured": true,
  "validated": true,
  "created_at": "2026-07-15T10:00:00Z"
}
```

```
POST /api/v1/credentials
Content-Type: application/json

{
  "type": "search",
  "service": "tavily",
  "api_key": "tvly-xxxxx"
}

Response 201:
{
  "id": "cred_002",
  "type": "search",
  "service": "tavily",
  "configured": true,
  "validated": true,
  "created_at": "2026-07-15T10:01:00Z"
}
```

#### 列出凭证

```
GET /api/v1/credentials?type=model

Response 200:
{
  "items": [
    {
      "id": "cred_001",
      "type": "model",
      "service": "openai",
      "configured": true,
      "validated": true
    },
    {
      "id": "cred_003",
      "type": "model",
      "service": "anthropic",
      "configured": true,
      "validated": false
    }
  ],
  "total": 2
}
```

`type` 为可选过滤参数，取值 `model` / `search` / `custom`；省略时返回全部凭证。

#### 查询单个凭证

```
GET /api/v1/credentials/cred_001

Response 200:
{
  "id": "cred_001",
  "type": "model",
  "service": "openai",
  "configured": true,
  "validated": true,
  "created_at": "2026-07-15T10:00:00Z",
  "updated_at": "2026-07-15T10:05:00Z"
}
```

#### 更新凭证

```
PUT /api/v1/credentials/cred_001
Content-Type: application/json

{
  "api_key": "sk-new-key"
}

Response 200:
{
  "id": "cred_001",
  "type": "model",
  "service": "openai",
  "configured": true,
  "validated": true,
  "updated_at": "2026-07-15T10:05:00Z"
}
```

#### 删除凭证

```
DELETE /api/v1/credentials/cred_001

Response 204: No Content
```

### 2.7 模型管理

#### 列出可用模型

```
GET /api/v1/models

Response 200:
{
  "models": [
    {
      "id": "gpt-4o",
      "name": "GPT-4o",
      "provider": "openai",
      "type": "chat",
      "is_available": true,
      "cost_per_token": 0.00003
    },
    {
      "id": "claude-sonnet-4",
      "name": "Claude Sonnet 4",
      "provider": "anthropic",
      "type": "chat",
      "is_available": true,
      "cost_per_token": 0.000003
    },
    {
      "id": "ollama:qwen2.5:32b",
      "name": "Qwen2.5 32B",
      "provider": "ollama",
      "type": "chat",
      "is_available": true,
      "cost_per_token": 0
    }
  ]
}
```

#### 触发模型路由决策

```
POST /api/v1/models/route
Content-Type: application/json

{
  "task_type": "coding",
  "complexity": "standard",
  "prefer_local": true
}

Response 200:
{
  "selected_model": "ollama:qwen2.5:32b",
  "reason": "Local model preferred for coding task",
  "fallback_models": ["gpt-4o", "claude-sonnet-4"]
}
```

### 2.8 审批相关

#### 创建审批请求

```
POST /api/v1/approvals
Content-Type: application/json

{
  "action": "send_messages",
  "preview": {
    "jobs": [...],
    "message_template": "您好，我对贵司的..."
  },
  "timeout_seconds": 300
}

Response 201:
{
  "request_id": "req_20260715_103000",
  "status": "pending",
  "expires_at": "2026-07-15T10:35:00Z"
}
```

#### 获取审批详情

```
GET /api/v1/approvals/:id

Response 200:
{
  "request_id": "req_20260715_103000",
  "action": "send_messages",
  "status": "pending",
  "preview": {...},
  "expires_at": "2026-07-15T10:35:00Z"
}
```

#### 提交审批决策

```
PUT /api/v1/approvals/:id/decision
Content-Type: application/json

{
  "decision": "approve",
  "selected_jobs": [...],
  "modified_message": null
}

Response 200:
{
  "request_id": "req_20260715_103000",
  "decision": "approve",
  "processed_at": "2026-07-15T10:30:30Z"
}
```

#### 获取审批历史记录

```
GET /api/v1/approvals/history?page=1&per_page=20

Response 200:
{
  "approvals": [
    {
      "request_id": "req_001",
      "action": "send_messages",
      "decision": "approve",
      "processed_at": "2026-07-15T10:30:30Z"
    }
  ],
  "total": 15,
  "page": 1
}
```

### 2.9 接管相关

#### Agent 举手请求接管

```
POST /api/v1/takeovers/raise
Content-Type: application/json

{
  "reason": "captcha_solver_failed",
  "context": {
    "current_node": "node_scrape_page",
    "screenshot": "base64...",
    "attempt_count": 3
  },
  "suggestion": "请手动完成滑块验证"
}

Response 201:
{
  "takeover_id": "tk_20260715_103000",
  "status": "raised",
  "created_at": "2026-07-15T10:30:00Z"
}
```

#### 用户接受接管

```
POST /api/v1/takeovers/:id/accept

Response 200:
{
  "takeover_id": "tk_20260715_103000",
  "status": "accepted",
  "accepted_at": "2026-07-15T10:30:10Z"
}
```

#### 用户释放接管

```
POST /api/v1/takeovers/:id/release

Response 200:
{
  "takeover_id": "tk_20260715_103000",
  "status": "released",
  "released_at": "2026-07-15T10:35:00Z"
}
```

### 2.10 可观测性

#### 获取完整追踪链

```
GET /api/v1/traces/:trace_id

Response 200:
{
  "trace_id": "wf_boss_zhipin_20260715_103000",
  "spans": [
    {
      "span_id": "span_001",
      "operation_name": "node_init_browser",
      "duration_ms": 3200,
      "status": "OK"
    }
  ]
}
```

#### 获取 Span 详情

```
GET /api/v1/traces/:trace_id/spans/:span_id

Response 200:
{
  "span_id": "span_001",
  "operation_name": "playwright.launch",
  "start_time": "2026-07-15T10:30:00Z",
  "end_time": "2026-07-15T10:30:01Z",
  "attributes": {
    "stealth_mode": true,
    "session_id": "bz_1784045621"
  }
}
```

#### 手动运行基准测试

```
POST /api/v1/benchmarks/run

Response 202:
{
  "test_run_id": "bench_001",
  "status": "running"
}
```

#### 获取测试结果

```
GET /api/v1/benchmarks/results/:test_run_id

Response 200:
{
  "test_run_id": "bench_001",
  "status": "completed",
  "results": {
    "total_cases": 12,
    "passed": 12,
    "failed": 0,
    "total_latency_ms": 45200,
    "total_cost_usd": 0.32
  }
}
```

#### 获取性能指标

```
GET /api/v1/metrics

Response 200:
{
  "cpu_usage_percent": 12.5,
  "memory_usage_mb": 256,
  "active_sessions": 3,
  "tokens_used_today": 125000,
  "cost_today_usd": 2.50,
  "error_rate": 0.02
}
```

### 2.11 SubAgent 管理

#### 创建 SubAgent

```
POST /api/v1/sessions/:id/subagents
Content-Type: application/json

{
  "task": "搜索相关知识",
  "parent_context": {
    "session_id": "sess_001",
    "shared_data": { ... }
  }
}

Response 201:
{
  "subagent_id": "sa_20260715_001",
  "status": "created",
  "created_at": "2026-07-15T10:30:00Z"
}
```

#### 获取 SubAgent 状态

```
GET /api/v1/subagents/:id/status

Response 200:
{
  "subagent_id": "sa_20260715_001",
  "status": "streaming",
  "task": "搜索相关知识",
  "created_at": "2026-07-15T10:30:00Z",
  "expires_at": "2026-07-15T10:35:00Z",
  "size_bytes": 1024,
  "is_expired": false
}
```

#### 提交 SubAgent 结果

```
POST /api/v1/subagents/:id/result
Content-Type: application/json

{
  "result": "搜索到 3 篇相关文章..."
}

Response 200:
{
  "subagent_id": "sa_20260715_001",
  "status": "completed",
  "size_bytes": 1024
}
```

#### 销毁 SubAgent

```
DELETE /api/v1/subagents/:id

Response 204: No Content
```

### 2.12 Inspector 监控

#### 获取对话活动卡片列表

```
GET /api/v1/inspector/cards

Response 200:
{
  "cards": [
    {
      "session_id": "sess_001",
      "title": "帮我分析这个项目",
      "status": "running",  // running | completed | failed | paused
      "running_duration_sec": 155,
      "current_step": "正在执行: 搜索相关知识",
      "token_count": 1234,
      "tool_call_count": 3,
      "subagent_count": 2,
      "subagent_running": 1,
      "subagent_completed": 1
    },
    {
      "session_id": "sess_002",
      "title": "帮我搜索最新 AI 新闻",
      "status": "completed",
      "total_duration_sec": 15,
      "token_count": 567,
      "tool_call_count": 2
    },
    {
      "session_id": "sess_003",
      "title": "帮我部署网站",
      "status": "failed",
      "error": "Docker 构建超时",
      "retry_count": 2,
      "token_count": 890,
      "tool_call_count": 4
    }
  ]
}
```

#### 获取对话时间线

```
GET /api/v1/inspector/sessions/:id/timeline?dimensions=task,tool,model,event,error,subagent

Response 200:
{
  "session_id": "sess_001",
  "nodes": [
    {
      "node_id": "sess_001_2026-07-15T10:30:00",
      "node_type": "task",
      "title": "任务开始",
      "status": "running",
      "timestamp": "2026-07-15T10:30:00Z",
      "duration_ms": null,
      "details": { "task_id": "task_001" },
      "children": [
        {
          "node_id": "sess_001_2026-07-15T10:30:01",
          "node_type": "tool",
          "title": "file_reader 读取 package.json",
          "status": "completed",
          "timestamp": "2026-07-15T10:30:01Z",
          "duration_ms": 120,
          "details": {
            "tool_name": "file_reader",
            "arguments": { "path": "package.json" },
            "return_value_length": 2048
          }
        },
        {
          "node_id": "sess_001_2026-07-15T10:30:02",
          "node_type": "model",
          "title": "qwen2.5 调用",
          "status": "completed",
          "timestamp": "2026-07-15T10:30:02Z",
          "duration_ms": 800,
          "details": {
            "model": "qwen2.5:32b",
            "input_tokens": 120,
            "output_tokens": 450,
            "cost_usd": 0.001
          }
        }
      ]
    }
  ]
}
```

#### 获取历史 Inspector 记录

```
GET /api/v1/inspector/history?session_id=sess_002

Response 200:
{
  "session_id": "sess_002",
  "completed_at": "2026-07-15T10:25:00Z",
  "nodes": [ ... ],  // 同 timeline 格式
  "summary": {
    "total_duration_sec": 15,
    "token_count": 567,
    "tool_call_count": 2,
    "error_count": 0,
    "subagent_count": 0
  }
}
```

#### 切换 Inspector 记录保存开关

```
PUT /api/v1/inspector/settings
Content-Type: application/json

{
  "save_history": true  // true: 保存 / false: 不保存
}

Response 200:
{
  "save_history": true,
  "updated_at": "2026-07-15T10:30:00Z"
}
```

---

## 3. gRPC 接口 (Go ↔ Python)

### 3.1 Protobuf 定义

```protobuf
syntax = "proto3";

package nanamigopher.agent.v1;

option go_package = "pkg/proto/agent";

// Agent 服务
service AgentService {
  // 发送消息（流式响应）
  rpc ProcessMessage(ProcessRequest) returns (stream AgentResponse);
  
  // 会话管理
  rpc CreateSession(SessionRequest) returns (SessionResponse);
  rpc SwitchSession(SessionRequest) returns (SessionResponse);
  rpc ListSessions(Empty) returns (SessionListResponse);
  
  // 记忆管理
  rpc SearchMemories(MemorySearchRequest) returns (MemorySearchResponse);
  rpc UpdateMemory(MemoryUpdateRequest) returns (MemoryUpdateResponse);
  
  // 模型路由
  rpc RouteModel(ModelRouteRequest) returns (ModelRouteResponse);
  
  // 权限检查
  rpc CheckPermission(PermissionCheckRequest) returns (PermissionCheckResponse);
}

// 消息请求
message ProcessRequest {
  string session_id = 1;
  string content = 2;
  repeated Attachment attachments = 3;
}

message Attachment {
  string type = 1;  // file, image, url
  string path = 2;
  string url = 3;
}

// 消息响应
message AgentResponse {
  string type = 1;  // step_start, step_complete, message_chunk, error
  StepData step = 2;
  MessageChunk chunk = 3;
  ErrorInfo error = 4;
}

message StepData {
  string step = 1;
  string status = 2;  // running, completed, failed
}

message MessageChunk {
  string content = 1;
}

message ErrorInfo {
  string level = 1;  // P0, P1, P2
  string code = 2;
  string message = 3;
  string suggestion = 4;
  bool retryable = 5;
}

// 会话
message SessionRequest {
  string id = 1;
  string title = 2;
  string model_id = 3;
}

message SessionResponse {
  string id = 1;
  string title = 2;
  string created_at = 3;
  string updated_at = 4;
}

message SessionListResponse {
  repeated SessionResponse sessions = 1;
}

// 记忆搜索
message MemorySearchRequest {
  string query = 1;
  string type = 2;
  repeated string tags = 3;
  int32 top_k = 4;
  bool use_vector_search = 5;
}

message MemorySearchResponse {
  repeated MemoryResult results = 1;
}

message MemoryResult {
  string id = 1;
  string content = 2;
  float similarity = 3;
  string type = 4;
}

// 模型路由
message ModelRouteRequest {
  string task_type = 1;
  string complexity = 2;
  bool prefer_local = 3;
}

message ModelRouteResponse {
  string selected_model = 1;
  string reason = 2;
  repeated string fallback_models = 3;
}

// 权限检查
message PermissionCheckRequest {
  string operation = 1;
  string resource = 2;
}

message PermissionCheckResponse {
  bool allowed = 1;
  string reason = 2;
  string required_level = 3;
}

// 空消息
message Empty {}
```

### 3.2 使用示例

```go
// Go 客户端调用
conn, err := grpc.Dial("localhost:8081", grpc.WithTransportCredentials(insecure.NewCredentials()))
if err != nil {
    log.Fatal(err)
}
defer conn.Close()

client := agent.NewAgentServiceClient(conn)

// 发送消息
stream, err := client.ProcessMessage(context.Background(), &agent.ProcessRequest{
    SessionId: "sess_001",
    Content: "帮我分析一下这个项目的依赖关系",
})
if err != nil {
    log.Fatal(err)
}

// 接收流式响应
for {
    resp, err := stream.Recv()
    if err == io.EOF {
        break
    }
    if err != nil {
        log.Fatal(err)
    }
    
    switch resp.Type {
    case "step_start":
        fmt.Printf("步骤开始: %s\n", resp.Step.Step)
    case "message_chunk":
        fmt.Print(resp.Chunk.Content)
    case "error":
        fmt.Printf("错误: %s\n", resp.Error.Message)
    }
}
```

---

## 4. WebSocket 流式响应

### 4.1 连接方式

```javascript
// 前端连接 WebSocket
const ws = new WebSocket(`ws://localhost:8080/api/v1/sessions/${sessionId}/stream`);

ws.onopen = () => {
  console.log('WebSocket 连接已建立');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch (data.type) {
    case 'step_start':
      showStep(data.data.step, 'running');
      break;
    case 'step_complete':
      showStep(data.data.step, 'completed');
      break;
    case 'message_chunk':
      appendMessage(data.data.content);
      break;
    case 'error':
      showError(data.data.error);
      break;
  }
};

ws.onerror = (error) => {
  console.error('WebSocket 错误:', error);
};

ws.onclose = () => {
  console.log('WebSocket 连接已关闭');
};
```

### 4.2 事件类型

```typescript
interface StreamEvent {
  type: 'step_start' | 'step_complete' | 'step_error' | 'message_chunk' | 'error';
  data: {
    step?: string;        // 步骤标识
    status?: string;      // 进行中/成功/失败
    content?: string;     // 流式输出的文本片段
    error?: ErrorInfo;    // 错误信息
  };
}

interface ErrorInfo {
  level: 'P0' | 'P1' | 'P2';
  code: string;
  message: string;
  suggestion?: string;
  retryable?: boolean;
}

// Inspector 事件类型
interface InspectorEvent {
  type: 'card_update' | 'timeline_node' | 'card_action';
  data: {
    session_id?: string;
    status?: string;
    title?: string;
    node_id?: string;
    node_type?: string;
    details?: Record<string, any>;
    action?: 'pause' | 'resume' | 'stop';
  };
}
```

### 4.3 Inspector 专用 WebSocket 端点

```
WS /api/v1/inspector/ws

连接成功后接收事件:

// 卡片状态更新
{"type": "card_update", "data": {
  "session_id": "sess_001",
  "status": "running",
  "title": "帮我分析这个项目",
  "running_duration_sec": 155,
  "token_count": 1234,
  "tool_call_count": 3
}}

// 时间线节点更新
{"type": "timeline_node", "data": {
  "node_id": "sess_001_2026-07-15T10:30:01",
  "node_type": "tool",
  "title": "file_reader 读取 package.json",
  "status": "completed",
  "duration_ms": 120,
  "details": {"tool_name": "file_reader", "arguments": {"path": "package.json"}}
}}

// 卡片操作响应
{"type": "card_action", "data": {
  "action": "pause",
  "session_id": "sess_001",
  "result": "ok"
}}
```

---

## 5. MCP 协议接口

> **注意**：Phase 1 的前 8 个核心工具（file_read/write/edit, bash, web_search, web_fetch, glob, grep）全部做成**原生工具**（Python 直接实现），不走 MCP。MCP 协议仅用于 Layer 3 的 Skill 工具（browser、ocr、code_executor 等）。

### 5.1 工具发现

```json
// 请求
{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}

// 响应（MCP Server 返回该 Skill 的所有工具）
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "browser_navigate",
        "description": "Navigate to a URL in the browser",
        "inputSchema": {
          "type": "object",
          "properties": {
            "url": {"type": "string"}
          },
          "required": ["url"]
        }
      },
      {
        "name": "browser_click",
        "description": "Click an element by selector",
        "inputSchema": {
          "type": "object",
          "properties": {
            "selector": {"type": "string"}
          },
          "required": ["selector"]
        }
      }
    ]
  }
}
```

### 5.2 工具调用

```json
// 请求
{"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
  "name": "browser_navigate",
  "arguments": {
    "url": "https://example.com"
  }
}}

// 响应
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Navigated to https://example.com"
      }
    ]
  }
}
```

### 5.3 原生工具 vs MCP 工具

```
原生工具（Layer 1-2）:
  • 直接 Python 函数调用
  • 零网络开销
  • 统一 BaseTool 接口
  • Phase 1: file_read, file_write, file_edit, glob, grep, bash, web_search, web_fetch

MCP 工具（Layer 3）:
  • stdio 进程通信
  • tools/list 自动发现
  • MCPToolWrapper 统一包装
  • Phase 3+: browser, ocr, code_executor, custom skills
```

---

## 6. 错误码

| 错误码 | HTTP 状态 | 说明 |
|--------|----------|------|
| AUTH_REQUIRED | 401 | 需要认证 |
| INVALID_REQUEST | 400 | 请求参数错误 |
| SESSION_NOT_FOUND | 404 | 会话不存在 |
| PERMISSION_DENIED | 403 | 权限不足 |
| TOOL_FAILED | 500 | 工具执行失败 |
| MODEL_UNAVAILABLE | 503 | 模型不可用 |
| RATE_LIMITED | 429 | 请求频率超限 |

---

## 7. 附录

### 7.1 API 版本管理

所有 API 端点都带有版本前缀 `/api/v1/`，未来升级时可以使用 `/api/v2/` 等新版本。

### 7.2 分页参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | integer | 1 | 页码 |
| per_page | integer | 20 | 每页数量 |

### 7.3 排序参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| sort_by | string | created_at | 排序字段 |
| order | string | desc | 排序方向（asc/desc） |
