# NanamiGopher 核心用例

> 状态：Current。用例描述产品行为，不重复 API 字段或数据库结构。

## 参与者

- 用户：发起任务、观察过程、批准/拒绝副作用并接管；
- Workspace Owner：配置模型、凭证、权限与部署级扩展；
- 扩展作者：编写声明式 Skill 或 MCP Server；
- Agent Core：任务、权限、工具、事件和恢复的权威执行者。

个人与团队用户复用同一 Workspace 模型；团队身份认证和共享资源属于后续阶段。

## UC-01 发起通用任务

前置：会话已选择可用模型。

1. 用户用自然语言描述目标；
2. Gateway 创建/接收请求，Agent Core 创建 Message 与 Task；
3. HTTP 返回 task ID，任务独立继续；
4. 模型回答或提出 ToolCall；
5. UI 将过程活动与最终回答分开展示；
6. Task 进入 succeeded、failed、cancelled、waiting_approval 或 interrupted。

异常：模型不可用时显示明确配置/连接错误，不静默切换到不同服务。

## UC-02 浏览网页并完成操作

前置：Browser Tool 已启用。

1. Agent 打开公开 HTTP(S) 页面并获得不透明 session ID；
2. Agent 读取标题、URL 和文本快照；
3. 若需填表、点击或按键，ToolPolicy 按动作判定风险；
4. 需要批准时任务暂停，UI 展示目标、选择器和风险；
5. 用户允许后继续，拒绝则任务结束；
6. 截图只能写入 Workspace，结束后关闭页面会话。

边界：不访问本机/私网地址，不在 URL 嵌入凭证，不绕过验证码或站点访问控制。

## UC-03 编排多个工具

1. 模型在一轮响应中提出一个或多个原生/MCP ToolCall；
2. 系统逐个执行并保存 ToolCall、结果和活动事件；
3. 中途审批时保存 continuation 和已完成结果；
4. 用户允许后从批次游标继续，不重复已完成副作用；
5. Tool 失败以结构化结果回注模型，模型可解释失败或选择替代工具；
6. 最终用户回复不包含原始调用 JSON 或转义残片。

## UC-04 离开、返回并恢复状态

1. 用户在任务运行时切换对话或关闭页面；
2. WebSocket 断开不等于取消任务；
3. 返回时 UI 读取消息、任务、审批和事件历史；
4. UI 按 event ID 去重、按 sequence 重建活动；
5. 随后连接实时事件流；
6. 若 Core 曾重启，等待审批任务仍可决定；其他无安全检查点任务显示 interrupted。

当前限制：历史读取和 WebSocket 订阅尚非原子动作，极小缺口窗口列为发布阻塞项。

## UC-05 批准或拒绝副作用

1. ToolPolicy 返回 approval_required；
2. Core 持久化 ToolCall、参数 hash、Approval 和 Task waiting 状态；
3. UI 展示能力、资源范围、关键参数、风险和过期时间；
4. 用户提交带版本的 allow/deny；
5. Core 校验 Workspace、主体、版本、hash 和过期；
6. allow 后执行并继续任务；deny 后取消任务。

任何客户端状态都不能替代 Core 授权。

## UC-06 停止持续任务

1. 运行时输入框发送控件切换为停止；
2. 用户点击停止，客户端按 task ID 调用取消；
3. Core 写入 cancelled，拒绝 pending Approval，取消活动 ToolCall；
4. 模型流和 Tool 在协作边界停止；
5. UI 收到 task.cancelled 并恢复可输入状态。

限制：不能保证所有第三方 MCP 进程立即响应取消，必须有超时和最终状态兜底。

## UC-07 使用本地 Skill

1. Owner 在配置目录添加 `skills/<name>/SKILL.md`；
2. Core 启动时校验并注册合法 Skill，非法条目只记录警告；
3. 模型从目录提示获知 Skill，先调用 `skill list/read`；
4. Skill 指令参与当前任务，但不直接获得新权限；
5. UI 显示实际加载的名称、版本、描述、kind 和来源。

安装、签名、更新、回滚和远程市场不属于此用例。

## UC-08 使用 MCP 工具

1. Owner 在部署配置中声明 stdio Server、参数、cwd 与环境变量 allowlist；
2. Core 启动子进程，执行 initialize/tools/list；
3. MCP Tool 以 namespace 名称进入统一 ToolRegistry；
4. 调用与原生 Tool 一样接受参数校验、权限、审批和审计；
5. Core shutdown 时关闭 MCP 子进程。

## UC-09 领域工作流（Planned）

研究、生图、电子开发、业余无线电、招聘等场景以 Skill/MCP/Workflow 包组合核心能力。进入产品路线图前必须通过用户需求证据、任务频率、失败成本和人工接管点评审，不因某个示例直接成为内核功能。
