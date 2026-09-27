# Prompt 与模型上下文设计

> **状态**：Current + Planned（逐节标注）
> **最后核验**：2026-09-18
> **权威范围**：模型上下文、Tool Schema、Local Skill 注入和可见输出边界

权限、安全和数据边界由代码策略执行，Prompt 不能授予权限，也不能覆盖 hard-deny。

## 1. 当前模型输入

每一轮模型调用由 Agent Core 组装：

```text
可选 Local Skill 目录 system message
→ 当前 Conversation 的持久消息（按 token 上限裁剪）
→ 当前已完成 ToolCall 的 assistant/tool messages
→ ToolRegistry 动态生成的 provider-native Tool Schema
```

- 当前没有把 Knowledge Base、Embedding 检索或 User Memory 自动注入模型。
- Local Skill 目录只包含名称与描述；模型必须调用 `skill read` 才能读取正文。
- Local Skill 正文仍是不可信指令上下文，不获得新的文件、网络、命令或凭证权限。
- `python/agent/prompts/` 中的 LangChain 模板/Parser 是遗留未接线模块，不是当前 Agent Core 的系统 Prompt 或工具调用协议。

## 2. 当前 Tool 调用协议

Core 向 Provider 传递 `ToolRegistry` 中实际可用工具的名称、英文描述和 JSON Schema。模型通过 Provider 原生 tool call 字段返回工具名与参数；不要求把 ToolCall JSON 写进最终回答文本。

当前内置目录包含文件、只读检索、Bash、Web search/fetch、Todo、Sleep、Browser、Local Skill，以及启动时发现的 MCP Tool。具体清单由运行时决定，文档不维护第二份固定列表。

工具调用进入以下代码路径：

```text
Provider ToolCall
→ JSON Schema 校验与参数清理
→ PermissionManager
→ allow / approval_required / deny
→ Native 或 MCP 执行
→ ToolResult + TaskEvent
→ 作为 tool role 返回模型
```

Prompt 中声称“已获授权”没有效力；只有持久 Approval 和服务端策略能允许副作用。

## 3. 当前可见输出边界

- `message.*` 只承载用户可见的最终回答。
- Provider 单独返回的 reasoning，或回答开头完整的 `<think>...</think>`，会从最终文本分离并作为简短过程活动显示。
- Tool 参数、结果和错误进入结构化 `tool.*` 活动；默认不拼进回复框。
- Local Skill 不应要求暴露隐藏思维链；只可要求可审阅的计划、假设、来源或执行摘要。
- ToolResult 按不可信数据处理，不能改变系统权限；后续仍需加强内容注入隔离与来源标记。

## 4. Tool 描述规范

- 名称使用稳定的 `snake_case`；MCP Tool 使用 namespace 防冲突。
- 描述说明用途和重要副作用，不包含 Secret 或部署内部地址。
- Schema 必须限制类型、必填字段、字符串长度、枚举和额外字段。
- 资源范围与风险不只依赖描述，必须由 PermissionManager 根据规范化参数计算。
- Tool 失败返回稳定错误码、简短用户提示和可选内部设置路由，原始详情只在活动二级视图显示。

## 5. Local Skill 规范

Skill 的目录提示应尽量短，只帮助模型判断何时读取。`SKILL.md` 正文应包含：

- 适用条件与不适用条件；
- 输入、输出和停止条件；
- 可验证步骤与失败处理；
- 所需 Tool/MCP 能力，但不能假定这些能力已获批；
- 不包含凭证值、隐藏系统 Prompt 或要求绕过权限的指令。

当前 `instruction / workflow` kind 都只表示可读取的声明内容；版本化可执行 Workflow 尚未实现。

## 6. Planned Prompt Runtime

以下能力尚未接线：

- 版本化全局系统 Prompt 与按 Workspace 选择；
- Prompt hash、变更审计、A/B Eval 和回滚；
- Conversation Summary、User Memory 与 RAG 的带来源注入；
- 基于失败类型的正式 reflection/replan 状态机；
- 对 ToolResult/网页内容的更强注入隔离和引用标记；
- 上下文预算按 system/history/tool/result 分区及可观测指标。

引入这些能力时必须先定义 Eval：工具选择正确率、审批绕过率、无效 ToolCall 率、最终回答完整度、上下文成本和注入攻击成功率。只有模板文件而没有运行时接线与 Eval，不能标记为 Current。
