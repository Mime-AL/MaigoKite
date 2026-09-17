# NanamiGopher 常见问题

> **状态**：Current
> **最后核验**：2026-09-16

## 如何理解个人和团队空间？

两者使用同一套 Workspace 模型。Personal Workspace 通常只有一个成员，Team Workspace 有多个 Membership；不是两套客户端或业务代码。

## 只读、工作区和完全访问有什么区别？

只读档位仅自动读取和搜索；工作区档位会自动进行 Workspace 内编辑及安全命令；完全访问档位还会自动执行普通联网操作。重大影响操作仍需逐次批准，hard-deny 永远拒绝。详见 [Tool Permission](../agent-capabilities/security/tool-permission.md)。

## Native Tool 和 MCP Tool 有什么区别？

Native Tool 在 Python Agent Core 进程内执行；MCP Tool 由 Python MCPClient 调用独立 Server。二者都经过同一个 ToolRegistry、ToolPolicy、取消、超时和审计流程。

## 如何安装 Skill？

本地文件使用 import，受支持的注册源使用 install。安装前系统会验证 manifest、来源、能力、资源和凭证请求。格式见 [Skill Lifecycle](../agent-capabilities/skills/skill-lifecycle.md)。

## 数据存在哪里？

本地模式默认使用 SQLite 和本地内容存储；服务器模式可使用 PostgreSQL 和对象存储。Secret 使用 Keychain/Vault，不进入普通数据库。详见 [Database](../design/Database.md)。

## Memory 和知识库有什么区别？

Memory 保存 Agent 运行和用户相关信息；知识库保存用户导入或授权接入的外部资料。消息和原始文档是事实来源，摘要与向量索引可以重建。详见 [Memory](../agent-capabilities/memory/memory-system.md)。

## WebSocket 断开会取消任务吗？

不会。任务状态由 Agent Core 持久化管理。客户端重连后先获取状态快照，再从最后事件序号恢复。

## 如何取消任务？

使用显式取消操作。关闭页面或断开 WebSocket 不等价于取消。

## 如何备份？

使用一致性快照或数据库支持的备份方式，不直接复制活动 SQLite 文件。详见 [Backup](../ops-security/Backup.md)。

## 从哪里开始排障？

1. 查看 Gateway 和 Agent Core 健康状态。
2. 使用 trace/request/task ID 查询日志。
3. 检查模型、MCP Server、数据库和索引依赖。
4. 参考 [Installation](Installation.md)、[Logging](../ops-security/Logging.md) 和 [Monitoring](../ops-security/Monitoring.md)。

未标记为 Current 的能力不保证已经交付。
