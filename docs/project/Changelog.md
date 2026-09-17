# NanamiGopher 更新日志

> 状态：Current
> 本文件只记录已经合并且可验证的变化。计划版本属于 [Roadmap.md](Roadmap.md)，不得提前写成已发布功能。

格式遵循 Keep a Changelog，版本号遵循 Semantic Versioning。发布记录必须能够关联 Git 标签、构建产物与验收结果。

## Unreleased

### Added

- 建立根级权威 Proto，接通 Go Gateway 到 Python Agent Core 的 gRPC 会话、消息、健康检查与事件流。
- 实现 SQLite Workspace/会话/消息/偏好/审计 Repository、原生 Tool 执行管道和 MCP stdio 客户端。
- 实现 Vue 会话 Store、REST/WebSocket 客户端、Electron 安全 preload 与本地 Runtime Supervisor。
- 增加 Go、Python gRPC/MCP/领域逻辑与 Vue 交互自动化测试。
- 增加模型服务预设和基于 Base URL 的模型目录发现，支持 OpenAI/Anthropic/兼容 `/models` 与 Ollama `/api/tags`。
- 接通配置式 MCP stdio Server 的 Agent Core 启停、工具发现、统一审批与审计链路。
- 增加 Bash 工作区进程沙箱和 Gateway 完整路由构造回归测试。

### Changed

- 重构 `docs/` 文档体系，建立 Current、Planned、Deprecated、Generated 状态。
- 统一系统边界：Go Gateway 是 Python Agent Core 的 gRPC 客户端；Python 是 Agent 领域数据的唯一写入方。
- 统一 Workspace、权限、工具、MCP、Skill、记忆与凭证语义。
- 将 API、数据库、前端、后端、部署、测试和运维文档收敛为单一职责文档。
- 将原生 Tool 与 MCP 的运行时所有权统一到 Python，Gateway 仅保留协议边界和系统密钥环适配。
- 模型设置页移除普通用户不需要的生成参数，权限设置收敛为只读、工作区和完全访问三档。
- 将模型连接验证和目录发现改为无歧义的 `/models/actions/*` 路由，修复 Gateway 启动冲突。

### Removed

- 删除与 `GitWorkflow.md` 重复的 `BranchStrategy.md`。
- 移除项目文档中未验证的“已发布版本”声明；历史目标仍可从路线图与里程碑查看。

## 发布记录

当前文档没有足够的标签和验收证据可确认已发布版本。首次正式发布时，在此新增版本、日期和对应标签，不从路线图自动推导。
