# MaigoKite

MaigoKite 是一个运行在你电脑上的个人 Agent。它可以读写工作区文件、查资料、操作网页，也可以通过 MCP 接入其他工具。你选择模型，并决定它能访问什么、哪些操作需要确认。

比如你可以让它：

- 阅读一个文件夹，整理里面的 Markdown 和资料
- 搜索公开网页，把结果和来源写回文件
- 修改本地文件，并在界面里查看 diff
- 点击网页、填写表单或截图
- 通过本地 Skill 和 MCP 组合自己的工作流

项目仍在开发中，提供 Web 和 Electron 桌面入口。暂时需要从源码运行，还没有独立安装包。

## 模型、工具与工作区

支持 OpenAI、Anthropic、Ollama 和 OpenAI-compatible API。可以添加多个模型，设置默认模型，也可以为不同会话选择模型。

源码启动时，默认工作区是项目根目录下的 `.workspace`，不是源码目录本身。启动时会自动创建它，但不会搬入旧文件。用侧栏加号添加已有文件夹后，可以让 Agent 读写、搜索文件，并在侧栏预览内容、查看 Git diff。

可用 `MAIGOKITE_WORKSPACE_ROOT` 或配置文件的 `workspace.root` 指定其他目录。默认位置不可写时需要手动指定，不会自动换位置。工作区权限与 Agent 的执行权限分开管理；你可以选择只读、工作区访问或完全访问。需要审批的操作会先显示给你确认，界面也会显示工具调用过程。

浏览器工具使用 Playwright，可以点击、填写表单、获取页面快照和截图。它不会自动继承你日常浏览器中的登录状态，使用前需要配置 Chromium。

从侧栏“扩展”可以管理本地 `SKILL.md` 和 stdio MCP Server。Skill 告诉 Agent 某类任务应该怎么做，本身不会直接执行代码；MCP 用来接入外部工具。保存配置后点击“应用并检查连接”。有任务运行或审批待处理时，需要先处理完，才能应用新配置。

工作区管理、权限和扩展设置的具体规则见 [配置指南](docs/user-guide/Configuration.md)。

## 运行

### 环境要求

- Go 1.22+
- Python 3.11+
- Node.js 22.22.2+（22.x）、24.15.0+（24.x）或 26+ / npm
- ripgrep (`rg`)

推荐安装 [uv](https://github.com/astral-sh/uv)，以便按锁文件安装 Python 依赖。请在运行应用的机器上安装依赖，不要复制其他机器的 `.venv` 或 `node_modules`。详细环境要求见 [开发指南](docs/development/DevelopmentGuide.md)。

### Linux

在仓库根目录，首次使用时安装依赖，再构建并启动桌面：

```bash
bash scripts/setup.sh                # 首次使用，或更新依赖后执行
bash scripts/build.sh desktop
bash scripts/start.sh desktop built
```

如果只使用 Web，在执行 setup 后改用：

```bash
bash scripts/build.sh web
bash scripts/start.sh web built
```

### Windows

使用 PowerShell，在仓库根目录执行，无需 WSL、Bash 或 Make：

```powershell
.\scripts\setup.ps1                  # 首次使用，或更新依赖后执行
.\scripts\build.ps1 desktop
.\scripts\start.ps1 desktop built
```

如果只使用 Web，在执行 setup 后改用：

```powershell
.\scripts\build.ps1 web
.\scripts\start.ps1 web built
```

Agent 的命令工具也支持 Windows PowerShell：默认优先使用 PowerShell 7，没有时选择系统 5.1，可显式指定版本。两版的中文命令传输统一处理，但文件编码默认值仍不同。Windows 暂无受限进程沙箱，执行命令需单次明确授权或用户开启完全访问。使用方式与尚待实机验收的边界见[配置指南](docs/user-guide/Configuration.md#windows-powershell-命令工具)。

Web 和桌面入口二选一，不要同时启动。日常使用只需执行最后一条启动命令，不用每次重装或构建。修改源码后重新构建；需要热更新开发时，省略 `built`，使用 `start.sh web|desktop` 或 `start.ps1 web|desktop`。

Web `built` 地址为 `http://127.0.0.1:4173`，开发模式地址为 `http://127.0.0.1:5173`。桌面 `built` 直接打开本地界面。两种入口都只用于本机，不要直接把端口暴露到公网。

`Ctrl+C` 停止本次启动的整套服务。关闭浏览器标签页不会停止服务；桌面关闭窗口会隐藏到托盘，用托盘“退出”关闭整套服务。若提示端口占用，请先退出旧实例；脚本不会替你结束其他进程或连接旧 Core。

如果 Electron 报 `Electron failed to install correctly`，先更新仓库，再运行 `bash scripts/setup.sh electron`；Windows 使用 `.\scripts\setup.ps1 electron`。无需重装 Go/Python 或反复构建。原因及处理步骤见 [开发指南](docs/development/DevelopmentGuide.md#electron-installation编译成功但运行时缺失)。

这些命令仍依赖本机开发环境，不会生成自带 Python 等运行资源的独立安装包。发布限制见 [构建与发布指南](docs/deployment/ReleaseGuide.md)。

### 浏览器工具

浏览器工具需要 Chromium。可以安装 Playwright Chromium，也可以在配置中指定已有 Chrome / Chromium 的可执行文件：

```text
browser.executable_path
```

默认留空时使用 Playwright 管理的 Chromium，不会自动寻找固定路径的 Chrome。安装与配置见 [开发指南](docs/development/DevelopmentGuide.md#路径与解释器) 和 [配置指南](docs/user-guide/Configuration.md)。

## 第一次使用

启动后，先到 **设置 → 模型** 添加模型服务。填写 API 地址、模型 ID，以及服务要求的 API Key。测试连接后保存，选择默认模型，再确认工作区路径和权限模式。

例如，将本项目目录添加为工作区后，可以输入：

```text
读取 README.md，告诉我这个项目现在主要在做什么。
```

或者：

```text
查一下这个项目依赖的几个库最近有什么重要变化，把结果整理到 notes.md。
```

不同模型对 Tool Calling 的支持不同。API 能连接，并不一定意味着这个模型能完成工具调用。

## 数据

会话、任务、审批和运行事件保存在本地 SQLite 中。API Key 使用操作系统凭证存储，普通配置接口不会返回明文密钥。

“本地优先”不等于离线运行：

- Ollama 可以完全运行在本机
- OpenAI / Anthropic 等服务会向对应 API 发送模型请求
- Web 搜索会访问配置的搜索服务
- MCP 是否访问网络取决于对应 MCP Server

数据目录为 `~/.maigokite`，环境变量使用 `MAIGOKITE_` 前缀，Python 命令为 `maigokite-agent`。旧名称不提供别名或自动迁移；项目文件夹可以自行改名。

## 当前状态

项目还没有进入稳定发布阶段。使用前请留意这些限制：

- 新执行内核和新 UI 仍有待回归验证的部分
- 任务停止或失败后，不是所有情况都能从原位置恢复
- 远程 MCP 操作不一定能被本地取消立即终止
- 浏览器会话不能跨 Core 重启恢复
- Memory 主要用于手工管理，还没有自动检索并注入会话
- 子 Agent、持久工作流和手机远程访问还没有完整交付

历史聊天、任务和审批数据会保留，但缺少 LangGraph checkpoint 的历史待审批任务不能继续执行。可以拒绝或取消，再发起新任务。

功能进度见 [Roadmap](docs/project/Roadmap.md)，变更记录见 [更新日志](docs/project/Changelog.md)。源码可运行不代表已经通过发布验收。

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

开发环境、协议生成和贡献约束见 [开发指南](docs/development/DevelopmentGuide.md)；测试范围见 [测试与验收](docs/testing/TestPlan.md)。

提交 Issue 或 PR 时，请附上复现步骤、实际行为、预期行为和必要的脱敏日志。不要提交 API Key、个人数据、运行数据库或构建产物。

## 文档

模型、权限、工作区和扩展设置见 [配置指南](docs/user-guide/Configuration.md)。遇到问题可查看 [安装与首次使用](docs/user-guide/Installation.md) 和 [日志与诊断](docs/ops-security/Observability.md)。架构与其他文档从 [文档索引](docs/README.md) 进入。

## License

Copyright (c) 2026 NanamiKite.

Licensed under **Mozilla Public License 2.0** (`MPL-2.0`).

See [LICENSE](LICENSE).

Third-party dependencies retain their respective licenses.
