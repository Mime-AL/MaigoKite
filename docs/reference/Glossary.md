# NanamiGopher 术语表

> 本文档收录 NanamiGopher 项目中涉及的关键术语，提供中英文对照与简要解释。术语按领域分类，便于快速查阅。

---

## 1. 架构术语

| 术语 | 英文 | 解释 |
|------|------|------|
| Agent Runtime | 智能体运行时 | 管理 Agent 生命周期（初始化、运行、暂停、恢复、销毁）的核心组件，负责调度消息流转与工具调用。 |
| API Gateway | API 网关 | 系统的入口层，负责路由、鉴权、限流和协议转换。NanamiGopher 中由 Go/Gin 实现。 |
| Agent Core | 智能体核心 | 系统的决策中枢，运行在 Python 侧，负责任务规划、记忆检索、工具选择与执行协调。 |
| Sandbox | 沙箱 | 隔离的执行环境，用于安全地运行不受信任的代码或工具调用。 |
| Execution Engine | 执行引擎 | 接收 TaskManager 下发的任务，驱动 Agent Core 完成规划-执行循环。 |
| TaskManager | 任务管理器 | 负责任务的创建、分发、状态跟踪和生命周期管理。 |
| SkillRegistry | 技能注册表 | 维护所有可用 Skill（技能）的定义与元数据，支持动态注册与发现。 |
| Provider | 提供者 | 遵循统一接口的可插拔组件，如 Embedding Provider、Memory Provider、Storage Provider 等。 |
| Factory Pattern | 工厂模式 | 用于创建 Provider 实例的设计模式，根据配置动态选择具体的实现类。 |
| Message Bus | 消息总线 | 系统内部各组件之间的异步通信机制，基于事件驱动的消息传递。 |
| EventBus | 事件总线 | 轻量级的事件发布/订阅机制，用于模块间的松耦合通信。 |

---

## 2. 记忆术语

| 术语 | 英文 | 解释 |
|------|------|------|
| IMemorySystem | 记忆系统接口 | 定义记忆读写、持久化、检索的统一接口契约。 |
| ShortTerm Memory | 短期记忆 | 保存最近 N 轮对话的上下文窗口内容，用于维持即时对话连贯性。 |
| Conversation Memory | 会话记忆 | 按会话维度组织的历史对话摘要与关键信息，支持跨轮次回溯。 |
| Episodic Memory | 情景记忆 | 记录具体事件、交互过程和时间序列的长期记忆形式。 |
| User Profile | 用户画像 | 持久化的用户偏好、习惯、背景信息等结构化数据。 |
| IKnowledgeBase | 知识库接口 | 定义文档存储、检索和向量搜索的统一接口。 |
| DocumentStore | 文档存储 | 原始文档的持久化存储层，支持多种格式（文本、Markdown、PDF 等）。 |
| VectorStore | 向量存储 | 将文档切片并编码为向量后存储，支持语义相似度搜索。 |
| Retriever | 检索器 | 从知识库中根据查询条件召回相关文档或片段的服务组件。 |
| Embedding | 嵌入 | 将文本转换为固定维度的向量表示，用于语义搜索和相似性计算。 |
| Embedding Provider | 嵌入提供者 | 封装不同 Embedding 模型的统一接口，支持 BGE-M3、OpenAI、GTE 等后端切换。 |
| Chunk | 文本块 | 文档被切分后的段落单元，是向量化和检索的基本粒度。 |
| FTS5 | 全文搜索引擎 | SQLite 内置的全文检索扩展，支持关键词匹配与相关性排序。 |

---

## 3. 工具术语

| 术语 | 英文 | 解释 |
|------|------|------|
| BaseTool | 基础工具 | 所有工具类的抽象基类，定义了 `execute`、`validate`、`get_metadata` 等标准方法。 |
| Tool | 工具 | Agent 可调用的能力单元，如文件读写、代码执行、网络请求等。 |
| Tool Result | 工具结果 | 工具执行后返回的结构化结果，包含输出内容、状态码、错误信息和元数据。 |
| ExecutionContext | 执行上下文 | 工具执行时的环境信息，包括用户身份、权限级别、会话 ID、资源配额等。 |
| MCP Server | MCP 服务器 | 实现 Model Context Protocol 的工具服务进程，对外暴露标准化工具接口。 |
| MCP Client | MCP 客户端 | 调用 MCP Server 的组件，负责协议握手、工具发现和远程调用。 |
| MCP Protocol | MCP 协议 | Model Context Protocol，定义工具与服务端之间标准化的通信格式和生命周期管理。 |
| Atomic Tool | 原子工具 | 不可再拆分的单一功能工具，是 MCP 工具的最小执行单元。 |
| Composite Tool | 组合工具 | 由多个原子工具编排而成的复杂工具，封装了多步操作流程。 |
| Four-Layer Architecture | 四层工具架构 | 将工具分为 Runtime 内核层、高频原生层、低频原生层、MCP 层的分层设计。 |

---

## 4. 安全术语

| 术语 | 英文 | 解释 |
|------|------|------|
| Permission Level | 权限等级 | 工具访问敏感资源的分级制度，分为 L1 至 L5 五个级别。 |
| L1 - 公开 | Level 1 Public | 无需任何鉴权的公开工具，如只读信息查询。 |
| L2 - 用户 | Level 2 User | 需验证用户身份的普通操作，如个人文件读写。 |
| L3 - 受限 | Level 3 Restricted | 需要额外授权的操作，如系统配置修改。 |
| L4 - 敏感 | Level 4 Sensitive | 涉及敏感数据的操作，需明确的用户确认和审计日志。 |
| L5 - 危险 | Level 5 Dangerous | 可能破坏系统状态的操作，需最高级别审批和多重确认。 |
| Whitelist | 白名单 | 允许执行的工具或域名列表，默认拒绝不在白名单内的操作。 |
| Blacklist | 黑名单 | 禁止执行的工具或域名列表，明确拒绝列入黑名单的资源。 |
| Credential | 凭证 | 用于身份认证和安全授权的密钥、Token 或证书等敏感信息。 |
| Sanitization | 清理/消毒 | 对输入数据进行过滤、转义和规范化，防止注入攻击和数据泄露。 |
| Truncation | 截断 | 对超出长度限制的内容进行裁剪，防止缓冲区溢出和资源耗尽。 |
| 先截断后检测 | Truncate-Then-Detect | 安全策略：先对输入进行长度截断，再对内容进行安全检测，兼顾性能与安全。 |

---

## 5. 前端术语

| 术语 | 英文 | 解释 |
|------|------|------|
| Inspector | 检查器 | 前端组件，用于可视化展示 Agent 的执行过程、工具调用链和中间结果。 |
| SubAgent | 子智能体 | 由主 Agent 派生的独立执行单元，负责处理子任务或并行工作流。 |
| Vue 3 | Vue 3 | 前端 UI 框架，采用 Composition API 和响应式系统构建用户界面。 |
| Vite | Vite | 前端构建工具，提供极速的开发热更新和优化的生产打包。 |
| Electron | Electron | 桌面应用框架，将 Web 前端打包为跨平台的桌面程序。 |
| Three-Panel Layout | 三栏布局 | 前端 UI 设计：左侧导航/会话列表、中间对话主区域、右侧检查器/工具面板。 |
| WebSocket | WebSocket | 浏览器与服务器之间的全双工通信协议，用于实时推送 Agent 状态和事件。 |
| REST API | RESTful API | 基于 HTTP 的标准接口，用于前后端的数据交互和资源管理。 |
| gRPC | gRPC | Google 开源的高性能 RPC 框架，用于服务间的高效通信。 |

---

## 6. 工作流术语

| 术语 | 英文 | 解释 |
|------|------|------|
| SKILL.md | 技能定义文件 | 描述 Agent 技能的 YAML/Markdown 配置文件，包含意图定义、工具依赖和执行约束。 |
| Intent | 意图 | 用户请求背后的高层目标，如"编写代码"、"分析数据"、"搜索信息"。 |
| LangGraph | LangGraph | 基于图结构的工作流编排引擎，用于定义和调度复杂的 Agent 执行流程。 |
| Workflow | 工作流 | 由多个步骤和条件分支组成的完整执行流程。 |
| Orchestration | 编排 | 将多个原子工具和子智能体按预定逻辑组合成可执行的流程。 |
| Chain of Thought | 思维链 | Agent 在推理过程中生成的中间思考步骤，用于提升复杂任务的解决能力。 |

---

## 7. 其他术语

| 术语 | 英文 | 解释 |
|------|------|------|
| NanamiGopher | NanamiGopher | 项目名称，中文优先的 AI 工作助手，基于 Claude Code 生态理念构建。 |
| Chinese-First | 中文优先 | 产品定位原则，优先优化中文场景的理解、生成和交互体验。 |
| Claude Code Ecosystem | Claude Code 生态 | 指 Anthropic Claude Code 的工具链和设计理念，NanamiGopher 在此基础上进行适配和本地化。 |
| Phase | 阶段 | 项目开发的里程碑划分，如 Phase 1（核心）、Phase 2（记忆）、Phase 3（知识库）等。 |
