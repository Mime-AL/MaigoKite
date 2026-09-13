# NanamiGopher — 更新日志

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 规范。

## 格式规范

### 版本号

采用 [Semantic Versioning](https://semver.org/lang/zh-CN/) 规范（主版本.次版本.修订版本）。

### 变更类别

- **Added** — 新增功能
- **Changed** — 现有功能的变更
- **Deprecated** — 即将废弃的功能
- **Removed** — 已移除的功能
- **Fixed** — Bug 修复
- **Security** — 安全性修复

### 变更日志结构

```markdown
## [版本号] — YYYY-MM-DD

### Added
- 新增功能描述

### Changed
- 变更内容描述

### Fixed
- 修复内容描述
```

---

## 已发布的版本

### [v1.5] — 2026-10-13

> 第一个正式公开发布版本，完成安全加固、性能优化、Skill 市场和 Team 功能。

#### Added
- Skill 市场：用户可浏览、搜索、评价和安装社区 Skill
- Team 功能：多用户协作、共享对话空间和共享记忆库
- CI/CD 流水线：GitHub Actions 自动化测试、构建和部署
- Docker Compose 一键部署方案
- Kubernetes 部署模板
- 完整的 API 文档（OpenAPI 3.0 规范）
- 用户手册、开发者指南和部署文档

#### Security
- 全面渗透测试和漏洞修复
- 输入验证增强（SQL 注入 / XSS / CSRF 防护）
- API 速率限制
- 安全审计日志

#### Changed
- 响应缓存（Redis）显著降低 API 延迟
- 数据库查询优化，吞吐量提升 3 倍
- 前端资源压缩和懒加载

#### Fixed
- 修复了多对话切换时的状态丢失问题
- 修复了 Playwright 进程内存泄漏
- 修复了流式输出在弱网环境下的断连问题

---

### [v1.0] — 2026-09-01

> GA 版本，功能完整，达到生产可用标准。

#### Added
- DSL 工作流引擎：支持 YAML/JSON 定义的条件分支和循环
- 多 Agent 架构：Master-Worker 模式的 Agent 集群
- 可观测性平台：OpenTelemetry 集成、链路追踪、Grafana 面板
- Plugin 热加载：无需重启即可加载/卸载/更新插件
- SubAgent 系统：主 Agent 可创建和管理子任务
- Inspector：实时查看 Agent 状态、工具调用链和记忆内容
- 长期记忆系统：ChromaDB 向量存储 + 语义检索
- 文件存储系统：上传/下载/版本控制/搜索

#### Changed
- 将 Plugin 架构从示例级别提升至生产级别
- 对话引擎支持更复杂的上下文管理

#### Fixed
- 修复了长对话中的 Token 溢出问题
- 修复了 SubAgent 超时后状态不一致的问题

---

### [v0.5] — 2026-07-28

> Beta 版本，核心体验打磨完成，支持本地模型和浏览器自动化。

#### Added
- 多对话管理：同时打开多个对话窗口，支持搜索和归档
- 流式输出：SSE + WebSocket 双通道传输
- 本地模型支持：Ollama 集成，可在本地运行推理
- Telemetry 基础版：对话统计、延迟监控、Token 消耗
- Playwright 集成：Agent 可操控浏览器完成任务
- OCR 模块：中文图片文字识别
- Electron 桌面端：打包为桌面应用

#### Changed
- 前端从概念验证升级为完整的多对话界面
- 错误处理从简单日志升级为结构化错误码体系

#### Fixed
- 修复了流式输出在 Firefox 下的兼容性问题
- 修复了 OCR 识别大图片时的内存溢出

---

### [v0.1] — 2026-07-07

> MVP 版本，验证核心技术栈的可行性。

#### Added
- Go API Gateway（Gin）：RESTful 路由、CORS、JWT 认证
- Python Agent Core：LLM 调用封装、工具调用接口
- 对话引擎：单轮/多轮对话、会话管理
- 工具注册中心：动态工具发现和参数校验
- 短期记忆：会话内上下文窗口管理
- 权限系统 v1：用户注册/登录、基础 RBAC
- 2 个 Example 插件：天气查询、代码格式化
- Vue 3 前端：基础对话界面

---

## 未来版本预留

### [Unreleased]

> 此区域用于记录尚未发布版本的变更。发布时移动至对应版本号下。

#### Added
- （预留）

#### Changed
- （预留）

#### Fixed
- （预留）

#### Security
- （预留）

---

### [v2.0] — 规划中

> 预计 1 年后发布，聚焦生态成熟和跨平台集成。

#### Planned
- VS Code / JetBrains / Xcode 原生集成
- Skill 市场开放提交和审核流程
- 更多 LLM 后端支持（Gemini、Mistral、通义千问等）
- 社区贡献指南和开发者计划

---

### [v3.0] — 远期规划

> 预计 3 年后发布，聚焦自主软件工程项目能力。

#### Planned
- 从需求分析到部署上线的端到端自主开发
- MCP 协议成为行业标准参考实现
- 全球开发者社区超过 1,000,000 人
