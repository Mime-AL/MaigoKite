# MCP 集成规范

> **状态**：Current
> **架构版本**：v1
> **最后核验**：2026-09-18
> **权威范围**：MCP transport、客户端、Server 生命周期和工具发现

Skill 包、安装和授权见 [Skill Lifecycle](../skills/skill-lifecycle.md)；工具权限见 [Tool Permission](../security/tool-permission.md)。

## 1. 边界

- Python Agent Core 是 MCP Client 所有者。
- 每个 MCP Server 是独立工具进程；当前由 Core 启停，自动监督与重启仍是 Planned。
- Go Gateway 和 Electron 不直接调用 MCP Tool。
- 当前版本只承诺 stdio transport。
- 远程/HTTP transport 为 Planned，启用前必须补充认证、租户和网络信任设计。

## 2. 当前最小生命周期

```text
读取部署者显式配置
→ 校验 command / args / cwd / env allowlist
→ 构建最小进程环境
→ 启动 MCP Server
→ initialize
→ initialized
→ tools/list
→ 注册 MCPTool
→ calls（每次请求有超时）
→ Core shutdown 时 terminate / kill 进程组
```

当前运行清单只维护 namespace、transport、running/disabled 状态和工具名称。子进程不会继承完整环境，工作目录必须位于 Workspace；协议 stderr 当前丢弃，不进入日志。

### 2.1 目标完整生命周期（Planned）

目标 MCP Manager 还需维护每个 Server 的：

- skill version 与内容 hash。
- process ID 和工作目录。
- protocol version 和 capabilities。
- tool definitions。
- health、last used、restart count。
- credential/resource grants。

SkillGrant 绑定、健康重启、空闲回收、资源配额和热切换属于后续阶段，不应从“已能发现工具”推断为已经实现。

## 3. 目标启动约束（Current 子集 + Planned）

启动前必须：

1. 验证 SkillVersion 与 SkillGrant（Planned；当前信任边界是部署配置）。
2. 校验入口命令为解析后的 argv，不通过 shell 拼接。
3. 创建独立工作目录（Planned；当前只校验配置的 cwd 位于 Workspace）。
4. 构建环境变量 allowlist，不继承完整 `os.environ`。
5. 应用文件、网络、进程和资源限制（Planned）。
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
→ MCP 请求超时
→ 结果转换
→ ToolResult
```

- 调用 ID 与 Task/ToolCall/trace 关联。
- MCP stdout 只承载协议；stderr 的限长脱敏采集属于 Planned，当前不会回传 stderr。
- 返回内容按不可信数据处理，不能成为系统指令。
- 副作用调用不得因连接错误盲目自动重试。
- 显式取消会阻止后续 Tool 步骤，但当前不能强制中断已经进入 `tools/call` 的第三方 Server；依赖请求超时收敛。

## 7. 目标停止与恢复（Planned，除明确说明外）

- 当前 Core shutdown 直接终止 MCP 进程组，5 秒后强制 kill。
- 目标正常停止先拒绝新调用，等待或取消活动调用，再执行协议关闭。
- 目标超过调用 deadline 后终止对应调用或进程树。
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
