# NanamiGopher Agent 快速导航

> **状态**：Current
> **最后核验**：2026-09-14

本文面向参与项目开发的 AI Agent 和新开发者，只提供导航，不重复架构定义。

## 项目概要

NanamiGopher 是 Vue/Electron、Go Gateway 与 Python Agent Core 组成的本地优先 AI Agent。个人与团队空间共用 Workspace 领域模型。

## 开始阅读

1. [文档中心](README.md)
2. [系统设计](design/SystemDesign.md)
3. [架构决策](reference/Decisions.md)
4. [目录结构](development/DirectoryStructure.md)
5. 根据任务选择专项文档

## 任务路由

| 任务 | 阅读 |
|---|---|
| 修改 Go/Python 边界 | [BackendDesign](design/BackendDesign.md)、[API](design/API.md) |
| 修改 Vue/Electron | [FrontendDesign](design/FrontendDesign.md) |
| 修改 REST/gRPC/事件 | [API](design/API.md) |
| 修改表或迁移 | [Database](design/Database.md) |
| 修改 Memory/RAG | [Memory](agent-capabilities/memory/memory-system.md) |
| 修改 Tool 权限 | [Tool Permission](agent-capabilities/security/tool-permission.md) |
| 修改 MCP | [MCP Integration](agent-capabilities/mcp/mcp-integration.md) |
| 修改 Skill | [Skill Lifecycle](agent-capabilities/skills/skill-lifecycle.md) |
| 修改模型路由 | [Model Routing](agent-capabilities/models/model-routing.md) |
| 测试 | [TestPlan](testing/TestPlan.md) |
| 部署 | [Production](deployment/Production.md) |

## 核心约束

- Electron 监督桌面进程；容器编排监督服务器进程。
- Go 是外部 Gateway 和 Python gRPC Client。
- Python 是 Agent Core、gRPC Server、Tool/MCP 所有者和 Agent 领域写入者。
- 前端不决定工具是否获批。
- API、Proto、迁移和配置 Schema 优先于 Markdown 字段副本。
- Planned 能力不能写成已经交付。

## 仓库入口

```text
gateway/        Go Gateway
python/         Python Agent Core
web/            Vue 与 Electron
docs/           项目文档
```

运行命令以仓库实际 Makefile/package scripts 为准，不从设计文档复制旧命令。
