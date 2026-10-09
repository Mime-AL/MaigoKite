# NanamiGopher

本地优先、用户可控的个人通用智能体，为选定的个人工作流组合浏览器、文件和外部工具。不是团队平台，也不限定为编码助手。

## 当前能力与边界

- Go 网关 + Python 核心服务 + Vue/Electron；SQLite 保存产品数据。
- 多个模型配置、默认模型与会话选择，支持 OpenAI、Anthropic、Ollama 和 OpenAI-compatible。
- 工作区文件预览/Git 差异，受控内置/MCP 工具、Playwright 浏览器与本地声明式技能。
- 权限模式、逐次审批、任务活动和持久事件；停止/重启恢复能力有具体运行时和工具限制。
- 默认仍是 legacy；create_agent + LangGraph 已接文件、搜索、命令、联网、浏览器、技能和 MCP 工具，仍在临时迁移开关 后，尚未验收。

用户可修改界面助手称呼。记忆当前是显式管理，自动检索/注入、持久工作流/子智能体和手机远程访问尚未交付。完整桌面运行资源打包及 Docker 部署也未完成验收。

## 从源码运行

需要 Go、Python 3.11+、Node/npm，精确版本以模块清单为准。依赖安装与解释器说明见 [开发指南](docs/development/DevelopmentGuide.md)，避免 setup 脚本创建的环境与实际启动环境不一致。

文件查找和内容搜索需要 ripgrep（`rg`），缺失时工具会提示安装，不使用自写搜索降级。

安装后从根目录启动：

```bash
make dev
```

也可执行 `bash scripts/dev.sh`。默认开发入口为网关 `localhost:8080`、核心服务 gRPC `localhost:8081`、Vite `localhost:5173`；开发脚本 Vite 绑定所有网卡，不用于未经认证的远程服务。

Electron 开发入口在 `web/`：

```bash
npm run electron:dev
```

不要同时启动两份网关/核心服务。正式桌面安装包的构建/资源闭环见 [发布指南](docs/deployment/ReleaseGuide.md)，开发启动成功不等于普通用户安装即可运行。

## 首次使用

在“设置 → 模型”添加实际服务的基础地址/模型 ID，测试连接，保存并选择默认项；会话可选择模型、输出预算档和权限模式。预设只提供协议/地址，模型目录从真实服务读取，不保证所有模型都支持工具调用。

API 密钥按配置隔离存入 OS 凭证存储，响应不回显；本地模型提供方不借用云端 Key。联网搜索、MCP 与模型凭证分别配置。用户设置、生效与排障见 [配置指南](docs/user-guide/Configuration.md) 和 [安装指南](docs/user-guide/Installation.md)。

本地技能只提供按需读取的声明流程，不执行目录代码；受信可执行扩展通过 stdio MCP。格式见 [技能](docs/agent-capabilities/skills/skill-lifecycle.md)。手机 Web/PWA 首版设计见 [手机远程访问](docs/design/RemoteAccess.md)，当前不能直接公开本地端口使用。

“设置 → 工具”可启停助手可见的内置/已连接 MCP 工具，独立于权限审批；待办和短暂等待默认关闭。
新聊天路径通过 `NANAMI_AGENT_RUNTIME=langgraph` 显式启用，限制与删除旧路径的条件见
[运行时迁移说明](docs/development/RuntimeMigration.md)。上述新增接线尚未运行测试，不能据此判断已验收；本次文档中文化不改变该状态。

## 开发与文档

- [文档入口](docs/README.md)：按主题定位唯一权威来源。
- [系统设计](docs/design/SystemDesign.md)、[智能体运行时](docs/design/AgentRuntime.md)：实际边界与待迁移部分。
- [需求与验收](docs/requirements/RequirementList.md)、[交付路线与状态](docs/project/Roadmap.md)。
- [测试策略](docs/testing/TestPlan.md)：PROTOCOL 与 LIVE 区分，未运行不算通过。
- [日志与诊断](docs/ops-security/Observability.md)：当前控制台/审计/事件，不宣称 OTel/Langfuse 已接线。

聚合测试入口为 `make test`，构建入口为 `make build`；详细范围、限制和质量命令在开发/发布指南维护。协议源为 `proto/agent.proto`，后端 `gateway/`、核心服务 `python/`、客户端 `web/`；不另维护重复目录树。

根目录 `prd.md / project.md` 为历史材料，不作为当前产品范围。

## 许可证

MIT，见 [LICENSE](LICENSE)。
