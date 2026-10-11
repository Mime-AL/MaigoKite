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

没有 uv 时可从同一清单安装，但 pip 路径不保证使用 uv 锁定版本：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

再分别运行：

```bash
cd gateway
go mod download
```

```bash
cd web
npm ci
```

`make setup` 聚合以上安装步骤；uv 和 pip 分支均使用根项目及根 `.venv`，不再选择 Poetry/子项目，也不默认安装向量库或 Docker SDK。不要向全局解释器强行安装。若主动覆盖 `UV_PROJECT_ENVIRONMENT`，须同时用 `MAIGOKITE_PYTHON` 指定启动解释器；否则保持默认根环境。

## 3. 启动

从根目录：

```bash
make dev
```

脚本启动网关、Python gRPC 核心服务和 Vite；优先使用根 `.venv`，否则使用 `MAIGOKITE_PYTHON` 或 python3。当前开发脚本 Vite 监听 `0.0.0.0:5173`，仅用于受信开发网络，不可当作受认证远程访问入口。

Electron 开发模式在 `web/` 执行：

```bash
npm run electron:dev
```

Electron 使用真实的主进程环境，通过既有白名单传递 PATH、HOME、代理和 Go 缓存设置；这些值不会编译到前端。Core 监听 8081 后启动 Gateway，Gateway 监听 8080 后加载界面。两步分别最多等待 90 秒，失败显示原生错误弹窗，后台输出直接保留在启动终端。

开发命令的 Vite 固定在 5173，启用 `--strictPort`，不允许端口冲突时静默改成 5174。Electron 与 Vite 联动退出；桌面启动失败返回非零退出码，不继续留下一个独立开发页面。

不要同时运行两个会启动同一网关/核心服务的进程监督器。已有外部运行时联调时可用 `MAIGOKITE_EXTERNAL_RUNTIME=1` 避免 Electron 再启动子进程。此模式下后端由外部启动者负责，Electron 不会结束它们。

桌面进程退出时清理自己启动的进程；Unix 使用独立进程组，包含 `go run` 创建的 Gateway 子进程，Windows 使用系统 `taskkill /T` 清理进程树。正常退出先请求终止，等待关闭；Unix 超过 10 秒仍未退出时强制结束。窗口关闭默认隐藏到托盘，彻底退出使用托盘菜单或启动终端的 `Ctrl+C`。

配置、生效范围和凭证管理见 [配置指南](../user-guide/Configuration.md)。LangGraph 临时迁移开关 只见 [运行时迁移说明](RuntimeMigration.md)。

## 4. 质量与构建入口

| 入口 | 范围 |
| --- | --- |
| `make test-go` | 网关 Go 测试 |
| `make test-python` | 根环境的 Python 测试集 |
| `make test-vue` | Vue/Vitest |
| `scripts/run_tests.sh` | 聚合测试入口，具体场景见 [测试与验收](../testing/TestPlan.md) |
| `make build` | 当前 Go、Python 分发包和 Vue/Electron 编译，不是完整桌面发布 |

Python 质量检查可从根执行 `.venv/bin/ruff check python/` 和 `.venv/bin/mypy python/agent`；报告实际检查范围和失败，不用“工具缺失”掩盖检查失败。现有 `make lint` 会将部分非零退出降为“跳过”，不能单独作为发布绿灯。构建的平台限制和安装包门禁见构建与发布指南。

Go 模块路径为 `maigokite/gateway`，当前不绑定任何 Git 托管地址；`go.mod`、内部导入和 proto 的 `go_package` 使用同一前缀。

Proto 改动须重新生成 Go/Python 绑定并做契约回归，生成文件不得手改。Go 绑定使用 `make -C gateway proto`（需要 protoc 与对应 Go 插件），Python 绑定使用 `.venv/bin/python python/scripts/generate_proto.py`；两者读取根 `proto/agent.proto`。契约说明见 [API 设计](../design/API.md#5-grpc-服务)。新增持久字段须验证空库与旧库升级。

## 5. 修改规则

- Go：遵循 gofmt，错误保留包装链，context 传播期限/取消；避免吞错或隐藏 goroutine 生命周期。
- Python：公开边界写类型，异步资源由明确生命周期持有，取消后等待资源清理；不创建通用 DI、插件或取消框架替代已有组件。
- Vue：使用 TypeScript 与清晰的组件/store 边界；卸载清理订阅，渲染不可信 Markdown 前消毒，渲染进程不获 Node/Shell 权限。
- 工具、副作用、权限、恢复修改必须覆盖对应失败路径；日志不记录敏感凭证、完整环境和隐藏思维链。
- 成熟实现优先。新增自研基础设施须说明替代调查、关键需求和长期维护收益，不能因已有代码就默认沿用。

## 6. 提交与文档

使用短生命周期目标分支，保持改动可审阅；Conventional Commits 可用 `feat/fix/docs/refactor/test/chore/perf`，scope 按模块。不得把示例 Git reset/force push 当作自动清理步骤。

提交或 PR 说明实际差异、验证范围、未验证项及兼容/回滚影响。协议变化改 API，表变化改 Database，运行机制改 AgentRuntime，验收状态改 Roadmap；不要再新建同义文档。只有实测证据才能写“通过”，编译与测试不代替发布包验收。
