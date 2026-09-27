# NanamiGopher 常见问题

> **状态**：Current
> **最后核验**：2026-09-18

## 如何理解个人和团队空间？

两者使用同一套 Workspace 模型。Personal Workspace 通常只有一个成员，Team Workspace 有多个 Membership；不是两套客户端或业务代码。

## 只读、工作区和完全访问有什么区别？

只读档位仅自动读取和搜索；工作区档位会自动进行 Workspace 内编辑及安全命令；完全访问档位还会自动执行普通联网操作。重大影响操作仍需逐次批准，hard-deny 永远拒绝。详见 [Tool Permission](../agent-capabilities/security/tool-permission.md)。

## Native Tool 和 MCP Tool 有什么区别？

Native Tool 在 Python Agent Core 进程内执行；MCP Tool 由 Python MCPClient 调用独立 Server。二者都经过同一个 ToolRegistry、ToolPolicy 和审计入口。MCP 请求已有超时，但任务取消目前只能在调用边界阻止后续步骤，不能保证立即中断正在执行的第三方 MCP 调用。

## 如何安装 Skill？

Phase 1 没有远程“安装”流程，但可以在配置的目录中添加声明式 `SKILL.md`，重启 Core 后由 `skill list/read` 使用；它不会执行 Skill 目录中的代码。可执行扩展由部署者配置受信 stdio MCP Server。远程 install、签名版本、Grant 与回滚是后续目标，格式见 [Skill Lifecycle](../agent-capabilities/skills/skill-lifecycle.md)。

## 数据存在哪里？

当前实现使用 SQLite 和本地内容存储；PostgreSQL/对象存储是团队部署阶段目标。Secret 使用 Keychain/Vault，不进入普通数据库。详见 [Database](../design/Database.md)。

## Memory 和知识库有什么区别？

Phase 2 已开始提供用户直接维护的 User Memory，可以在“用户记忆”页面查询、修改和遗忘。自动抽取、语义检索、知识库、摘要、Embedding 与向量索引仍在后续切片；其中消息和原始文档是事实来源，摘要与索引均可重建。详见 [Memory](../agent-capabilities/memory/memory-system.md)。

## WebSocket 断开会取消任务吗？

不会。任务状态由 Agent Core 持久化管理。客户端重进对话时读取任务和事件历史，连接实时流后再按最新 sequence 补拉一次并按 event ID 去重。当前限制是单次最多补拉 1000 条事件，服务端原子续传与分页仍在发布门禁中跟踪。

Core 进程重启与普通断线不同：没有安全检查点的运行任务会显示 `interrupted`，不会自动重复副作用；等待审批的文件等持久操作可续接，但依赖已丢失 Browser session 的审批会被关闭并标记 interrupted。

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
