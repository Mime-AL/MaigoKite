# 目录结构

> 状态：Current
> 最后核对：2026-09-14
> 本文是仓库物理目录的说明；组件职责以 [SystemDesign.md](../design/SystemDesign.md) 为准。

## 顶层目录

```text
NanamiGopher/
├── gateway/        # Go Gateway、外部 API、鉴权与进程边界
├── python/         # Python Agent Core、工具、MCP、记忆与工作流
├── web/            # Vue 3 前端与 Electron 壳
├── docs/           # 产品、架构、开发、部署和运维文档
├── proto/          # Go/Python 共用的唯一 gRPC 协议源
├── go.work         # 将根目录声明为 Go workspace，引用 gateway 模块
├── docker-compose.yml
└── Makefile
```

## Go Gateway

```text
gateway/
├── cmd/gateway/        # 可执行入口
├── internal/api/       # DTO、Handler、Router 与 WebSocket 接入
├── internal/config/    # Gateway 配置
├── internal/credentialstore/ # OS 凭证存储边界
├── internal/grpc/      # Python Agent Core Client
├── internal/observability/
├── internal/websocket/
└── pkg/                # 生成的 Proto 与通用中间件
```

Go 只承担外部接入、身份与访问策略、流式转发和 Agent Core 客户端职责，不实现 Agent 领域写入。

## Python Agent Core

```text
python/
├── agent/              # Agent 运行时与领域模块
│   ├── tools/          # Native Tool 与统一注册表
│   ├── memory/         # 记忆生命周期
│   ├── knowledge_base/ # 文档与检索
│   ├── workflow/       # 规划中的版本化工作流骨架
│   ├── browser_runtime.py
│   ├── repository.py   # 当前 SQLite Repository
│   ├── skill_registry.py
│   └── grpc_generated/ # 由根目录 Proto 生成，不手工编辑
└── tests/              # 单元、集成、安全与性能测试
```

## Web 与 Electron

```text
web/
├── src/components/     # 展示组件
├── src/views/          # 路由页面
├── src/stores/         # Pinia 状态
├── src/composables/    # 可复用交互逻辑
├── src/electron/       # 桌面端桥接代码
└── public/             # 静态资源
```

目录新增应服从组件边界，不能通过复制类型、协议或策略定义来建立新的“局部真相源”。API、数据库和权限定义分别回到对应规范文档维护。
