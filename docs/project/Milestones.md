# NanamiGopher 里程碑与完成度

> 状态：Current（2026-09-18）。本文件只记录可由代码或测试证明的状态。

状态：✅ 已闭环；🟡 已有实现但仍有明确缺口；⬜ 未实现。

## Phase 1：通用 Agent 执行内核

| 能力 | 状态 | 当前证据 | 剩余门禁 |
|---|---:|---|---|
| 对话与模型接入 | ✅ | 多 Provider、OpenAI-compatible、本地 Base URL、模型发现/验证、默认与会话级选择 | 高级能力路由属于 Phase 2 |
| 工具编排 | ✅ | 原生 Tool、参数校验、模型多 ToolCall、结果回注、失败提示、过程/回复分离 | 长任务步骤级重试属于 Phase 2 |
| 浏览器操作 | 🟡 | Playwright Runtime 与 browser Tool；公开 URL/工作区截图边界；权限与审计统一；系统 Chrome 公网站点冒烟通过 | 登录态/交互站点 E2E、下载上传策略、进程隔离 |
| 持续任务 | 🟡 | HTTP 只启动任务；任务持久化；按对话并行；停止 API 和 UI | Gateway/Core 进程管理、调度队列、资源配额 |
| 权限批准 | ✅ | 三种权限模式、L1-L5 风险、hard-deny、持久化审批、批准后继续、审计 | “本次/本会话”作用域授权属于 Phase 2 |
| 状态恢复 | 🟡 | SQLite 任务事件序列、历史 API、连接后补拉与回放去重；可持久续接的 approval 可恢复，Browser 易失会话会明确 interrupted | 原子游标订阅与连续分页；安全检查点自动续跑 |
| Local Skill | ✅ | `SKILL.md` 扫描、YAML 元数据校验、目录逃逸/大小限制、list/read Tool、前端真实清单 | 热重载、签名、版本安装/回滚属于后续阶段 |
| MCP | 🟡 | 配置式 stdio 启停、Tool 发现、统一权限/审计、运行清单 | 健康重启、空闲回收、页面配置和授权治理 |
| Web/Electron 客户端 | 🟡 | 对话、活动、审批、停止、模型/权限、文件预览/Diff、扩展清单、重连后补拉，Electron 构建 | 大事件流分页和真实桌面 E2E |

## 本轮完成内容

- 浏览器能力从 `web_fetch` 提升为有会话的 Playwright 操作，并复用系统 Chrome 配置；
- 将任务输入、状态、错误、版本和事件序列写入 SQLite；
- 新增任务查询、取消、事件历史和 Skill 清单的 gRPC/REST 契约；
- Gateway 的实时事件沿用 Core 持久化的 event ID、sequence 和 occurred_at；
- 前端按对话保存运行任务，切换对话不再共享一个全局发送锁；
- 输入框运行时显示明确的停止操作；
- Core 启动时不盲目续跑无检查点任务，而标记 `interrupted`；
- 本地声明式 Skill 与 MCP 一同进入实际扩展清单；
- 产品愿景和路线图从编码/垂直示例收敛到通用 Agent 内核。

## Phase 1 发布阻塞项

以下问题完成前，不把 Phase 1 宣称为稳定发布：

1. **重连无缝性**：客户端已在 WebSocket 建立后按 sequence 再补拉并去重，普通连接窗口不会丢事件；但单次补拉上限为 1000，仍需分页游标和服务端原子 `after_sequence` 握手。
2. **浏览器生产隔离**：当前页面按任务会话隔离，但 Chromium 仍在 Agent Core 进程内；需要资源上限、超时回收和下载/上传策略。
3. **取消一致性**：模型流和 Tool 边界会检查取消，但无法强制中断所有第三方 MCP 调用；MCP Tool 需要取消/超时契约。
4. **恢复级别**：当前恢复的是“真实状态”，不是任意步骤自动续跑。自动续跑必须先引入幂等步骤和安全检查点。
5. **端到端验证**：浏览器 Runtime 已使用系统 Chrome 完成公网站点冒烟，但仍需完成 Gateway + Core + WebSocket + Chrome 的整链路 E2E。

## Phase 2 候选目标

- 原子事件续传与安全检查点；
- 浏览器隔离、任务队列、超时/重试/配额；
- 模型能力路由与 fallback；
- Skill 热重载和 MCP 健康管理；
- 用户可控 Memory v1；
- 经验证的第一批领域工作流。

Memory、Embedding、Image 模型和数据管理页面可以提前注册，但未有完整 API 与执行语义时必须标记为规划状态，不能计入完成度。

## 验收命令

```bash
bash scripts/run_tests.sh
bash scripts/build.sh all
```

额外人工冒烟：

1. 配置一个 OpenAI-compatible 或本地模型；
2. 发起包含 browser open/snapshot/click 的任务并验证批准；
3. 切换对话后返回，检查任务历史和活动恢复；
4. 取消运行任务并确认待审批同步关闭；
5. 新增本地 Skill、配置 stdio MCP，重启后检查扩展清单与实际调用。
