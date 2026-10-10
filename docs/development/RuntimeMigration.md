# Runtime 切换记录

> 当前事实：2026-10-10 按用户“测试先不管，收尾第三批并完成第四批”的指令，
> 生产已统一到 LangChain create_agent + LangGraph，旧执行链和 feature flag 已删除。
> 随后用户授权前四批定向后端回归；最新结果与修复记录见下一节，不再沿用“切换后未验收”。
> 未运行前端/桌面全量、真实付费 Provider、全量 Python 或完整 lint/类型检查。
> 权威运行机制见 [AgentRuntime](../design/AgentRuntime.md)。

## 前四批收口验收（2026-10-10）

本节为最新证据，后文各轮记录保持历史语境。前四批按既定开发范围收口，不用第五批的
Workflow/SubAgent、完整 Browser 产品体验或第六批安装/手机功能继续延长旧 Runtime 迁移。
当前只有 LangGraph；没有恢复旧 Loop、开关、MCP 协议实现或增加通用取消/资源框架。

| 剩余项 | 本次完成 |
| --- | --- |
| 一：残留自研事件身份 | 删除两个无调用的 WebSocket broadcaster/inspector 包装，以及 Hub 自增序号/伪 ID 分配；真实 inspection API 保留 |
| 二：生命周期可靠性 | Core 关闭共用受保护任务，等根任务排空；Runtime/checkpoint/MCP/Browser/模型/产品库各自清理失败不跳过其余所有者，最后汇总错误；初始化失败同样清理 |
| 二：官方 MCP 接入验证 | Linux 官方 SDK stdio 发现、调用、权限审批、错误、超时、取消后共享会话复用及关闭；超时覆盖整个发送与等待 |
| 二：模型流取消 | 发现并修复 Anthropic 回调暂停时取消后响应流未关闭；约 50 行 request-local 生命周期适配，不复制协议/解析/重试，不关闭 SDK 共享客户端 |
| 三：事件补拉竞态 | Gateway 注册锁内先发送 `stream.ready`；Web 收到确认再分页补拉，缓冲实时事件，失败重连而不释放越过缺口的增量；Core 是唯一持久身份来源 |
| 三：上下文预算 | 摘要触发、摘要上限和调用前拒绝统一采用 SDK 已知容量扣除配置输出后的保守输入预算；未知模型保留用户上限；不增加容量表或 KV 缓存引擎 |
| 三：恢复状态隔离 | 默认 checkpoint 从实际 Repository 路径推导，避免临时/自定义产品库对应的执行状态误写默认库；显式配置仍优先 |
| 四：删除后的回归 | 在唯一生产 Runtime 上重跑文件审批、进程崩溃恢复、取消关闭、上下文与四种 Provider 本地协议；样例不再依赖旧执行链 |

### 实际运行结果

- Python 最后同组复跑：**63 passed in 38.19s**。范围为 `test_langgraph_production.py`、
  `test_context_optimization.py`、`test_mcp.py`、`test_langgraph_process_recovery.py`、
  `test_runtime_spike_http.py`、`scripts/acceptance/test_runtime_closure.py`，不是全量测试。
- Gateway：`internal/websocket` 与 `internal/api` 的 `Test(Stream|Broadcast|TaskResume|TaskHistory)`
  **7 个顶层测试通过**（其中包含 8 个恢复拒绝子用例）。包括真实本地 WebSocket 注册确认先于
  业务事件、持久身份保持、拒绝伪身份、恢复转发/事件历史及归属/版本/资格检查。
- 真实进程：审批 interrupt → 终止 Core → 新进程打开落盘 checkpoint → 批准 → 文件写入/最终回复；
  部分批准后重启同样通过，保留 hash/version 和不读取 continuation_json 的断言。
- 文件副作用：批准后未执行的 crash 恢复；写入后、ToolMessage/checkpoint 未提交的 crash 重放。
  后者工具可再次进入，但相同字节返回 reconciliation，避免再次物理写入；不是通用 exactly-once。
- 取消/关闭：模型 HTTP streaming、文件读取、受控慢工具、根任务准备/关闭、共享资源清理顺序；
  新增关闭失败注入与关闭等待者取消。Anthropic/Ollama 额外在 token callback 暂停点取消，
  验证响应断开、并发另一回合完成及取消后同模型可复用，不靠 GC 才关闭。
- 事件历史：1005 条既有事件取得快照水位后，再追加第 1006 条；跨 1000 条分页核对连续序号、
  原始 ID 和水位后的补拉。与 Gateway 注册测试共同验证后端契约，不冒充浏览器 GUI E2E。
- 样例首次运行暴露旧 ModelRequest 注入、新增观测事件及工具目录首位假设。修正现行 SDK/DTO
  fixture，保留业务结果、事件顺序、工具 schema、审批安全和单次写入断言，不恢复 legacy 来迎合测试。
  随后额外取消用例揭示 Anthropic 响应泄漏，修复生产适配后全部重跑通过。

Anthropic 修复依据为锁定环境源码与可复现回归：`ChatAnthropic._astream` 未在外层调用退出时
显式关闭嵌套流。已核对 [上游实现](https://github.com/langchain-ai/langchain/blob/master/libs/partners/anthropic/langchain_anthropic/chat_models.py)，
没有以重写 Provider 解决问题。`anthropic_lifecycle.py` 只通过 `_acreate` 登记 SDK 响应的公开
`close()`，由标准库 AsyncExitStack 在调用退出时等待关闭。该私有接缝需要随依赖升级复核；
上游确定性关闭修复且同样例通过后删除，不扩展为通用模型包装。

### Provider 矩阵

| Provider | Protocol | Live | Tool Loop | Cancel | 备注 |
| --- | --- | --- | --- | --- | --- |
| OpenAI | PROTOCOL PASS | UNVERIFIED | 本地 HTTP/SSE 通过 | 本地流断开通过 | 未请求真实 OpenAI 服务 |
| OpenAI-compatible | PROTOCOL PASS | UNVERIFIED | 本地 HTTP/SSE 通过 | 本地流断开通过 | 未验证用户目标网关/LM Studio 实例 |
| Anthropic | PROTOCOL PASS | UNVERIFIED | tool_use → tool_result → 第二轮/最终回复通过 | 回调暂停取消、共享客户端复用通过 | 官方格式模拟服务，含缓存控制字段；不算实际缓存命中 |
| Ollama | PROTOCOL PASS | UNVERIFIED | 本地 NDJSON 工具回合通过 | 回调暂停取消、共享客户端复用通过 | 未启动真实 Ollama 模型 |

测试沿用已有环境，无安装/升级包；设置 `PYTHONDONTWRITEBYTECODE=1`、`-B`、
`-p no:cacheprovider`，pytest basetemp、TMPDIR、Go GOCACHE/GOTMPDIR 使用专用
`/tmp/maigokite-batch14-wv0VB7`。早期 fixture 暴露 Repository 与 checkpoint 默认路径不一致，
可能触及既有 `~/.maigokite/data/agent.langgraph.db`；已修复并重新隔离复跑，无法确认原库中
哪些记录原本属于用户，因此没有清除或修改其历史。本轮明确拥有的临时目录约 268 MiB
（数据库、checkpoint、Go 编译缓存与临时构建）已删除，确认无本轮残留测试/fixture 进程。
本地验收样例按仓库忽略策略保留，MCP fixture 改名后另单项复跑通过，不重复计入 63 项。

### 完成范围与保留限制

前四批的开发交付与这次授权的定向后端收口完成；不是稳定发布声明，也不以移走未完成的
功能冒充通过。尚未运行的是 GUI 整链路、真实 Provider 服务、Windows/桌面安装与全量质量门禁，
不把它们标为通过。按仓库现有本地测试策略运行了保留在工作目录的样例，未撤销用户暂存的
测试文件删除；因此这份记录也不表示已经建立可从干净检出直接运行的 CI 测试包。

明确保留的执行边界：同步文件系统/线程不可抢占；MCP 本地等待取消不证明远端副作用停止；
只有已验证的文件任务开放恢复；file_write 重放不检测外部编辑冲突；checkpoint/产品事件之间
仍不是跨库事务。Workflow、子 Agent 后续增强、Browser 登录态/下载上传、安装包与手机入口
归第五/六批，不能用“前四批完成”覆盖它们。

## 当前部署与历史数据

普通启动即使用唯一 LangGraph Runtime，无需设置执行后端。旧 `agent.runtime` /
`MAIGOKITE_AGENT_RUNTIME` 已不读取；请从自定义配置中移除。可选 checkpoint 路径仍为：

```yaml
agent:
  langgraph_checkpoint_path: ~/.maigokite/data/agent.langgraph.db
```

省略时按产品 SQLite 路径生成相邻文件。产品库与 checkpoint 必须一起备份；不自动迁移或删除
历史聊天、工具调用、审批审计及 continuation_json 列。不支持在当前代码中切回旧后端；
如需代码回退，应使用版本控制，并保留两份数据库备份。

旧成功回合可导入可见消息开启新回合。无原生 checkpoint 的旧待审批任务：
允许会拒绝且不消费版本，拒绝/取消仍可使用；不能读取 continuation_json 强行续接。
无 checkpoint 的 interrupted 任务也不能 resume。检查真实文件/外部副作用后再发起新任务。

## 第三、四批此前源码收尾

- 聊天、审批、提问回答、恢复流共用小型 Gateway 转发函数；取消固定 10 分钟流截止。
  Core 执行不依赖 HTTP 连接存活。订阅失败记录 gRPC 状态码、断开对应 WS 触发既有补拉，
  不制造任务失败/取消事件，不添加事件总线或恢复框架。
- 唯一生产链：REST → gRPC → AgentCore → LangGraphRuntime → create_agent/HITL/ToolNode。
  停止和 shutdown 继续取消并等待根任务后关闭共享资源。
- Core 直接接受 BaseChatModel；模型设置、连接验证、命令行示例和 Spike 共用 native_model。
  删除旧 Provider 缓存与协议包装，ToolRegistry 删除无人使用的 invoke 执行入口。
  原有响应模式输出预算移入原生模型配置，缓存按模式区分，不复活旧模型协议。
  Core 从本轮开始时的 1,839 行降至 1,045 行；删除五个旧执行/聊天模块，
  Gateway 共用转发函数为 39 行。Runtime 不增加状态机、调度器、续接或取消树。
- 上下文/缓存/token 三项保留第三批实现：当前回合预算保护、原生压力摘要、稳定前缀、
  checkpoint 历史延续、工具输出减量与实际 usage 观测；没有新增 KV 缓存管理器。
- 现有样例/fixture 的导入改为原生模型边界；旧新比较样例保留产品里程碑断言，不保留可执行旧 Loop。
  未运行这些样例，剩余行为差异由后续授权验收确认，尤其旧 UI 展示和生成参数语义。
- 第三批 GUI 收尾：待审批/待回答从同一个会话快照按真实水位安装，不再用负序列伪造事件；
  截断快照不会把未返回的待处理项当成已关闭。问题卡片明确提交选项或自由文本到既有 AnswerQuestion，
  `question.requested/answered` 与审批分别投影，不把普通聊天队列当作回答通道。
  决定提交用户看到的版本；驳回理由进入既有后端审计。成功、冲突与传输失败均重新查询，
  不乐观伪造已批准/已回答，不自动重试执行。
- 第四批兼容层收尾：删除 `python/agent/runtime_spike` 的三个兼容文件；三个历史验证文件
  直接引用生产 `LangGraphRuntime / RuntimeRunRequest / native_model`。保留样例和既有 opt-in
  环境变量，不保留第二个模型工厂包装或另一条执行入口。本次未运行这些样例。

## DELETE / KEEP / ADAPT（当前）

| 对象 | 当前处理 |
| --- | --- |
| 旧 AgentCore Loop、流式 Tool Call 解析、旧续接/审批执行分支 | DELETE |
| ExecutionEngine、TaskManager、ContextManager | DELETE |
| ChatAdapter / IChatProvider、旧 Provider 缓存及私有降级 | DELETE |
| agent.runtime / MAIGOKITE_AGENT_RUNTIME 分支与开关 | DELETE |
| continuation_json 执行读写 | DELETE；列与历史数据 KEEP，仅默认空值兼容 |
| ToolRegistry | ADAPT：保留工具目录/发现，删除 invoke 调度入口 |
| Core、PermissionPolicy、Repository、Event DTO/审计、Workspace | KEEP：产品层 |
| LangGraphRuntime、原生模型工厂、官方 MCP SDK、Playwright | KEEP：唯一执行链及薄适配 |
| runtime_spike 别名与模型工厂包装 | DELETE：历史验证引用已迁入正式 Runtime |
| 无消费者的 WS broadcaster/inspector、自增事件身份 | DELETE：保留真实持久事件转发/检查 API |
| Anthropic response ownership shim | ADAPT：约 50 行仅修复流关闭；上游修复并回归后 DELETE |
| 历史验证样例 | ADAPT：本地样例直接调用生产实现；最新结果见顶部，未恢复用户暂存删除的测试文件 |

## 产品接线与本轮未覆盖的验收

随后 GUI 接线已补会话快照、提交幂等键、能力探测及中断任务显式恢复。状态以快照水位和
事件序列防止旧回放覆盖，活动历史仍单独补拉；消息提交结果不明时保留原键供用户确认，
不会自动重发或同时回填待发队列。该键仅保留在当前页面内，不承诺刷新页面后的提交确认。
`task.resumed` 只改变原回合的产品投影，不创建新任务；恢复前取当前版本，Core 仍负责
资格与权限检查。Mock 没有持久恢复能力，明确关闭该按钮。这些接线未运行验收。
待处理快照、结构化提问回答及驳回理由已补齐接线；第三、四批最新后端收口见顶部，
不外推为 GUI 验收通过。inspection、逐步插话、进程管理等体验仍属第五批待接线项，不能算作已交付；
没有重做界面布局或新增 Runtime。Mock 只返回空问题列表，不冒充已验证的提问续接流程。
Provider Live、真实 Browser 取消/外部副作用和桌面发布回归未补跑；本地 MCP 取消/超时及生命周期已有顶部的实际验收记录。
文件恢复仅限 file_read/file_write，仍是至少一次工具调用；相同字节可避免重写，
但不检测外部编辑冲突。同步线程无法抢占，浏览器会话无法跨 Core 重启恢复。
持久 Workflow 和手机远程仍未实现；单层只读、多模型 SubAgent 已有源码接入，后续增强与本轮验收无关，不能因旧链删除而计入完成度。

以下第 5–13 节为切换前的历史记录，所述“默认 legacy / KEEP BEHIND FLAG”均已被上述
用户指令与当前实现替代，不再是启动说明或阻止执行第四批的条件。保留这些记录仅用于区分
哪些版本实际运行过哪些验收；本文件不再承担临时开关配置。

---

## 5. 第一批轻量化与后续删除地图（2026-10-10）

本批只清理未接线的重复骨架、统一依赖入口、替换 MCP 协议实现，不切默认 Runtime。工作流、子 Agent、HITL 和 Recovery 能力仍保留，现有实现与缺口见 AgentRuntime 第 7 节；没有把删除空文件记为功能完成。

| 对象 | 本批处理 | 后续条件 / 保留边界 |
| --- | --- | --- |
| Workflow/HITL、SubAgent、Recovery 五个空骨架 | DELETE：移除没有消费者、方法仅为 `...` 的占位文件 | 保留能力需求，采用 LangGraph/HITL/子图；不重建同名自研框架 |
| MCP JSON-RPC 与进程轮询 | ADAPT：改用官方 SDK，删除私有协议实现 | 保留 `start/stop/list_tools/call_tool`、命名空间、风险、配置校验和错误投影；取消及关闭仍待验收 |
| Python 安装清单 | DELETE：移除子项目 pyproject/requirements，根清单和锁文件为唯一来源 | setup/build 使用根项目；协议生成和测试依赖在 dev，向量适配器依赖仅为可选组 |
| `AgentCore._run_agent/_stream_model/_execute_tool_batch` 等旧执行分支 | KEEP NOW → DELETE | 新路径已解除显式 `/tool` 依赖；满足第 3 节门禁后删除，保留 Core 产品组合与 API 方法 |
| ExecutionEngine / TaskManager | KEEP LEGACY ONLY → DELETE | 仅 legacy 模式创建；新模式取消与全局停止已不回退旧组件（本次未验收）。旧入口和消费者迁出后删除，保留源码不等于在新运行时创建第二套状态管理 |
| ChatAdapter / IChatProvider / 自研流和 Tool Call 解析 | ADAPT → DELETE LEGACY PARTS | 原生模型创建、端点兼容和 HTTP 生命周期已移至 native_model；新模型路径和默认连接验证不再依赖旧包装，显式注入的旧 Provider 保持兼容，待 legacy 消费者迁出再删 |
| `continuation_json` 读写及恢复分支 | KEEP NOW → DELETE CODE | 先处理历史待审批任务；旧库字段不能随删代码直接破坏性删除 |
| PermissionPolicy、Repository、产品 EventBus/DTO、Workspace | KEEP | 属于产品权限、审计、数据隔离和投影；不得因框架替换而取消 |
| `runtime_spike` 兼容入口与验证样本 | KEEP | 仍有历史验证消费者，后续统一迁移引用，不以删测试掩盖兼容问题 |
| `agent.runtime` 开关 | KEEP NOW → DELETE | 切默认并完成回归后连同旧执行路径移除，不等未来 Workflow/SubAgent/手机功能全部实现 |

本批完成依赖锁文件解析和只读源码核对，没有安装环境、运行测试、Ruff/mypy、项目构建或真实模型/MCP 验收。不得据此标记 READY TO DEFAULT；后续验收需用户明确要求后执行。

## 6. 正确性修复与入口收敛（2026-10-10，未验收）

- 聊天/批准后的审批续接共用凭证准备，审批流保留持久事件身份，新路径先检查模型再消费批准；2026-10-10 起拒绝直接结束回合、关闭剩余待审批项，不准备凭证或调用模型（本批未运行验收）。
- UI 待发队列绑定当前任务，仅成功终态触发并核对服务端状态；失败、取消、断线后等待再次确认。快照载入期间缓冲事件，HTTP 202 不直接推断批准已完成。
- 复用工作区已补齐的桌面 IPC，renderer 类型直接从真实 preload 白名单派生；不将此计为安装包验收。
- 新路径 `/tool` 通过公开模型 middleware 和原生 HITL/ToolNode；不新增工具调度器。原生模型工厂为生产、legacy 与 Spike 共用，客户端仍由 Core 管理。
- 成功回合从上一任务的终止 checkpoint 继承保留消息与摘要，失败/中断和 legacy 导入边界见 AgentRuntime；没有切换历史 checkpoint ID 或新增双向状态同步。
- 本轮只修改源码/文档、格式化 Go 和做 diff/引用核对；未运行测试、lint、类型检查、构建或 Live 验收。默认不变，旧 Loop、TaskManager、continuation 代码及数据均保留；Workflow/SubAgent 不提前扩建。

## 7. 第二批收尾与第三批上下文收敛（2026-10-10，未验收）

- 共用聊天准入事务与可选提交幂等键；补齐有界会话快照 gRPC/HTTP，重复请求只返回原任务。仅后端接线，未改前端；既有 GUI 不会自动获得幂等提交或新快照语义。
- 新路径加强 shutdown 的入口任务 drain、准入后启动失败状态和恢复入口边界；失败/取消后的历史导入显式标注副作用不确定性，不伪造无损续接。
- 使用原生 SummarizationMiddleware 加产品预算保护，记录摘要用量；按输入压力触发，摘要软目标约 10%、上限约 15% 且有绝对封顶，不固定压缩后的总占比。完整规则只在 AgentRuntime 维护。
- 文件分页、搜索限额、命令输出预览和日志路径让进入上下文的工具结果先减量；保留固定前缀与已有历史，不引入缓存预热、Provider KV 管理器或第二套摘要框架。
- 插话仅在包含该输入的模型调用成功返回后确认消费；预算拒绝/失败/取消不再提前发已消费回执。响应丢失后的服务端消费仍未知。
- 本批仅源码/文档修改、协议绑定生成、局部 Go 格式化与人工源码核对。按用户要求没有测试、lint、类型检查、构建或 Live 请求；缓存收益、跨进程恢复与取消正确性均未重新验收。默认继续 legacy，不进入第四批删除。

命令日志当前没有自动保留期/磁盘配额；file_read 仅在小片段间协作取消，单次 I/O 和其他线程工具仍不可抢占。MCP/浏览器外部副作用、文件至少一次重放、共享客户端关闭的实际表现仍须在获准验收后确认。

旧 `test_context_optimization.py` 中直接用 `trigger/keep` 构造 SafeSummarizationMiddleware 的样例已在第 9 节的获准测试中改为新的 `input_budget` 接口与带 context 的 runtime 样例；未为旧样例增加第二套生产摘要策略。通过记录仅覆盖该节所列范围。

## 8. 本批完成情况复核与补漏（2026-10-10，源码级）

按代码审查的资源所有权、授权顺序和产品状态一致性要求，核对 API → Core → Runtime → Repository/事件的实际调用关系，补齐以下问题：

| 发现的缺口 | 本次修正 |
| --- | --- |
| 失败后导入历史在中间追加 SystemMessage，可能被 Anthropic 拒绝 | 执行边界说明进入连续系统前缀；未改 Provider 协议 |
| 根任务首次调度前取消，可能不执行 finally | RunHandle 通过原生 Event 等待根任务进入清理范围；根任务先让出执行，再准备/执行 |
| 重复停止或等待者取消，可能打断根任务清理 | 检查原生 Task.cancelling，shield 等待；不建立 token tree |
| 审批/回答已提交，但执行元数据准备失败发生在根任务之外 | 准备移入根任务的异常/取消范围，沿用现有任务失败投影 |
| 活跃任务停止先操作句柄后校验工作区；迟到取消与成功投影冲突 | 先验证归属；终态事件与 Repository 已提交状态一致 |
| 归档会话提前拒绝幂等回执；删除竞态可能新建另一个会话 | 重放判断先于新请求归档检查；有指纹的请求不重新绑定会话 |
| 空 protobuf 列表在 HTTP 快照中成为 null | 空 messages/tasks/approvals/questions 固定为数组 |
| Core 将整个事件流 collect 后丢弃，长任务多保留一份历史 | 生产三处消费改为逐事件排空；保留 collect 供显式收集者使用 |
| 旧 usage 无调用开始记录却显示零次调用 | 调用/失败次数为 null，保留实际回执 token 小计 |
| 产品审批记录存在，但 checkpoint 已缺失/结束或等待的是另一调用 | “允许”在消费版本与审计决定前匹配原生 HITL interrupt、工具 ID 和名称；复用原有调用映射，参数 hash 仍由既有安全链验证；“拒绝”不依赖 checkpoint/模型 |
| Core 用 checkpoint 存在性选执行链，缺失时可能误走旧工具执行 | langgraph 启用时审批只进入新路径；缺失执行状态明确拒绝，不静默借用 legacy |
| shutdown 已停止准入，但审批/提问回答仍可新进入入口任务集合 | 共用入口跟踪方法先检查 Core 状态，关闭未启动的 coroutine 后拒绝，不让新请求越过关闭快照 |

复核未涉及并行修改的前端、模型发现/UI 工作；本次没有运行服务、测试、lint、类型检查、构建或 Live 请求，只核对源码并局部格式化。测试样例适配、新接口前端接入、真实 Provider/进程恢复/取消验收仍未完成。结论保持 `KEEP BEHIND FLAG`，不进入切默认和删除旧 Runtime 的第四批，也不以工作流/子 Agent 开发替代当前门禁。

下一步应结束反复源码补漏，进入获准后的定向验收：上下文/用量与摘要样例适配、取消/关闭、多项审批与进程重启、legacy 对照；失败先定位再修复，不放宽安全断言。新快照/提交键的 GUI 接入是第三批产品闭环的剩余项，但不是第四批后端选型/切默认的独立前置；第四批仍以真实运行时迁移门禁为准。测试授权和必要真实服务证据不足时，维持开关而非把“未运行”记为通过。

## 9. 获准的小规模后端回归（2026-10-10）

用户本次授权小规模测试及清理临时产物。最终同组复跑 **28 passed in 10.52s**：

- `test_context_optimization.py`：15 项，覆盖摘要失败保留历史、当前回合/工具配对、摘要预算拒绝、摘要取消与 UI 隔离、用量、调用上限、按需 Skill 和原生模型客户端回收。
- `test_langgraph_production.py`：9 项，覆盖读写/逐项审批、缺失 checkpoint 不回退 legacy 且拒绝仍可用、根任务启动前/模型流/同步线程等待取消、shutdown 落盘与客户端回收顺序、新旧写入语义对照。
- `test_langgraph_process_recovery.py`：1 项，真实终止并重启独立 Core 后批准续接，核对文件结果、单次工具启动、审批 hash/version、空 legacy continuation。模型端是本地模拟 HTTP/SSE，只算本地协议/进程恢复通过，不是 Provider LIVE PASS。
- `test_core.py`：3 项，聊天消息往返、审批规范化参数变化失效、工作区会话隔离；不是 legacy 全量回归。

首次受限沙箱运行在摘要取消用例挂起，已中止；同项本机隔离运行 0.14 秒通过，未把沙箱挂起判为产品缺陷。本机首轮 16 通过/9 失败主要暴露旧测试接线和预期：旧 Provider 工厂注入不再影响新 Runtime、SDK 规划提示与新增产品事件未计入、关闭入口任务应收到 CancelledError 而非普通响应。修正样例后增加三个小回归，最后同组复跑全部通过；没有修改生产逻辑来适配旧断言。

本轮不运行前端、Go、全量 Python、lint/类型检查、构建或真实 Provider；未补跑两个 file_write 副作用崩溃点、MCP/Browser 取消和完整发布回归。结论仍是 `KEEP BEHIND FLAG`，不切默认、不删除旧执行链。测试禁用 Python 字节码与 pytest 缓存，临时 DB/checkpoint/文件统一置于专用 `/tmp/maigokite-smoke-*` 目录，结束后清理，不动用户已有缓存和运行中的服务。

## 10. 新路径解除旧执行组件依赖（2026-10-10，未验收）

继续开发仅做执行入口收尾，没有把新功能开发扩大为迁移门槛：

- Core 在读取迁移开关后，只为 legacy 创建 TaskManager/ExecutionEngine；旧公开属性在新模式明确拒绝访问，避免误用时悄悄创建旧执行器。初始化/关闭只为真实存在的旧执行器更新工具注册表。
- langgraph 的单任务取消始终使用原生根任务路径，不再因缺少 checkpoint 而回退 ExecutionEngine；全局 `interrupt()` 同样取消并等待原生根任务。移除无人调用的 `owns_task` 检查点路由辅助方法。
- 复用既有会话锁处理“任务已入库、根任务未注册”的停止竞态；重复停止等待审批任务时不会反复发布取消，已结束的根句柄也不会吞掉停止操作。
- 关闭期间审批/停止不落回 legacy；单任务和全局停止也纳入 Core 的入口关闭范围。批量根任务清理先等待全部结果，再报告清理错误，不新增任务调度框架。

仅核对源码调用关系，未修改前端、运行服务、执行测试/检查/构建；第 9 节的 28 项通过不覆盖这些后续修改。默认仍为 legacy。剩余迁移收口是实际 GUI/Gateway 入口、常用 Provider/工具、两个文件副作用崩溃点与历史待审批任务交接；没有宣称该批已经达到切默认或删除门槛。

## 11. 审批授权绑定与文件工具收口（2026-10-10，未验收）

本批仅补后端恢复链路，不扩展 Workflow/子 Agent 或恢复框架：

- 审批入口在消费版本前，将当前工作区规范化后的 checkpoint 参数及风险绑定到已有审批 hash；恢复到工具节点时同样检查当前任务/调用的已消费审批，移除无条件 `approved=True`。重用其他任务/工作区的 Tool Call ID 明确报错，不能借旧投影或授权继续。
- 删除 Runtime 内按名称拦截 `file_write` 的私有核对分支，核对移到真实文件工具；旧、新运行时共用，工具仍经标准结果、审计和文件事件投影。按编码后的字节比较而非会折叠 CRLF 的文本比较，并在截断文件前完成编码。
- 同内容回执明确零实际写入和目标大小；原始 Diff 不可恢复就标明未知，不伪造 before image。仍是至少一次执行，不提供外部改写冲突检测、原子替换、跨运行文件锁或通用副作用框架。

本节落码时未运行测试、lint、类型检查、构建、服务或 Live 请求，也未修改前端。原 Spike 的 `test_file_write_reconciles_matching_content_after_result_checkpoint_crash` 当时仍注入替代 StructuredTool 并断言 Runtime 截断调用；现已在第 12 节迁至真实 FileWriteTool 的公开转换，并保留“不重复磁盘写入”及崩溃恢复断言，没有恢复 Runtime 名称特判。

结论仍为 `KEEP BEHIND FLAG`。下一步是定向验收和真实服务证据，不继续增加自研运行时层来代替这些门禁。

## 12. 获准的恢复与关闭定向验收（2026-10-10）

用户单独批准本轮小规模后端验收。首轮 **16 passed / 3 failed**，三个 Spike 崩溃样例暴露同一关闭竞态：根任务异常结束后，释放句柄的回调尚未运行，批量取消重新等待已结束的根任务，重复抛出旧异常而中断资源关闭。修复为仅取消尚未结束的根任务；活跃任务在清理过程中报错仍会在全部等待后上报，没有吞掉清理错误或放宽崩溃断言。

增加针对性样例后，同范围最终复跑 **26 passed in 29.03s**：

| 文件 / 范围 | 数量 | 证据 |
| --- | ---: | --- |
| `test_langgraph_production.py` | 12 | 新路径不创建旧执行组件、批准参数路径变化不消费版本、缺失 checkpoint 不走旧链、模型取消/同步线程限制、双运行全局停止、shutdown、读写审批、新旧写入语义对照 |
| `test_file_write_recovery.py` | 3 | 字节换行差异不误报相等、相同内容零写入且 mtime 不变、未知编码/编码失败保留原文件 |
| `test_langgraph_process_recovery.py` | 4 | 单项审批重启；两项调用仅批准第一项后重启，第二项批准前均未写入；批准后的写入前/写入后两个真实进程崩溃点 |
| `test_runtime_spike.py` 指定样例 | 4 | 写前恢复、一般副作用可重复、真实文件工具核对避免重写、慢异步工具取消；不是 Spike 全量 |
| `test_core.py` 指定样例 | 3 | legacy 消息往返、参数变更审批失效、工作区隔离；不是 legacy 全量 |

进程级样例真正杀死独立 Core，再启动新 Core，数据库/检查点共用临时磁盘路径而不继承内存。文件工具故障注入只在测试 worker 中，生产没有新增测试开关、续接数据或恢复状态机：

- Case A：批准后、实际写入前崩溃，恢复后执行写入一次。
- Case B：实际写入后、ToolMessage 返回前崩溃，恢复再进入工具节点，核对字节相等并返回零写入；两次工具启动可见，真实写入一次、文件 mtime 不变。不是将 at-least-once 声称为通用 exactly-once。
- 两种情况均核对审批 hash/status/version、`continuation_json={}`、最终消息、工具/任务终态、持久事件 ID/顺序与第二次模型调用。

边界：审批重启通过实际 Core gRPC `DecideApproval`；**已批准后的两个副作用崩溃点由测试 worker 显式调用内部 `LangGraphRuntime.recover`**，不代表已经交付 GUI/Gateway 的通用恢复入口。模型为本地模拟 OpenAI HTTP/SSE，只算协议/本地进程恢复通过，不是任何 Provider 的 LIVE PASS。未测 GUI/Gateway、真实 Provider、MCP/Browser 外部副作用、完整发布回归、全量 Python/Go/前端或 lint/类型检查/构建。

本轮临时 DB/checkpoint/文件统一放在 `/tmp/maigokite-runtime-acceptance-*`，禁用 pytest 缓存与 Python 字节码；结束后清理专用目录，不删除用户缓存或终止用户 Core。默认继续 legacy，结论保持 `KEEP BEHIND FLAG`。下一步只补真实入口与 Provider 证据、明确历史任务交接，不扩建另一套 Runtime。

## 13. 文件任务显式恢复的生产入口（2026-10-10）

本批接通后端生产链，不修改前端、不切默认、不删除 legacy：

```text
POST /api/v1/workspaces/:workspaceID/tasks/:taskID/resume {version}
→ 工作区 owner / 产品状态预检 / 现有凭证重新注入
→ 流式 gRPC ResumeTask
→ AgentCore.resume_task（现有入口任务跟踪）
→ LangGraphRuntime.recover（现有会话锁 + checkpoint + 根 asyncio.Task）
→ task.resumed + 既有审批/工具/最终回复事件 → Gateway WS
```

- Core 再校验主体、版本、最新会话回合、活跃根、归档和未完成检查点，不能依赖 Gateway 预检作为安全边界。等待审批仍走现有 Approval API。
- Repository 在已有锁内再次检查状态、版本与归档后提交 running 投影，避免准备期间的归档操作穿透预检；它不保存执行续接，也不验证或重建 checkpoint。
- public recovery 暂只允许保留历史中的 `file_read/file_write` 与这两项直接命令；其他工具的 checkpoint 不进入自动重放。检查保守地覆盖保留历史，可能拒绝继承过非文件工具的回合；这不是通用恢复能力。
- 不使用 `continuation_json`。权限仍由原 PermissionPolicy/审批审计执行；没有新的恢复状态机、取消树、仓库或事件总线。file_write 仍是至少一次调用 + 相同字节的自然核对，外部编辑冲突尚不受保护。
- gRPC 以本请求的 `task.resumed.trace_id` 作为事件转发准入，拒绝的并发请求不会收到另一请求的执行事件或误返回 202。HTTP 返回接受后，Core 仍持有执行；断线不停止任务。
- 恢复启动失败回到 interrupted，取消启动则落 cancelled；根任务启动后复用原取消/shutdown 清理路径，不销毁其他运行共享的模型客户端。
- 删除测试 worker 的 `AgentCore.initialize` 恢复钩子。写前/写后崩溃样例改为重启后调用正式 `ResumeTask`，核对持久事件身份、版本拒绝与最终投影。
- 新增 Core 拒绝边界、待审批不绕过、恢复运行取消/shutdown、重复请求流隔离样例；Gateway 样例覆盖 HTTP → 实际 gRPC client → 模拟 Core → WS、先注入凭证及保留事件身份。

验收记录：本节新入口和新增样例暂未执行；第 12 节的 26 项通过是修改前证据，不能冒充本接口已通过。仅重新生成 Python/Go 协议绑定，不将绑定生成算测试。真实 Provider、GUI 全链路、非文件副作用与发布回归仍未覆盖。默认和删除门禁保持不变。

协议生成复用已缓存的同版本 Go generators；本轮专用 `/tmp/maigokite-resume-tools-*` 中约 119 MB 的临时生成器及 Go 编译缓存已清理，可重新生成。没有清理用户缓存、修改密钥或终止正在使用的 Core。
