# NanamiGopher 前端设计

> **状态**：Current
> **架构版本**：v1
> **最后核验**：2026-09-16
> **权威范围**：Vue UI、Electron Host、前端状态与交互边界

API 字段以 [API](API.md) 为准，权限行为以 [Tool Permission](../agent-capabilities/security/tool-permission.md) 为准。

## 1. 前端分层

```text
Views
  → Feature Components
    → Stores / Composables
      → Generated API Client / Event Client
        → Go Gateway
```

- View 负责页面组合，不直接发请求。
- Store 保存客户端状态，不复制服务端任务状态机。
- API Client 由 OpenAPI/事件 Schema 生成或集中封装。
- 所有 Workspace 资源请求显式携带当前 Workspace 上下文。

## 2. 项目结构

```text
web/
├── src/
│   ├── app/
│   ├── router/
│   ├── features/
│   │   ├── chat/
│   │   ├── workspace/
│   │   ├── inspector/
│   │   ├── skills/
│   │   └── settings/
│   ├── stores/
│   ├── composables/
│   ├── api/                # generated client and adapters
│   ├── events/
│   ├── components/
│   └── types/
└── electron/
    ├── main.ts
    ├── preload.ts
    └── supervisor.ts
```

## 3. 页面结构与阶段边界

Phase 1 当前采用可折叠三栏布局：左栏是会话与导航，中栏是对话或设置工作区，右栏是当前 Workspace 的文件与 Git 变更。只在主导航暴露已连通服务端契约的能力：

| 界面 | Phase 1 状态 |
|---|---|
| 总览、会话、审计日志 | 可用 |
| 用户称呼、多模型配置、默认模型与权限设置 | 可用 |
| 会话模型/速度/权限切换、Tool 状态与审批卡片 | 可用 |
| Workspace 文件树、只读预览、Git Diff | 可用 |
| Inspector | 未挂载，等待快照/事件 API |
| 搜索、定时任务、浏览器、Skill/包管理、回顾/归档 | 路由可保留明确的规划页，不进入主导航 |

文件栏只消费 Gateway 提供的受限只读契约，不从渲染进程直接访问 Node 文件系统。路由按 feature 划分，真正的访问授权和路径边界仍由 Gateway 执行。

### 3.1 模型设置交互

Phase 1 的模型设置采用渐进式的“配置行 → 单一编辑器 → 模型目录”结构：

- 一个 Workspace 最多保存 32 个 Chat 模型配置，并显式指定一个默认模型；新会话继承默认模型。
- 默认页面只展示已配置服务的摘要、凭证状态和默认标记；同一时间最多展开一个编辑器，避免列表、预设与连接参数同时争夺注意力。
- 每个配置保存名称、Provider、模型 ID 和 Base URL；生成参数使用运行时的稳定默认值，不占用常规设置界面。
- 添加配置时先选择 OpenAI、Anthropic、Ollama 或常用 OpenAI-compatible 服务。DeepSeek、OpenRouter、阿里云百炼、Groq、Together AI、LM Studio、vLLM 和 llama.cpp 预设只负责填充地址；模型 ID、密钥和最终连接结果仍以用户实际服务为准。
- API Key 与模型选择位于主操作路径；接口类型、服务预设和 Base URL 收在“自定义设置”中，常规配置无需接触底层协议字段。
- 用户可使用当前表单值从服务端目录获取模型。OpenAI、Anthropic、OpenAI-compatible 读取 `/models`，Ollama 读取 `/api/tags`；结果进入可搜索的单选目录，确认后才写入草稿且不会自动保存。目录不可用时仍允许手工输入模型 ID。
- API Key 按模型配置 ID 隔离，只显示“已保存”状态，不回显真实值；Provider 或端点变化时清除旧凭证，禁止跨端点复用。
- 连接测试使用当前草稿且不保存；草稿变化后立即清除旧测试结果。
- 聊天输入框可覆盖当前会话的模型、速度档和执行权限。速度档为 `fast / balanced / thorough`，通过统一输出预算控制响应速度；不会触发自动模型路由。
- 目录发现只负责列出服务端模型，不推断能力与成本。按任务路由、能力/成本选择和自动 fallback 仍属于 Phase 2。

### 3.2 权限设置交互

- 普通用户只选择 `只读 / 工作区 / 完全访问` 三档模式，不编辑逐工具 L1–L5 矩阵。
- `工作区` 是新安装的推荐默认值：工作区读取、编辑和安全命令自动执行，联网与高风险命令请求批准。
- 会话可以覆盖 Workspace 默认档位；hard-deny、路径边界和风险动态升级始终由服务端 ToolPolicy 判定。

### 3.3 文件与 Diff

- 文件树按目录懒加载，默认忽略 `.git`、依赖目录、虚拟环境和构建产物。
- 文件内容只读预览，单次最多读取 512 KiB；二进制内容不进入页面。
- “变更”页一次读取当前 Workspace 的 staged、unstaged 和 untracked 状态，选中文件后再懒加载其增加/删除统计与统一 Diff。
- Gateway 对相对路径、路径穿越和逃逸 Workspace 的符号链接执行强制校验；前端传入的路径不是授权依据。

### 3.4 对话与执行活动

聊天记录与 Agent 执行过程是两类不同的界面对象，不共用消息气泡：

- 对话区只显示用户消息和助手最终回复；模型调用工具前产生的过程说明不得拼接进最终回复。
- `reasoning.*`、`tool.*` 和 `subagent.*` 事件按 `task_id` 聚合为可折叠的活动流，并按 `sequence` 排序，显示在对应最终回复之前。
- 活动流只展示模型主动输出的简短过程说明、工具状态和子 Agent 生命周期，不请求、存储或展示模型隐藏思维链。
- 运行中默认展开，完成后允许折叠；参数与结果放在二级详情中，避免挤占对话主阅读路径。
- 输入组件只负责编辑和提交用户消息。运行状态通过活动流和 `aria-busy` 表达，不修改输入框内容或占位文本。
- `message.delta` 只承载面向用户的最终回答增量；过程信息必须使用独立事件类型。前端不得再根据文字内容猜测它属于回答还是执行过程。
- 助手最终回复按 GitHub Flavored Markdown 渲染。完整的重复 JSON 字符串编码和代码块外的 Markdown 结构转义可在展示层规范化；代码、正则与公式中的反斜杠必须保留。
- Markdown 生成的 HTML 必须经过 allowlist 清洗后才能进入 DOM；脚本、事件属性、表单和主动加载的媒体资源不得渲染。

## 4. 状态管理

建议 Store 边界：

| Store | 状态 |
|---|---|
| identity | 当前主体和认证状态 |
| workspace | Workspace 列表、当前 Workspace、Membership |
| conversation | 会话目录和当前会话 |
| task | 当前任务快照、取消/重试操作状态 |
| inspector | 事件窗口、筛选、连接状态 |
| approval | 待审批项目和用户草稿决定 |
| settings | 用户级和 Workspace 级设置 |

服务端状态以快照为准；WebSocket事件用于增量更新。重连后先恢复快照，再消费新事件。

## 5. API 与事件

- REST 用于资源 CRUD、命令提交和状态快照。
- WebSocket 用于消息增量、任务事件、审批通知和 Inspector。
- 事件按 `event_id` 去重，按 `sequence` 检测缺口。
- UI 不自行推断任务已完成，必须等待服务端终态。
- endpoint 不散落在组件或 Electron IPC 中。
- 消息投影与活动投影分别维护：`message.*` 更新聊天记录，`reasoning.* / tool.* / subagent.*` 更新任务活动流。

## 6. 审批交互

审批弹窗必须展示：

- 工具能力和风险等级。
- 将访问或修改的资源范围。
- 规范化后的关键参数和副作用预览。
- 凭证与网络使用范围。
- 本次允许、拒绝及可用的范围授权选项。

前端提交决定后仍等待服务端确认；不得本地直接把 ToolCall 标记为获批。

## 7. Electron 边界

### 7.1 BrowserWindow 基线

```text
contextIsolation = true
nodeIntegration = false
sandbox = true
webSecurity = true
```

- 生产环境只加载打包资源或受信来源。
- 禁止渲染进程获得任意 Node、Shell 或文件系统能力。
- 导航、新窗口、下载和外部链接使用显式 allowlist。

### 7.2 Preload API

Preload 只暴露有限、强类型的方法：

```text
runtime.status()
runtime.restartService(service)
dialog.selectFiles(options)
shell.openExternal(approvedUrl)
```

普通会话、Memory、Skill 和权限请求通过统一 API Client 访问 Gateway，不在 preload 中复制一组 REST 包装器。事件订阅必须返回 unsubscribe 方法。

### 7.3 Runtime Supervisor

- 桌面模式由 Electron 启动 Go 和 Python。
- 验证可执行文件路径和签名/校验值。
- 使用最小环境变量和随机本地认证材料。
- 捕获退出状态并执行有限重启。
- 应用关闭时按 MCP、Python、Go 顺序终止。

容器模式不使用 Electron Supervisor。

## 8. 错误与可访问性

- 对 Validation、AccessDenied、ApprovalRequired、Timeout 和 Offline 使用不同交互。
- 网络重试不得重复提交没有幂等键的命令。
- 所有关键操作可用键盘完成，焦点在弹窗关闭后返回触发元素。
- 流式消息支持暂停自动滚动，Inspector 不应阻塞主输入。

## 9. 构建目标

- Web：静态资源，由 Gateway/反向代理提供 API。
- 本地 Vite 开发与生产预览统一把 `/api`、`/health` 代理到 Gateway；预览端口可通过 `NANAMI_GATEWAY_PROXY_TARGET` 指定目标，但不能脱离 Gateway 单独提供业务功能。
- Desktop：Vue资源与 Electron Host 打包，附带受验证的 Go/Python运行时。
- 环境差异通过构建配置和 Runtime Adapter 处理，不在 Vue 业务组件内分叉。

## 10. 性能基线

- 高频输入（拖拽、流式消息）以 `requestAnimationFrame` 合并到每帧一次更新。
- 持久化写入在交互结束时执行，不在 `mousemove` 等高频路径中同步写 `localStorage`。
- 长对话使用 `content-visibility` 跳过屏外消息绘制；自动滚动只观察消息数和末条长度，不扫描全历史。
- 大面积容器和重复卡片禁用 `backdrop-filter`；使用实色/半透明表面与阴影保留视觉层次。
- 路由复用按 route name 定位，切换会话 ID 时不重建整个 Chat 组件树。
