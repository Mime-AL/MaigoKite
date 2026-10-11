# Inkline 阶段 5+6 收尾审阅

状态：本地实现与证据已交付，待最终用户验收。2026-10-11。

后续规则：除非用户明确要求，不再运行或新增软件测试。以下验证数字均为此前已经完成的记录，不表示清理后重新执行。

## 结论与范围

页面收尾已实施；构建通过，前端 154 项测试通过、0 失败。148 张 After 截图与 145 项浏览器检查通过，未出现页面异常或整页横向溢出。**不将这些截图算作真实 Provider / Electron / 前后端联合 E2E。**

本轮不新增依赖，不修改 Go、Electron、API 或业务 store。唯一事先允许的 UI store 例外是可选 textSize。后续用户明确允许运行中改权限，因此追加两个 Python Runtime 文件的窄范围修复，不引入权限状态机、continuation 或 cancellation framework。

共同工作区内另有并行变更：`api/client.ts`、`api/socket.ts`、`stores/run.ts`、`stores/session.ts`，以及 Runtime 的授权复用逻辑。本轮保留这些变更；验证针对当前共同版本，不能把它们归为本轮开发。没有执行 Git 命令、提交、索引修改或重启现有后端。

## A. 页面完成情况

| 要求 | 完成情况与边界 |
| --- | --- |
| Settings 导航与搜索 | 左分组/右内容；≤1100px 顶部导航；18 项字段检索与深链高亮，旧 tab=workspace 兼容，显示改为运行状态 |
| 字段反馈 | 助手名称、工具、模型、搜索凭证、权限就近反馈；页面加载错误仍在顶部并重试；失败保留输入 |
| 外观预览 | 主题/强调色/字号/纸纹即时应用；预览复用消息、节点、Pulse、模式控件，不添加假业务数据 |
| 工具用途 | 原有 12 项加 ask_user_question / delegate / list_subagent_models 的中文用途；未知外部工具只显示名字与暂无说明，模型说明折叠 |
| 模型 | 保留真实目录发现、手工填写、多选及默认模型；紧凑列表、键盘目录选择、Secret 默认遮蔽 |
| 凭证 | 仅可复制当前输入的新凭证；已保存 Secret 不读取回显。复制失败不显示已复制，异步反馈卸载后清理 |
| 权限 | 文字与形状说明后果，只有完全访问/危险操作使用朱砂；原有提交语义保留 |
| MCP / Skill | 展示已配置连接和已安装/禁用技能，不虚构应用市场。失败就地重试；重连沿用现有整体应用接口 |
| AuditLog | 真实时间线、操作者/动作/目标与筛选；无操作者不猜测；初始 60 条、按需加载更多 |
| DataManagement | 真实只读计数及空/载/错态。没有删除/清空接口，不添加危险操作按钮 |
| EmbeddingIndexes | 当前没有索引管理 API，入口说明可使用的文件能力，不伪造进度或重建功能 |
| Capsule | 同砚台视觉、可见最近/新会话选择，键盘逻辑不变；560×56 内容适配已检查，未启动 Electron 验收 |
| 文件与 diff | 树缩进与键盘导航、行号、折叠、复制反馈；沿用真实加载/重试。未连接的右键菜单删除，不添加假文件动作 |

字段搜索的限制：编辑器未打开时，模型地址/凭证搜索先定位服务列表；不猜测要编辑哪一个服务，也不为搜索打开一个新的未保存草稿。

工具用途补齐清单：`ask_user_question`、`delegate`、`list_subagent_models`。当前暴露的 15 项内置工具均已映射；历史 bash 是 exec_command 的非暴露别名，不重复显示。外部 MCP 工具名字由服务器提供，无法穷举中文映射；例如截图夹具的 browser__navigate 不能据此宣称用户已安装该工具。

### 页面 × 状态覆盖

✓ 为实际展示实现；N/A 表示没有对应数据请求/操作，不伪造状态。

| 页面/面板 | 加载 | 空态 | 错误/重试 | 证据或限制 |
| --- | --- | --- | --- | --- |
| Settings / 外观 | ✓ 父页 InkLoader | N/A 固定偏好 | ✓ 名称保存失败保留/重试 | 字段搜索与预览专项 |
| 模型 | ✓ | ✓ 添加服务 | ✓ 连接/发现/保存 | 冷加载、失败、全空截图 |
| 工具 / 联网搜索 | ✓ | ✓ 工具空清单/设置入口 | ✓ 区分加载/保存/凭证 | 冷态截图+单测 |
| 权限 | ✓ 父页 | N/A 三个固定选项 | ✓ 原保存错误就近显示 | 正常三断点；未单独制作冷态图片 |
| 运行状态 | ✓ | N/A 不把缺失状态当空 | ✓ 重试 | 两主题冷加载/失败截图 |
| MCP / Skill | ✓ | ✓ 添加入口 | ✓ 原因/编辑/重试 | 连接与技能专项 |
| 审计 | ✓ | ✓ 工作记录入口 | ✓ 重试 | 真实字段；不补造操作者 |
| 数据概况 | ✓ | ✓ 无数据说明/对话入口 | ✓ 重试 | 危险写 API 不存在 |
| 知识索引 | N/A | ✓ 可用文件能力入口 | N/A | 无索引接口，不制造错误或加载动画 |
| Capsule | ✓ Pulse 提交中 | ✓ 可输入的空砚台 | ✓ 提交错误可再次发送 | 当前截图只覆盖正常/固定窗口尺寸，未跑桌面 IPC |
| 文件树/预览 | ✓ | ✓ 空文件/选中文件/二进制 | ✓ 原因/重新加载 | 正常树与代码预览；未补齐冷态专项截图 |
| 变更 | ✓ | ✓ 无变更/非 Git | ✓ 原因/重试 | 正常 diff 专项；未补齐冷态专项截图 |
| Chat / Overview / Memory | 沿用阶段 4 | 沿用阶段 4 | 沿用阶段 4 | 不另改已验收的数据结构与视觉；本轮不是重新验收所有历史场景 |

“所有页面三态全部完成”不能简单打勾：无接口项不适用，未拍摄专项的状态在上表明确标注。

## 立即发送 / 队列 / 停止与权限

参考的是 Codex 的两种既有行为：进行中发送补充与下一轮排队，而非把终端 Tab 键照搬到桌面并破坏焦点导航。官方依据：[Codex Prompting](https://learn.chatgpt.com/docs/prompting)。

- Enter：立即发送到现有任务 inputs 接口；展示等待纳入/已纳入/本轮未采用。
- Alt+Enter：加入下一回合队列；砚台上方支持立即发送、编辑、移除。
- Esc / 独立停止按钮：取消当前执行。普通补充不当作停止。
- 等待审批时立即发送不可用，队列仍可用；失败与尚未采用的消息保留可见。
- 不声称已实现 Codex 的全部偏好或像素级复刻：本轮没有队列重排、可配置默认发送行为；没有新增前端调度器。

权限链路：

```text
既有会话权限 PUT → Repository
    ↓
模型提案后 + 工具实际开始前读取最新 PermissionPolicy
    ↓
允许 → 用权限快照执行（开始后不变）
需要审批 → LangGraph HITL / native interrupt → 现有 Approval API → resume
```

审批记录的 hash/version/风险和参数校验保留；放宽模式不自动批准一个已经展示的待审批项。原始 native HITL 批次用于 resume，新收紧的调用在 ToolNode 开始前用原生 interrupt 暂停。两个用于映射的 call-id 集合从原生 checkpoint interrupt 派生，不是新的持久状态机。只读子 Agent 不因为父模式变化中止，也不继承写权限；工作区变化/工具撤销仍维持原保护。

新增 5 个真实 LangGraph/Core 场景通过：模型等待时三种升降权限；同批第一项执行中收紧权限、第二项审批并恢复；等待审批时放宽模式、错误版本拒绝且 hash 不变。串行写入恢复后第一项没有重复执行。模型是本地测试 double，不是 Provider Live Test。

现有运行进程未重启；需要重启 Core 才会加载 Python 修复。

## B. 全局质量

### 对比度抽检

实际 DOM 计算前四种；ink-3/error/danger 用当前令牌在最深 paper-3 上测量。实色 WCAG 比值，不将纸纹逐像素采样或整站每个状态伪装成穷尽审查。

| 内容 | 浅色 | 深色 | 门槛 | 结果 |
| --- | --- | --- | --- | --- |
| body | 13.86:1 | 15.58:1 | ≥ 7:1 | 通过 |
| ink-2 | 7.25:1 | 10.00:1 | ≥ 4.5:1 | 通过 |
| ink-3 | 4.57:1 | 4.71:1 | ≥ 4.5:1 | 通过 |
| button | 12.80:1 | 14.09:1 | ≥ 4.5:1 | 通过 |
| input | 13.86:1 | 15.58:1 | ≥ 7:1 | 通过 |
| error | 11.59:1 | 11.99:1 | ≥ 7:1 | 通过 |
| danger | 4.64:1 | 4.74:1 | ≥ 4.5:1 | 通过 |

本轮抽检为石青主题、正文/二级/三级/按钮/输入/错误角色。未对六种强调色的每个状态执行穷尽对比度扫描。

### 键盘走查与焦点

以下为隔离 UI/HTTP 夹具，未实际创建用户会话或执行工具；真正运行时权限校验由 Python 场景补充。

| 顺序 | 操作 | 结束焦点 | 记录 |
| --- | --- | --- | --- |
| 1 | 新建会话 Ctrl+N | 消息内容 | [截图](../../web/test-results/inkline-final/after-keyboard-1.png) |
| 2 | 发送 Enter | 消息内容 | [截图](../../web/test-results/inkline-final/after-keyboard-2.png) |
| 3 | 运行中调整权限：只读 | 执行权限 | [截图](../../web/test-results/inkline-final/after-keyboard-3.png) |
| 4 | 加入队列 Alt+Enter | 消息内容 | [截图](../../web/test-results/inkline-final/after-keyboard-4.png) |
| 5 | 立即发送 Enter | 消息内容 | [截图](../../web/test-results/inkline-final/after-keyboard-5.png) |
| 6 | 审批按钮 Tab 定位 | 允许 Y | [截图](../../web/test-results/inkline-final/after-keyboard-6.png) |
| 7 | 批准 Enter | 消息内容 | [截图](../../web/test-results/inkline-final/after-keyboard-7.png) |
| 8 | 打开等你处理抽屉 Ctrl+J | drawer-tab-pending | [截图](../../web/test-results/inkline-final/after-keyboard-8.png) |
| 9 | 命令面板跳转设置 | 搜索设置 | [截图](../../web/test-results/inkline-final/after-keyboard-9.png) |
| 10 | 设置即时预览：字号 | 紧凑标准舒展 | [截图](../../web/test-results/inkline-final/after-keyboard-10.png) |

主流程为 Ctrl+N → Enter → 权限选择 → Alt+Enter → Enter → 审批 → Ctrl+J → Ctrl+K → 字号选择，无鼠标提交。菜单额外截图单独通过 DOM 聚焦拍摄，不冒充键盘主流程。

原生命令面板连续 12 次 Tab 保持焦点，Esc 后回到原触发位置；719px 覆盖面板互斥检查通过。宽屏抽屉是非模态工作面板，不加焦点陷阱。权限选择在运行中可操作，但模型/速度仍保持原有锁定。

两主题三断点的设置页没有无可读名称的图标按钮。全站依靠组件检查、原生 dialog 和 aria-live；没有真实读屏软件或 Electron 通知动作的端到端验收。

媒体偏好：[减少动态/浅](../../web/test-results/inkline-final/after-reduced-light-1440.png)、[减少动态/深](../../web/test-results/inkline-final/after-reduced-dark-1440.png)、[高对比/浅](../../web/test-results/inkline-final/after-contrast-light-1440.png)、[高对比/深](../../web/test-results/inkline-final/after-contrast-dark-1440.png)。

### 长会话性能

环境：系统 Chrome Headless + Vite 开发模式 + 隔离夹具；不是 Electron 发布包或真实流式网络。

| 场景 | 结果 |
| --- | --- |
| 数据规模 | 240 条记录 / 1200 工具步骤 |
| 默认分段展示 | 20 条记录、80 节点 |
| 默认安装至两帧呈现 | 84.3ms，包含 Vue 更新，不是全应用冷启动 |
| 默认滚动 | 中位 16.7ms / P95 18.5ms；超过 32ms：0 帧 |
| 全部展开 | 240 条、960 节点、29,534 DOM 元素 |
| 全展开滚动 | 中位 22.1ms / P95 33.4ms；超过 32ms：7 帧 |
| 分批展开总时间 | 1988ms，含人为逐批 30ms 间隔，不当作单次渲染耗时 |
| Rail + Minimap 单次更新 | 100.0ms，含两次 rAF 等待，不是纯 CPU 指令耗时 |
| 全段采样 Layout / Style / Script | 333.1 / 611.0 / 116.6ms，累计值而非单帧值 |

[长会话图片](../../web/test-results/inkline-final/after-long-conversation-240.png)。原始性能 trace 已按用户要求移出项目，采样结果保留在上表。默认分段流畅，全历史展开有掉帧，**B2 的“长列表不卡顿”未完全满足**。本轮没有以估计高度替代 Minimap 的真实位置，也没有另造虚拟列表框架。

### 构建体积

缺少阶段 1 之前可重建的产物，不能在禁止 Git 操作的条件下倒造基线；所以下表如实使用本轮开始（阶段 4 后）保存的产物。数据为 Web JS/CSS 分文件总和，gzip level 9；不含 Electron 和 sourcemap，也不是首屏实际传输量。

| 类型 | 阶段 4 后基线 | 当前 | 增长 |
| --- | --- | --- | --- |
| JS / raw | 669,087 B | 703,090 B | 5.08% |
| JS / gzip | 251,716 B | 265,611 B | 5.52% |
| CSS / raw | 172,348 B | 178,827 B | 3.76% |
| CSS / gzip | 31,368 B | 32,968 B | 5.10% |

均未超过 15%。新增展示组件、字段搜索和翻译增加体积；共同版本还包括并行 API/Session 变更，不能将全部增量归因于本轮视觉。没有新依赖。

### 清理证据

- 删除前引用检查无匹配；5 份源码保存在本地 [清理证明/备份](../../web/test-results/inkline-final/cleanup-proof-and-backup.json)，可恢复。
- 删除 LoadingSpinner、未接线 ContextMenu、兼容 globals 转发与两份已替代面板样式；原生托盘 setContextMenu 不属于删除对象。
- InboxPopover / ui.inboxOpen 已无引用；GUI 没有独立“通知”入口。
- 删除 30 个没有 var() 读取的令牌及 6 个无引用旧 i18n 标签；两项动态读取的断点令牌保留。
- 原有历史令牌/维度中仍有语义兼容项，未为了改名重构数据链路。
- 样式区扫描（不含 tokens / 唯一 SCSS 断点文件）：字面色值、px/rem/ms/deg 尺寸、非合成属性 transition 均 0；证据 [static-review.json](../../web/test-results/inkline-final/static-review.json)。
- “通知”剩余仅 Electron 参数校验的两个错误及其 i18n 键，未改 Electron；不是产品导航入口。保留“任务”作为实际执行对象，抽屉页签统一“运行”。
- 测试、夹具、截图位于既有忽略目录，未更改 Git 索引、忽略规则或创建提交。

### 检查结果与失败分类

| 检查 | 结果 |
| --- | --- |
| npm run build | 通过，含 vue-tsc 与 Electron 编译；不代表安装包 E2E |
| 前端全量 test:run | 154 通过、0 失败；本轮起点 136 通过、0 失败，无新增失败 |
| 全量 ESLint | 0 错误，183 警告；改动组件无新增 lint 错误 |
| Python 本次权限专项 | 5 通过，包括已完成写入不重复执行 |
| Python Runtime/上下文/进程恢复回归 | 45 通过、1 失败；不伪装全绿 |
| 两个 Runtime 文件 Ruff | 28 项既有样式问题：26 行长、2 引号注解；未进行范围外格式重构 |
| 浏览器检查 | 145 项通过；148 张 After；0 页面异常 |

前端剩余失败分类：**无**。只修测试装配/夹具：setup 的 dialog polyfill、旧 Settings 测试的搜索装配、Socket double 的 close；没有改旧断言。

Python 唯一失败：`test_core_shutdown_cancels_runs_before_closing_model_owner` 在关闭完成后期待旧 RuntimeError 文案，当前未改的 Core._track_langgraph_entry 抛 ConversationBusyError。取消/资源关闭的先前断言均通过；保留旧断言和真实失败，不顺手修改 Core 或扩大权限修复。

ESLint 警告分类：max-attributes-per-line 111、singleline-content-newline 22、html-indent 20、html-closing-bracket-newline 16、multiline-content-newline 11、html-self-closing 2，以及既有 MarkdownContent 的 no-v-html 1。Markdown 继续使用现有 html:false / DOMPurify 链路，未以删除警告替代安全处理。

保留的最终结果文件：[前端测试](../../web/test-results/inkline-final/final-tests.json)、[lint](../../web/test-results/inkline-final/final-lint.json)、[Python 回归](../../web/test-results/inkline-final/python-runtime-tests.xml)、[权限专项](../../web/test-results/inkline-final/live-permission-tests.xml)、[Python lint](../../web/test-results/inkline-final/python-runtime-lint.json)。构建原始日志已清理，此前通过的结果保留在本报告中。

## 截图对照

Before 60 张覆盖以下 10 个页面；After 148 张含正常、冷态、字段聚焦、键盘与性能专项。全部为本地展示夹具，没有把夹具里的连接/文件/凭证算作真实服务。

| 页面 | 浅 1440 | 浅 1100 | 浅 719 | 深 1440 | 深 1100 | 深 719 |
| --- | --- | --- | --- | --- | --- | --- |
| 外观 | [前](../../web/test-results/inkline-final/before-settings-general-light-1440.png) / [后](../../web/test-results/inkline-final/after-settings-general-light-1440.png) | [前](../../web/test-results/inkline-final/before-settings-general-light-1100.png) / [后](../../web/test-results/inkline-final/after-settings-general-light-1100.png) | [前](../../web/test-results/inkline-final/before-settings-general-light-719.png) / [后](../../web/test-results/inkline-final/after-settings-general-light-719.png) | [前](../../web/test-results/inkline-final/before-settings-general-dark-1440.png) / [后](../../web/test-results/inkline-final/after-settings-general-dark-1440.png) | [前](../../web/test-results/inkline-final/before-settings-general-dark-1100.png) / [后](../../web/test-results/inkline-final/after-settings-general-dark-1100.png) | [前](../../web/test-results/inkline-final/before-settings-general-dark-719.png) / [后](../../web/test-results/inkline-final/after-settings-general-dark-719.png) |
| 模型 | [前](../../web/test-results/inkline-final/before-settings-models-light-1440.png) / [后](../../web/test-results/inkline-final/after-settings-models-light-1440.png) | [前](../../web/test-results/inkline-final/before-settings-models-light-1100.png) / [后](../../web/test-results/inkline-final/after-settings-models-light-1100.png) | [前](../../web/test-results/inkline-final/before-settings-models-light-719.png) / [后](../../web/test-results/inkline-final/after-settings-models-light-719.png) | [前](../../web/test-results/inkline-final/before-settings-models-dark-1440.png) / [后](../../web/test-results/inkline-final/after-settings-models-dark-1440.png) | [前](../../web/test-results/inkline-final/before-settings-models-dark-1100.png) / [后](../../web/test-results/inkline-final/after-settings-models-dark-1100.png) | [前](../../web/test-results/inkline-final/before-settings-models-dark-719.png) / [后](../../web/test-results/inkline-final/after-settings-models-dark-719.png) |
| 工具 / 搜索 | [前](../../web/test-results/inkline-final/before-settings-tools-light-1440.png) / [后](../../web/test-results/inkline-final/after-settings-tools-light-1440.png) | [前](../../web/test-results/inkline-final/before-settings-tools-light-1100.png) / [后](../../web/test-results/inkline-final/after-settings-tools-light-1100.png) | [前](../../web/test-results/inkline-final/before-settings-tools-light-719.png) / [后](../../web/test-results/inkline-final/after-settings-tools-light-719.png) | [前](../../web/test-results/inkline-final/before-settings-tools-dark-1440.png) / [后](../../web/test-results/inkline-final/after-settings-tools-dark-1440.png) | [前](../../web/test-results/inkline-final/before-settings-tools-dark-1100.png) / [后](../../web/test-results/inkline-final/after-settings-tools-dark-1100.png) | [前](../../web/test-results/inkline-final/before-settings-tools-dark-719.png) / [后](../../web/test-results/inkline-final/after-settings-tools-dark-719.png) |
| 权限 | [前](../../web/test-results/inkline-final/before-settings-permissions-light-1440.png) / [后](../../web/test-results/inkline-final/after-settings-permissions-light-1440.png) | [前](../../web/test-results/inkline-final/before-settings-permissions-light-1100.png) / [后](../../web/test-results/inkline-final/after-settings-permissions-light-1100.png) | [前](../../web/test-results/inkline-final/before-settings-permissions-light-719.png) / [后](../../web/test-results/inkline-final/after-settings-permissions-light-719.png) | [前](../../web/test-results/inkline-final/before-settings-permissions-dark-1440.png) / [后](../../web/test-results/inkline-final/after-settings-permissions-dark-1440.png) | [前](../../web/test-results/inkline-final/before-settings-permissions-dark-1100.png) / [后](../../web/test-results/inkline-final/after-settings-permissions-dark-1100.png) | [前](../../web/test-results/inkline-final/before-settings-permissions-dark-719.png) / [后](../../web/test-results/inkline-final/after-settings-permissions-dark-719.png) |
| 运行状态 | [前](../../web/test-results/inkline-final/before-settings-workspace-light-1440.png) / [后](../../web/test-results/inkline-final/after-settings-workspace-light-1440.png) | [前](../../web/test-results/inkline-final/before-settings-workspace-light-1100.png) / [后](../../web/test-results/inkline-final/after-settings-workspace-light-1100.png) | [前](../../web/test-results/inkline-final/before-settings-workspace-light-719.png) / [后](../../web/test-results/inkline-final/after-settings-workspace-light-719.png) | [前](../../web/test-results/inkline-final/before-settings-workspace-dark-1440.png) / [后](../../web/test-results/inkline-final/after-settings-workspace-dark-1440.png) | [前](../../web/test-results/inkline-final/before-settings-workspace-dark-1100.png) / [后](../../web/test-results/inkline-final/after-settings-workspace-dark-1100.png) | [前](../../web/test-results/inkline-final/before-settings-workspace-dark-719.png) / [后](../../web/test-results/inkline-final/after-settings-workspace-dark-719.png) |
| MCP | [前](../../web/test-results/inkline-final/before-integrations-light-1440.png) / [后](../../web/test-results/inkline-final/after-integrations-light-1440.png) | [前](../../web/test-results/inkline-final/before-integrations-light-1100.png) / [后](../../web/test-results/inkline-final/after-integrations-light-1100.png) | [前](../../web/test-results/inkline-final/before-integrations-light-719.png) / [后](../../web/test-results/inkline-final/after-integrations-light-719.png) | [前](../../web/test-results/inkline-final/before-integrations-dark-1440.png) / [后](../../web/test-results/inkline-final/after-integrations-dark-1440.png) | [前](../../web/test-results/inkline-final/before-integrations-dark-1100.png) / [后](../../web/test-results/inkline-final/after-integrations-dark-1100.png) | [前](../../web/test-results/inkline-final/before-integrations-dark-719.png) / [后](../../web/test-results/inkline-final/after-integrations-dark-719.png) |
| 审计 | [前](../../web/test-results/inkline-final/before-audit-light-1440.png) / [后](../../web/test-results/inkline-final/after-audit-light-1440.png) | [前](../../web/test-results/inkline-final/before-audit-light-1100.png) / [后](../../web/test-results/inkline-final/after-audit-light-1100.png) | [前](../../web/test-results/inkline-final/before-audit-light-719.png) / [后](../../web/test-results/inkline-final/after-audit-light-719.png) | [前](../../web/test-results/inkline-final/before-audit-dark-1440.png) / [后](../../web/test-results/inkline-final/after-audit-dark-1440.png) | [前](../../web/test-results/inkline-final/before-audit-dark-1100.png) / [后](../../web/test-results/inkline-final/after-audit-dark-1100.png) | [前](../../web/test-results/inkline-final/before-audit-dark-719.png) / [后](../../web/test-results/inkline-final/after-audit-dark-719.png) |
| 数据概况 | [前](../../web/test-results/inkline-final/before-data-light-1440.png) / [后](../../web/test-results/inkline-final/after-data-light-1440.png) | [前](../../web/test-results/inkline-final/before-data-light-1100.png) / [后](../../web/test-results/inkline-final/after-data-light-1100.png) | [前](../../web/test-results/inkline-final/before-data-light-719.png) / [后](../../web/test-results/inkline-final/after-data-light-719.png) | [前](../../web/test-results/inkline-final/before-data-dark-1440.png) / [后](../../web/test-results/inkline-final/after-data-dark-1440.png) | [前](../../web/test-results/inkline-final/before-data-dark-1100.png) / [后](../../web/test-results/inkline-final/after-data-dark-1100.png) | [前](../../web/test-results/inkline-final/before-data-dark-719.png) / [后](../../web/test-results/inkline-final/after-data-dark-719.png) |
| 知识索引入口 | [前](../../web/test-results/inkline-final/before-knowledge-light-1440.png) / [后](../../web/test-results/inkline-final/after-knowledge-light-1440.png) | [前](../../web/test-results/inkline-final/before-knowledge-light-1100.png) / [后](../../web/test-results/inkline-final/after-knowledge-light-1100.png) | [前](../../web/test-results/inkline-final/before-knowledge-light-719.png) / [后](../../web/test-results/inkline-final/after-knowledge-light-719.png) | [前](../../web/test-results/inkline-final/before-knowledge-dark-1440.png) / [后](../../web/test-results/inkline-final/after-knowledge-dark-1440.png) | [前](../../web/test-results/inkline-final/before-knowledge-dark-1100.png) / [后](../../web/test-results/inkline-final/after-knowledge-dark-1100.png) | [前](../../web/test-results/inkline-final/before-knowledge-dark-719.png) / [后](../../web/test-results/inkline-final/after-knowledge-dark-719.png) |
| 速记胶囊 | [前](../../web/test-results/inkline-final/before-capsule-light-1440.png) / [后](../../web/test-results/inkline-final/after-capsule-light-1440.png) | [前](../../web/test-results/inkline-final/before-capsule-light-1100.png) / [后](../../web/test-results/inkline-final/after-capsule-light-1100.png) | [前](../../web/test-results/inkline-final/before-capsule-light-719.png) / [后](../../web/test-results/inkline-final/after-capsule-light-719.png) | [前](../../web/test-results/inkline-final/before-capsule-dark-1440.png) / [后](../../web/test-results/inkline-final/after-capsule-dark-1440.png) | [前](../../web/test-results/inkline-final/before-capsule-dark-1100.png) / [后](../../web/test-results/inkline-final/after-capsule-dark-1100.png) | [前](../../web/test-results/inkline-final/before-capsule-dark-719.png) / [后](../../web/test-results/inkline-final/after-capsule-dark-719.png) |

其他专项：[外观真实预览](../../web/test-results/inkline-final/after-appearance-preview-light-1440.png)、[字段搜索](../../web/test-results/inkline-final/after-field-search-dark-719.png)、[模型编辑器](../../web/test-results/inkline-final/after-model-editor-light-1100.png)、[Skill](../../web/test-results/inkline-final/after-skills-dark-719.png)、[文件树/预览](../../web/test-results/inkline-final/after-file-preview-dark-719.png)、[diff](../../web/test-results/inkline-final/after-workspace-diff-light-1440.png)、[队列](../../web/test-results/inkline-final/after-keyboard-4.png)、[发送菜单](../../web/test-results/inkline-final/after-send-now-queue-menu.png)、[胶囊真实尺寸](../../web/test-results/inkline-final/after-capsule-native-size-light.png)。

模型编辑器、Skill、文件预览和 diff 有两主题 × 三断点 After；这些追加专项没有阶段 5 前的逐项 Before，不倒造历史截图。冷态有 models/tools/runtime/integrations/audit/data 的浅深 719px；并非每个冷态都拍摄六个组合。完整文件名见 [截图/检查索引](../../web/test-results/inkline-final/after-visual.json)。

## 四条验收自评

| 标准 | 已做到 | 尚有差距 |
| --- | --- | --- |
| 好用 | 键盘主流程、字段搜索、就地反馈、立即发送/队列/停止和运行中权限边界 | 队列重排与可配置默认发送未做；模型搜索未打开时先定位服务列表 |
| 易用 | 信息三级层次、真实空/载/错、错误不丢草稿、没有伪统计或幽灵危险操作 | 无索引/数据删除 API；未完成真实桌面与读屏软件验收 |
| 美观 | 全站沿用已验收的纸面、墨线、Pulse、砚台与印记；两主题三断点检查 | 所有页面冷态六组合与每种强调色穷尽对比度尚缺；部分历史格式警告保留 |
| 惊艳 | 保留已验收的工作纸第一笔与执行小票，设置预览呈现真实片段 | 冲击力仍以用户评审为准，不自行宣布通过；全展开历史仍掉帧 |

## 修改文件

以下为本轮拥有的展示层文件；不包含四个受保护的并行 API/store 文件。大量组件只是精确尺寸的令牌迁移，不代表重新实现业务能力。

| 文件 | 修改依据 |
| --- | --- |
| [src/components/chat-area/ApprovalCard.vue](../../web/src/components/chat-area/ApprovalCard.vue) | 处理后的 DOM 焦点回收与令牌清理；提交版本/错误语义不另写。 |
| [src/components/chat-area/ChangeItem.vue](../../web/src/components/chat-area/ChangeItem.vue) | 纯展示样式令牌迁移、状态密度或格式清理，不调整 API / store 业务结构。 |
| [src/components/chat-area/InputBox.vue](../../web/src/components/chat-area/InputBox.vue) | 暴露展示聚焦入口，其他提交与停止路径保持原样。 |
| [src/components/chat-area/MessageList.vue](../../web/src/components/chat-area/MessageList.vue) | 纯展示样式令牌迁移、状态密度或格式清理，不调整 API / store 业务结构。 |
| [src/components/chat-area/QueuedMessages.vue](../../web/src/components/chat-area/QueuedMessages.vue) | 砚台上方紧凑队列、发送/编辑/移除及错误保留，不新增调度器。 |
| [src/components/chat-area/StepStatusPanel.vue](../../web/src/components/chat-area/StepStatusPanel.vue) | 纯展示样式令牌迁移、状态密度或格式清理，不调整 API / store 业务结构。 |
| [src/components/chat-area/SubagentSettings.vue](../../web/src/components/chat-area/SubagentSettings.vue) | 纯展示样式令牌迁移、状态密度或格式清理，不调整 API / store 业务结构。 |
| [src/components/chat-area/TaskViewPanel.vue](../../web/src/components/chat-area/TaskViewPanel.vue) | 纯展示样式令牌迁移、状态密度或格式清理，不调整 API / store 业务结构。 |
| [src/components/common/CodeBlock.vue](../../web/src/components/common/CodeBlock.vue) | 复制反馈只作用于当前内容；异步回执与计时器在卸载后不写展示状态。 |
| [src/components/common/CollapseCard.vue](../../web/src/components/common/CollapseCard.vue) | 纯展示样式令牌迁移、状态密度或格式清理，不调整 API / store 业务结构。 |
| [src/components/common/CommandPalette.vue](../../web/src/components/common/CommandPalette.vue) | 纯展示样式令牌迁移、状态密度或格式清理，不调整 API / store 业务结构。 |
| [src/components/common/IconSymbol.vue](../../web/src/components/common/IconSymbol.vue) | 纯展示样式令牌迁移、状态密度或格式清理，不调整 API / store 业务结构。 |
| [src/components/common/InkButton.vue](../../web/src/components/common/InkButton.vue) | 纯展示样式令牌迁移、状态密度或格式清理，不调整 API / store 业务结构。 |
| [src/components/common/InkLoader.vue](../../web/src/components/common/InkLoader.vue) | 纯展示样式令牌迁移、状态密度或格式清理，不调整 API / store 业务结构。 |
| [src/components/common/Kbd.vue](../../web/src/components/common/Kbd.vue) | 纯展示样式令牌迁移、状态密度或格式清理，不调整 API / store 业务结构。 |
| [src/components/common/ResizeHandle.vue](../../web/src/components/common/ResizeHandle.vue) | 纯展示样式令牌迁移、状态密度或格式清理，不调整 API / store 业务结构。 |
| [src/components/common/SessionTitle.vue](../../web/src/components/common/SessionTitle.vue) | 纯展示样式令牌迁移、状态密度或格式清理，不调整 API / store 业务结构。 |
| [src/components/common/StatusIcon.vue](../../web/src/components/common/StatusIcon.vue) | 纯展示样式令牌迁移、状态密度或格式清理，不调整 API / store 业务结构。 |
| [src/components/common/Tooltip.vue](../../web/src/components/common/Tooltip.vue) | 纯展示样式令牌迁移、状态密度或格式清理，不调整 API / store 业务结构。 |
| [src/components/drawer/JobsTab.vue](../../web/src/components/drawer/JobsTab.vue) | 纯展示样式令牌迁移、状态密度或格式清理，不调整 API / store 业务结构。 |
| [src/components/file-explorer/FileNode.vue](../../web/src/components/file-explorer/FileNode.vue) | 缩进引导线、aria-level/selected/expanded 与可读树项。 |
| [src/components/file-explorer/FilePreview.vue](../../web/src/components/file-explorer/FilePreview.vue) | 使用现有 CodeBlock 的行号、折叠和复制；加载/错误/二进制状态。 |
| [src/components/file-explorer/FileTree.vue](../../web/src/components/file-explorer/FileTree.vue) | 一个 roving tab stop，完整树键盘导航，沿用原 expand/select。 |
| [src/components/file-explorer/Toolbar.vue](../../web/src/components/file-explorer/Toolbar.vue) | 纯展示样式令牌迁移、状态密度或格式清理，不调整 API / store 业务结构。 |
| [src/components/file-explorer/WorkspaceDiff.vue](../../web/src/components/file-explorer/WorkspaceDiff.vue) | 统一 diff、加载、错误重试及可读状态；不添加不存在的回滚接口。 |
| [src/components/inkwell/ComposerFooter.vue](../../web/src/components/inkwell/ComposerFooter.vue) | 发送快捷键使用一致的产品文案。 |
| [src/components/inkwell/ComposerToolbar.vue](../../web/src/components/inkwell/ComposerToolbar.vue) | 立即发送/加入队列的已有提交事件；运行中只解锁权限选择，模型/速度仍锁定。 |
| [src/components/inkwell/InkMeter.vue](../../web/src/components/inkwell/InkMeter.vue) | 纯展示样式令牌迁移、状态密度或格式清理，不调整 API / store 业务结构。 |
| [src/components/inkwell/StatPopover.vue](../../web/src/components/inkwell/StatPopover.vue) | 复用原生 dialog/useDialog，焦点回收，小面积浮层。 |
| [src/components/interact/QuestionCard.vue](../../web/src/components/interact/QuestionCard.vue) | 回答后焦点回到可操作位置，不切割回复正文。 |
| [src/components/layout/AppLayout.vue](../../web/src/components/layout/AppLayout.vue) | 纯展示样式令牌迁移、状态密度或格式清理，不调整 API / store 业务结构。 |
| [src/components/layout/FileExplorer.vue](../../web/src/components/layout/FileExplorer.vue) | 文件面板加载与错误重试，保留工作区切换和现有请求。 |
| [src/components/layout/MainContent.vue](../../web/src/components/layout/MainContent.vue) | 纯展示样式令牌迁移、状态密度或格式清理，不调整 API / store 业务结构。 |
| [src/components/message/MemoryItem.vue](../../web/src/components/message/MemoryItem.vue) | 纯展示样式令牌迁移、状态密度或格式清理，不调整 API / store 业务结构。 |
| [src/components/rail/RailMinimap.vue](../../web/src/components/rail/RailMinimap.vue) | 纯展示样式令牌迁移、状态密度或格式清理，不调整 API / store 业务结构。 |
| [src/components/rail/RailNode.vue](../../web/src/components/rail/RailNode.vue) | 纯展示样式令牌迁移、状态密度或格式清理，不调整 API / store 业务结构。 |
| [src/components/rail/RailTrack.vue](../../web/src/components/rail/RailTrack.vue) | 纯展示样式令牌迁移、状态密度或格式清理，不调整 API / store 业务结构。 |
| [src/components/settings/AppearanceSettingsPanel.vue](../../web/src/components/settings/AppearanceSettingsPanel.vue) | 按任务分组、即时字号/主题预览，助手名称保存失败保留草稿并就地重试。 |
| [src/components/settings/ModelCatalogPicker.vue](../../web/src/components/settings/ModelCatalogPicker.vue) | 目录结果的上下键/Home/End 导航与滚动对齐。 |
| [src/components/settings/ModelProfileEditor.vue](../../web/src/components/settings/ModelProfileEditor.vue) | 凭证遮蔽、当前输入复制反馈、分组错误及反馈清理。 |
| [src/components/settings/ModelSelectionField.vue](../../web/src/components/settings/ModelSelectionField.vue) | 密度与字段搜索定位，原有多选/手工输入不变。 |
| [src/components/settings/ModelSettingsPanel.vue](../../web/src/components/settings/ModelSettingsPanel.vue) | 紧凑服务/模型列表及就地反馈，保留多模型、手工填写和目录发现。 |
| [src/components/settings/PermissionSettingsPanel.vue](../../web/src/components/settings/PermissionSettingsPanel.vue) | 权限后果与形状标签，朱砂仅用于高风险。 |
| [src/components/settings/RuntimeStatusPanel.vue](../../web/src/components/settings/RuntimeStatusPanel.vue) | 按真实健康/路径/版本展示；加载和重试，不虚构重启要求。 |
| [src/components/settings/SearchToolSettingsPanel.vue](../../web/src/components/settings/SearchToolSettingsPanel.vue) | 凭证保存/删除就地反馈，失败保留草稿，删除确认说明影响。 |
| [src/components/settings/ToolSettingsPanel.vue](../../web/src/components/settings/ToolSettingsPanel.vue) | 补齐用途映射，模型说明折叠；加载/保存分别重试。 |
| [src/components/shell/Drawer.vue](../../web/src/components/shell/Drawer.vue) | 页签键盘与关闭焦点回收；宽屏非模态抽屉不困住焦点。 |
| [src/components/shell/TitleBar.vue](../../web/src/components/shell/TitleBar.vue) | Pulse 汇总状态用 aria-live 播报。 |
| [src/components/sidebar/NavItem.vue](../../web/src/components/sidebar/NavItem.vue) | 纯展示样式令牌迁移、状态密度或格式清理，不调整 API / store 业务结构。 |
| [src/components/sidebar/NavMenu.vue](../../web/src/components/sidebar/NavMenu.vue) | 纯展示样式令牌迁移、状态密度或格式清理，不调整 API / store 业务结构。 |
| [src/components/sidebar/WorkspaceSelector.vue](../../web/src/components/sidebar/WorkspaceSelector.vue) | 纯展示样式令牌迁移、状态密度或格式清理，不调整 API / store 业务结构。 |
| [src/i18n/locales/en.ts](../../web/src/i18n/locales/en.ts) | 新增文案统一翻译；删除 6 个已无引用的旧入口/发送标签。 |
| [src/styles/agent-activity.scss](../../web/src/styles/agent-activity.scss) | 沿用组件职责，尺寸/颜色/间距/动效改用令牌；消除重复或非合成属性动画。 |
| [src/styles/base.scss](../../web/src/styles/base.scss) | 全局控件、焦点、墨色、减少动态效果和高对比模式统一。 |
| [src/styles/chat.scss](../../web/src/styles/chat.scss) | 沿用组件职责，尺寸/颜色/间距/动效改用令牌；消除重复或非合成属性动画。 |
| [src/styles/composer-controls.scss](../../web/src/styles/composer-controls.scss) | 沿用组件职责，尺寸/颜色/间距/动效改用令牌；消除重复或非合成属性动画。 |
| [src/styles/composer-menu.scss](../../web/src/styles/composer-menu.scss) | 沿用组件职责，尺寸/颜色/间距/动效改用令牌；消除重复或非合成属性动画。 |
| [src/styles/composer-stats.scss](../../web/src/styles/composer-stats.scss) | 沿用组件职责，尺寸/颜色/间距/动效改用令牌；消除重复或非合成属性动画。 |
| [src/styles/drawer.scss](../../web/src/styles/drawer.scss) | 沿用组件职责，尺寸/颜色/间距/动效改用令牌；消除重复或非合成属性动画。 |
| [src/styles/input-box.scss](../../web/src/styles/input-box.scss) | 沿用组件职责，尺寸/颜色/间距/动效改用令牌；消除重复或非合成属性动画。 |
| [src/styles/jobs-tab.scss](../../web/src/styles/jobs-tab.scss) | 沿用组件职责，尺寸/颜色/间距/动效改用令牌；消除重复或非合成属性动画。 |
| [src/styles/model-catalog.scss](../../web/src/styles/model-catalog.scss) | 沿用组件职责，尺寸/颜色/间距/动效改用令牌；消除重复或非合成属性动画。 |
| [src/styles/model-editor.scss](../../web/src/styles/model-editor.scss) | 沿用组件职责，尺寸/颜色/间距/动效改用令牌；消除重复或非合成属性动画。 |
| [src/styles/model-picker.scss](../../web/src/styles/model-picker.scss) | 沿用组件职责，尺寸/颜色/间距/动效改用令牌；消除重复或非合成属性动画。 |
| [src/styles/model-selection.scss](../../web/src/styles/model-selection.scss) | 沿用组件职责，尺寸/颜色/间距/动效改用令牌；消除重复或非合成属性动画。 |
| [src/styles/model-settings.scss](../../web/src/styles/model-settings.scss) | 沿用组件职责，尺寸/颜色/间距/动效改用令牌；消除重复或非合成属性动画。 |
| [src/styles/receipt.scss](../../web/src/styles/receipt.scss) | 沿用组件职责，尺寸/颜色/间距/动效改用令牌；消除重复或非合成属性动画。 |
| [src/styles/sidebar.scss](../../web/src/styles/sidebar.scss) | 沿用组件职责，尺寸/颜色/间距/动效改用令牌；消除重复或非合成属性动画。 |
| [src/styles/tokens.scss](../../web/src/styles/tokens.scss) | 收敛度量/层级/字距令牌、字号与压层文字对比度；删除 30 个无读取令牌。 |
| [src/styles/workspace-diff.scss](../../web/src/styles/workspace-diff.scss) | 沿用组件职责，尺寸/颜色/间距/动效改用令牌；消除重复或非合成属性动画。 |
| [src/styles/workspace-list.scss](../../web/src/styles/workspace-list.scss) | 沿用组件职责，尺寸/颜色/间距/动效改用令牌；消除重复或非合成属性动画。 |
| [src/views/AuditLog.vue](../../web/src/views/AuditLog.vue) | 真实审计时间线、筛选及分段呈现；没有操作者时如实显示未记录。 |
| [src/views/Capsule.vue](../../web/src/views/Capsule.vue) | 砚台式速记与可见发送目标，保留 Enter/Ctrl+Enter/Esc 和现有 IPC。 |
| [src/views/Chat.vue](../../web/src/views/Chat.vue) | 新页聚焦砚台；保持审批、引导、队列和原有会话控制。 |
| [src/views/DataManagement.vue](../../web/src/views/DataManagement.vue) | 只读真实统计、墨线加载、零数据入口与错误重试。 |
| [src/views/EmbeddingIndexes.vue](../../web/src/views/EmbeddingIndexes.vue) | 说明当前可用的文件能力；没有索引 API，不添加伪操作。 |
| [src/views/Integrations.vue](../../web/src/views/Integrations.vue) | 已配置 MCP 与已安装 Skill 分区，Pulse、原有编辑/应用/删除及就地重试。 |
| [src/views/Settings.vue](../../web/src/views/Settings.vue) | 分组导航、字段深链定位、加载重试和已打开面板的草稿保留。 |
| [src/components/common/SecretField.vue](../../web/src/components/common/SecretField.vue) | 遮蔽/显示、复制失败提示和计时器清理；不读取已保存 Secret。 |
| [src/components/settings/AppearancePreview.vue](../../web/src/components/settings/AppearancePreview.vue) | 复用真实消息、Pulse、RailGlyph 与模式控件，不用虚构示意图。 |
| [src/components/settings/SettingsSearch.vue](../../web/src/components/settings/SettingsSearch.vue) | 纯展示搜索、键盘选择与字段聚焦；不搜索凭证值。 |
| [src/config/settings-fields.ts](../../web/src/config/settings-fields.ts) | 18 项真实字段及中英文关键词映射，不增加配置接口。 |
| [src/styles/audit.scss](../../web/src/styles/audit.scss) | 沿用组件职责，尺寸/颜色/间距/动效改用令牌；消除重复或非合成属性动画。 |
| [src/styles/data.scss](../../web/src/styles/data.scss) | 沿用组件职责，尺寸/颜色/间距/动效改用令牌；消除重复或非合成属性动画。 |
| [src/styles/integrations.scss](../../web/src/styles/integrations.scss) | 沿用组件职责，尺寸/颜色/间距/动效改用令牌；消除重复或非合成属性动画。 |
| [src/styles/settings.scss](../../web/src/styles/settings.scss) | 沿用组件职责，尺寸/颜色/间距/动效改用令牌；消除重复或非合成属性动画。 |
| [src/utils/await-focus.ts](../../web/src/utils/await-focus.ts) | 仅 DOM 聚焦的薄辅助函数，不保存业务状态。 |
| [src/stores/ui.ts](../../web/src/stores/ui.ts) | 经单独允许增加可选外观 textSize；校验旧数据、持久化与 data-text-size，非业务字段。 |
| [python/agent/runtime/langgraph_runtime.py](../../python/agent/runtime/langgraph_runtime.py) | 用户单独允许的 live permission 边界：新策略读取、单操作快照、原生 HITL/interrupt 与审批安全匹配。并行授权复用变更不算本轮。 |
| [python/agent/runtime/subagents.py](../../python/agent/runtime/subagents.py) | 子 Agent 保持只读；父模式变化不误取消已经开始的调查，工具/工作区撤销保护保留。 |
| [docs/design/agent-ui-design.md](agent-ui-design.md) | 更新当前令牌、交互、无障碍和产品边界；各阶段历史证据保留但标为历史。 |
| [docs/project/Changelog.md](../project/Changelog.md) | 按阶段记录本地未发布变化，不宣称已经提交/合并。 |
| docs/design/inkline-final-review.md | 本报告：范围、证据、逐项差距与完整清单。 |

删除：`web/src/assets/styles/globals.scss`、`components/common/LoadingSpinner.vue`、`components/file-explorer/ContextMenu.vue`、`styles/runtime-status.scss`、`styles/search-tool-settings.scss`；组件/样式路径均位于 web/src。备份如上，可恢复。

保留的本地测试源码（既有忽略目录）：`web/src/tests/setup.ts`、`settings.test.ts`、`event-socket.test.ts` 的夹具修正；`final-presentation.test.ts`、`live-composer-permissions.test.ts`；`python/tests/unit/test_live_permissions.py`。没有借此新建测试基础设施或改变旧断言。

按用户要求，已将 24 个非必要文件移出项目，约 9.1 MB：5 个临时脚本/视觉夹具、1 个本轮 Python 字节码缓存，以及中间报告、构建日志、原始性能 trace 和失败诊断截图。可恢复副本位于 `/tmp/maigokite-test-cleanup-oIjFYr`，目录内保留原相对路径；临时目录可能被系统清理，不作为长期归档。阶段 1–4 验收材料、最终对照截图、最终结果和已删除源码的恢复备份未动。本次清理没有运行测试、操作 Git 或停止现有开发服务。

审查按 code-review / auto-test 技能收敛到凭证生命周期、异步反馈、焦点 ownership 与真实回归；项目不是技能示例中的 FastAPI/双库应用，不套用其不适用假设。
