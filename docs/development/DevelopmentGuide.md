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

`go.work` 引用 gateway 模块。目录存在不证明模块已接入；工作流等骨架不视为可用能力。不复制类型、策略或协议建立“局部真相”。

## 2. 初始化

Go 最低版本见 `gateway/go.mod`；Python 两份项目清单当前均要求 3.11+；Node/npm 版本与依赖以 `web/package.json` 和锁文件为准。安装行为不同，不能假设根与 python 子项目的依赖完全一致。

以下从仓库根目录执行，使用根项目清单和同一个虚拟环境：

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

`make setup` 是已有快捷脚本，但其 uv/Poetry 分支在 `python/` 安装，可能不对应根 `.venv`；不要仅凭脚本成功假设 `make dev` 使用了该解释器。需要时通过 `NANAMI_PYTHON` 指定。不要向全局解释器强行安装。

## 3. 启动

从根目录：

```bash
make dev
```

脚本启动网关、Python gRPC 核心服务和 Vite；优先使用根 `.venv`，否则使用 `NANAMI_PYTHON` 或 python3。当前开发脚本 Vite 监听 `0.0.0.0:5173`，仅用于受信开发网络，不可当作受认证远程访问入口。

Electron 开发模式在 `web/` 执行：

```bash
npm run electron:dev
```

不要同时运行两个会启动同一网关/核心服务的进程监督器。已有外部运行时联调时可用 `NANAMI_EXTERNAL_RUNTIME=1` 避免 Electron 再启动子进程。

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
