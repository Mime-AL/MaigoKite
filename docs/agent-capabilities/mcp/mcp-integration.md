# MCP 集成规范

> **状态**：Current
> **架构版本**：v1
> **最后核验**：2026-09-18
> **权威范围**：MCP transport、客户端、Server 生命周期和工具发现

Skill 包、安装和授权见 [Skill Lifecycle](../skills/skill-lifecycle.md)；工具权限见 [Tool Permission](../security/tool-permission.md)。

## 1. 边界

- Python Agent Core 是 MCP Client 所有者。
- 每个 MCP Server 是独立、受监督的工具进程。
- Go Gateway 和 Electron 不直接调用 MCP Tool。
- 当前版本只承诺 stdio transport。
- 远程/HTTP transport 为 Planned，启用前必须补充认证、租户和网络信任设计。

## 2. 生命周期

```text
SkillGrant 已验证
→ 构建最小进程环境
→ 启动 MCP Server
→ initialize
→ initialized
→ tools/list
→ 注册 MCPTool
→ ready / calls
→ shutdown / terminate
```

Python MCP Manager 维护每个 Server 的：

- skill version 与内容 hash。
- process ID 和工作目录。
- protocol version 和 capabilities。
- tool definitions。
- health、last used、restart count。
- credential/resource grants。

Phase 1 当前实现的是其中的最小闭环：由部署配置显式声明受信 stdio Server，Agent Core 负责启动、握手、发现、注册和关闭，并将调用送入统一 ToolPolicy。SkillGrant 绑定、健康重启、空闲回收、资源配额和热切换属于 Phase 2，不应从“已能发现工具”推断为已经实现。

## 3. 启动

启动前必须：

1. 验证 SkillVersion 与 SkillGrant。
2. 校验入口命令为解析后的 argv，不通过 shell 拼接。
3. 创建独立工作目录。
4. 构建环境变量 allowlist，不继承完整 `os.environ`。
5. 应用文件、网络、进程和资源限制。
6. 设置启动与握手 deadline。

启动失败不得把未完成初始化的 Tool 注册到 Registry。

## 4. 握手与兼容

- Client 提供支持的协议版本和客户端能力。
- Server 返回协议版本、Server 信息和 capabilities。
- 版本不兼容时终止进程并记录稳定错误码。
- 完成 initialized 通知后才能进行工具发现。
- Server 声明发生变化时重新验证能力和授权。

具体 JSON-RPC 字段以采用的 MCP 协议版本为准，本文不维护协议字段副本。

## 5. 工具发现

```text
tools/list result
→ 校验名称、描述和 inputSchema
→ 绑定 server/skill/version
→ 映射 capability 请求
→ ToolPolicy 验证可暴露范围
→ 注册 MCPTool
```

- 工具名在有效命名空间内唯一。
- 无效或过大的 Schema 拒绝注册。
- Server 自报权限不构成授权。
- Registry 对模型只暴露当前 Principal/Workspace 可用的工具。

## 6. 调用

```text
ExecutionEngine
→ ToolRegistry.resolve
→ 参数校验和 ToolPolicy
→ MCPClient.call_tool
→ 超时/取消传播
→ 结果大小和内容边界处理
→ ToolResult
```

- 调用 ID 与 Task/ToolCall/trace 关联。
- MCP stdout 只承载协议；stderr 进入限长、脱敏日志。
- 返回内容按不可信数据处理，不能成为系统指令。
- 副作用调用不得因连接错误盲目自动重试。

## 7. 停止与恢复

- 正常停止先拒绝新调用，等待或取消活动调用，再执行协议关闭。
- 超过 deadline 后终止进程树。
- 非预期退出使关联 Tool 暂时不可用并产生事件。
- 重启采用限次退避；连续失败进入 quarantined 状态。
- 更新 SkillVersion 时启动新实例、验证后切换，再关闭旧实例。

## 8. 凭证与资源

- Skill manifest 只声明 credential reference 和用途。
- CredentialProvider 按 SkillGrant 提供最小范围值。
- Secret 不写入 Skill 配置、ToolResult 或普通日志。
- 凭证撤销后相关 Server 必须重启或刷新上下文。
- 文件访问使用明确 Workspace 根和路径策略。

## 9. 健康与观测

指标至少包括：

- server start/ready latency。
- active/failed/restarted server 数。
- tool call latency、timeout、cancel 和 error count。
- protocol error 和 output truncation count。

健康状态区分 `starting`、`ready`、`degraded`、`failed`、`quarantined`、`stopped`。

## 10. 验收清单

- [x] 只有 Python 管理 MCP 生命周期。
- [x] Current transport 只有 stdio。
- [x] 子进程不继承完整环境。
- [ ] 未授权 Tool 不进入模型可见列表。
- [ ] 超时和取消终止完整进程树。
- [x] 副作用调用没有不安全的透明重试。
