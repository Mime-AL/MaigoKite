# 开发指南

> 本文说明源码初始化、启动、质量检查、协议生成和贡献约束。
> 组件职责见 [系统设计](../design/SystemDesign.md)，发布要求见 [构建与发布指南](../deployment/ReleaseGuide.md)。

## 1. 仓库入口

| 路径 | 用途 |
| --- | --- |
| `gateway/` | Go 外部接入与 gRPC 客户端 |
| `python/agent/` | 核心服务、运行时桥接、工具和业务持久化 |
| `web/src/` | Vue；`electron/` 下为主进程/预加载层 |
| `proto/agent.proto` | 唯一共享 gRPC 源 |
| `config/`、`scripts/` | 运行配置、开发/构建/测试脚本 |
| `docs/` | 按 [文档索引](../README.md) 分配权威范围 |

`go.work` 引用 gateway 模块。判断能力是否可用，需要看实际调用，不能只看目录是否存在。未接线的工作流/HITL、子智能体和 Recovery 空骨架已移除，但这些需求仍然保留，见 [智能体运行时设计](../design/AgentRuntime.md#7-技能子任务与工作流边界)。不要在不同模块重复定义同一套类型、策略或协议。

## 2. 初始化

Go 最低版本见 `gateway/go.mod`，Python 要求 3.11+，Node/npm 版本与依赖以 `web/package.json` 和锁文件为准。

Python 依赖在根目录的 `pyproject.toml` 中声明，解析结果保存在根目录的 `uv.lock`。`python/` 只存放源码，不单独安装，也不维护另一份 requirements 清单。

推荐从仓库根目录执行，按锁文件安装到根 `.venv`：

```bash
uv sync --locked --extra dev
```

`dev` 包含质量工具、测试 HTTP 服务和协议生成器。不需要这些工具的运行环境使用 `uv sync --locked --no-dev`，不要添加 `--all-extras`。

`vectorstores` 只用于尚未接入聊天的实验适配器，默认不安装，也不表示知识库功能已经交付。维护者修改依赖后须运行 `uv lock` 更新锁文件；依赖锁定成功不代表运行或发布验收通过。

也可以让 `setup.sh` / `setup.ps1` 安装完整依赖。脚本优先使用 uv；没有 uv 时，用可用的 Python 3.11+ 创建项目环境，再通过 pip 安装同一清单。pip 安装不保证使用 uv 锁定的版本，解释器命令名也不必是 `python3`：

```bash
bash scripts/setup.sh
```

如果只运行了上面的 uv 命令，还需要安装 Go 和 Web 依赖。下面两组命令分别从仓库根目录执行：

```bash
cd gateway
go mod download
```

```bash
cd web
npm ci --include=dev --foreground-scripts --ignore-scripts=false --engine-strict
```

`setup.sh` / `setup.ps1` 会执行以上安装步骤。uv 和 pip 都使用根项目，默认环境目录为根 `.venv`。可用 `UV_PROJECT_ENVIRONMENT` 指定其他目录，相对路径以项目根为基准。

脚本不使用 Poetry 或子项目清单，也不默认安装向量库或 Docker SDK。不要把项目依赖强行安装到全局解释器中。设置 `MAIGOKITE_PYTHON` 后，uv 安装和构建使用指定解释器；pip 用它创建项目环境，依赖仍安装在项目环境内。

## 3. 成套启动与构建（Linux / Windows）

两平台共用 `scripts/local.cjs`，Shell / PowerShell 入口只转发参数，不依赖 Makefile、WSL 或 Git Bash。

需要 Node.js 22.22.2+（22.x）、24.15.0+（24.x）或 26+，Go 1.22+、Python 3.11+。Node 范围来自锁定的 vue-i18n / nopt / abbrev 等依赖，不支持 Node 18。Windows 使用 PowerShell 5.1/7。请在目标机器上初始化，不要复用从 Linux 复制的 `.venv` 或 `node_modules`。

| 操作 | Linux（仓库根） | Windows PowerShell（仓库根） |
| --- | --- | --- |
| 初始化 | `bash scripts/setup.sh` | `.\scripts\setup.ps1` |
| 修复 Electron | `bash scripts/setup.sh electron` | `.\scripts\setup.ps1 electron` |
| Web 开发 | `bash scripts/start.sh web` | `.\scripts\start.ps1 web` |
| 桌面开发 | `bash scripts/start.sh desktop` | `.\scripts\start.ps1 desktop` |
| 构建 Web + Gateway | `bash scripts/build.sh web` | `.\scripts\build.ps1 web` |
| 构建桌面 + Gateway | `bash scripts/build.sh desktop` | `.\scripts\build.ps1 desktop` |
| 构建两种入口 | `bash scripts/build.sh all` | `.\scripts\build.ps1 all` |
| 已构建 Web | `bash scripts/start.sh web built` | `.\scripts\start.ps1 web built` |
| 已构建桌面 | `bash scripts/start.sh desktop built` | `.\scripts\start.ps1 desktop built` |

`start` 的默认目标是 web，默认模式是 dev。dev 会先编译 Gateway；桌面入口还会编译 Electron，然后启动 Vue 热更新页面。built 使用已有产物，不自动编译，缺少产物时会报错。桌面 built 直接加载 `web/dist/index.html`，不需要开发服务器。

`build` 默认构建 all，也可选择 go/python/vue 单个组件。其中 python 生成 wheel/sdist。

Gateway 产物为 `dist/maigokite-api[.exe]`。脚本只构建本机架构；GOOS/GOARCH 与本机不一致时会报错。不能用这套脚本在 Linux 上生成可用的 Windows 桌面包。

Web dev 使用 `http://127.0.0.1:5173`，built 使用 `http://127.0.0.1:4173`。两者都将请求代理到 8080 的 Gateway，包括 WebSocket；Core 监听 8081。Web built 是 Vite 本地预览，不是公网生产服务器，不得用作手机远程认证入口。

默认配置为 `config/config.dev.yaml`。built 也使用这份配置和开发数据库，不会自动切换数据目录。可通过 `MAIGOKITE_CONFIG` 指定其他配置，但 Gateway/Core/UI 端口仍须保持上述约定。

### 路径与解释器

Web 与桌面默认使用安装根目录下的 `.workspace`，由 Core 在启动时创建。源码模式的安装根目录就是项目根目录。可通过非空 YAML `workspace.root` 或 `MAIGOKITE_WORKSPACE_ROOT` 指定其他目录；启动不会搬动旧文件，也不会把源码根目录本身当作工作区。

脚本中的相对安装、工作区、配置和解释器路径，都以项目根目录为基准解析，不随子进程的工作目录变化。

Core 解释器顺序：`MAIGOKITE_PYTHON` → `UV_PROJECT_ENVIRONMENT` 或根 .venv → 已激活环境 → `uv python find --no-python-downloads` → 系统 Python / Windows `py -3`。
显式配置无效立即报错；启动不下载解释器或安装依赖。
工作区命令和 MCP 的 command/args 不必使用 Core 的解释器。Linux 沙箱仍按原有权限和挂载边界处理路径。

浏览器工具需单独执行 `<Core Python> -m playwright install chromium`，或在配置中指定已有 Chromium 的路径。
桌面需本机图形会话；Linux 的系统图形库依赖不由脚本提权安装。

### Windows 找不到 GOROOT

如果出现 `go: cannot find GOROOT directory: 'go' binary is trimmed and GOROOT is not set`，说明当前 Go 工具找不到配套 SDK，不是 Agent 业务代码报错。

在报错的 PowerShell 中执行 `where.exe go` 和 `$env:GOROOT`。检查是否选中了另一环境的 Go，或者只复制了 go.exe，没有安装完整 SDK。
`GOROOT` 如需显式设置，应指向同一套 SDK 的根目录，包含 `bin/go.exe`、`src/runtime`、`pkg/tool`，不能指向 bin、项目目录或 GOPATH。
建议按 [Go 官方安装说明](https://go.dev/doc/install) 修复完整安装并重新打开终端。

setup 和 Gateway 构建会先用 `go env GOROOT` 检查 Go 安装。失败时显示原始错误和排查命令，不猜测 Conda/Scoop 的目录，也不修改系统环境变量。

在 scripts 目录中，用 `./start.ps1 desktop` 启动桌面；不传目标时仍默认为 Web。已有完整构建产物时可用 `./start.ps1 desktop built`，此模式不调用 Go 编译器。

### Electron installation：编译成功但运行时缺失

`electron:compile` 只编译主进程和 preload 的 JavaScript，不负责安装 Electron 可执行文件。
若启动报告 `Electron failed to install correctly`，不要反复构建，也不必先删除整个 node_modules。

Node.js 24.16.0 / 26.1.0 起，旧 `extract-zip → yauzl 2.x` 可能在解压第一项时静默退出，安装命令返回 0，但没有生成 `dist/electron`（Windows 为 `electron.exe`）和 `path.txt`。
参见 [Electron #51619](https://github.com/electron/electron/issues/51619) 和 [extract-zip #154](https://github.com/max-mapper/extract-zip/issues/154)。
项目使用 npm `overrides`，仅将 `extract-zip` 的 `yauzl` 固定为已修复该问题的 `3.3.1`；不替换 Electron 安装器、不手工伪造 path.txt、不关闭校验，也不改变 Electron 主版本。
未来升级 Electron 安装依赖、确认上游已不受影响后删除此覆盖。

首次获取源码时，按 setup → build desktop → start desktop built 的顺序执行即可。依赖覆盖和锁文件随仓库分发，不依赖开发机的缓存，也不需要手工修改 node_modules。
已安装旧依赖的环境，先更新仓库，再在项目根目录执行：

```bash
bash scripts/setup.sh electron
```

```powershell
.\scripts\setup.ps1 electron
```

修复入口要求已有 Web 依赖。它先用 npm install 同步项目锁文件和解压依赖覆盖，不删除整个 node_modules，也不执行其他包的安装脚本；随后只重跑 Electron 官方安装脚本。安装器会复用有效缓存，缓存不存在时下载并校验文件。这个过程不安装 Go / Python 依赖，也不重编业务代码。新机器没有依赖时，应执行完整 setup。

完整 setup 使用 npm ci 重新安装 Web 依赖，并显式包含 devDependencies、启用安装脚本，避免 NODE_ENV=production 或 ignore-scripts 设置导致桌面工具缺失。

setup 在安装前检查 `ELECTRON_SKIP_BINARY_DOWNLOAD` 及跨平台、跨架构的 npm 覆盖配置。有冲突时会报错，不会安装另一平台的文件。如果设置过 `ELECTRON_SKIP_BINARY_DOWNLOAD`，请先取消；即使值为 `0`，Electron 28 也会跳过下载。

下载使用已有的网络和代理设置。不要通过禁用 TLS 或 checksum 校验来解决网络错误。

`setup` 会显示安装脚本输出。结束前会检查 Electron 可执行文件是否非空、是否可执行，以及 dist/version 是否与 npm 包版本一致；显式使用 ELECTRON_OVERRIDE_DIST_PATH 时，由调用者管理版本。桌面 build/start 也会在编译或创建服务前检查，不只依据 npm 的退出码判断安装是否完成。Web build/start 不要求 Electron。
修复后，已有构建产物可直接使用 `start.sh desktop built` / `start.ps1 desktop built`，无需重新编译业务代码。

### 生命周期

- Web 入口管理 Core、Gateway、Vite；桌面入口管理 Electron 和可选的 Vite，再由 Electron 管理 Core/Gateway。默认不连接旧实例。
- 端口冲突在服务创建前报错，Core 禁止 reuseport 并在恢复业务库前绑定端口；不会按名称杀掉其他程序。
- 子进程创建与联动退出复用 concurrently，强制清理复用 tree-kill / 操作系统进程组，不建立另一个进程管理框架。
- Ctrl+C 或任一组件退出会停止本次拥有的其他组件。Web 标签页关闭不代表退出。桌面关窗口隐藏到托盘，托盘“退出”才关闭整套。
- 启动器保留 stdin 管道；Core/Gateway 收到 EOF 后执行现有关闭逻辑。Windows 也先通过 EOF 通知进程清理，而不是立即 taskkill；超过等待上限才强制结束本次启动的进程。强制结束不能保证任务完成清理。
- Core 处理 SIGINT/SIGTERM，停止服务并关闭运行时；Gateway 等待 HTTP shutdown 完成。重复桌面退出不会跳过已经开始的清理。
- `scripts/dev.sh` 是 `start web dev` 的兼容快捷方式。在 web 目录执行 `npm run electron:dev`，也会调用成套桌面入口。
- 成套入口拒绝 `VITE_MOCK=1` / `MAIGOKITE_EXTERNAL_RUNTIME=1`。UI 单独联调可在 web 目录运行 Vite 和显式 `npx electron .`；这些外部服务仍由各自启动者负责。

PowerShell 禁止执行脚本时，确认源码可信后可使用进程级 `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start.ps1 web`；脚本不更改全局执行策略。
这些脚本不自动运行软件测试。脚本与调用链已做静态核对，但 Windows 实机运行和整套退出仍待验收；静态检查不能代替启动验证或安装包验收。

配置、生效范围和凭证管理见 [配置指南](../user-guide/Configuration.md)。

## 4. 质量与构建入口

以下测试命令以本地已有测试文件为前提。当前 `.gitignore` 排除了 Go/Python/Web 测试、Vitest 配置与 `scripts/run_tests.sh`，新克隆不包含这些入口或完整测试集；依赖安装不会补齐它们。不要把“未发现测试”或未执行记录写成通过。测试范围与证据口径见 [测试与验收](../testing/TestPlan.md)。

| 入口 | 范围 |
| --- | --- |
| `cd gateway` 后 `go test ./...` | 网关 Go 测试 |
| 项目 Python 执行 `-m pytest python`（根目录） | 根环境的 Python 测试集 |
| `cd web` 后 `npm run test:run` | Vue/Vitest |
| `scripts/run_tests.sh` | 维护者本地聚合测试入口，不随 Git 分发 |
| `build.sh all` / `build.ps1 all` | Go + Vue/Electron；Python 分发包另用 python 目标，不是完整桌面发布 |

从根目录执行 `.venv/bin/ruff check python/` 和 `.venv/bin/mypy python/agent` 可检查 Python 代码。报告时写明实际检查范围和失败结果，不要将检查失败写成“工具缺失”或“跳过”。静态检查失败须保留非零退出码。平台限制和安装包验收要求见构建与发布指南。

Go 模块路径为 `maigokite/gateway`，当前不绑定任何 Git 托管地址；`go.mod`、内部导入和 proto 的 `go_package` 使用同一前缀。

Proto 改动须重新生成 Go/Python 绑定并做契约回归，生成文件不得手改。Go 绑定在 gateway 目录执行 `protoc -I ../proto --go_out=. --go_opt=module=maigokite/gateway --go-grpc_out=. --go-grpc_opt=module=maigokite/gateway ../proto/agent.proto`（需要 protoc 与对应 Go 插件），Python 绑定使用 `.venv/bin/python python/scripts/generate_proto.py`；两者读取根 `proto/agent.proto`。契约说明见 [API 设计](../design/API.md#5-grpc-服务)。新增持久字段须验证空库与旧库升级。

## 5. 修改规则

- Go：遵循 gofmt，错误保留包装链，context 传播期限/取消；避免吞错或隐藏 goroutine 生命周期。
- Python：公开边界写类型，异步资源由明确生命周期持有，取消后等待资源清理；不创建通用 DI、插件或取消框架替代已有组件。
- Vue：使用 TypeScript 与清晰的组件/store 边界；卸载清理订阅，渲染不可信 Markdown 前消毒，渲染进程不获 Node/Shell 权限。
- 工具、副作用、权限、恢复修改必须覆盖对应失败路径；日志不记录敏感凭证、完整环境和隐藏思维链。
- 成熟实现优先。新增自研基础设施须说明替代调查、关键需求和长期维护收益，不能因已有代码就默认沿用。

## 6. 提交与文档

使用短生命周期目标分支，保持改动可审阅；Conventional Commits 可用 `feat/fix/docs/refactor/test/chore/perf`，scope 按模块。不得把示例 Git reset/force push 当作自动清理步骤。

提交或 PR 须说明改动、验证范围、未验证项，以及对兼容性和回滚的影响。协议变化更新 API，表变化更新 Database，运行机制变化更新 AgentRuntime，验收状态更新 Roadmap；不要另建内容重复的文档。只有实测证据才能标记“通过”，编译和测试不能代替发布包验收。
