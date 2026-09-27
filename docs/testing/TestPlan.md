# NanamiGopher 测试计划

> **状态**：Current
> **最后核验**：2026-09-14
> **权威范围**：测试层次、关键场景和发布质量门

流水线执行方式见 [CI-CD](../deployment/CI-CD.md)。权限预期引用 [Tool Permission](../agent-capabilities/security/tool-permission.md)，不在本文复制第二份矩阵。

本文是质量目标，不代表每个测试项已经实现。当前可验证证据以 [Milestones](../project/Milestones.md) 和测试目录为准；标有 PostgreSQL、Outbox、lease、Workflow 或 Skill 包生命周期的场景只在对应能力进入交付阶段后成为发布门。

## 1. 测试层次

| 层次 | 目标 | 触发 |
|---|---|---|
| 单元 | 单个模块和状态转换 | 每次提交 |
| 契约 | OpenAPI、Proto、事件、配置、Skill Schema | 每次提交 |
| 集成 | Go/Python、数据库、Tool/MCP、Memory | PR |
| E2E | 用户关键流程 | 主分支/发布 |
| 安全 | 访问隔离、权限、Electron、Skill供应链 | PR/发布 |
| 恢复 | 崩溃、重连、迁移、备份恢复 | 发布 |
| 性能 | 延迟、吞吐、资源、长任务 | 定期/发布 |

覆盖率是辅助指标，不能替代契约、状态机和故障测试。

## 2. Go Gateway

- 认证上下文和 Workspace Membership。
- AccessPolicy 对资源列表、详情和命令的一致约束。
- 请求大小、限流、超时和错误映射。
- gRPC metadata/CallContext 传播。
- WebSocket身份、Origin、订阅过滤、重放和慢消费者。
- 不直接执行 Tool、不写 Agent领域状态。

## 3. Python Agent Core

- Task合法状态转换和乐观锁冲突。
- Message/Task/TaskEvent 原子创建（当前架构债务的目标回归测试）。
- Approval 创建、过期、版本和单次消费。
- ToolCall 幂等与不可重试副作用。
- cancellation/deadline 传播。
- 当前重启后 interrupted/等待审批恢复；引入调度器后再测试 lease 回收和安全续跑。

## 4. Tool 与 MCP

- Native/MCP 使用同一 ToolPolicy入口。
- 未知 capability 默认拒绝。
- 参数规范化后风险升级。
- 只读档位只自动执行无副作用读取，副作用操作进入审批。
- L5逐次审批，hard-deny 不可覆盖。
- MCP握手、工具发现、超时、取消、异常退出和隔离。
- MCP子进程不继承完整环境或无关 Secret。

## 5. Memory 与知识库

- Working、Conversation、User Memory职责隔离。
- Message顺序、Summary source range 和失效重建。
- User Memory来源、确认、可见性、过期和遗忘。
- Workspace间无检索泄露。
- Document删除会清理 chunk、FTS、Embedding 和缓存。
- 更换 Embedding/Chunk版本后索引可重建。

## 6. 数据库

- SQLite 空库与现存文件兼容升级；PostgreSQL 接入后增加双库迁移。
- 最低支持版本升级。
- 外键、唯一约束和状态约束。
- Workspace作为列表索引首列和查询条件。
- 引入 Outbox 后验证业务状态与 OutboxEvent 同事务。
- 活动 SQLite 的一致性备份与恢复。

## 7. 前端与 Electron

- Store从状态快照和事件恢复。
- 事件去重、sequence缺口和重连。
- 审批预览与服务端确认。
- 重复点击使用幂等键。
- `contextIsolation=true`、`nodeIntegration=false`、`sandbox=true`。
- Preload API白名单、参数校验和 unsubscribe。
- 外部导航、下载、新窗口和可执行文件路径限制。

## 8. E2E关键流程

1. 创建 Personal Workspace并完成对话。
2. Native只读 Tool成功执行。
3. 文件编辑触发符合模式的审批或自动范围。
4. 配置式 stdio MCP 启动、发现、调用和关闭；Skill 包导入/卸载在包生命周期实现后测试。
5. WebSocket 断线后任务继续并恢复事件。
6. 取消长任务；MCP 强制中断在 transport 取消实现后作为门禁。
7. 删除 Conversation；Document/派生数据在知识库实现后测试。
8. 当前本地 Membership 越权拒绝；完整 Team 成员流程在团队 API 实现后测试。

## 9. 安全测试

- IDOR与跨 Workspace访问。
- JWT/OIDC claims、算法、过期和密钥轮换。
- 路径穿越、符号链接和 Workspace边界。
- Shell参数注入和 hard-deny绕过。
- Prompt/检索/ToolResult注入边界。
- Skill包篡改、hash不一致、依赖能力升级。
- Secret日志、Memory、向量和 ToolResult泄露。

## 10. 性能与可靠性

基准至少记录：

- REST/gRPC/WebSocket延迟。
- 首 token和完整任务延迟。
- 并发 Task与ToolCall吞吐。
- SQLite 锁等待；PostgreSQL 接入后再测连接池。
- MCP进程启动和常驻资源。
- 长会话上下文构建和检索延迟。

测试必须注明硬件、模型、数据规模、并发和版本，不能只记录“提升倍数”。

## 11. 发布质量门

- [ ] 单元、契约、关键集成和安全测试通过。
- [ ] OpenAPI/Proto/事件无未批准 breaking change。
- [ ] 当前目标数据库迁移通过（Phase 1 为 SQLite；PostgreSQL 接入后扩展）。
- [ ] 无跨 Workspace访问。
- [ ] 权限模式和 hard-deny符合唯一规范。
- [ ] 备份可恢复。
- [ ] 桌面与服务器至少各完成一次 smoke test。
- [ ] P0/P1缺陷清零或有明确阻断决定。
