# NanamiGopher 文档中心

> **状态**：Current
> **架构版本**：v1
> **最后核验**：2026-09-14

本目录是 NanamiGopher 的项目文档入口。文档遵循“一项事实、一个权威来源”：权威文档负责定义，其他文档只解释、引用或展示派生视图。

## 阅读路径

1. [项目愿景](project/Vision.md)
2. [系统设计](design/SystemDesign.md)
3. [架构决策](reference/Decisions.md)
4. [术语表](reference/Glossary.md)
5. 按需阅读前端、后端、API、数据库或 Agent 能力设计
6. 阅读开发、测试、部署和用户指南

## 文档状态

| 状态 | 含义 |
|---|---|
| `Current` | 当前有效、可作为实现依据 |
| `Planned` | 已规划但尚未成为当前架构 |
| `Deprecated` | 已废弃，仅供历史追溯 |
| `Generated` | 从代码或机器契约生成，不应手工维护字段 |

未显式标记状态的旧文档，在完成本轮整理前按 `Planned` 参考，不应单独作为实现依据。

## 权威来源

| 主题 | 权威来源 | 其他文档的职责 |
|---|---|---|
| 总体架构、组件边界 | [SystemDesign.md](design/SystemDesign.md) | 图表和专项设计引用它 |
| 架构决策及取舍 | [Decisions.md](reference/Decisions.md) | 不在其他文档重复论证 |
| 术语 | [Glossary.md](reference/Glossary.md) | 统一使用相同名称 |
| 后端内部设计 | [BackendDesign.md](design/BackendDesign.md) | 不重复 API、数据库字段 |
| 前端与 Electron | [FrontendDesign.md](design/FrontendDesign.md) | 不定义后端权限规则 |
| REST、gRPC、WebSocket | [API.md](design/API.md) | 最终以 OpenAPI、Proto、事件 Schema 为机器契约 |
| 数据模型 | [Database.md](design/Database.md) | ER 图是派生视图，迁移文件是实现事实 |
| 工具权限 | [tool-permission.md](agent-capabilities/security/tool-permission.md) | 用户指南只解释，不复制矩阵 |
| Memory | [memory-system.md](agent-capabilities/memory/memory-system.md) | 数据字段引用 Database |
| MCP | [mcp-integration.md](agent-capabilities/mcp/mcp-integration.md) | Skill 生命周期只引用协议 |
| Skill 生命周期 | [skill-lifecycle.md](agent-capabilities/skills/skill-lifecycle.md) | SKILL.md 格式只在此定义 |
| 测试策略 | [TestPlan.md](testing/TestPlan.md) | CI-CD 只描述流水线执行 |
| 安全、日志、监控、备份 | [ops-security](ops-security/) | 部署文档引用这些基线 |

## 设计文档分工

- `SystemDesign` 定义系统边界、依赖方向和部署形态。
- `BackendDesign`、`FrontendDesign`、`Database` 分别定义各自内部结构。
- `API` 定义组件之间的通信契约。
- `ComponentDiagram`、`Sequence`、`ClassDiagram`、`ERDiagram` 是上述权威设计的派生视图，不自行增加规则。
- `agent-capabilities` 定义单项 Agent 能力，不重复总体架构。

## 维护规则

1. 修改架构边界前先更新或新增 ADR。
2. 权限矩阵、API 字段、数据库字段和配置字段不得在多个 Markdown 文件中完整复制。
3. Current 与 Planned 内容必须分节或分文件标记。
4. 示例代码只用于解释边界，不作为可复制的完整实现。
5. 删除的重复内容由 Git 历史保留，不新建长期维护的 archive 副本。
6. 文档中的路径、命令、端口和接口必须可由仓库或机器契约验证。
