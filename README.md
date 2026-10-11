# MaigoKite

一个本地优先的个人 Agent。

它可以在你的工作区里读写文件、查资料、操作网页，也可以通过 MCP 接入其他工具。你可以选择自己使用的模型，并决定 Agent 能访问什么、哪些操作需要确认。


比如你可以让它：

- 阅读一个工作区，整理里面的 Markdown 和资料
- 搜索公开网页，把结果和来源写回文件
- 修改本地文件，并在界面里查看 diff
- 操作网页完成一些需要点击、填写或截图的任务
- 通过本地 Skill 和 MCP 组合自己的工作流

> 项目仍在开发中。目前推荐从源码运行，Electron 桌面端也处于开发阶段，还没有正式发布的独立安装包。

## 功能

### 模型

目前支持：

- OpenAI
- Anthropic
- Ollama
- OpenAI-compatible API

可以配置多个模型、设置默认模型，也可以在不同会话中切换。

### 工作区

默认工作区为安装目录下的 `.workspace`，启动时自动创建；源码运行时为项目根目录下的 `.workspace`，不再把源码根目录本身当作工作区。
`MAIGOKITE_WORKSPACE_ROOT` 或配置文件的 `workspace.root` 可覆盖默认路径。安装目录不可写时请显式指定可写目录，不会自动改用其他位置。
旧文件不会搬动；若要继续操作原目录，请将其添加为文件夹工作区。数据库和凭证的存放位置不变。

侧栏加号用于添加文件夹，点击工作区名称可直接选择，对话按所属工作区分组。
Electron 使用系统文件夹选择器；本机 Web 版使用应用内目录浏览器，不必手填绝对路径。
添加的工作区可通过侧栏或工作区列表的删除按钮移除，需二次确认；磁盘文件不动，对话保留并移到默认工作区。
运行中、等待审批或尚可恢复的任务须先完成或停止。启动配置的默认工作区不可删除。
Web 浏览的是 Gateway 所在电脑的目录，Gateway 与 Core 需要使用同一文件系统；此入口不开放远程目录浏览。
会话右侧的 `···` 菜单支持重命名、移动到其他工作区、
归档/恢复和确认删除；侧栏“归档对话”可查看历史。已有对话保留在默认工作区，不会自动移动。

Agent 可以在指定工作区中：

- 读取文件
- 写入和编辑文件
- 搜索文件名和文件内容
- 预览文件
- 查看 Git diff

工作区权限和 Agent 的执行权限是分开的，你可以限制它只读，也可以允许它修改文件。

### 浏览器

内置网页相关工具，包括：

- Web 搜索
- 页面读取
- Playwright 浏览器操作
- 点击和填写表单
- 页面快照
- 截图

浏览器默认用于公开网页，不会自动继承你浏览器中的登录状态。

### 权限与审批

目前有三种主要权限模式：

- 只读
- 工作区访问
- 完全访问

需要审批的操作会先显示给你确认。

界面中也可以查看 Agent 当前调用了哪些工具，并请求停止正在执行的任务。

### Skill 和 MCP

MaigoKite 支持两种扩展方式。

**Skill** 用来告诉 Agent 某类任务应该怎么做。Skill 是本地声明文件，本身不会直接执行其中的代码。

**MCP** 用来接入外部工具。目前支持本地 stdio MCP Server，协议与子进程通信复用官方 SDK。

从侧栏“扩展”进入管理页：添加 MCP 的启动程序、参数和凭证，或导入/编辑 `SKILL.md`、设置本地技能目录。
保存后点击“应用并检查连接”生效；有运行中的任务或待处理审批时会拒绝应用，不替换它们正在使用的工具。
Core 重启沿用上次生效配置；“恢复已有连接”可在待审批时重新注入 MCP 凭证，不应用新编辑。批准 MCP 调用前也会尝试恢复所需连接，失败不消费审批。
配置与实际加载状态分开显示，停用或移除不会删除本地源目录。详细边界见 [配置指南](docs/user-guide/Configuration.md#8-技能与-mcp)。

## 运行

### 环境要求

需要：

- Go 1.22+
- Python 3.11+
- Node.js 18+ / npm
- ripgrep (`rg`)

推荐安装 [uv](https://github.com/astral-sh/uv)。

更完整的环境说明见：

[开发指南](docs/development/DevelopmentGuide.md)

### Linux

在仓库根目录初始化，然后选择 Web 或桌面，二者不要同时启动：

```bash
bash scripts/setup.sh
bash scripts/start.sh web            # Web 开发：Core + Gateway + Vite
# 或：bash scripts/start.sh desktop  # 桌面开发：Electron + Core + Gateway + Vite
```

先构建、后启动已有产物：

```bash
bash scripts/build.sh all            # 也可只选 web 或 desktop
bash scripts/start.sh web built
# 或：bash scripts/start.sh desktop built
```

### Windows

使用 PowerShell，无需 WSL、Bash 或 Make；在仓库根目录：

```powershell
.\scripts\setup.ps1
.\scripts\start.ps1 web              # 或 desktop
```

先构建、后启动已有产物：

```powershell
.\scripts\build.ps1 all               # 也可只选 web 或 desktop
.\scripts\start.ps1 desktop built     # 或 web built
```

PowerShell 若按本机策略禁止脚本，可在确认源码可信后使用进程级命令，例如
`powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start.ps1 web`，无需永久修改系统执行策略。

Web 开发地址为 `http://127.0.0.1:5173`，构建产物本地预览为 `http://127.0.0.1:4173`；Gateway/Core 分别使用 8080/8081。
桌面 `built` 模式直接加载本地 HTML，不启动 Vite。Web `built` 使用 Vite preview，只用于本机，不是公网生产部署方案。

两平台共用 `scripts/local.cjs`，所有命令均不依赖 Makefile。`setup` 默认安装到根 `.venv`，也支持 `UV_PROJECT_ENVIRONMENT`；优先复用 uv 锁文件，没有 uv 时使用 pip。
Core 解释器选择顺序为 `MAIGOKITE_PYTHON` → 项目环境 → 已激活环境 → uv → 系统 Python / Windows `py -3`，无效的显式覆盖直接报错。
开发启动会先编译 Gateway（桌面还编译 Electron）；`built` 不自动编译，缺少产物会明确报错。两者默认使用 `config/config.dev.yaml` 和同一份开发数据，可用 `MAIGOKITE_CONFIG` 指定配置，端口仍需保持上述约定。

`Ctrl+C` 停止本次启动的整套服务；任一组件失败也会停止其余组件。关闭浏览器标签页不会停止服务。桌面关闭窗口隐藏到托盘，托盘“退出”才停止整套服务。
启动器通过持有的管道通知 Core/Gateway 退出，正常退出先等待清理，再对超时的自有进程强制结束；不会按进程名清理其他实例。端口占用时直接报错，不会连接旧 Core。**请先退出旧启动方式遗留的实例再运行新入口。**

这些是源码构建/启动脚本：仍需本机 Python 环境、Node 和项目依赖，不是自带 Runtime 的安装包。具体限制见 [构建与发布指南](docs/deployment/ReleaseGuide.md)。

### 浏览器工具

浏览器工具需要 Chromium。

可以安装 Playwright Chromium，也可以在配置中指定：

```text
browser.executable_path
```

默认留空，使用 Playwright 管理的 Chromium，不再假定本机安装了某个固定路径的 Chrome。使用已有 Chrome / Chromium 时，填写该机器上真实的可执行文件路径。

详细配置见：

[配置指南](docs/user-guide/Configuration.md)

## 第一次使用

启动后，先到 **设置 → 模型** 添加一个模型服务。

需要填写的内容通常包括：

- API 地址
- 模型 ID
- API Key（如果需要）

测试连接后保存，并选择一个默认模型。

然后确认工作区路径和权限模式，就可以直接开始使用。

例如：

```text
读取 README.md，告诉我这个项目现在主要在做什么。
```

或者：

```text
查一下这个项目依赖的几个库最近有什么重要变化，把结果整理到 notes.md。
```

不同模型对 Tool Calling 的支持情况不同。API 可以正常连接，并不一定意味着这个模型能够完整运行 Agent 工具。

## 数据

MaigoKite 会把会话、任务、审批和运行事件保存在本地 SQLite 中。

模型请求是否离开本机，取决于你配置的模型服务。

例如：

- Ollama 可以完全运行在本机
- OpenAI / Anthropic 等服务会向对应 API 发送模型请求
- Web 搜索会访问配置的搜索服务
- MCP 是否访问网络取决于对应 MCP Server

所以这里的“本地优先”主要指数据、工作区和 Agent 控制权留在你自己的环境里，而不是强制所有组件离线运行。

API Key 使用操作系统凭证存储，普通配置接口不会返回明文密钥。

项目统一使用 **MaigoKite** 标识：数据目录为 `~/.maigokite`，环境变量前缀为
`MAIGOKITE_`，Python 命令为 `maigokite-agent`，不保留旧名称别名或自动迁移。
Go 使用本地模块路径 `maigokite/gateway`，不依赖 GitHub 仓库地址。
项目文件夹可自行改名；历史快照仅保留旧设计，不作为当前配置依据。

## 当前状态

项目还没有进入稳定发布阶段。

执行内核统一使用 LangChain `create_agent` + LangGraph；普通聊天、`/tool`、审批、
提问、取消和文件任务恢复共用这一条路径。旧 Runtime 和切换开关已移除，无需额外启用。

历史聊天、任务和审批数据保留；没有 LangGraph checkpoint 的历史待审批任务不能继续执行，
可以拒绝或取消，再发起新任务。当前切换按要求暂未运行回归，不代表已经完成发布验收。

变更与历史验证记录：[RuntimeMigration.md](docs/development/RuntimeMigration.md)

目前还有一些已知限制：

- 单 Runtime 切换和新 UI 尚待后续回归验证
- 任务停止和恢复不是所有情况下都能继续原来的执行位置
- 远程 MCP 操作不一定能被本地取消立即终止
- 浏览器会话不能跨 Core 重启恢复
- Memory 目前主要是手工管理，还没有自动检索并注入会话
- 子 Agent、持久工作流和手机远程访问还没有完成

当前进度以这里为准：

[Roadmap.md](docs/project/Roadmap.md)

## 项目结构

| 路径 | 内容 |
| --- | --- |
| `gateway/` | Go Gateway、REST / WebSocket、gRPC Client |
| `python/agent/` | Python Core、Agent Runtime、Tools、权限和持久化 |
| `web/` | Vue 前端、Electron |
| `proto/agent.proto` | Go / Python 共用的 gRPC 协议 |

## 开发

运行测试：

```bash
bash scripts/run_tests.sh
```

构建：

```bash
bash scripts/build.sh all
```

开发环境和项目结构见：

[DevelopmentGuide.md](docs/development/DevelopmentGuide.md)

测试范围见：

[TestPlan.md](docs/testing/TestPlan.md)

桌面构建和发布状态见：

[ReleaseGuide.md](docs/deployment/ReleaseGuide.md)

如果准备提交 Issue 或 PR，尽量附上复现步骤、实际行为、预期行为和必要的脱敏日志。

不要提交 API Key、个人数据、运行数据库或构建产物。

## 文档

- [文档索引](docs/README.md)
- [Roadmap](docs/project/Roadmap.md)
- [系统设计](docs/design/SystemDesign.md)
- [Agent Runtime](docs/design/AgentRuntime.md)
- [前端设计](docs/design/FrontendDesign.md)
- [UI 设计](docs/design/agent-ui-design.md)
- [MCP](docs/agent-capabilities/mcp/mcp-integration.md)
- [日志与诊断](docs/ops-security/Observability.md)

根目录中的 `prd.md` 和 `project.md` 是早期设计材料，部分内容已经过时。

## License

Copyright (c) 2026 NanamiKite.

Licensed under **Mozilla Public License 2.0** (`MPL-2.0`).

See [LICENSE](LICENSE).

Third-party dependencies retain their respective licenses.
