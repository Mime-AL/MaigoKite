# NanamiGopher 日志与审计

> **状态**：Phase 1 Current + Production Planned
> **最后核验**：2026-09-18
> **权威范围**：当前输出、脱敏不变量和生产演进

## 1. 当前实现

- Go Gateway 输出带组件前缀的控制台日志。
- Python ConsoleObserver 使用标准 logging 输出事件名与 JSON 化数据。
- 安全/业务审计写入 SQLite `audit_events`，与普通运行日志分开查询。
- Task 的可恢复执行过程写入 `task_events`；它是产品事件账本，不等同于运维日志。
- 当前没有按级别日志文件、自动轮转、S3 同步或统一 JSON 外层 Schema。

因此生产日志文件路径、保留期和云同步都属于部署能力，不能从本文推断为当前程序已实现。

## 2. 当前脱敏不变量

- 不记录 API Key、Bearer Token、Cookie、完整认证头或 MCP 完整环境。
- Audit details 会过滤键名包含 `secret` 或 `token` 的字段；调用方仍必须避免把 Secret 放进其他键。
- Tool 审计优先记录工具名、风险、结果和限长摘要，不记录完整敏感参数。
- Browser 页面文本、模型 Prompt、ToolResult 和隐藏思维链不自动写入普通日志。
- 用户可见 TaskEvent 只保存恢复所需 payload，不是调试 dump。

当前键名过滤不是完整 DLP。接入生产前仍需递归脱敏、凭证模式检测和回归测试。

## 3. 目标结构化字段（Planned）

```text
timestamp, level, service, version,
request_id, trace_id, workspace_id, conversation_id,
task_id, tool_call_id, component, event, message,
error_code, duration_ms, metadata
```

- 全部时间使用 UTC。
- 字段缺失时省略，不写伪造占位值。
- `workspace_id` 可用于授权后检索；日志平台访问仍需最小权限。
- 高体积内容使用受控对象引用，不内嵌到日志。

## 4. 生产演进（Planned）

- 统一 Go/Python JSON logger 和 request/trace 上下文传播；
- stdout 由 systemd、Docker 或 Kubernetes 收集，应用不自行实现云上传；
- 本地桌面采用限大小、限份数的滚动文件，并提供用户导出前脱敏；
- Audit 采用独立保留策略和完整性保护；
- 明确每类数据的保留期、删除和访问审计。

## 5. 验收

- [x] 凭证不进入模型设置响应或 TaskEvent。
- [x] Tool/Approval 关键决定进入 Audit。
- [ ] Go/Python 统一结构化 Schema。
- [ ] 递归脱敏与 Secret 模式测试。
- [ ] 轮转、保留、导出和生产采集验证。
