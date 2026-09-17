# 工具权限与执行安全

> **状态**：Current
> **架构版本**：v1
> **最后核验**：2026-09-18
> **权威范围**：工具风险等级、权限模式、审批与 hard-deny

系统级认证、凭证与网络安全见 [Security](../../ops-security/Security.md)。

## 1. 分层

```text
Go AccessPolicy                  Python ToolPolicy
谁能访问哪个 Workspace 资源       Agent 能否执行具体能力与参数
```

两层都必须通过。Gateway 的允许结果不能替代 ToolPolicy。

## 2. 风险等级

| 等级 | 含义 | 基础示例 |
|---|---|---|
| L1 | 无副作用读取 | 工作区内读取、glob、grep |
| L2 | 可恢复的低风险状态修改 | todo、短时等待、本地临时状态 |
| L3 | 外部交互或受限命令 | web search/fetch、受限 shell |
| L4 | 持久化写入 | 工作区文件写入、批量编辑 |
| L5 | 重大或难以恢复的影响 | 大范围删除、发布、发送外部消息、系统变更 |

等级是基础风险，不是最终决定。参数、路径、数据敏感度和部署策略可以提升等级或触发 hard deny。

## 3. 权限模式

| 用户档位 | 自动执行 | 请求批准 |
|---|---|---|
| 只读 `read_only` | 工作区内无副作用读取与搜索 | 编辑、命令、联网及其他副作用操作 |
| 工作区 `workspace` | 工作区读取、低风险状态、可恢复文件编辑、安全只读命令 | 联网、动态升级后的命令和重大影响操作 |
| 完全访问 `full_access` | 授权范围内 L1–L4 操作 | L5 重大影响操作 |

说明：

- `workspace` 的文件写入自动范围仅限当前 Workspace，安全命令限只读命令集合。
- `full_access` 不等于越权；仍受 Workspace、能力授权、范围、沙箱、额度和 hard-deny 限制。
- L5 不支持永久自动批准。
- L1–L5 是服务端风险模型，不作为普通用户需要逐工具调节的设置项。

## 4. 基础工具映射

| 工具能力 | 基础等级 | 动态规则 |
|---|---|---|
| file_read/glob/grep | L1 | 敏感或范围外路径升级/拒绝 |
| todo_write/sleep | L2 | 超额资源占用可拒绝 |
| web_search/web_fetch | L3 | 携带 Secret 或禁止域名时拒绝 |
| bash | L3 | 按命令、目录和副作用提升至 L4/L5/hard deny |
| file_write/file_edit | L4 | Workspace 外拒绝或提升 |
| external_send/publish | L5 | 必须展示接收方和内容预览 |

Skill 声明的是 capability 请求。最终等级由受信 ToolPolicy 根据能力和参数决定。未知能力默认拒绝。

## 5. 决策输入与结果

```text
evaluate(
  principal,
  workspace,
  task_mode,
  capability,
  normalized_arguments,
  resource_scope,
  active_grants,
  deployment_policy
) → allow | approval_required | deny
```

顺序：

1. Schema 校验并规范化参数。
2. 解析实际资源范围和副作用。
3. 检查 Workspace 访问与能力授权。
4. 检查 hard-deny。
5. 计算有效风险等级。
6. 应用模式与临时授权。
7. 检查沙箱、额度和并发限制。
8. 执行或创建审批。

## 6. Hard deny

Hard deny 优先于任何用户确认，包括但不限于：

- 沙箱逃逸或访问明确禁止的宿主资源。
- 读取/发送未授权 Secret。
- 破坏 Workspace 根目录之外的系统路径。
- 绕过审批、审计或安全边界。
- 违反部署管理员设置的不可覆盖策略。

规则应基于规范化参数和结构化能力，不仅依赖原始字符串正则。

## 7. 审批

审批必须绑定：

```text
principal_id
workspace_id
task_id
tool_call_id
capability
normalized_arguments_hash
resource_scope
risk_level
expires_at
version
```

- 参数或范围变化后审批失效。
- 审批只能消费一次。
- 过期、拒绝和重复提交必须有确定结果。
- UI 显示能力、目标、参数摘要、副作用、凭证与网络范围。
- Approval 与 Task/ToolCall 状态在同一事务中更新。

## 8. 沙箱

- Native Tool 使用路径、进程和网络策略限制。
- Bash 不经过 shell 展开；Linux 在 bubblewrap 可用时只挂载只读运行库和可写 Workspace。系统沙箱不可用时只保留受限只读命令，解释器和其他任意命令失败关闭。
- Workspace 不得配置为文件系统根目录；用户批准 L5 命令也不会解除 Workspace 文件系统边界。
- 第三方 MCP Server 默认按不受信代码处理。
- Skill 只获得声明并获批的目录、域名、资源和凭证引用。
- 子进程不继承完整宿主环境。
- 超时和取消必须传播到子进程及其后代。

## 9. 审计

记录：

- 决策输入的安全摘要和最终结果。
- 风险升级原因与命中的 hard-deny 规则。
- 审批创建、决定、消费和过期。
- Tool 开始、结束、失败、取消与资源范围。

不记录完整 Secret、认证头或未经脱敏的敏感内容。

## 10. 验收清单

- [x] 权限模式只有本文一份完整矩阵。
- [x] 用户界面只暴露三个稳定权限档位。
- [x] 未知能力默认拒绝。
- [x] L5 无永久自动批准。
- [x] hard-deny 无确认绕过路径。
- [x] 参数变化会使审批失效。
- [x] Native 与 MCP Tool 使用相同策略入口。
