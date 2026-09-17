# Docker 容器化部署

> **状态**：Planned（目标容器拓扑；当前根目录 Compose/Dockerfile 尚未完成对齐）
> **最后核验**：2026-09-14
> **权威范围**：镜像、Compose 服务边界和容器运行约束

总体上线流程见 [Production](Production.md)，安全、监控和备份分别引用 ops-security 文档。

## 1. 服务拓扑

```text
frontend / ingress
    → Go Gateway
        → Python Agent Core (gRPC)
            → PostgreSQL/SQLite profile
            → Vector Store（可选）
            → MCP child processes/workers
```

容器模式由 Compose/Kubernetes 管理 Go 与 Python；Go 不启动 Python 子进程。

## 2. 构建上下文

| 服务 | 上下文 |
|---|---|
| gateway | `gateway/` |
| agent-core | `python/` |
| frontend | `web/` |

镜像使用多阶段构建、非 root 用户、固定基础镜像 digest 和最小运行时依赖。第三方 Skill 不安装到 Gateway 镜像。

## 3. Compose 结构示例

以下仅展示目标关系。当前根目录 `docker-compose.yml` 仍使用旧服务、端口和构建 target，不能作为此架构的可部署证明；实现时应先按本节边界重写并通过部署测试。

```yaml
services:
  gateway:
    build: ./gateway
    environment:
      AGENT_CORE_GRPC_ENDPOINT: agent-core:8081
    depends_on:
      agent-core:
        condition: service_healthy

  agent-core:
    build: ./python
    environment:
      DEPLOYMENT_PROFILE: server
      DATABASE_URL: ${DATABASE_URL}
      VECTOR_ENDPOINT: ${VECTOR_ENDPOINT:-}

  frontend:
    build: ./web
    depends_on: [gateway]
```

- Python 8081 是 gRPC endpoint；健康检查使用 gRPC health。
- Vector endpoint 来自配置，不在架构文档固定 ChromaDB 端口。
- 数据库迁移由一次性 Job 完成，不由多个应用副本竞争执行。

## 4. Secret

- `.env` 仅适合本地开发，不作为生产 Secret 方案。
- 生产使用 Docker Secret、Vault、KMS 或 Kubernetes Secret。
- 容器只获得当前服务所需的 Secret 引用或值。
- MCP Server 不继承 Agent Core 的完整环境。

## 5. 数据卷

- 本地单实例 profile 可挂载 SQLite 和内容目录。
- 多实例服务器 profile 使用外部 PostgreSQL/对象存储。
- Vector 数据是派生索引；原始 Document 必须单独持久化。
- 不直接复制运行中的 SQLite 文件，按 [Backup](../ops-security/Backup.md) 创建一致性快照。

## 6. 健康与关闭

- Gateway readiness 依赖 Agent Core 可连接，但 liveness 不应因短时依赖失败反复重启。
- Agent Core readiness 依赖迁移完成和权威数据库可用。
- Vector 服务不可用可进入 degraded，是否阻断 readiness 由产品能力要求决定。
- shutdown 时停止接收新任务，传播取消/期限并关闭 MCP 子进程。

## 7. 资源和网络

- Gateway 只暴露公开入口。
- Agent Core、数据库和 Vector Store 位于内部网络。
- MCP 网络访问根据 SkillGrant 单独限制。
- 为 Go、Python、模型和 MCP 配置 CPU、内存、进程数和输出大小限制。

## 8. 验收

- [ ] Compose 使用实际仓库路径。
- [ ] Go 不在容器内启动 Python。
- [ ] Python health 与 gRPC 协议一致。
- [ ] Secret 不进入镜像和普通环境模板。
- [ ] 数据迁移只有一个执行者。
- [ ] 服务可优雅关闭并清理 MCP 进程。
