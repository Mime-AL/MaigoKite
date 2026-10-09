# MCP 集成

> 权威范围：当前传输方式、客户端/进程所有权、工具发现和调用边界。
> 本地技能格式见 [技能](../skills/skill-lifecycle.md)，策略见 [工具权限](../security/tool-permission.md)。

## 1. 当前生命周期

Python 核心服务是唯一 MCP Client 和子进程所有者，Go/Electron 不直接调用 MCP 工具。当前为自研 stdio 客户端，全面官方 SDK 迁移尚未完成；不因已有代码就继续扩建协议栈。

```text
部署者显式配置
→ 校验 command/args/cwd/env allowlist
→ 最小环境启动进程
→ initialize / initialized
→ tools/list 与工具注册
→ 受控调用
→ Core shutdown 终止进程组
```

当前 command 为 argv，不经过 shell；cwd 位于工作区，子进程不继承完整环境。清单只展示命名空间/传输方式/运行状态/工具名。stderr 当前被丢弃，不能假设已能在诊断页读取。

启动失败不得注册未就绪工具。健康重启、独立目录、资源配额、热切换、SkillVersion/Grant 和远程传输方式都未交付。

## 2. 发现与参数

结构定义/JSON-RPC 字段以 MCP 标准和实际版本为准，不维护协议字段副本。后续协议升级/取消优先调查官方 SDK，以薄产品 封装 保留权限与命名。

- 命名空间防工具名冲突；名称、描述和结构定义大小受限。
- Server 自报权限不构成授权；默认风险和 destructiveHint 只能收紧，由 ToolPolicy 最终判断。
- 参数复用 JSON Schema 校验与现有错误 DTO；引用不能在校验时联网或读取外部文件。
- 模型可见工具范围与执行授权要一致；全面按主体能力过滤仍须验收，不用“发现成功”宣称授权完成。

## 3. 调用与错误

已连接 MCP 工具新增公开转换，接入显式启用的新运行时；协议客户端仍是现有 stdio 实现。工具接线不等于官方 SDK、远端取消或恢复已经验收：

```text
ToolRegistry resolve / 参数规范化
→ PermissionPolicy / 现有 Approval
→ MCP tools/call（请求超时）
→ ToolResult / audit / 活动投影
```

返回内容是不可信数据，不授予权限。非对象结果映射为 MCP_INVALID_RESULT；`isError: true` 映射为 MCP_TOOL_ERROR/ToolResult.failure，保留原始结果和检查连接、凭证、参数的简短提示，不记成工具成功，也不伪造不存在的设置链接。

连接错误不盲目重试副作用。请求/工具调用 ID 用于关联；全面 追踪上下文传播 和 stderr 脱敏采集未接线。配置示例只在 [配置指南](../../user-guide/Configuration.md) 维护。

## 4. 取消、关闭和隔离限制

显式取消可阻止后续步骤，不能保证立即中断已进入第三方 `tools/call`的操作；超时限制等待不等于外部副作用停止。当前关闭终止进程组，等待约 5 秒后 kill；活动调用的优雅终止和 SDK 取消能力 需单独验证。

核心服务当前最小环境/cwd 检查不等于完整 OS 沙箱。凭证仅继承显式 allowlist，文件/网络/进程资源隔离尚未完整实现；不得把假想 SkillGrant 写成实际授权器。

## 5. 后续准入

先复用官方 MCP SDK 提供协议、stdio 生命周期和取消，再保留最薄命名/策略/错误投影。若官方能力与现有行为有差异，记录迁移和回归成本，不复制第二套协议实现。

远程传输方式只有真实个人服务需求后才设计服务身份、连接会话与网络信任；不预建多租户/插件 Manager。新能力须通过发现、错误、超时、取消、异常退出、资源回收与凭证隔离测试，见 [测试与验收](../../testing/TestPlan.md)。
