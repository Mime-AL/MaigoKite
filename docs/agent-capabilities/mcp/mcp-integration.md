# MCP 集成

> 权威范围：当前传输方式、客户端/进程所有权、工具发现和调用边界。
> 本地技能格式见 [技能](../skills/skill-lifecycle.md)，策略见 [工具权限](../security/tool-permission.md)。

## 1. 当前生命周期

Python 核心服务是唯一 MCP Client 所有者，Go/Electron 不直接调用 MCP 工具。2026-10-10 第一批轻量化将 stdio 协议实现替换为官方 Python SDK；`agent.mcp.MCPClient` 仅保留配置校验、SDK 生命周期桥接和字典结果转换，调用入口不变。本次替换尚未运行集成或生命周期测试。

```text
部署者显式配置
→ 校验 command/args/cwd/env allowlist
→ SDK stdio_client 启动进程
→ SDK ClientSession 协商 / initialize
→ 分页 tools/list 与工具注册
→ 受控调用
→ Core shutdown 等待 SDK 上下文退出 / 子进程回收
```

当前 command 为 argv，不经过 shell；cwd 由 Core 限制在工作区。SDK 合并其平台基础环境白名单与 MaigoKite 允许的环境项/显式配置凭证，不继承完整环境。清单只展示命名空间/传输方式/运行状态/工具名。stderr 当前被丢弃，不能假设已能在诊断页读取。

SDK 的 AnyIO 上下文由单个连接所有者 `asyncio.Task` 进入和退出，以适配 Core 初始化/关闭可能位于不同任务的情况；它不调度工具，也不实现请求队列或取消树。单次工具调用取消不关闭共享连接；关闭等待所有者退出。协议解析、请求 ID、响应关联、初始化消息和进程终止由 SDK 承担，不读取 SDK 私有字段。

启动失败不得注册未就绪工具。健康重启、独立目录、资源配额、热切换、SkillVersion/Grant 和远程传输方式都未交付。

## 2. 发现与参数

结构定义/JSON-RPC 字段以 MCP 标准和锁定 SDK 为准，不维护协议字段副本。SDK 模型通过公开 `model_dump(by_alias=True)` 传给既有产品包装，保留 `inputSchema`、`isError` 等字段名；发现遍历分页并限制总时间、重复游标和最大页数，失败不返回不完整目录。

- 命名空间防工具名冲突；名称、描述和结构定义大小受限。
- Server 自报权限不构成授权；默认风险和 destructiveHint 只能收紧，由 ToolPolicy 最终判断。
- 参数复用 JSON Schema 校验与现有错误 DTO；引用不能在校验时联网或读取外部文件。
- 模型可见工具范围与执行授权要一致；全面按主体能力过滤仍须验收，不用“发现成功”宣称授权完成。

## 3. 调用与错误

已连接 MCP 工具通过公开转换接入显式启用的新运行时；legacy 与 LangGraph 共用此次 SDK 桥接，不保留第二套 MCP 协议客户端。代码替换不等于远端取消、恢复或 legacy 回归已经验收：

```text
ToolRegistry resolve / 参数规范化
→ PermissionPolicy / 现有 Approval
→ MCP tools/call（请求超时）
→ ToolResult / audit / 活动投影
```

返回内容是不可信数据，不授予权限。SDK 负责协议结果模型校验；产品包装仍保留非对象结果的 MCP_INVALID_RESULT 防御分支。`isError: true` 映射为 MCP_TOOL_ERROR/ToolResult.failure，保留原始结果和检查连接、凭证、参数的简短提示，不记成工具成功，也不伪造不存在的设置链接。

连接错误不盲目重试副作用。请求/工具调用 ID 用于关联；全面 追踪上下文传播 和 stderr 脱敏采集未接线。配置示例只在 [配置指南](../../user-guide/Configuration.md) 维护。

## 4. 取消、关闭和隔离限制

`asyncio.CancelledError` 向调用方传播，不被转换成成功结果或重试。当前锁定 SDK 的请求等待取消不能证明已向服务器发送取消通知，更不能证明远端副作用停止；超时也只限制等待。本批不重新实现协议取消通知，不承诺 MCP 远端取消确认。

Core 关闭时退出 SDK 上下文，由 SDK 关闭 stdin、等待并按平台回收进程；不再自行轮询 returncode 或发送 killpg。进程崩溃、活动调用关闭、Windows 子进程树和资源释放均未在本批验收。此替换也不修复 legacy Runtime 自身的取消限制。

核心服务当前最小环境/cwd 检查不等于完整 OS 沙箱。凭证仅继承显式 allowlist，文件/网络/进程资源隔离尚未完整实现；不得把假想 SkillGrant 写成实际授权器。

## 5. 后续准入

本批采用 `mcp>=1.28,<2`（锁文件为 1.30.0），不安装 CLI extra。已调查 [官方 v1 维护线](https://github.com/modelcontextprotocol/python-sdk/tree/v1.x) 和 [v2 迁移说明](https://py.sdk.modelcontextprotocol.io/migration/)：v1 仍接收关键修复，能满足现有 stdio/字段兼容；v2 涉及协议、类型和 HTTP 依赖栈变更，本批不顺带扩大迁移。后续升级需重新核对维护状态及取消需求，不能无限期冻结版本。

本批仅更新依赖清单/锁文件和代码，未安装依赖、未执行测试或构建；使用新代码前按 [开发指南](../../development/DevelopmentGuide.md) 同步根环境。SDK 替换不能标记为 LIVE PASS 或恢复验收通过。

远程传输方式只有真实个人服务需求后才设计服务身份、连接会话与网络信任；不预建多租户/插件 Manager。新能力须通过发现、错误、超时、取消、异常退出、资源回收与凭证隔离测试，见 [测试与验收](../../testing/TestPlan.md)。
