# NanamiGopher 需求清单

> 状态：Current。本文定义优先级和验收，不替代 API、数据库或权限设计。

## 1. 优先级

- P0：通用 Agent 核心闭环，Phase 1 发布阻塞；
- P1：核心闭环稳定后的日常可用性；
- P2：经需求验证的扩展和领域工作流；
- P3：生态与规模化能力。

## 2. Phase 1 P0 需求

### R-CORE-01 模型与对话

- Workspace 可保存多个 Chat 模型连接，并指定默认模型；
- 会话可选择模型、响应档位和权限模式；
- Base URL 规范化不得重复追加 `/v1`，OpenAI-compatible 调用必须命中正确 endpoint；
- 模型返回的 reasoning、ToolCall 和最终回答使用不同事件/展示对象；
- Secret 只进入 CredentialStore 和 Core 进程内存。

验收：至少一个云端或本地兼容端点完成模型发现、验证和真实对话。

### R-CORE-02 工具编排

- 模型可以在一轮任务中提出一个或多个 ToolCall；
- 所有 Tool 经过统一 Schema 校验、ToolPolicy、执行、结果回注和审计；
- Tool 失败返回稳定错误码、用户提示和可选设置入口；
- 工具参数/结果 JSON 不得拼入最终回答气泡。

验收：多 ToolCall、失败后继续推理、审批后从批次游标继续均有测试。

### R-CORE-03 浏览器操作

- 支持 open、snapshot、fill、click、press、screenshot 和 close；
- 只允许公开 HTTP(S) 目标，不允许嵌入凭证或访问 loopback/private/link-local/reserved 地址；
- screenshot 只能写入 Workspace；
- 读操作与副作用操作按动作动态分级，点击/提交类操作需要明确批准。

验收：Playwright 使用隔离页面会话，操作经过统一活动、批准和审计链路。

### R-CORE-04 持续任务与取消

- 发送消息返回 task ID，任务不依赖原始 HTTP 请求存活；
- 同一用户的不同会话可以独立运行；
- 任务至少具有 running、waiting_approval、succeeded、failed、cancelled、interrupted；
- 用户可从输入区域停止当前运行任务；取消同时关闭 pending Approval 与活动 ToolCall。

验收：切换对话不会错误共享发送锁；取消 API、持久状态和 UI 投影一致。

### R-CORE-05 权限批准

- 用户只需理解 read_only、workspace、full_access 三种模式；
- ToolPolicy 内部维护 L1-L5、路径范围、allowlist 和 hard-deny；
- 审批绑定主体、任务、ToolCall、参数 hash、版本和过期时间；
- Gateway 或前端不能绕过 Core 的最终授权。

验收：拒绝、过期、版本冲突、参数变化和 Core 重启后决定均可验证。

### R-CORE-06 状态恢复

- 会话、消息、任务、ToolCall、Approval 和运行事件持久化；
- 每个会话事件具有稳定 ID 和递增 sequence；
- 客户端可按 sequence 获取历史、按 ID 去重并恢复活动投影；
- Core 重启后 waiting_approval 仍可继续；无安全检查点的运行任务标记 interrupted；
- 系统不能把“标记中断”描述成“自动续跑”。

验收：数据库关闭/重开后状态和事件可读取；重启协调测试覆盖非终态转换。

### R-CORE-07 Skill 与 MCP 扩展

- 从配置目录发现 `SKILL.md`，校验名称、描述、版本、大小和目录边界；
- Phase 1 Skill 仅提供可审阅的 instruction/workflow 内容，通过 list/read Tool 使用；
- 从配置启动 stdio MCP Server、发现 Tool，并接入统一 ToolPolicy/审计；
- UI 只展示实际加载的 Skill/MCP，不提供无后端语义的安装按钮。

验收：新增本地 Skill 和测试 MCP Server 后能被模型调用；非法/重复 Skill 不使 Core 崩溃。

### R-CORE-08 客户端与工作区

- Web/Electron 提供对话、活动时间线、审批、停止、模型/权限选择；
- 工作区文件树、文本预览和 Git Diff 只读且限制路径/大小；
- 重进对话读取服务端任务与事件，不以 WebSocket 内存作为事实来源；
- 用户可设置助手显示称呼，不把项目名强制显示为称呼。

验收：Vue 类型检查、组件/Store 测试、Web 和 Electron 构建通过。

## 3. Phase 2 P1 需求

- 原子 `after_sequence` 重连，消除历史读取与实时订阅之间的窗口；
- 幂等步骤、安全检查点与可控自动重试；
- 浏览器资源隔离、下载上传、登录态托管和人工接管；
- 任务队列、并发/预算/超时/配额；
- 模型能力目录、路由和显式 fallback；
- Skill 热重载与启停、MCP 健康检查和有限重启；
- 用户可控 Memory v1；Embedding 仅在检索评测证明必要后加入；
- 生图/OCR 作为工具 Provider 接入。

## 4. Phase 3 P2 需求

- 可版本化 Workflow、人工节点、条件、重试和 checkpoint；
- Skill 包签名、内容 hash、安装、回滚与 Workspace Grant；
- 只有在单 Agent 基线证明收益后才引入子 Agent；
- 领域工作流必须先有用户访谈/任务频率/失败成本证据，不因示例直接进入核心。

## 5. Phase 4 P3 需求

- 身份认证、团队 Workspace、角色和共享资源；
- PostgreSQL Repository、迁移工具、多实例任务租约与事件分发；
- Skill/MCP 供应链治理和市场；
- 备份恢复、安全与性能发布门禁。

## 6. 非功能需求

### 安全

- 本地服务默认只监听 loopback；服务端部署必须认证；
- URL、文件路径、命令和 MCP 环境都使用 allowlist/边界校验；
- 日志、事件和数据库不记录 Secret；
- 外部内容视为不可信数据，不能提升权限或覆盖系统策略。

### 可靠性

- 状态更新与对应任务事件应原子提交；当前实现未完全达到时必须记录为架构债务；
- 取消、批准和 Tool 执行在重复请求下保持可预测；
- 所有依赖故障向用户提供明确状态，不静默降级到其他付费/远程服务。

### 性能

- 前端按对话隔离活动更新，长列表避免全量重绘；
- 浏览器按需启动并回收页面；
- 事件历史分页，单次响应有上限；
- 发布前建立延迟、内存和并行任务基线，禁止无测量的性能承诺。

## 7. 需求变更门禁

新增领域功能前回答四个问题：谁高频使用、现有替代成本是什么、失败会造成什么副作用、是否能作为 Skill/MCP/Workflow 实现。能由扩展实现的能力默认不进入内核；只有跨领域共享且影响权限、恢复或执行一致性的能力才进入核心。
