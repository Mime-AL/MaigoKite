# 构建与发布指南

> 权威范围：源码构建、桌面制品、发布门禁与回滚。
> 当前尚未形成正式桌面 runtime bundling 闭环；本页的发布检查项是目标，不是验收结果。

## 1. 当前可生成什么

| 入口 | 当前产物 / 限制 |
| --- | --- |
| 根 `make build` / `scripts/build.sh all` | 聚合 Go、Python 包与 Web 编译 |
| `scripts/build.sh go` | 当前固定 Linux/amd64、CGO=0 的网关到 `dist/`；不是多平台发布 |
| `scripts/build.sh python` | 从根 Python 项目生成 wheel/sdist，不等于带解释器和依赖的智能体可执行运行时 |
| `web/ npm run build` | Vue 静态资源与 Electron 主进程/预加载层编译 |
| `web/ npm run electron:build` | electron-builder 入口；不证明已包含正确的 Go/Python/Chromium 资源 |

Electron packaged 分支期待 `resources/bin/agent-core` 和 `resources/bin/gateway`，当前源码构建产物尚未证明满足该路径和跨平台执行要求。不能把开发机已有 Go/Python、依赖或浏览器当作用户安装环境。

开发安装与命令仅在 [开发指南](../development/DevelopmentGuide.md) 维护。当前没有已核验远程 CI workflow，本文检查项不是 CI 已实施清单。

Python 构建与安装统一读取根 `pyproject.toml`，依赖锁定使用根 `uv.lock`；不再从 `python/` 选择另一套分发包。第一批轻量化仅修改入口并更新锁文件，没有执行构建或安装包验收，也没有补齐 runtime bundling。

## 2. 个人桌面发布闭环

```text
确定目标平台与版本
→ 契约/测试检查
→ 构建受锁定依赖的 Go + Python runtime
→ 打包 Vue/Electron 与所需 Browser 资源
→ 校验、签名和安装
→ 干净机器完整 E2E
→ 备份兼容检查
→ 发布与观察 / 回滚
```

必须验证：

- [ ] 目标平台的可执行格式、架构、路径与权限正确，不从任意可写位置执行替换资源。
- [ ] 用户不装 Go/系统 Python，也能完成首次聊天、文件读取、写入审批和关闭。
- [ ] 浏览器资源可用，错误提示能定位缺失依赖；不得默默依赖开发机浏览器。
- [ ] 网关/核心服务默认 loopback；本地认证缺口明确，端口不可当作安全认证。
- [ ] 启动就绪、异常退出、重启策略和退出等待经过测试，无孤儿核心服务/MCP/浏览器进程。
- [ ] 取消确认后没有持续执行和新的非终态 UI 事件。
- [ ] 旧 SQLite 升级、检查点恢复和文件 crash/replay 通过；范围见 TestPlan。
- [ ] 敏感凭证不进入制品、普通配置、数据库或日志；导出内容已脱敏。
- [ ] 版本、Changelog、制品校验信息和验证记录一致。

运行代码存在或 electron-builder 成功不等于以上门禁通过。完整发布阻塞状态只在 [交付路线与状态](../project/Roadmap.md) 跟踪。

## 3. 最小质量门

场景由 [测试与验收](../testing/TestPlan.md) 定义，执行命令由 DevelopmentGuide 定义。至少包括适用的静态检查/type、Go/Python/Vue 测试、协议兼容、授权安全、数据库升级、真实进程恢复与桌面 package-smoke。

缺少工具、凭证或平台时写明未运行/跳过，不标通过。模型提供方验收分别记录 PROTOCOL、LIVE 和 UNVERIFIED；真实缓存收益与成本不能从模拟服务推断。逐步复用现成 CI，不为个人项目建设发布平台或要求值班系统。

## 4. 配置与数据升级

使用当前配置方式，不为发布另造配置 Schema。敏感凭证留在 OS 凭证存储；用户路径和业务数据不能写入不可变应用资源目录。活动运行实例关闭后才能安全退出/更换其资源。

当前 Repository 是启动时兼容升级，不是 Alembic 或单独 Migration Job。发布前用受支持旧库副本验证，再留一致性恢复点；备份边界见 [备份与恢复](../ops-security/Backup.md)。业务库、检查点、文件和凭证不能假定一次复制就形成全局原子快照。

## 5. 回滚与诊断

保留上一稳定制品及适用的数据兼容说明。升级后数据库格式若不兼容旧版，不能直接降级程序；先恢复副本演练或做明确的向前兼容修复。

诊断查 [日志与诊断](../ops-security/Observability.md)，发布说明写实际功能，不把规划中页面、空壳工作流或未验收运行时当成已交付。回滚不能恢复已撤销的权限/凭证，也不能撤销已发生的工具副作用。

## 6. 历史容器与未来远程访问

根 Compose/Dockerfile 有历史残留，当前没有完成服务边界、health、端口和制品对齐，不能作为已支持的部署方式。不继续维护另一份目标 Compose 示例，避免与实际配置分叉。

若未来有具体容器需求，再修复构建上下文、非 root、敏感凭证、仅网关公开、gRPC health、数据一致性和进程关闭，并通过真实容器 E2E。PostgreSQL、多副本 lease、Kubernetes 不是个人桌面发布前提。

手机远程访问在 [手机远程访问](../design/RemoteAccess.md) 单独定义；必须完成设备配对和受保护入口，不能通过部署旧 Compose 或公开 loopback 端口“实现”。
