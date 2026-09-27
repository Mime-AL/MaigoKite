# NanamiGopher 监控与运行可见性

> **状态**：Phase 1 Current + Production Planned
> **最后核验**：2026-09-18

## 1. 当前能力

- Python `Observability` 支持事件、metric 和 trace 的 Observer 接口，当前只注册 ConsoleObserver。
- Go 使用 ConsoleObserver 输出 Gateway 运行信息。
- Agent 执行状态以 SQLite Task/TaskEvent/Approval/ToolCall 为事实来源。
- 前端活动流展示当前会话的 reasoning 摘要、Tool、审批和任务终态；断线后从 TaskEvent Journal 补拉。
- `/health`、`runtime-status` 和 MCP/Skill 只读清单提供基本运行诊断。

当前没有 Prometheus exporter、Grafana 仪表盘、Langfuse 接线、Token/费用指标、长期指标库、HTTP polling fallback 或告警通知集成。配置文件也不再暴露未接线的这些开关。

## 2. 当前应观测事件

| 范围 | 当前来源 | 关键标识 |
|---|---|---|
| Task | TaskEvent Journal | workspace、conversation、task、sequence |
| Tool | `tool.proposed/started/completed/failed` | task、tool_call、tool_name |
| Approval | `approval.requested/decided` + audit | approval、task、principal、version |
| Browser/MCP | Tool 活动与 audit | task、tool_call、错误码 |
| 进程健康 | Gateway health/runtime status | component、version、status |

事件 payload 不得包含 API Key、认证头、Cookie、完整环境变量或模型隐藏思维链。

## 3. Production Planned 指标

引入生产指标后至少覆盖：

- HTTP/gRPC 延迟和错误率；
- 模型首 token、总耗时、token 与费用；
- Task 成功、失败、取消、等待审批、超时和 interrupted；
- Tool/MCP 调用耗时、失败、超时与 Server 重启；
- WebSocket 连接、重连、事件补拉数量和 sequence 缺口；
- SQLite 锁等待/文件大小；接入 PostgreSQL 后增加连接池和锁；
- Browser 页面数、存活时间、崩溃和资源占用。

高基数 ID（task/tool_call/user）进入 trace 或日志，不作为长期 metric label。

## 4. Production Planned 告警

- P0：服务不可用、数据损坏、跨 Workspace 泄露或 Secret 泄露。
- P1：持续高错误率、任务队列停滞、事件无法持久化、磁盘临界。
- P2：延迟显著升高、MCP/Browser 持续失败、重连缺口增长。

具体阈值必须根据部署 SLO 和容量测试确定，不能把示例数字写成当前承诺。通知渠道和值班流程由部署方配置。

## 5. 交付门禁

- [x] 任务与工具活动有稳定 ID 和持久事件。
- [x] 客户端可恢复活动状态并显式停止任务。
- [ ] metrics exporter 与 trace propagation。
- [ ] Browser/MCP 资源指标和进程健康监督。
- [ ] 告警规则、仪表盘、值班和演练。
