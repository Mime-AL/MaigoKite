# NanamiGopher 开发任务拆解

> **版本**: v1.1  
> **日期**: 2026-07-15  
> **周期**: 16 周（4 个月）  
> **团队**: 1 人全栈

---

## 1. 任务管理工具

使用项目任务管理工具创建定时任务，每个任务设置 `scheduled_date` + `scheduled_time` + `execution_type=auto`。

---

## 2. Phase 1: Agent Framework MVP (Week 1-2)

### 2.1 Week 1: 基础框架搭建

| 序号 | 任务 | 描述 | 预计工时 | 优先级 |
|------|------|------|---------|--------|
| 1.1.1 | 初始化 Go 项目 | 创建 Go module，初始化 Gin 项目结构 | 2h | P0 |
| 1.1.2 | 初始化 Python 项目 | 创建 Python package，初始化 LangChain 项目结构 | 2h | P0 |
| 1.1.3 | 初始化 Vue 3 + Vite | 创建前端项目，配置 TypeScript | 2h | P0 |
| 1.1.4 | 配置 Electron | 集成 Electron，配置 main.ts 和 preload.ts | 2h | P0 |
| 1.1.5 | 数据库初始化 | 创建 SQLite 数据库，初始化表结构 | 2h | P0 |
| 1.1.6 | 配置管理模块 | 实现 IConfigManager（YAML 加载/保存） | 3h | P0 |
| 1.1.7 | 基础 HTTP 路由 | 配置 Go API Gateway 路由结构 | 2h | P0 |
| 1.1.8 | WebSocket 基础 | 实现 WebSocket 连接和消息转发 | 3h | P0 |

### 2.2 Week 2: 核心功能实现

| 序号 | 任务 | 描述 | 预计工时 | 优先级 |
|------|------|------|---------|--------|
| 1.2.1 | 会话管理 API | 实现 CRUD 接口（POST/GET/DELETE） | 4h | P0 |
| 1.2.2 | 消息发送接口 | 实现消息发送和流式响应 | 4h | P0 |
| 1.2.3 | 前端对话界面 | 实现 Sidebar + ChatArea + InputBox | 6h | P0 |
| 1.2.4 | MCP 通信基础 | 实现 MCP stdio 通信协议（仅用于 Layer 3 Skill） | 2h | P0 |
| 1.2.5 | 原生 Tool: file_read/write/edit | 实现 BaseTool 接口 + 三个文件操作工具 | 4h | P0 |
| 1.2.6 | 原生 Tool: bash + web_search + web_fetch | 实现流式 bash 输出 + DuckDuckGo 搜索 + URL 抓取 | 4h | P0 |
| 1.2.7 | 原生 Tool: glob + grep | 实现文件通配搜索和文本搜索 | 2h | P0 |
| 1.2.8 | Tool 基础设施 | BaseTool 接口 + ToolResult 结构 + ExecutionContext + ToolRegistry + PermissionManager + ToolValidator | 4h | P0 |
| 1.2.9 | 凭证管理 | 实现 CredentialStore（跨平台密钥链） | 4h | P0 |
| 1.2.9 | 安全过滤管道 | 实现正则匹配 + 长度截断 | 3h | P0 |
| 1.2.10 | 安全过滤管道 | 实现正则匹配 + 长度截断 | 3h | P0 |
| 1.2.11 | 白名单机制 | 实现白名单配置和检查 | 2h | P0 |
| 1.2.12 | 权限分级 | 实现 L1-L5 五级权限 + Manual/Auto 模式 | 3h | P0 |
| 1.2.13 | 审计日志 | 实现 JSON 日志存储 + GUI 查看 | 2h | P0 |
| 1.2.14 | Example: 代码分析工作流 | 实现纯 Python 代码分析 Example | 3h | P1 |
| 1.2.15 | Example: 搜索 + 总结工作流 | 实现搜索 + LLM 总结 Example | 3h | P1 |
| 1.2.16 | Phase 1 集成测试 | 端到端测试 + 修复 Bug | 4h | P0 |

**Phase 1 里程碑**: Week 2 结束可演示 Framework + 2 个 Example

---

## 3. Phase 2: 核心体验完善 (Week 3-6)

### 3.1 Week 3: 记忆系统与模型路由

| 序号 | 任务 | 描述 | 预计工时 | 优先级 |
|------|------|------|---------|--------|
| 2.3.1 | 完整模型路由 | 实现多模型切换 + 降级策略 | 3h | P0 |
| 2.3.2 | RAG++ 记忆系统 | 实现向量检索 + Agentic Search | 5h | P0 |
| 2.3.3 | 记忆自动清理 | 实现双重条件触发 + 混合粒度清理 | 2h | P0 |
| 2.3.4 | 多对话并行 | 实现 Tab 管理、独立上下文 | 3h | P0 |
| 2.3.5 | Embedding Provider 抽象 | 实现 BGE/OpenAI 工厂模式 | 3h | P0 |
| 2.3.6 | 向量数据库集成 | 集成 ChromaDB（本地） | 2h | P0 |

### 3.2 Week 4: 用户体验完善

| 序号 | 任务 | 描述 | 预计工时 | 优先级 |
|------|------|------|---------|--------|
| 2.4.1 | 步骤面板 | 实现流式状态更新、可折叠 | 4h | P0 |
| 2.4.2 | 流式输出 | 实现 WebSocket 推送、打字机效果 | 3h | P0 |
| 2.4.3 | 错误处理和重试 | 实现渐进式报告 + 分级呈现 | 4h | P0 |
| 2.4.4 | SKILL.md 双模式导入 | 实现自包含 + 目录模式 | 4h | P0 |
| 2.4.5 | 前端 UI 完善 | 主题、布局、交互优化 | 5h | P1 |

### 3.3 Week 5: 扩展功能

| 序号 | 任务 | 描述 | 预计工时 | 优先级 |
|------|------|------|---------|--------|
| 2.5.1 | 本地模型支持 | 集成 Ollama | 3h | P0 |
| 2.5.2 | Tavily/Google 搜索 | 实现需 API Key 的搜索引擎 | 3h | P0 |
| 2.5.3 | MCP Server 生命周期 | 实现常驻 + 空闲超时关闭 | 4h | P0 |
| 2.5.4 | 基础 Telemetry | 实现 Token/Latency/Cost/Retry 追踪 | 4h | P0 |
| 2.5.5 | Playwright 基础 | 实现浏览器自动化 MCP Server | 4h | P0 |
| 2.5.6 | MCP Tool 自动发现 | 实现 MCPToolDiscovery + MCPToolWrapper | 3h | P0 |

### 3.4 Week 6: 收尾与优化

| 序号 | 任务 | 描述 | 预计工时 | 优先级 |
|------|------|------|---------|--------|
| 2.6.1 | 向量语义拦截 | 实现可选增强安全 | 2h | P1 |
| 2.6.2 | 审计日志导出 | 实现 CSV 格式导出 | 1h | P1 |
| 2.6.3 | OCR 识别 | 实现 PaddleOCR MCP Server | 3h | P0 |
| 2.6.4 | 前端完善 | 设置页、记忆管理页、Skill 管理页 | 6h | P1 |
| 2.6.5 | Phase 2 集成测试 | 端到端测试 + 性能优化 | 4h | P0 |

**Phase 2 里程碑**: Week 6 结束可演示"可用的日常助手"

---

## 4. Phase 3: 高级编排能力 (Week 7-12)

### 4.1 Week 7-8: 工作流引擎

| 序号 | 任务 | 描述 | 预计工时 | 优先级 |
|------|------|------|---------|--------|
| 3.7.1 | LangGraph 工作流引擎 | 实现 JSON Schema 定义、DAG 调度 | 8h | P0 |
| 3.7.2 | HITL 人机协同 | 实现挂起/恢复、事件驱动 | 8h | P0 |
| 3.7.3 | Checkpoint 机制 | 实现浏览器 Session 持久化 | 6h | P0 |
| 3.7.4 | Stealth Runtime | 实现指纹防检测、代理轮换 | 8h | P0 |
| 3.7.5 | Go/Python 解耦 | 实现控制流与数据流分离 | 6h | P0 |

### 4.2 Week 9-10: 规划反思与可观测性

| 序号 | 任务 | 描述 | 预计工时 | 优先级 |
|------|------|------|---------|--------|
| 3.9.1 | 规划与反思 | 实现 ReAct + Plan-and-Solve | 8h | P0 |
| 3.9.2 | 自我反思机制 | 实现错误根因分析 + 替代策略 | 6h | P0 |
| 3.9.3 | 反思知识库 | 实现失败模式积累 | 4h | P0 |
| 3.9.4 | 完整 Telemetry | 集成 OpenTelemetry + Langfuse | 8h | P0 |

### 4.3 Week 11-12: 多 Agent、SubAgent 与 Plugin

| 序号 | 任务 | 描述 | 预计工时 | 优先级 |
|------|------|------|---------|--------|
| 3.11.1 | 多 Agent 框架 | 实现角色定义、通信机制 | 10h | P0 |
| 3.11.2 | 状态强管控 | 实现 LangGraph 强制约束 | 4h | P0 |
| 3.11.3 | 基准测试 | 实现 Golden Dataset + 自动化回归 | 6h | P0 |
| 3.11.4 | 审批拦截 | 实现敏感操作挂起 + 前端审批 | 6h | P0 |
| 3.11.5 | 接管机制 | 实现 Agent 举手 + 无缝移交 | 6h | P0 |
| 3.11.6 | Plugin 架构 | 实现 MCP Plugin 注册/发现/加载 | 8h | P0 |
| 3.11.7 | Boss 直聘工作流 | 实现首个完整浏览器工作流 | 10h | P1 |
| 3.11.8 | Phase 3 集成测试 | 端到端测试 + 性能优化 | 6h | P0 |

### 4.4 Week 12: SubAgent 与 Inspector

| 序号 | 任务 | 描述 | 预计工时 | 优先级 |
|------|------|------|---------|--------|
| 3.17.1 | SubAgent 管理器 | 实现创建/结果提交/状态查询/销毁 | 8h | P0 |
| 3.17.2 | SubAgent 共享上下文 | 实现只读上下文 + 单写锁 + 50KB 限制 | 6h | P0 |
| 3.17.3 | SubAgent 超时降级 | 实现 Retry + Degrade 策略 | 4h | P1 |
| 3.17.4 | Inspector 事件模型 | 实现 InspectorEvent + TimelineBuilder | 6h | P0 |
| 3.17.5 | Inspector WebSocket | 实现实时事件推送 + 断线重连 | 6h | P0 |
| 3.17.6 | Inspector 前端组件 | 实现 InspectorView + InspectorCard + TimelineNode | 10h | P0 |
| 3.17.7 | Inspector API | 实现卡片列表 + 时间线 + 历史回放 | 6h | P0 |
| 3.17.8 | Inspector 自定义维度 | 实现维度选择器 + 前端配置保存 | 4h | P1 |

**Phase 3 里程碑**: Week 12 结束可演示"工业级工作流引擎 + Inspector 实时监控"

---

## 5. Phase 4: 生产就绪 (Week 13-16)

### 5.1 Week 13-14: 安全与性能

| 序号 | 任务 | 描述 | 预计工时 | 优先级 |
|------|------|------|---------|--------|
| 4.13.1 | 安全加固 | 渗透测试 + 漏洞修复 | 8h | P0 |
| 4.13.2 | 性能优化 | 实现并发控制、缓存策略 | 8h | P0 |
| 4.13.3 | Skill Market 雏形 | 实现搜索、安装、评价 | 10h | P1 |

### 5.2 Week 15-16: 部署与文档

| 序号 | 任务 | 描述 | 预计工时 | 优先级 |
|------|------|------|---------|--------|
| 4.15.1 | 加密云同步 | 实现 AES-256 + 端到端加密 | 6h | P1 |
| 4.15.2 | 离线能力完善 | 核心功能离线可用 | 4h | P1 |
| 4.15.3 | 文档体系 | 编写用户手册 + 开发者文档 | 6h | P0 |
| 4.15.4 | 自动化部署 | 实现 Docker + CI/CD | 6h | P0 |
| 4.15.5 | 监控告警 | 实现健康检查 + 异常通知 | 4h | P1 |
| 4.15.6 | 国际化 | 实现中英文切换 | 4h | P2 |
| 4.15.7 | 移动端适配 | 实现响应式设计 | 6h | P2 |
| 4.15.8 | 基础 Team | 实现共享知识库、权限管理 | 6h | P2 |
| 4.15.9 | Phase 4 集成测试 | 端到端测试 + 发布准备 | 8h | P0 |

**Phase 4 里程碑**: Week 16 结束达到生产就绪标准

---

## 6. 任务依赖关系

```
Phase 1
  ├── 1.1.x (Week 1) 无依赖
  └── 1.2.x (Week 2) 依赖 1.1.x 完成

Phase 2
  ├── 2.3.x (Week 3) 依赖 Phase 1 完成
  ├── 2.4.x (Week 4) 依赖 2.3.x 完成
  ├── 2.5.x (Week 5) 依赖 2.4.x 完成
  └── 2.6.x (Week 6) 依赖 2.5.x 完成

Phase 3
  ├── 3.7.x (Week 7-8) 依赖 Phase 2 完成
  ├── 3.9.x (Week 9-10) 依赖 3.7.x 完成
  ├── 3.11.x (Week 11-12) 依赖 3.9.x 完成
  └── 3.17.x (Week 12) 依赖 3.11.x 完成

Phase 4
  ├── 4.13.x (Week 13-14) 依赖 Phase 3 完成
  └── 4.15.x (Week 15-16) 依赖 4.13.x 完成
```

---

## 7. 风险管理

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| Phase 1 时间紧张 | 高 | 高 | 砍掉非核心功能，前端只做最简版 |
| 本地模型集成复杂 | 中 | 中 | 先支持 Ollama，vLLM/LM Studio 延后 |
| 反爬对抗升级 | 中 | 中 | 预留 Playwright stealth，必要时降级 |
| 单人开发进度慢 | 高 | 高 | 严格遵循 MVP 原则，Feature Freeze |

---

## 8. 每周演示计划

| 周次 | 演示内容 |
|------|---------|
| Week 2 | 可对话的 Agent + 文件读写/代码执行/搜索 |
| Week 6 | 多对话 + 流式输出 + 记忆系统 + 本地模型 |
| Week 12 | DSL 工作流 + HITL + 多 Agent + SubAgent + Inspector 实时监控 |
| Week 16 | 完整产品 + Skill Market + 文档体系 |

---

## 9. 创建任务命令

使用 MCP 工具批量创建任务：

```json
{
  "tasks": [
    {
      "title": "1.1.1 初始化 Go 项目",
      "description": "创建 Go module，初始化 Gin 项目结构",
      "scheduled_date": "2026-07-20",
      "scheduled_time": "09:00",
      "execution_type": "auto",
      "priority": 0
    },
    {
      "title": "1.1.2 初始化 Python 项目",
      "description": "创建 Python package，初始化 LangChain 项目结构",
      "scheduled_date": "2026-07-20",
      "scheduled_time": "09:00",
      "execution_type": "auto",
      "priority": 0
    }
  ]
}
```
