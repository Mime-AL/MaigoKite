# 开发指南

> 权威范围：源码初始化、启动、质量检查、协议生成与贡献约束。
> 组件职责见 [系统设计](../design/SystemDesign.md)，发布见 [构建与发布指南](../deployment/ReleaseGuide.md)。

## 1. 仓库入口

| 路径 | 用途 |
| --- | --- |
| `gateway/` | Go 外部接入与 gRPC 客户端 |
| `python/agent/` | 核心服务、运行时桥接、工具和业务持久化 |
| `web/src/` | Vue；`electron/` 下为主进程/预加载层 |
| `proto/agent.proto` | 唯一共享 gRPC 源 |
| `config/`、`scripts/` | 运行配置、开发/构建/测试脚本 |
| `docs/` | 按 [文档索引](../README.md) 分配权威范围 |

`go.work` 引用 gateway 模块。目录存在不证明模块已接入；本批移除未接线的工作流/HITL、子智能体和 Recovery 空骨架，不取消这些能力需求，归属见 [智能体运行时设计](../design/AgentRuntime.md#7-技能子任务与工作流边界)。不复制类型、策略或协议建立“局部真相”。

## 2. 初始化

Go 最低版本见 `gateway/go.mod`；Python 要求 3.11+；Node/npm 版本与依赖以 `web/package.json` 和锁文件为准。Python 依赖唯一声明为根 `pyproject.toml`，解析结果为根 `uv.lock`；`python/` 仅为源码目录，不再独立安装或维护 requirements 清单。

推荐从仓库根目录执行，按锁文件安装到根 `.venv`：

```bash
uv sync --locked --extra dev
```

`dev` 包含质量工具、测试 HTTP 服务和协议生成器；不需要它们的运行环境使用 `uv sync --locked --no-dev`，不要添加 `--all-extras`。`vectorstores` 仅供尚未接入聊天的实验适配器，不是已交付的知识库功能，默认不安装。修改依赖后由维护者运行 `uv lock` 更新锁文件；锁定成功不代表运行或发布验收通过。

没有 uv 时，`setup.sh` / `setup.ps1` 会从可用的 Python 3.11+ 创建项目环境，再用 pip 安装同一清单；pip 路径不保证使用 uv 锁定版本。不再要求解释器的命令名为 `python3`：

```bash
bash scripts/setup.sh
```

如果不使用聚合 setup 脚本，而只运行了上面的 uv 命令，再分别运行：

```bash
cd gateway
go mod download
```

```bash
cd web
npm ci
```

`setup.sh` / `setup.ps1` 聚合以上安装步骤；uv 和 pip 分支均使用根项目，环境默认根 `.venv`，也读取 `UV_PROJECT_ENVIRONMENT`（相对路径以项目根为基准）。不再选择 Poetry/子项目，也不默认安装向量库或 Docker SDK。不要向全局解释器强行安装。设置 `MAIGOKITE_PYTHON` 时，uv 安装/构建也使用该解释器；pip 分支将它用于创建项目环境，依赖仍装在项目环境内。

## 3. 成套启动与构建（Linux / Windows）

两平台共用 `scripts/local.cjs`，Shell / PowerShell 仅转发参数，不依赖 Makefile、WSL 或 Git Bash。
需要 Node.js 18+、Go 1.22+、Python 3.11+；Windows 支持 PowerShell 5.1/7，先在该机器本地初始化，不要复用从 Linux 复制的 .venv 或 node_modules。

| 操作 | Linux（仓库根） | Windows PowerShell（仓库根） |
| --- | --- | --- |
| 初始化 | `bash scripts/setup.sh` | `.\scripts\setup.ps1` |
| Web 开发 | `bash scripts/start.sh web` | `.\scripts\start.ps1 web` |
| 桌面开发 | `bash scripts/start.sh desktop` | `.\scripts\start.ps1 desktop` |
| 构建 Web + Gateway | `bash scripts/build.sh web` | `.\scripts\build.ps1 web` |
| 构建桌面 + Gateway | `bash scripts/build.sh desktop` | `.\scripts\build.ps1 desktop` |
| 构建两种入口 | `bash scripts/build.sh all` | `.\scripts\build.ps1 all` |
| 已构建 Web | `bash scripts/start.sh web built` | `.\scripts\start.ps1 web built` |
| 已构建桌面 | `bash scripts/start.sh desktop built` | `.\scripts\start.ps1 desktop built` |

`start` 的默认目标是 web，默认模式 dev。dev 会编译 Gateway（桌面另编译 Electron），然后运行 Vue 热更新页面；built 不编译，缺少产物就报错。桌面 built 直接加载 `web/dist/index.html`，不再需要开发服务器。`build` 默认 all；另保留 go/python/vue 单组件构建，其中 python 单独生成 wheel/sdist。

Gateway 产物为 `dist/maigokite-api[.exe]`。成套脚本只构建本机架构，发现不一致的 GOOS/GOARCH 显式拒绝，避免构建成功后不能启动。跨平台分发不等于在一台 Linux 机器上输出可用的 Windows 桌面包。

Web dev 使用 `http://127.0.0.1:5173`，built 使用 `http://127.0.0.1:4173`；两者均代理 8080 的 Gateway，包括 WebSocket。Core 监听 8081。
Web built 是 Vite 本地预览，不是公网生产服务器；不得将它当作手机远程认证入口。
默认配置为 `config/config.dev.yaml`，built 也沿用这份配置和开发数据库，不会因为使用编译产物就切换数据目录。
可显式设置 `MAIGOKITE_CONFIG`，但 Gateway/Core/UI 端口仍需保持上述约定。

### 路径与解释器

Web 与桌面启动默认使用安装根目录下的 `.workspace`（源码模式为项目根）；Core 启动时创建。非空 YAML `workspace.root` 或 `MAIGOKITE_WORKSPACE_ROOT` 可覆盖；不搬动旧文件，不把源码根本身当作工作区。
成套脚本的相对安装/工作区/配置/解释器路径统一相对项目根解析，避免子进程不同工作目录带来歧义。

Core 解释器顺序：`MAIGOKITE_PYTHON` → `UV_PROJECT_ENVIRONMENT` 或根 .venv → 已激活环境 → `uv python find --no-python-downloads` → 系统 Python / Windows `py -3`。
显式配置无效立即报错；启动不下载解释器或安装依赖。
Core 的解释器不会强加给工作区命令或 MCP 的 command/args。Linux 沙箱仍按原有权限和挂载边界处理路径。

浏览器工具需单独执行 `<Core Python> -m playwright install chromium`，或在配置中指定已有 Chromium 的路径。
桌面需本机图形会话；Linux 的系统图形库依赖不由脚本提权安装。

### 生命周期

- Web 入口持有 Core、Gateway、Vite；桌面入口持有 Electron 和可选的 Vite，Electron 持有 Core/Gateway。默认绝不连接旧实例。
- 端口冲突在服务创建前报错，Core 禁止 reuseport 并在恢复业务库前绑定端口；不会按名称杀掉其他程序。
- 子进程创建与联动退出复用 concurrently，强制清理复用 tree-kill / 操作系统进程组，不建立另一个进程管理框架。
- Ctrl+C 或任一组件退出会停止本次拥有的其他组件。Web 标签页关闭不代表退出。桌面关窗口隐藏到托盘，托盘“退出”才关闭整套。
- 启动器保留 stdin 管道；Core/Gateway 收到 EOF 后请求现有关闭逻辑。Windows 也先通过 EOF 清理，而非立即 taskkill；超过等待上限才强制结束自有进程。强制结束不能承诺任务的优雅收尾。
- Core 处理 SIGINT/SIGTERM，停止服务并关闭运行时；Gateway 等待 HTTP shutdown 完成。重复桌面退出不会跳过已经开始的清理。
- `scripts/dev.sh` 保留为 `start web dev` 的兼容快捷方式。`web/npm run electron:dev` 同样转调成套桌面入口。
- 成套入口拒绝 `VITE_MOCK=1` / `MAIGOKITE_EXTERNAL_RUNTIME=1`。UI 单独联调可在 web 目录运行 Vite 和显式 `npx electron .`；这些外部服务仍由各自启动者负责。

PowerShell 禁止执行脚本时，确认源码可信后可使用进程级 `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start.ps1 web`；脚本不更改全局执行策略。
本次只静态核对脚本与调用链，不自动跑测试、启动服务或生成安装包；Windows 实机与整套退出仍需后续验收。

配置、生效范围和凭证管理见 [配置指南](../user-guide/Configuration.md)。

## 4. 质量与构建入口

| 入口 | 范围 |
| --- | --- |
| `cd gateway` 后 `go test ./...` | 网关 Go 测试 |
| 项目 Python 执行 `-m pytest python`（根目录） | 根环境的 Python 测试集 |
| `cd web` 后 `npm run test:run` | Vue/Vitest |
| `scripts/run_tests.sh` | 聚合测试入口，具体场景见 [测试与验收](../testing/TestPlan.md) |
| `build.sh all` / `build.ps1 all` | Go + Vue/Electron；Python 分发包另用 python 目标，不是完整桌面发布 |

Python 质量检查可从根执行 `.venv/bin/ruff check python/` 和 `.venv/bin/mypy python/agent`；报告实际检查范围和失败，不用“工具缺失”掩盖检查失败。静态检查失败应保留非零退出码，不得降为“工具缺失/跳过”。构建的平台限制和安装包门禁见构建与发布指南。

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

提交或 PR 说明实际差异、验证范围、未验证项及兼容/回滚影响。协议变化改 API，表变化改 Database，运行机制改 AgentRuntime，验收状态改 Roadmap；不要再新建同义文档。只有实测证据才能写“通过”，编译与测试不代替发布包验收。
