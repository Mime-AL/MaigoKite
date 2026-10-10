# 运行时临时迁移开关

> 本页只负责启用方式、未验收风险和删除条件。运行机制唯一来源为 [智能体运行时设计](../design/AgentRuntime.md)。

## 1. 默认与范围

`legacy` 是默认，保持旧 AgentCore 可用。`langgraph` 显式启用聊天的 create_agent/LangGraph 路径，已适配文件读写编辑、ripgrep 搜索、exec_command、联网、浏览器、技能和已配置 MCP 工具；todo_write/sleep 可选择启用。显式 `/tool` 也走同一 HITL/ToolNode，不按命令或工具静默回退旧循环。

通过当前 YAML 配置：

```yaml
agent:
  runtime: langgraph
  # 可选，省略则按 storage.sqlite_path 生成独立 checkpoint 文件
  langgraph_checkpoint_path: ~/.maigokite/data/agent.langgraph.db
```

或启动核心服务前设置 `MAIGOKITE_AGENT_RUNTIME=langgraph`。该迁移开关 是迁移脚手架，不是长期产品选项。

## 2. 当前风险

最近多工具审批已改为完整批次原生 HITL + 逐项产品审批，全批决定齐备前不执行。原先“首项批准就写第一个文件”的测试预期已过时，后续须更新/验收同名参数、部分批准后重启与拒绝投影。旧版本丢失的调用不能补回。

执行恢复只读 LangGraph 检查点，安全审计读 Repository，UI 读产品投影，不读取 legacy continuation_json。`file_write` 有有限同内容状态核对，但执行恢复仍是至少执行一次（at-least-once），详见 AgentRuntime。

此前上下文版本的回归结果不覆盖最新工具调用修改；该批修改未运行测试/静态检查/构建或真实模型提供方验收。本次文档整理也不构成运行时验收或切默认授权。

## 3. 删除条件

1. 目标模型提供方真实服务矩阵和生产纵向语义验收满足迁移条件；
2. 跨进程审批恢复、取消、文件 crash/replay 与投影回归稳定；
3. 新路径设为默认并完成 legacy 对比与发布回归；
4. 删除旧主循环、legacy 工具调用/续接数据和无消费者的执行脚手架；
5. 同时删除 `agent.runtime` 迁移开关 和本临时文档，将稳定配置/行为留在权威设计。

不要边迁移边拆旧桥，也不得把新增模型协议、检查点或取消框架放回新适配层。

## 4. 工具迁移的未验收边界

这批实现复用公开 `BaseTool.to_langchain_tool()`、LangChain ToolRuntime/ToolNode 与既有
PermissionPolicy。设置/API 已接线，协议绑定已生成；未运行测试、静态检查、类型检查、项目构建
或真实模型提供方验收，不切默认。配置方法见 [配置指南](../user-guide/Configuration.md)。

- MCP stdio 已在第一批轻量化中替换为官方 SDK，工具产品接口和权限边界不变。
  legacy 与新 Runtime 均使用该客户端，因此两条路径的 MCP 行为都仍需验收；本地取消等待不证明远端副作用已停止。
- 命令与 ripgrep 取消时终止进程组并等待退出。浏览器取消时关闭对应页面 浏览器上下文，
  不关闭其他会话；页面状态仍不能跨核心服务重启恢复。
- 文件工具仍有同步 I/O，不能中途抢占；DuckDuckGo 同步库在线程中执行，取消等待不
  能杀死线程。本轮不新增线程终止框架。
- 只有 file_write 沿用有限的同内容状态核对。`file_edit`、命令、浏览器、MCP
  不具有通用恰好一次（exactly-once）或安全重放保证，不能据此宣布恢复迁移完成。
- MCP 服务启动参数与技能来源继续由 YAML 配置后重启；新增工具开关不等于交付
  MCP 服务安装/编辑或技能安装管理。

## 5. 第一批轻量化与后续删除地图（2026-10-10）

本批只清理未接线的重复骨架、统一依赖入口、替换 MCP 协议实现，不切默认 Runtime。工作流、子 Agent、HITL 和 Recovery 能力仍保留，现有实现与缺口见 AgentRuntime 第 7 节；没有把删除空文件记为功能完成。

| 对象 | 本批处理 | 后续条件 / 保留边界 |
| --- | --- | --- |
| Workflow/HITL、SubAgent、Recovery 五个空骨架 | DELETE：移除没有消费者、方法仅为 `...` 的占位文件 | 保留能力需求，采用 LangGraph/HITL/子图；不重建同名自研框架 |
| MCP JSON-RPC 与进程轮询 | ADAPT：改用官方 SDK，删除私有协议实现 | 保留 `start/stop/list_tools/call_tool`、命名空间、风险、配置校验和错误投影；取消及关闭仍待验收 |
| Python 安装清单 | DELETE：移除子项目 pyproject/requirements，根清单和锁文件为唯一来源 | setup/build 使用根项目；协议生成和测试依赖在 dev，向量适配器依赖仅为可选组 |
| `AgentCore._run_agent/_stream_model/_execute_tool_batch` 等旧执行分支 | KEEP NOW → DELETE | 新路径已解除显式 `/tool` 依赖；满足第 3 节门禁后删除，保留 Core 产品组合与 API 方法 |
| ExecutionEngine / TaskManager | KEEP NOW → DELETE | 旧入口和消费者迁出后删除；新运行时不得依赖它们管理执行状态 |
| ChatAdapter / IChatProvider / 自研流和 Tool Call 解析 | ADAPT → DELETE LEGACY PARTS | 原生模型创建、端点兼容和 HTTP 生命周期已移至 native_model；新模型路径和默认连接验证不再依赖旧包装，显式注入的旧 Provider 保持兼容，待 legacy 消费者迁出再删 |
| `continuation_json` 读写及恢复分支 | KEEP NOW → DELETE CODE | 先处理历史待审批任务；旧库字段不能随删代码直接破坏性删除 |
| PermissionPolicy、Repository、产品 EventBus/DTO、Workspace | KEEP | 属于产品权限、审计、数据隔离和投影；不得因框架替换而取消 |
| `runtime_spike` 兼容入口与验证样本 | KEEP | 仍有历史验证消费者，后续统一迁移引用，不以删测试掩盖兼容问题 |
| `agent.runtime` 开关 | KEEP NOW → DELETE | 切默认并完成回归后连同旧执行路径移除，不等未来 Workflow/SubAgent/手机功能全部实现 |

本批完成依赖锁文件解析和只读源码核对，没有安装环境、运行测试、Ruff/mypy、项目构建或真实模型/MCP 验收。不得据此标记 READY TO DEFAULT；后续验收需用户明确要求后执行。

## 6. 正确性修复与入口收敛（2026-10-10，未验收）

- 聊天/批准后的审批续接共用凭证准备，审批流保留持久事件身份，新路径先检查模型再消费批准；2026-10-10 起拒绝直接结束回合、关闭剩余待审批项，不准备凭证或调用模型（本批未运行验收）。
- UI 待发队列绑定当前任务，仅成功终态触发并核对服务端状态；失败、取消、断线后等待再次确认。快照载入期间缓冲事件，HTTP 202 不直接推断批准已完成。
- 复用工作区已补齐的桌面 IPC，renderer 类型直接从真实 preload 白名单派生；不将此计为安装包验收。
- 新路径 `/tool` 通过公开模型 middleware 和原生 HITL/ToolNode；不新增工具调度器。原生模型工厂为生产、legacy 与 Spike 共用，客户端仍由 Core 管理。
- 成功回合从上一任务的终止 checkpoint 继承保留消息与摘要，失败/中断和 legacy 导入边界见 AgentRuntime；没有切换历史 checkpoint ID 或新增双向状态同步。
- 本轮只修改源码/文档、格式化 Go 和做 diff/引用核对；未运行测试、lint、类型检查、构建或 Live 验收。默认不变，旧 Loop、TaskManager、continuation 代码及数据均保留；Workflow/SubAgent 不提前扩建。
