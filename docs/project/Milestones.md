# NanamiGopher — 版本规划

> 状态：v0.1 实现完成，发布待定
> 本文记录实现状态；正式发布状态仍以版本标签和发布记录为准。

## 概览

NanamiGopher 在 16 周的开发周期内发布 4 个主要版本，每个版本对应一个明确的交付目标和用户群体。

| 版本 | 代号 | 发布时间 | 目标用户 | 成熟度 |
|------|------|---------|---------|--------|
| v0.1 | MVP | Week 2 | 内部测试 | 技术验证 |
| v0.5 | Beta | Week 6 | 早期采用者 | 体验打磨 |
| v1.0 | GA | Week 12 | 生产用户 | 功能完整 |
| v1.5 | Release | Week 16 | 大众用户 | 生态就绪 |

---

## v0.1 — MVP（Week 2）

> **目标**：验证核心技术栈，展示最小可用功能。

### 版本说明

这是 NanamiGopher 的第一个可运行版本。它证明了 Go API Gateway + Python Agent Core 的混合架构可行，并展示了基础的 AI 对话能力。

### Feature List

#### 核心功能

- [x] Go API Gateway（Gin）
  - [x] RESTful 路由框架
  - [x] 本地 Origin/CORS 边界
  - [x] Workspace AccessPolicy（服务器身份认证后续接入）
  - [x] 基础健康检查接口 `/health`
- [x] Python Agent Core
  - [x] LLM 调用封装（OpenAI、Anthropic、Ollama、OpenAI-compatible）
  - [x] Workspace 多模型配置、默认模型、连接验证与运行时热更新
  - [x] 工具调用（Tool Calling）接口
  - [x] 消息格式标准化
- [x] 对话引擎
  - [x] 单轮对话
  - [x] 多轮对话（会话上下文管理）
  - [x] 会话创建/删除/列表
- [x] 工具系统
  - [x] 工具注册中心
  - [x] MCP Tool 动态发现
  - [x] 工具参数校验
- [x] 记忆系统
  - [x] 短期记忆（会话内上下文窗口）
  - [x] 最大 Token 限制管理
- [x] 权限系统 v1
  - [x] Personal Workspace Owner 初始化
  - [x] Workspace Membership 访问拦截
  - [x] ToolPolicy 风险分级
- [x] Example Workflow × 2
  - [x] Example: 文件读取 + 模型代码审查
  - [x] Example: 文档读取 + 模型结构化摘要
- [x] 前端基础
  - [x] Vue 3 + Vite 项目初始化
  - [x] 对话界面（消息列表 + 输入框）
  - [x] 模型接入设置（云端 API 与本地端口）
  - [x] 聊天级模型、响应速度和执行权限选择
  - [x] Workspace 文件树、文本预览与 Git Diff
  - [x] 按用户持久化界面助手称呼
  - [x] 一阶段导航只暴露已连通的功能

### 已知限制

- 单个任务固定使用当前会话选择的一个 LLM；自动模型路由和 fallback 属于 Phase 2
- WebSocket 已传输 Provider 的真实增量，但尚无断线重放
- Workspace 可保存多个模型、按 Base URL 手动获取目录并由会话选择；仍无后台自动探测、按任务路由和自动 fallback
- MCP 已完成显式配置的 stdio 启停、发现、统一权限和审计链路；SkillGrant、健康重启与空闲回收属于 Phase 2
- 仅持久化会话消息和用户偏好，无向量长期记忆
- 错误模型为 MVP 子集，尚无自动重试和恢复
- 模型自主 Tool Calling、统一 ToolPolicy、持久化审批及审批恢复已接入；单任务最多执行 8 轮工具调用
- 前端已接入审批决策、结构化 Tool 状态、会话级权限模式和 Workspace 风险设置
- 文件浏览器、只读预览和 Git Diff 已接入；Inspector 尚未接入后端事件快照契约

### 验收方式

- `bash scripts/run_tests.sh`：Go、Python（含 gRPC/MCP/本地 OpenAI-compatible）与 Vue 回归。
- `bash scripts/build.sh all`：Go 可执行文件、Python wheel/sdist、Vue Web 与 Electron 主进程构建。
- 本地 REST 冒烟：健康检查、用户称呼、模型设置、权限设置、会话消息和一次性审批恢复。

---

## v0.5 — Beta（Week 6）

> **目标**：打磨核心体验，让用户愿意日常使用。

### 版本说明

v0.5 是第一个面向早期采用者的版本。它在 Phase 1 单模型与真实增量输出基础上，引入并行会话、可恢复事件流和高级模型管理等关键能力。

### Feature List

#### v0.1 增量

- [ ] 多对话管理
  - [ ] 同时打开多个对话窗口
  - [ ] 对话列表侧边栏
  - [ ] 对话搜索
  - [ ] 对话归档
- [ ] 可恢复事件流
  - [ ] WebSocket 断线续传与事件重放
  - [ ] WebSocket 双向通信
  - [ ] 打字机效果前端组件
- [ ] 错误处理系统
  - [ ] 统一错误码体系
  - [ ] 用户友好的错误提示
  - [ ] 错误日志记录
- [ ] 高级模型管理
  - [ ] 自动发现 Ollama / LM Studio 模型
  - [x] 会话级模型选择器（云端 / 本地，已提前交付）
  - [ ] 多模型 fallback 与能力说明
- [ ] Telemetry 基础版
  - [ ] 对话数量统计
  - [ ] 平均响应延迟
  - [ ] Token 消耗统计
- [ ] Playwright 集成
  - [ ] Agent 可发起浏览器请求
  - [ ] 网页内容抓取
- [ ] OCR 模块
  - [ ] 中文图片文字识别
  - [ ] 截图 → 文字 → 工具输入 链路
- [ ] Electron 桌面端
  - [ ] 项目初始化
  - [ ] 基本窗口布局
  - [ ] 系统托盘集成
- [ ] 前端完善
  - [ ] 多对话标签页
  - [ ] 设置页面
  - [ ] 用户中心

### 已知限制

- DSL 工作流尚未实现
- 无可观测性面板
- 无完整 Skill 更新与回滚
- 无长期记忆
- 无团队协作功能
- 前端未完全响应式

---

## v1.0 — GA（Week 12）

> **目标**：功能完整，达到生产可用标准，面向正式用户发布。

### 版本说明

v1.0 的候选目标是达到 General Availability，覆盖 Agent 编排、可观测性、长期记忆和安全的 Skill 生命周期；是否发布以验收结果为准。

### Feature List

#### v0.5 增量

- [ ] DSL 工作流引擎
  - [ ] YAML/JSON 工作流定义
  - [ ] 条件分支（if/else）
  - [ ] 循环（for/while）
  - [ ] 变量传递
  - [ ] 工作流执行器
  - [ ] 工作流可视化编辑器（基础版）
- [ ] 多 Agent 架构
  - [ ] Master Agent（任务分解）
  - [ ] Worker Agent（任务执行）
  - [ ] Agent 间通信协议
  - [ ] 结果聚合
- [ ] 可观测性完整版
  - [ ] OpenTelemetry 集成
  - [ ] 链路追踪（Trace ID 传播）
  - [ ] 指标面板（Prometheus + Grafana）
  - [ ] 日志聚合（结构化日志）
  - [ ] 告警规则
- [ ] Skill 生命周期
  - [ ] 激活、禁用、更新与回滚
  - [ ] 沙箱隔离（容器化执行）
  - [ ] 版本管理
  - [ ] Skill 市场（基础版）
  - [ ] 权限绑定
- [ ] SubAgent 系统
  - [ ] 主 Agent 创建子任务
  - [ ] 子任务优先级调度
  - [ ] 结果回传机制
  - [ ] 超时和重试
- [ ] Inspector
  - [ ] 实时 Agent 状态查看
  - [ ] 工具调用链可视化
  - [ ] 记忆内容浏览
  - [ ] 执行时间线
- [ ] 长期记忆系统
  - [ ] ChromaDB 向量存储
  - [ ] 语义检索
  - [ ] 记忆摘要生成
  - [ ] 跨会话记忆共享
- [ ] 文件存储系统
  - [ ] 文件上传/下载
  - [ ] 文件版本控制
  - [ ] 文件搜索
- [ ] 前端完善
  - [ ] 工作流编辑器
  - [ ] Inspector 面板
  - [ ] 可观测性仪表盘
  - [ ] Skill 管理界面

### 已知限制

- 无 Skill 市场（待 v1.5 实现）
- 无 Team 协作功能
- 安全加固尚未完成
- 性能优化未达生产级
- 文档体系不完整

---

## v1.5 — Release（Week 16）

> **目标**：生态初建，安全加固，面向大众正式发布。

### 版本说明

v1.5 的候选目标是在 v1.0 基础上完成安全、性能、Skill 市场和团队协作验收；不能在验收前宣称生产就绪。

### Feature List

#### v1.0 增量

- [ ] 安全加固
  - [ ] 渗透测试
  - [ ] 漏洞修复
  - [ ] 安全审计日志
  - [ ] 输入验证增强
  - [ ] SQL 注入防护
  - [ ] XSS 防护
  - [ ] CSRF 防护
  - [ ] 速率限制
- [ ] 性能优化
  - [ ] 响应缓存（Redis）
  - [ ] 连接池优化
  - [ ] 异步处理
  - [ ] 数据库查询优化
  - [ ] 前端资源压缩
  - [ ] 性能基准测试报告
- [ ] Skill 市场
  - [ ] 前端商城页面
  - [ ] Skill 分类和搜索
  - [ ] 用户评价系统
  - [ ] 一键安装
  - [ ] 审核后台
- [ ] Team 功能
  - [ ] 多用户协作
  - [ ] 共享对话空间
  - [ ] 共享记忆库
  - [ ] 协作编辑
  - [ ] Team 权限管理
  - [ ] Team 邀请机制
- [ ] CI/CD 流水线
  - [ ] GitHub Actions 自动化测试
  - [ ] 自动化构建
  - [ ] Docker 镜像推送
  - [ ] 部署脚本
- [ ] 部署方案
  - [ ] Docker Compose 一键部署
  - [ ] Kubernetes 部署模板
  - [ ] 环境配置指南
- [ ] 文档体系
  - [ ] API 文档（OpenAPI 3.0）
  - [ ] 用户手册
  - [ ] 开发者指南
  - [ ] 部署文档
  - [ ] Skill 与 MCP Server 开发教程

### 发布说明

这是 NanamiGopher 的第一个正式公开发布版本。建议在以下环境部署：

- 操作系统：Ubuntu 22.04 LTS / macOS Sonoma
- Go：1.22+
- Python：3.12+
- Node.js：20+
- 数据库：SQLite（开发）/ PostgreSQL（生产）
- 缓存：Redis 7+
