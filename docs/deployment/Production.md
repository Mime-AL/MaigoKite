# 生产部署指南

> **状态**：Planned（生产目标；当前仅源码开发与本地构建已验证）
> **最后核验**：2026-09-18
> **权威范围**：部署形态、上线流程、回滚与生产验收

## 1. 部署形态

当前仓库不能作为生产就绪证明：服务器身份认证、受认证内部 gRPC、PostgreSQL、多实例 lease、正式迁移、指标告警、制品签名和容器拓扑尚未闭环。以下内容是进入生产前必须满足的目标约束。

### 桌面

- Electron 作为 Runtime Supervisor。
- Go/Python 只监听 loopback 并使用本次启动的认证材料。
- 本地默认 SQLite 和 OS Credential Store；独立文档内容存储尚未接入。
- 打包资源包括经过校验的 Go/Python运行时，不从可写目录执行替换文件。

### 服务器

- Ingress → Go Gateway → Python Agent Core。
- Docker/Kubernetes 分别管理服务。
- 推荐 PostgreSQL、对象存储和受管 Secret Provider。
- 多副本任务处理需要 lease、幂等和可靠事件机制。

两种形态共享领域模型、API 和前后端业务代码，仅替换身份、存储、凭证与 supervisor 适配器。

## 2. 发布流程

```text
契约兼容检查
→ 构建与测试
→ 数据迁移演练
→ 生成不可变制品和 SBOM
→ 签名
→ 预发布环境验证
→ 备份/恢复点
→ 灰度或桌面渠道发布
→ 指标观察
→ 完成或回滚
```

发布版本与 [Changelog](../project/Changelog.md) 对应；Planned 能力不得进入发布说明。

## 3. 配置与 Secret

- 配置遵循统一 Schema，并在启动时严格校验。
- 生产配置不包含明文 API Key。
- Credential Reference 指向 Keychain/Vault/KMS/Secret Manager。
- 配置变更记录 actor、版本和生效范围。
- 权限缩减和凭证撤销对新调用立即生效。

## 4. 网络与认证

- 外部入口强制 HTTPS/WSS。
- Gateway 验证 JWT/OIDC issuer、audience、expiry、签名算法和 key。
- WebSocket 握手验证身份、Origin 和 Workspace Membership。
- 内部 gRPC 使用服务身份认证；不向公网暴露 Agent Core。
- CORS 使用显式来源列表，生产 CSP 不使用无必要的 `unsafe-eval`。

## 5. 数据迁移

- 先备份并完成恢复演练。
- 单独 Migration Job 执行 Schema 升级。
- 破坏性变更使用 expand/migrate/contract。
- 应用只在兼容 Schema 上启动。
- SQLite 与 PostgreSQL profile 分别验证迁移。

## 6. 可观测性

上线至少观察：

- HTTP/gRPC 错误率和延迟。
- Task 成功、失败、等待审批、取消和超时。
- Tool/MCP失败率与重启次数。
- 模型延迟、token 和费用。
- 数据库连接、锁和迁移状态。
- WebSocket连接、重放和积压。

指标与告警见 [Monitoring](../ops-security/Monitoring.md)，日志字段见 [Logging](../ops-security/Logging.md)。

## 7. 回滚

- 应用制品按不可变版本回滚。
- 数据库优先采用向前兼容修复；需要恢复时遵循备份流程。
- 桌面更新保留上一稳定版本及数据迁移兼容窗口。
- SkillVersion 可回滚，但不能恢复已撤销的权限或凭证。
- 回滚完成后验证任务租约、审批和事件积压。

## 8. 生产验收

- [ ] 当前制品、Changelog 和架构版本一致。
- [ ] OpenAPI/Proto/事件 Schema 兼容检查通过。
- [ ] 数据迁移和恢复演练通过。
- [ ] 无跨 Workspace 访问路径。
- [ ] L5 和 hard-deny 行为符合权威权限规范。
- [ ] Gateway、Agent Core 和 MCP 可优雅关闭。
- [ ] Secret 未进入镜像、日志或数据库。
- [ ] 告警、值班和回滚负责人明确。

容器细节见 [Docker](Docker.md)，流水线见 [CI-CD](CI-CD.md)，备份见 [Backup](../ops-security/Backup.md)。
