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
- Node.js / npm
- Make
- ripgrep (`rg`)

推荐安装 [uv](https://github.com/astral-sh/uv)。

更完整的环境说明见：

[开发指南](docs/development/DevelopmentGuide.md)

### 启动 Web 开发环境

在仓库根目录：

```bash
make setup
make dev
```

然后打开：

```text
http://localhost:5173
```

默认端口：

```text
Web      5173
Gateway  8080
Core     8081
```

`make setup` 会安装项目依赖并创建根目录下的 `.venv`。

### 启动 Electron

完成初始化后：

```bash
cd web
npm run electron:dev
```

此命令打开独立的 Electron 桌面窗口，并自动启动 Python Core 和 Gateway，不需要另外执行 `make dev` 或打开浏览器。Core 就绪后启动 Gateway，两者就绪后加载界面；首次 Go 编译可能需要等待。

启动失败会显示桌面错误弹窗，详细的 Core / Gateway 输出保留在当前终端。关闭窗口只是隐藏到托盘；右键托盘图标选择“退出”，或在启动终端按 `Ctrl+C`，才会退出并清理此桌面进程启动的后端。

桌面开发命令固定使用 5173 端口；端口已占用时直接报错，不自动切换到另一个页面。Electron 退出时开发服务器也会停止。

如果已经单独启动后端，可以只启动桌面界面：

```bash
MAIGOKITE_EXTERNAL_RUNTIME=1 npm run electron:dev
```

### 浏览器工具

浏览器工具需要 Chromium。

可以安装 Playwright Chromium，也可以在配置中指定：

```text
browser.executable_path
```

开发配置目前使用：

```text
/usr/bin/google-chrome
```

如果你的 Chrome / Chromium 在其他位置，需要自行修改配置。

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
make test
```

构建：

```bash
make build
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

Licensed under **GNU General Public License v3.0 only** (`GPL-3.0-only`).

See [LICENSE](LICENSE).
