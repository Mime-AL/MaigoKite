# 开发环境

> 状态：Current
> 最后核对：2026-09-14
> 版本下限以各模块清单文件为最终依据。

## 前置条件

- Go 1.22 或更高版本（`gateway/go.mod`）
- Python 3.11 或更高版本（`python/pyproject.toml`）
- Node.js 与 npm；前端依赖及脚本以 `web/package.json` 为准
- 可选：Docker Compose，用于容器化联调

## 初始化

```bash
cd gateway
go mod download

cd ../python
python -m venv ../.venv
source ../.venv/bin/activate
python -m pip install -e '.[dev]'

cd ../web
npm install
```

## 本地启动

可独立启动各组件，也可从仓库根目录统一启动：

```bash
make dev

# 或分别启动
cd gateway
go run ./cmd/gateway

cd ../python
../.venv/bin/python -m agent.main run --config ../config/config.dev.yaml --port 8081

cd web
npm run dev
```

Electron 开发模式使用 `web/package.json` 中的 `npm run electron:dev`。`agent.main:main_cli`、gRPC 服务和根目录启动脚本已经接通。实际监听地址、凭证和存储位置由环境配置决定。

## 配置与验证

- 配置项及优先级：[Configuration.md](../user-guide/Configuration.md)
- 接口契约：[API.md](../design/API.md)
- 测试入口：[TestPlan.md](../testing/TestPlan.md)
- 容器联调：[Docker.md](../deployment/Docker.md)

凭证不得提交到仓库，也不得写入普通 YAML、数据库业务表或日志。需要共享的示例配置只能包含键名和非敏感默认值。
