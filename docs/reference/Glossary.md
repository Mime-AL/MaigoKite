# 项目术语

术语只解释边界，不声明交付状态。状态与验收见 [交付路线与状态](../project/Roadmap.md)，实现细节见对应设计。

| 术语 | 项目含义 / 权威说明 |
| --- | --- |
| 个人智能体 | 为单一用户和其选定流程服务的本地优先通用智能体，不是团队平台或编码专用产品 |
| 工作区 | 个人项目/资料与资源范围；成员关系/team 值仅保留兼容 |
| 网关 | Go 外部协议与身份/访问边界，不执行智能体工具 |
| AgentCore | Python 组合根，组织产品命令、资源和业务写入 |
| 智能体运行时 | 执行模型/工具循环及暂停恢复；新路径复用 LangChain/LangGraph，见 [智能体运行时设计](../design/AgentRuntime.md) |
| 运行时适配层 | 执行入口、审批桥接、UI 投影与业务持久化的桥接代码，不是第二个运行时 |
| legacy | 暂留旧自研主循环/ExecutionEngine/TaskManager 的迁移兼容分支 |
| ExecutionEngine | 旧路径工具策略与执行协调组件，不是新路径调度器 |
| ToolRegistry | 工具发现、结构定义、权限/产品元数据和公开转换入口 |
| 工具调用 / ToolMessage | 模型工具请求与结果，必须保持调用配对，不混入最终回复 |
| Checkpoint | LangGraph 执行状态，新路径恢复的事实来源；不同于业务库 |
| 产品投影 | messages/task_events 等用户查询视图，不驱动另一个执行状态机 |
| 任务事件 / sequence | 持久活动事件与会话内顺序；WebSocket 只是增量通道 |
| 审批 / HITL | MaigoKite 保存审批安全事实；LangGraph interrupt/恢复控制新路径暂停执行 |
| AccessPolicy / ToolPolicy | 网关资源访问检查 / Python 工具最终决策；二者都需通过 |
| Risk level / permission mode | 内部风险 L1–L5 / 用户三个模式，不能混为用户角色；矩阵见 [工具权限](../agent-capabilities/security/tool-permission.md) |
| hard-deny | 用户批准和 full_access 都不可覆盖的禁止规则 |
| 沙箱 | 实际进程/文件/网络隔离；应用参数检查不是完整 OS 沙箱 |
| MCP | 标准工具服务协议；当前 stdio，由核心服务持有客户端/子进程 |
| BrowserRuntime | 核心服务持有的 Playwright 浏览器能力，session 易失，不是独立爬虫/协议栈 |
| SKILL.md / 技能 | 按需读取的本地声明指令；当前 workflow kind 也不执行代码 |
| 工作流 | 多步骤流程；技能说明不等于已实现持久 DAG/调度引擎 |
| 子智能体 | 独立任务上下文与执行状态的委派；当前编排尚未交付 |
| 运行上下文 | 输入/运行投影，不另建长期消息事实库 |
| User Preference / 用户记忆 | 显式产品设置 / 可管理长期信息；CRUD 不等于自动注入 |
| 摘要 / 上下文压缩 | 有损上下文压缩，当前新路径是任务内，不等于完整跨任务记忆 |
| 向量嵌入 / FTS / Vector Index | 未来资料检索的派生表示/索引，原文才是权威 |
| 提示词 cache | 模型提供方前缀缓存，不是本地回答缓存；命中只取真实返回值 |
| Inspector / activity | 用户可见执行活动，不表示隐藏思维链或子智能体已交付 |
| 运行时监督器 | 桌面进程所有权；当前启动已存在，完整监督/等待退出尚未闭环 |
| PROTOCOL / LIVE / UNVERIFIED | 本地协议验收 / 真实服务验收 / 未运行；不能互相替代 |
| 阶段 | 历史工程阶段编号，不是产品界面或实时完成度标签 |

删除泛用模式、未接线接口和“Claude Code 生态派生产品”等旧术语；MaigoKite 不因参考外部实现就成为其分支或插件。
