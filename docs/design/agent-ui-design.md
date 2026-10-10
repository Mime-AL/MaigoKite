# 个人 Agent 前端设计文档 · 「墨线 Inkline」

> 这套设计不追着 Codex / Claude Code 的“聊天框 + 工具卡片”走。核心想法是：**你的 Agent 走的每一步都是一条墨线，你随时能顺着它看、停下它、接着它走**。
> 技术基线：Vue 3 + TS + Vite 5 · Pinia · Vue Router 4 · SCSS + CSS 变量 · Electron 28 · fetch + WebSocket（Go Gateway）。
> 2026-10-11：阶段一视觉已确认；阶段二完成壳层与「等你处理」重构。历史样张见第 8 节，本轮实际范围、文件清单与验收证据见第 9 节；不代表后续页面改版已完成。

---

## 1. 设计身份

| 维度 | 主流 Agent 的做法 | Inkline 的做法 |
| --- | --- | --- |
| 隐喻 | 聊天窗 / 终端 | 手账 + 行程线：对话是正文，Agent 的动作是页边的一条墨线 |
| 气质 | 冷灰科技感 | 宣纸白 / 松烟墨，强调色只用一种「石青」，暖、静、耐看 |
| 过程展示 | 一张张卡片往下堆 | 卡片折进**轨道（Rail）**，正文只留结论 |
| 状态感知 | 转圈 spinner | 一枚会变形的**脉点（Pulse）**，同时出现在标题栏和托盘 |
| 人机协作 | 每个会话里各自弹审批 | 当前对话**就地处理**；抽屉的**「等你处理」**页签汇总跨会话事项，失焦时保持系统提醒 |
| 桌面能力 | 网页搬进壳里 | 全局快捷键唤出**速记胶囊**、无边框窗口、托盘常驻 |
| 个人属性 | 无记忆界面 | **「它记得」**面板：Agent 的记忆、偏好、人设可以直接看和改 |

设计原则：
1. 正文只放结论，过程沉到页边。
2. 一眼知道它在干嘛，一键让它停。
3. 它是你的，不是租来的：可以命名、配色、看到它记住了什么。
4. 不用强调色堆层级，靠留白、字重、墨色深浅。

---

## 2. 视觉语言

### 2.1 色彩（CSS 变量，SCSS 只引用变量）

| Token | 宣纸（Light） | 松烟（Dark） | 用途 |
| --- | --- | --- | --- |
| `--paper` | `#FAF8F4` | `#121314` | 主背景（带一点暖） |
| `--paper-2` | `#F2EFE9` | `#1A1B1D` | 侧栏、面板 |
| `--paper-3` | `#E9E5DD` | `#232427` | 用户消息、悬停 |
| `--rule` | `#DDD8CE` | `#2E3033` | 分隔线、轨道线 |
| `--ink` | `#1F1E1C` | `#E8E6E1` | 正文 |
| `--ink-2` | `#4E534B` | `#BCC3B8` | 次要正文、导航、标签、说明和状态 |
| `--ink-3` | `#6F7268` | `#818A7E` | 占位、时间戳和装饰性元信息，不用于操作说明 |
| `--accent`（石青） | `#2F6F6A` | `#5FA59D` | 主按钮、运行中、焦点 |
| `--accent-soft` | `#2F6F6A14` | `#5FA59D1F` | 选中底色 |
| `--seal`（朱砂） | `#B5442E` | `#D0644D` | 仅用于危险操作和「驳回」印记 |
| `--ok` | `#4C7A3F` | `#7FB06E` | 成功 |
| `--wait` | `#B07A1F` | `#D7A548` | 等待你 |

规则：页面上同时出现的饱和色不超过两种；`--seal` 只在需要你警惕的时候出现。
用户可以在设置里把 `--accent` 换成另外 5 种预设（黛蓝、竹青、赭石、藕荷、墨），这是「它是你的」的一部分。

### 2.2 字体
- 界面：`"Inter", "HarmonyOS Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif`
- 签名字体（只用在四处：空态问候、会话标题、回合小结标题、审批印记）：`"Source Han Serif SC", "Noto Serif SC", serif`。宋体用得少，才有辨识度。
- 代码：`"JetBrains Mono", "Cascadia Code", monospace`
- 字号：正文 15/26，次要 13/20，代码 13/20，标题 20/28（宋体）

### 2.3 形状与质感
- 圆角：6（Chip）/ 10（卡片）/ 14（输入区）。比主流的大圆角更收敛，像纸的切角。
- 深度使用四级 elevation；抽屉使用 `--shadow-raised`，命令面板使用 `--shadow-float`，不为每个会话条目添加阴影。
- 背景可开启极淡的纸纹噪点（opacity 0.025，设置里可关）。
- 控件 140ms、面板 240ms，复用 motion / ease 令牌。当前墨线生长使用 transform / opacity；减少动态效果时面板降级为 80ms 淡入。

---

## 3. 布局

```
┌───────────────────────────────────────────────────────────────┐
│ ▥  脉点  会话标题（宋体）              ◐   抽屉②  ─ □ ×       │ ← 标题栏高度使用现有令牌
├──────────┬──────────────────────────────────────┬─────────────┤
│ 侧栏     │  ┆                                   │ 抽屉        │
│ 240px    │  ○─ 翻了 3 个文件                    │ (按需滑出)  │
│          │  ┆   ┌─────────────────────────────┐ │ 变更 / 任务 │
│ ✎ 新页   │  ┆   │ 正文：Agent 的回答           │ │ / 计划      │
│ ⌕ 搜索   │  ●─ 跑了 pnpm build ✓             │ │             │
│          │  ┆   └─────────────────────────────┘ │             │
│ 今天     │  ◆ 回合小结 · 2m · 3 处改动          │             │
│ 本周     │                                      │             │
│ 更早     │  ┌───────── 砚台（输入区）──────────┐ │             │
│ 它记得 ✦ │  │                                  │ │             │
│ ⚙        │  └──────────────────────────────────┘ │             │
└──────────┴──────────────────────────────────────┴─────────────┘
```

- **标题栏**：保留现有 Electron 无边框窗口；侧栏开关只有一处。脉点 + 宋体会话标题支持中间省略和双击重命名，右侧为主题、抽屉与窗口按钮，不再有独立待处理弹层。
- **侧栏**：工作区 > 今天 / 本周 / 更早 > 会话。运行中的会话使用脉点；非当前会话的阻塞项使用等待菱形。底部保留「它记得」入口。`Ctrl+B` 收起。
- **正文区**：最大宽度 720px，左侧留 48px 给轨道。
- **抽屉**：保留宽度拖拽与持久化；「等你处理」跨会话，变更 / 任务 / 计划 / 文件沿用现有上下文。`Ctrl+.` 打开，`Ctrl+J` 直接切到待处理页签。
- 小于 1100px 时抽屉变覆盖层；小于 720px 时侧栏变抽屉（为将来的移动端预留）。

---

## 4. 签名组件

### 4.1 轨道 Rail（Inkline 的核心）
- 正文左侧一条 1px `--rule` 竖线，Agent 每做一步就在线上长出一个节点。
- 节点类型：
  - `○` 只读（读文件、搜索），连续的会合并成一个节点：「翻了 6 个文件」
  - `●` 有动作（执行命令、写文件）
  - `◇` 等你（审批 / 提问），用 `--wait` 色，节点会轻轻呼吸
  - `◆` 回合结束，后面跟回合小结
  - `×` 失败，用墨色并自动展开；朱砂保留给危险操作和驳回印记
  - `✦` 记下了一条记忆
- 节点右边是一行灰字摘要，点击就地展开详情：参数、输出（前 20 行）、耗时、退出码。
- 运行中的那段线用 `--accent` 色，从上往下“生长”。
- 长会话的滚动条位置显示**墨线缩略图**：节点密集的地方墨色更深，点击直接跳过去。
- 和主流卡片相比：正文读起来连贯，过程又一个不少。

### 4.2 脉点 Pulse
一个 10px 的图形，状态变化时形状跟着变，不只是换颜色：

| 状态 | 形态 | 颜色 |
| --- | --- | --- |
| 静息 | 实心圆 | `--ink-3` |
| 思考 | 圆形缓慢呼吸 | `--accent` |
| 行动 | 圆拉成短横线并左右移动 | `--accent` |
| 等你 | 菱形，轻微抖动一次后静止 | `--wait` |
| 出错 | 叉号 | `--ink-2` |
| 离线 | 空心圆 | `--ink-3` |

出现在三个地方：标题栏、侧栏会话项、系统托盘图标（Electron `Tray.setImage` 切换预渲染的图标）。

### 4.3 回合小结（Receipt）
每轮结束后在轨道末尾生成一张小票样式的小结（宋体标题，虚线分隔）：
```
◆ 回合小结                       14:32 · 用时 2m08s
  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
  改动 3 个文件  +42 −7      [查看变更]
  执行 2 条命令  全部通过
  等你 1 次      已允许
  上下文 38%                 [撤销本回合]
```
「撤销本回合」由 Gateway 根据回合开始时的文件快照回滚。很多 Agent 在这一点上做得不够。

### 4.4 「等你处理」

- 当前会话的审批与提问就在 Rail 对应位置处理；不在视口内时，砚台上方提示「N 项等你处理 ↓」，点击定位并聚焦第一个操作控件。
- 非当前会话显示侧栏菱形标记；收起侧栏时开关显示计数，抽屉入口也显示计数。两处均不计当前会话。
- 抽屉的独立页签展示全部会话事项，标明当前对话，可直接处理或跳转定位；空态、加载与错误重试分别设计。
- 窗口失焦时沿用既有桌面提醒与动作，不在本轮改动 Electron。

### 4.5 审批卡片与「印记」
- 卡片：`--wait` 色左边框，标题说明要做什么，下面是等宽字体的具体命令或路径，再一行风险说明。
- 按钮：`允许 (Y)` · `本会话都允许 (A)` · `驳回 (N)`。驳回时可以附一句理由。
- 处理完后卡片收起，节点右侧留一个小印记：石青的「准」或朱砂的「驳」（12px 方形，宋体）。这是这套界面独有的小细节，只在这里用。

### 4.6 砚台 Inkwell（输入区）
- 底部浮动，圆角 14px，宽度和正文一致。
- 第一行是输入框（1–10 行自适应）；第二行是工具条：
  - 左：附件 · `@` 引用 · 模式胶囊 `问 / 谋 / 做`（对应 Ask / Plan / Auto，用中文单字）
  - 右：上下文墨量条（一根细横线，用得越多墨色越深）· 模型名 · 发送
- `Enter` 发送，`Shift+Enter` 换行，`↑` 编辑上一条，运行中 `Esc` 中断。
- `@` 弹出文件 / 会话 / 记忆的混合搜索；`/` 弹出命令。
- 运行中输入框不锁定：新输入作为「插话」排队，在 Agent 下一步之前送达，输入区上方显示「将在下一步插入」。

### 4.7 速记胶囊（桌面特有）
- 全局快捷键 `Alt+Space`（可改）唤出一个 560×56 的无边框置顶小窗，位于屏幕中上方。
- 输入后 `Enter` 发到最近的会话，`Ctrl+Enter` 开新会话；可以把剪贴板内容或文件拖进来。
- 主窗口不打开也能用，回复完成后用系统通知提醒。

### 4.8 「它记得」面板
- 从侧栏底部进入，单独路由 `/memory`。
- 三栏：**人设**（名字、怎么称呼你、语气）、**偏好**（代码风格、常用命令、禁止事项）、**记忆**（Agent 自动记下的条目，带来源会话链接）。
- 每条都可以编辑、置顶、删除；Agent 新记住一条时，轨道上出现 `✦ 记下了：…` 节点，点击可撤销。
- 设置里可以给 Agent 起名，并选一个汉字当“头像字”（宋体），用在空态和托盘提示里。

### 4.9 抽屉
标签页：**变更**（按文件分组的 diff，单个文件可接受或回滚）· **任务**（后台进程、日志尾部、停止）· **计划**（Todo 列表，进度用墨线进度条表示）。

---

## 5. 关键交互流程

1. **空态**：正文居中显示宋体问候「午后好，{你的称呼}」，下面是砚台和最多 3 条“上次没做完的事”（来自记忆和未完成的会话），不放通用建议卡片。
2. **一轮任务**：发送 → 脉点进入思考 → 轨道开始长线 → 节点陆续出现并自动折叠 → 正文流式输出结论 → `◆` 回合小结。
3. **审批**：节点变 `◇`、脉点变菱形，就地确认后留下「准 / 驳」印记；其他会话的阻塞项才增加侧栏与抽屉入口计数。
4. **中断**：`Esc` 停止当前生成，轨道末端画一个「╳ 你叫停了」，已完成的步骤都保留。
5. **分叉**：点轨道上任意 `●` 节点，可以「从这里分叉」，新分支在侧栏显示为当前会话的子项。
6. **滚动**：上滑后停止自动跟随，右下角出现「↓ 墨线还在长」按钮。

---

## 6. 快捷键

| 键 | 作用 |
| --- | --- |
| `Alt+Space`（全局） | 速记胶囊 |
| `Ctrl+K` | 万能面板：会话 / 跳转 / 操作 / 设置 |
| `Ctrl+N` | 新页（新会话） |
| `Ctrl+B` / `Ctrl+.` | 侧栏 / 抽屉 |
| `Ctrl+J` | 抽屉「等你处理」页签 |
| `Esc` | 中断 / 关闭浮层 |
| `Y / N` | 允许 / 驳回；沿用逐次审批，不新增会话级授权 |
| `[` / `]` | 在轨道节点间上下跳 |
| `Ctrl+/` | 快捷键表 |

macOS 下 `Ctrl` 自动换成 `⌘`。

---

## 7. 状态设计
- **加载**：不用骨架屏，用一条从左到右慢慢写出来的墨线。
- **断线**：WebSocket 断开时脉点变空心圆，标题栏下方出现一条 2px 的 `--wait` 细线；自动指数退避重连，重连后根据 `lastSeq` 补齐事件。
- **错误**：在轨道上作为 `×` 节点出现，附「重试这一步」。
- **超长输出**：节点详情只渲染尾部 200 行，提供「在编辑器中打开」（Electron `shell.openPath`）。

## 8. 阶段一视觉样张 · 已确认（历史记录）

### 范围与审计落实

阶段一时，新纸面、深度、字号和墨线展示仅由 Chat 根节点的 `.inkline-preview` 启用，沿用现有 `data-theme`、`data-accent` 与纸纹设置。当时外部壳层保留原有视觉；本轮壳层调整见第 9 节。阶段一未修改 stores、api、composables、Electron 或后端，也未新增依赖。

| 审计问题 | 本轮处理 |
| --- | --- |
| 时间戳与说明同样浅，关键信息难读 | 全量检查 `ink-3` / `text-tertiary`；导航、分组、参数、风险、空态提示、快捷键、结果和状态改用二级墨色 |
| 空态只是小图标与一句问候 | 日线、大字宋体、呼应应用图标缎带的第一笔、三项起手式；仅填入可编辑草稿，不自动执行 |
| 容器同一描边、无接触层次 | 定义内凹、纸页、抬升、浮层四种多层 elevation；样张中的代码、执行小票、砚台与菜单分别使用，不给所有卡片加阴影 |
| 过程轨道只是一条死直线 | 双 SVG 曲线形成笔锋与细边；运行生长使用 transform / opacity，保留现有 read 合并与过程折叠 |
| 小票终点按钮拉成长框 | 样张中固定节点触控尺寸、取消默认边框，正文用纸面与撕边；名称仍为「执行小结」 |
| 加载反馈与墨线身份不一致 | 保留 `LoadingSpinner` 公共命名和 props，展示换为墨线；忙碌按钮也使用短墨线 |
| 720 / 1100px 的 JS 与 CSS 边界不一致 | 布局计算包含边界；从宽窗口进入 720px 时收起左栏，不更改已有宽度持久化和拖拽机制 |

### 对比度与文字角色

以下为 WCAG 相对亮度公式计算的实色值，不把纹理采样伪装为固定值。

| 主题 / 表面 | 表面色 | 正文 `ink` | 可读次要文字 `ink-2` | 元信息 `ink-3` |
| --- | --- | --- | --- | --- |
| 浅 / 画布 | `#F8F5EF` | 13.86:1 | 7.25:1 | 4.51:1 |
| 浅 / 次层 | `#F0ECE3` | 12.80:1 | 6.69:1 | 4.16:1 |
| 浅 / 压层 | `#E7E1D6` | 11.59:1 | 6.06:1 | 3.77:1 |
| 浅 / 抬升纸面 | `#FEFCF7` | 14.71:1 | 7.69:1 | 4.78:1 |
| 深 / 画布 | `#141716` | 15.58:1 | 10.00:1 | 5.04:1 |
| 深 / 次层 | `#1C211F` | 14.09:1 | 9.04:1 | 4.56:1 |
| 深 / 压层 | `#272E2B` | 11.99:1 | 7.70:1 | 3.88:1 |
| 深 / 抬升纸面 | `#1B211E` | 14.14:1 | 9.07:1 | 4.58:1 |

样张正文：浅 `#252722` / 深 `#F1EEE8`；二级与三级墨色使用第 2.1 节的值。`ink-3` 不用于对比不足的压层文字，文件结果、执行结果与说明使用 `ink-2`。剩余三级色用途只有占位、正文外时间戳、小票耗时、操作数量、展开符号与静息脉点。纹理造成的像素波动不能替代文字角色审查。

### 材质、节奏与降级

- 画布噪点 0.022、砚台和小票 0.025、代码 0.008，均在文字下面；浮层纹理令牌 0.012 为后续壳层预留，本轮不添加浮层噪点。
- 字号比例尺 12 / 13 / 15 / 19 / 24 / 30 / 38 / 48；问候随窗口收敛到 30，正文 15、行高 1.75。宋体仍仅用于签名位置。
- 按压沿用 65ms、控件 140ms、新面板层级 240ms、首屏 480ms；第一笔、落点与纸面进入只动画 transform / opacity。CSS `linear()` 不可用时回退到缓动曲线，减少动态效果时静态显示。
- 首屏的惊艳点是「第一笔 + 大字」；完成后的惊艳点是过程沉入轨道、结论后落下一张小票。视觉冲击力是否达标由用户评审，不自行宣布通过。

### 本地截图证据

截图与测试 JSON 位于被既有规则忽略的 `web/test-results/inkline-stage1/`，不进入 Git。Before 来自上轮界面审计，After 使用既有 `VITE_MOCK=1` 回放；是展示证据，不是后端审批或工具执行验收。Before/After 的会话内容不完全相同。

- 首页：[浅色](../../web/test-results/inkline-stage1/after-home-light.png)、[深色](../../web/test-results/inkline-stage1/after-home-dark.png)。
- Rail / 小票：[浅色](../../web/test-results/inkline-stage1/after-chat-light.png)、[深色](../../web/test-results/inkline-stage1/after-chat-dark.png)。
- 原界面：[首页浅色](../../web/test-results/inkline-stage1/before-home-light.png)、[首页深色](../../web/test-results/inkline-stage1/before-home-dark.png)、[轨道浅色](../../web/test-results/inkline-stage1/before-chat-light.png)、[轨道深色](../../web/test-results/inkline-stage1/before-chat-dark.png)。
- 补充：两主题首页/对话的 1100px、720px 截图，审批态、长输出、纸纹关闭对照；浏览器未报告页面异常。720px 首页无横向溢出，减少动态效果时节点动画为 `none`。

### 验收与保留问题

`npm run build` 通过（包括 vue-tsc 与 Electron 编译），仅结构改动的只读 ESLint 检查通过。`npm run test:run`：56 项中 28 通过、28 失败；基线为 41 失败，无新增失败。**测试尚未全绿**，符合本阶段「失败数不高于 41」的门槛。

仅修正 `src/tests/setup.ts` 的真实 i18n / 独立 Pinia 装配与 `session.test.ts` 缺失的回执 `status` 夹具字段，未修改断言。此前误在提交 `223479b` 中加入追踪；现已从索引移除，两份文件保留在本地，测试忽略规则继续有效。未创建新提交或改写已有历史。

| 剩余失败分类 | 数量 | 未改动原因 |
| --- | --- | --- |
| Session API / 事件投影预期 | 8 | 涉及业务契约，不在视觉修改范围 |
| 模型设置交互 / 请求预期 | 7 | 不调整模型功能或用断言迁就行为 |
| 输入控件 / 选择器预期 | 3 | 不变更发送、停止和模型选择逻辑 |
| 活动显示 / 投影预期 | 2 | 不变更运行状态投影 |
| 文件树请求参数预期 | 1 | 不变更文件 API |
| 文案预期差异 | 4 | 不恢复已移除的说明来迎合测试 |
| Memory 缺少路由装配 | 1 | 本轮未继续扩张装配修正 |
| MCP 清单预期 | 1 | 需要另行核对真实数据契约 |
| Markdown 安全渲染预期 | 1 | 不改变既有消毒策略来通过测试 |

阶段一只证明样张可构建、原基线没有新增测试失败及截图状态可用，未证明全站键盘交互、所有错误态、长会话性能或桌面系统通知。用户已确认四张核心样张；第二阶段的验证见下节。

## 9. 阶段二 · 壳层与待处理事项

### 实施边界

本轮不改后端、Electron、审批接口、版本号提交、审计或运行状态机；不新增依赖。保留多工作区、文件树、变更、计划、队列、记忆入口和两侧宽度拖拽。未执行 Git 命令，也未修改测试文件、测试断言、忽略规则或 Git 索引。

经确认的最小例外：`ui.ts` 只增加待处理页签、删除过时的弹层开关；`useShortcuts.ts` 只调整展示入口和键盘作用域；`events.ts` / `event-adapter.ts` / `run.ts` 只保留真实序号、时间及工具调用 ID 供展示。窄屏互斥与焦点协调放在 AppLayout 本地，不增加业务 store 字段。

### 先后位置与降级

1. Approval 的产品 DTO 和事件均带 `tool_call_id`。在同一会话、同一 task 内，精确匹配 Step.id，审批挂到该节点后。需要时拆开包含该节点的合并 read 组，不依据工具名称或参数相似度猜关联。
2. Question 使用真实 title，作为次要字号的「待回答」标签；空白或缺失时固定为「Agent 在等你回答」。不切割、不拼接、不去重回复正文。
3. 先使用真实事件 seq；没有可比序号时使用真实时间。snapshot-only Question 可以使用 created_at，历史回放可补入实际 seq。snapshot 的 last_sequence 仍只作为原有产品状态水位，不能冒充节点序号。
4. Question 两者均缺失时，明确放在正文后、执行小结前。Approval 缺失工具调用 ID 或对应节点尚未到达时，保留按已有事件顺序排列的独立节点，不能声称精确挂载；Approval 快照没有创建时间，不能由 expires_at / decided_at 推导创建顺序。
5. 定位、跨会话标记和汇总不依赖精确工具关联。所有视图过滤掉 closed / verdict / 已回答事项；操作仍走 inbox 的共享 busy 锁和原有请求、刷新与错误处理。

### 逐项完成情况

| 要求 | 本轮结果 |
| --- | --- |
| 标题栏去独立通知入口、单一侧栏开关 | 完成；Ctrl+B 保留，窗口按钮与导航按钮分权重 |
| 宋体会话标题、中间省略、双击重命名 | 完成，复用 manageSession；本地 mock API 验证重命名 |
| 六种 Pulse 状态 | 保留现有状态派生与 SVG 语言；两主题逐态截图 |
| 工作区 / 日期 / 会话层级、当前会话墨线 | 完成，保留多工作区与已有管理动作 |
| 其他会话等待标记与收起计数 | 完成，点击携带 await ID，进入后展开、定位并聚焦 |
| 审批、提问就地展示与处理后印记 | 完成；未知位置按上述规则降级，不伪造关联 |
| 视口外提示与等待占位文字 | 完成；IntersectionObserver 增量观察，流式正文不重置可见性 |
| 抽屉独立待处理页签 | 完成，全部事项 / 当前标记 / 空态 / 墨线加载 / 错误重读；共享原有提交逻辑 |
| 命令面板 | 完成四组、子序列与英文词首字母匹配、常用命令缩写、字符高亮、最近使用、上下 / Enter / Esc / Tab、焦点还原 |
| 弃用 InboxPopover | 引用核查后移除；删除 ui.inboxOpen，Ctrl+J 改开待处理抽屉；桌面提醒未动 |
| 统一断点与覆盖面板互斥 | `_breakpoints.scss` 唯一来源，导出 CSS 变量给 JS；抽屉 ≤1100，侧栏 <720；本地焦点陷阱与还原，主区域 inert，滚动位置保留 |
| 令牌、动效与 i18n | 新样式使用共享令牌；新面板仅 transform / opacity，reduced-motion 短淡入；新增文案进入现有语言目录 |

### 修改文件清单

以下均为本轮修改，按职责列出；复用而未改动的 Pulse、inbox、session、layout、文件树业务与 Electron 不计入。

| 文件（相对 web/src） | 原因 |
| --- | --- |
| `api/events.ts` | 展示 DTO 保留工具关联及序号 / 时间 |
| `api/event-adapter.ts` | 保留 Gateway 已有 tool_call_id，不修改后端协议 |
| `stores/run.ts` | 回放与快照保留展示顺序元信息，原有状态水位与审批逻辑不变 |
| `stores/ui.ts` | 新待处理页签；清理废弃 inboxOpen |
| `composables/useShortcuts.ts` | Ctrl+J 指向抽屉；审批键限制在有效展示作用域 |
| `utils/layout-media.ts` | JS 读取共享 CSS 断点与尺寸，不复制阈值 |
| `utils/rail-presentation.ts` | 只读 Rail 排序、精确关联及待处理过滤 / 先后排序 |
| `utils/tool-presentation.ts` | 描述已知操作、目标与影响，不能据此授权 |
| `components/layout/AppLayout.vue` | 壳层主题、覆盖互斥、焦点与 inert 协调 |
| `components/layout/Sidebar.vue` | 去重复收起入口，复用共享断点 |
| `components/shell/TitleBar.vue` | 导航 / 窗口按钮分层，非当前计数与新标题展示 |
| `components/shell/Drawer.vue` | 独立待处理页签，保留宽度、tab 切换和滚动记忆 |
| `components/common/SessionTitle.vue` | 新展示组件：中间省略及原接口重命名 |
| `components/common/CommandPalette.vue` | 分组匹配、高亮、最近使用与键盘 / 焦点展示逻辑 |
| `components/common/IconSymbol.vue` | 与等待 Pulse 一致的菱形图标 |
| `components/sidebar/RecentChats.vue` | 工作区下的日期分组，阻塞会话不被最近列表配额隐藏 |
| `components/sidebar/SessionItem.vue` | 非当前等待标记与指定事项导航 |
| `components/rail/RailTrack.vue` | 分段折叠，不抽走等待节点；未知序号提问放到正文后 |
| `components/rail/RailNode.vue` | 内联待处理卡、可定位锚点及处理后收起 |
| `components/rail/SealMark.vue` | 印记尺寸统一引用令牌 |
| `components/chat-area/ApprovalCard.vue` | 主层操作 / 目标 / 影响，详情折叠；原提交与错误逻辑保留 |
| `components/chat-area/PendingReminder.vue` | 视口可见性与定位提示，不参与业务状态 |
| `components/chat-area/InputBox.vue` | 等待占位文案、删除废弃弹层条件；发送 / 排队不变 |
| `components/interact/QuestionCard.vue` | 真实 title 次要标签、空标题降级、定位控件标记 |
| `components/drawer/PendingTab.vue` | 跨会话汇总，复用同一审批 / 提问组件 |
| `views/Chat.vue` | 当前事项派生、Rail / minimap 一致投影与定位焦点 |
| `i18n/locales/en.ts` | 新文案中英支持，清理废弃弹层标签 |
| `styles/_breakpoints.scss` | 新共享断点来源及 SCSS mixin |
| `styles/tokens.scss` | 壳层继承确认后的视觉令牌，新增面板 / 交互令牌 |
| `styles/base.scss` | 纹理位于文字下方，纸纹关闭与 reduced-motion 降级 |
| `styles/mixins.scss` | 共享行反馈使用令牌及 transform，不动画颜色 |
| `styles/sidebar.scss` | 壳层层次、纸纹、窄屏与滑入 |
| `styles/drawer.scss` | 240ms 滑入、raised 深度、页签与覆盖边界 |
| `styles/workspace-list.scss` | 工作区与日期层级，减少整块高亮 |
| `styles/session-item.scss` | 选中墨线与跨会话等待标记 |
| 删除 `components/interact/InboxPopover.vue` | 没有其他引用，功能已归入抽屉，无数据删除 |

本文件同步更新设计与验收记录。新建的展示组件均小于 250 行；未为整理行数拆分已有业务组件，也没有新建框架。

### Before / After 与专项证据

截图和测试 JSON 在已有忽略规则覆盖的 `web/test-results/inkline-stage2/`，未加入版本追踪。常规对照使用同一条现有 mock 回放输入；实际审批允许、驳回、版本与理由走原有 mock API。提问排序、缺失元信息和 Pulse 专项使用明确的展示夹具，不能算作后端或桌面 OS E2E。

| 主题 / 宽度 | Before | After | After 抽屉 |
| --- | --- | --- | --- |
| 宣纸 / 1440 | [查看](../../web/test-results/inkline-stage2/before-light-1440.png) | [查看](../../web/test-results/inkline-stage2/after-light-1440.png) | [查看](../../web/test-results/inkline-stage2/after-drawer-light-1440.png) |
| 宣纸 / 1100 | [查看](../../web/test-results/inkline-stage2/before-light-1100.png) | [查看](../../web/test-results/inkline-stage2/after-light-1100.png) | [查看](../../web/test-results/inkline-stage2/after-drawer-light-1100.png) |
| 宣纸 / 719 | [查看](../../web/test-results/inkline-stage2/before-light-719.png) | [查看](../../web/test-results/inkline-stage2/after-light-719.png) | [查看](../../web/test-results/inkline-stage2/after-drawer-light-719.png) |
| 松烟 / 1440 | [查看](../../web/test-results/inkline-stage2/before-dark-1440.png) | [查看](../../web/test-results/inkline-stage2/after-dark-1440.png) | [查看](../../web/test-results/inkline-stage2/after-drawer-dark-1440.png) |
| 松烟 / 1100 | [查看](../../web/test-results/inkline-stage2/before-dark-1100.png) | [查看](../../web/test-results/inkline-stage2/after-dark-1100.png) | [查看](../../web/test-results/inkline-stage2/after-drawer-dark-1100.png) |
| 松烟 / 719 | [查看](../../web/test-results/inkline-stage2/before-dark-719.png) | [查看](../../web/test-results/inkline-stage2/after-dark-719.png) | [查看](../../web/test-results/inkline-stage2/after-drawer-dark-719.png) |

- 位置与处理：[提问位于前后工具之间、审批精确跟随目标工具](../../web/test-results/inkline-stage2/inline-question-approval-order.png)、[空 title / 无顺序降级](../../web/test-results/inkline-stage2/question-title-fallback.png)、[提问提交错误不丢事项](../../web/test-results/inkline-stage2/question-submit-error.png)、[允许印记](../../web/test-results/inkline-stage2/approval-allowed-seal.png)、[驳回印记](../../web/test-results/inkline-stage2/approval-denied-seal.png)。
- 视口外：[提示](../../web/test-results/inkline-stage2/pending-outside-viewport.png)、[定位与焦点](../../web/test-results/inkline-stage2/pending-located-focused.png)。
- 跨会话：[侧栏标记](../../web/test-results/inkline-stage2/sidebar-other-waiting.png)、[收起计数](../../web/test-results/inkline-stage2/sidebar-collapsed-count.png)、[抽屉有数据](../../web/test-results/inkline-stage2/drawer-pending-data.png)、[抽屉空态](../../web/test-results/inkline-stage2/drawer-pending-empty.png)。
- 命令面板：[模糊命中高亮](../../web/test-results/inkline-stage2/palette-fuzzy.png)、[分组与键盘选中](../../web/test-results/inkline-stage2/palette-groups.png)、[深色](../../web/test-results/inkline-stage2/palette-dark.png)。
- 覆盖：[719 侧栏](../../web/test-results/inkline-stage2/overlay-sidebar-719.png)、[719 抽屉](../../web/test-results/inkline-stage2/overlay-drawer-719.png)、[英文抽屉](../../web/test-results/inkline-stage2/drawer-english.png)、[减少动态效果](../../web/test-results/inkline-stage2/drawer-reduced-motion.png)。

| Pulse | 宣纸标题栏 | 松烟标题栏 |
| --- | --- | --- |
| 静息 | [查看](../../web/test-results/inkline-stage2/pulse-light-idle.png) | [查看](../../web/test-results/inkline-stage2/pulse-dark-idle.png) |
| 思考 | [查看](../../web/test-results/inkline-stage2/pulse-light-thinking.png) | [查看](../../web/test-results/inkline-stage2/pulse-dark-thinking.png) |
| 行动 | [查看](../../web/test-results/inkline-stage2/pulse-light-acting.png) | [查看](../../web/test-results/inkline-stage2/pulse-dark-acting.png) |
| 等你处理 | [查看](../../web/test-results/inkline-stage2/pulse-light-waiting.png) | [查看](../../web/test-results/inkline-stage2/pulse-dark-waiting.png) |
| 出错 | [查看](../../web/test-results/inkline-stage2/pulse-light-error.png) | [查看](../../web/test-results/inkline-stage2/pulse-dark-error.png) |
| 离线 | [查看](../../web/test-results/inkline-stage2/pulse-light-offline.png) | [查看](../../web/test-results/inkline-stage2/pulse-dark-offline.png) |

### 验收与未覆盖项

- `npm run build`：通过，含 vue-tsc 与既有 Electron 编译；仍有 Sass legacy API 弃用警告。
- `npm run test:run`：56 项，28 通过、28 失败；失败项身份与本轮基线完全一致，新增失败 0，未修改装配、夹具或断言。剩余分类沿用第 8 节的 28 项分类，不能称为全量测试通过。
- 改动 TS / Vue 文件 ESLint：退出码 0、错误 0；仍有 498 项格式警告（属性换行、模板缩进、元素换行等）。没有运行项目带全目录 `--fix` 的 lint 脚本，以免顺手改动其他模块；本轮不宣称警告清零。
- 浏览器交互专项：[主记录](../../web/test-results/inkline-stage2/interaction-results.json)、[补充记录](../../web/test-results/inkline-stage2/extra-results.json)。覆盖版本化审批、驳回理由、提问错误保留、正文原样、顺序降级、定位焦点、计数、命令键盘、三个覆盖边界、互斥、焦点 / 滚动还原、宽度拖拽、双击重命名、英文与 reduced-motion；未报告页面异常。
- 未覆盖：真实 Gateway / Core 的审批与回答端到端，macOS 红绿灯、Windows 窗口按钮、失焦系统提醒及托盘。相关业务 / Electron 代码保留，浏览器验证不能替代真实桌面验收。
- 仍保留的边界：没有调用 ID 的审批不可能精确关联；缺少真实序号及时间的提问只能回落到末尾。没有新增后端接口需求，也不以猜测补齐缺失数据。
