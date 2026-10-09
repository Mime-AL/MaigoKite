# 运行时临时迁移开关

> 本页只负责启用方式、未验收风险和删除条件。运行机制唯一来源为 [智能体运行时设计](../design/AgentRuntime.md)。

## 1. 默认与范围

`legacy` 是默认，保持旧 AgentCore 可用。`langgraph` 显式启用普通聊天的 create_agent/LangGraph 路径，已适配文件读写编辑、ripgrep 搜索、exec_command、联网、浏览器、技能和已配置 MCP 工具；todo_write/sleep 可选择启用。显式 `/tool` 仍走旧路径。普通聊天不按工具静默回退到旧循环。

通过当前 YAML 配置：

```yaml
agent:
  runtime: langgraph
  # 可选，省略则按 storage.sqlite_path 生成独立 checkpoint 文件
  langgraph_checkpoint_path: ~/.nanamigopher/data/agent.langgraph.db
```

或启动核心服务前设置 `NANAMI_AGENT_RUNTIME=langgraph`。该迁移开关 是迁移脚手架，不是长期产品选项。

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

- MCP 此次只迁工具接线和可见性，现有 stdio 协议客户端尚未替换为官方 SDK。
  本地取消等待不证明远端副作用已停止；下一轮应替换客户端，而非扩写自制 JSON-RPC。
- 命令与 ripgrep 取消时终止进程组并等待退出。浏览器取消时关闭对应页面 浏览器上下文，
  不关闭其他会话；页面状态仍不能跨核心服务重启恢复。
- 文件工具仍有同步 I/O，不能中途抢占；DuckDuckGo 同步库在线程中执行，取消等待不
  能杀死线程。本轮不新增线程终止框架。
- 只有 file_write 沿用有限的同内容状态核对。`file_edit`、命令、浏览器、MCP
  不具有通用恰好一次（exactly-once）或安全重放保证，不能据此宣布恢复迁移完成。
- MCP 服务启动参数与技能来源继续由 YAML 配置后重启；新增工具开关不等于交付
  MCP 服务安装/编辑或技能安装管理。
