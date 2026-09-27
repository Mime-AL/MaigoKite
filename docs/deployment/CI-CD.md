# CI/CD 设计

> **状态**：Planned（当前仓库没有已核验的远程 CI workflow）
> **最后核验**：2026-09-18
> **权威范围**：流水线阶段、质量门与发布自动化

测试场景由 [TestPlan](../testing/TestPlan.md) 定义；本文只描述如何执行。

当前可重复入口是 `scripts/run_tests.sh` 与 `scripts/build.sh all`；它们覆盖 Go、Python、Vue 测试及 Go/Python/Vue/Electron 编译，但不等于下述完整发布流水线。

## 1. 流水线

```text
validate
→ unit
→ integration
→ security
→ build
→ package
→ deploy staging
→ smoke
→ approve/release
→ observe/rollback
```

## 2. Validate

- Go format/lint/type checks。
- Python lint/type checks。
- Vue/TypeScript lint/type checks。
- Markdown链接和格式。
- 配置 Schema 校验。
- OpenAPI/Proto/事件 breaking-change 检查。
- 文档 endpoint、表名和路径一致性检查。

## 3. Test

按模块并行执行：

```text
gateway/        go test ./...
python/         Python unit/integration/security tests
web/            frontend unit/component tests
web/            Electron tests
repository      contract/migration/deployment tests
```

PR 必须执行单元、契约和关键集成测试。性能、恢复、完整 E2E 和多平台打包可按主分支或发布流水线执行。

## 4. Build

- Go Gateway 生成平台制品。
- Python生成可锁定依赖的运行时包/镜像。
- Vue生成静态资源。
- Electron生成签名桌面包。
- Docker镜像使用不可变 tag/digest。
- 所有发布制品生成 SBOM、校验和和签名。

## 5. 数据库

- 当前阶段在空 SQLite 和兼容旧 SQLite 文件上执行验证；PostgreSQL 接入后加入全量迁移。
- 从最低受支持版本执行升级测试。
- 检查 ER/数据字典派生内容是否需要更新。
- 发布前在预发布副本完成迁移和恢复验证。

## 6. 发布与回滚

- Release 只从受保护 tag 产生。
- Changelog 必须对应实际差异。
- 生产部署使用环境保护和人工审批。
- 桌面、容器和 Schema 版本建立兼容矩阵。
- 关键指标超过门槛触发暂停或回滚，而不是仅依赖部署成功状态。

## 7. Required checks

```text
docs-contracts
go-quality
python-quality
web-quality
electron-security
api-compatibility
database-migrations
integration
security
package-smoke
```

任何临时跳过都必须有负责人、原因和到期时间。
