# NanamiGopher 配置指南

> **状态**：Current
> **最后核验**：2026-09-18

配置字段最终以仓库配置 Schema 和默认配置为准。本文解释用户可见的配置，不复制内部结构体。

## 1. 配置层级

优先级从低到高：

```text
内置默认值 → 配置文件 → 部署环境覆盖 → Workspace 设置 → 当前会话设置
```

Secret 不写入普通配置；配置只保存 Credential Reference。

## 2. 界面称呼

打开“设置 → 通用”，可修改对话标题栏、欢迎页和输入框中显示的助手称呼。称呼长度为 1–32 个字符，按 Workspace 中的当前用户保存；不会改变项目名、Workspace 名或模型身份。

## 3. 模型

Phase 1 支持在一个 Workspace 中保存多个 Chat 模型配置，并选择一个默认模型。打开“设置 → 模型”，默认只显示已配置的服务行、凭证状态和默认标记；点击配置行进入编辑，或点“添加模型”选择新服务。同一时间只会打开一个编辑器。

- `OpenAI`：官方 API，或带鉴权的 OpenAI-compatible 云服务；自定义服务可填写 API Base URL。
- `Anthropic`：Claude 官方 API，可选自定义 API Base URL。
- `OpenAI Compatible`：本地 LM Studio、vLLM 或兼容服务；若服务端启用 Bearer 鉴权，可选填写独立 API Key。
- `Ollama`：Ollama 原生接口。

常用本地配置：

| 服务 | API Base URL | 模型名称示例 |
|---|---|---|
| Ollama | `http://127.0.0.1:11434` | `qwen2.5` |
| LM Studio | `http://127.0.0.1:1234/v1` | 以 LM Studio 已加载模型 ID 为准 |
| vLLM | `http://127.0.0.1:8000/v1` | 以 vLLM 的 `--served-model-name` 为准 |

选择服务后先填写 API Key 和模型；接口类型、服务预设与 Base URL 位于“自定义设置”。点“从服务获取”会使用当前尚未保存的表单值读取服务端模型目录，目录支持按名称或 ID 搜索，选择并确认后才会写入当前草稿，不会自动保存。目录不可用时仍可手工输入准确的模型 ID。再点“测试连接”，成功后保存配置。Temperature、输出 Token 和超时由运行时采用稳定默认值，不在常规设置页中要求用户调节。

非敏感设置写入 Workspace 数据库；API Key 按模型配置 ID 隔离保存在系统密钥链，不写入 YAML、数据库或 API 响应。Provider 或 Base URL 变化后必须提供新 Key，旧凭证不会发送到新端点。本地 Provider 不会继承云端 API Key，也不会通过系统 HTTP 代理访问回环端口。

默认模型用于新对话。聊天输入框可以为当前会话选择其他已保存模型，并选择 `快速`、`均衡` 或 `深度` 输出档；该选择持久化到会话，不会改变 Workspace 默认模型。

无桌面的服务器环境可以使用 `NANAMI_MODEL_PROVIDER`、`NANAMI_MODEL_NAME`、`NANAMI_MODEL_BASE_URL` 以及 Provider 对应的 `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`。Workspace 中已保存的设置优先于 YAML 和这些模型设置环境变量。

Phase 1 的自动发现仅查询模型目录。多模型自动路由、能力/成本判断和自动 fallback 属于 Phase 2。

模型列表和路由规则见 [Model Routing](../agent-capabilities/models/model-routing.md)。

## 4. 联网工具

打开“设置 → 联网工具”可以为 Web 搜索配置可选服务。系统未配置凭证时使用无需密钥的 DuckDuckGo；保存 Tavily 后优先使用 Tavily，保存 Google Programmable Search 时需要同时填写 API Key 和搜索引擎 ID（CX）。Secret 保存在操作系统密钥链，只将引用状态返回界面；Gateway 在任务开始前把当前 Workspace 的凭证同步到 Agent Core 内存，不写入会话、ToolResult 或普通配置。

搜索服务请求失败时，活动流将工具标记为失败并显示检查网络或打开联网工具设置的提示；详细参数和原始结果仍收在二级详情中，模型可以根据失败结果继续给出说明。

## 5. Workspace 与运行状态

打开“设置 → 工作区”可以查看当前进程实际使用的 Workspace 根目录、配置来源、Gateway/Agent Core 状态和版本。该页面是只读状态投影，不允许浏览器直接修改本地路径或进程启动参数。

模型、联网凭证、权限模式和界面称呼通过当前 API 即时生效。Workspace 根目录、MCP Server 启动配置及 Gateway/Agent Core 端口由启动配置或环境变量提供，修改后需要重启。页面不会假装检测运行期间手工修改的外部 YAML。

### 5.1 存储边界

- Personal 与 Team Workspace 使用同一配置模型。
- 本地部署默认使用 SQLite 和本地内容存储。
- 当前服务器部署仍使用 SQLite；PostgreSQL、对象存储和独立向量服务属于 Planned。
- 向量索引可重建；修改 Embedding 或 chunk 版本后需触发索引重建。

存储语义见 [Database](../design/Database.md)。

## 6. 权限模式

权限运行时提供三个面向用户的档位：

- `只读（read_only）`：读取与搜索自动执行；编辑、命令和联网操作询问。
- `工作区（workspace，推荐）`：当前 Workspace 内的读取、编辑和安全命令自动执行；联网与高风险命令询问。
- `完全访问（full_access）`：在应用允许的范围内自动执行普通工具与联网操作；重大影响操作仍询问。

Hard-deny 规则任何模式都不能覆盖。完整矩阵见 [Tool Permission](../agent-capabilities/security/tool-permission.md)。

Phase 1 的设置页只修改新对话默认档位，聊天输入框可覆盖当前对话档位。需要确认时，审批卡片展示规范化参数、资源范围、风险等级和有效期；决定只对保存的这一次 ToolCall 生效。L1–L5 是服务端内部风险模型，不再要求用户逐工具配置。

部署者还可在 YAML 中配置额外白名单。空数组表示该维度不额外收紧；非空时，工具名、Bash 命令前缀和资源路径必须同时满足白名单。相对路径以 Workspace 根目录为基准，白名单只能缩小 ToolPolicy 的权限，不能绕过 Workspace 边界、审批或 hard-deny：

```yaml
permissions:
  allowlist:
    tools: [file_read, glob, grep, bash]
    command_prefixes: ["git status", "git diff"]
    paths: ["docs", "src"]
```

## 7. Workspace 文件与 Diff

右侧栏的“文件”页按需读取当前 Workspace，可选择文本文件进行只读预览；“变更”页展示 Git staged、unstaged 与 untracked 文件，并在选中文件后加载逐文件 Diff。配置 `NANAMI_WORKSPACE_ROOT` 可显式指定本地运行时根目录。服务端拒绝绝对路径、目录穿越与逃逸根目录的符号链接。

### 7.1 浏览器运行时

Browser Tool 默认按需启动，不需要为每次任务预先打开窗口。部署配置示例：

```yaml
browser:
  enabled: true
  headless: true
  executable_path: "/usr/bin/google-chrome"  # 留空时使用 Playwright 管理的 Chromium
```

Browser Tool 在应用层只接受公开 HTTP(S) 地址，并解析主机以拒绝私网、本机、链路本地和保留地址；截图路径必须位于 Workspace，`fill/click/press` 等页面副作用仍受当前会话权限与审批控制。该检查不是生产网络边界的替代品：部署时还应通过容器或主机出口策略阻止 Chromium 访问内网，以覆盖 DNS 重绑定等应用层无法彻底消除的风险。

## 8. Skill 与 MCP

Phase 1 会从 `skills.scan_directories` 扫描本地 `SKILL.md`。最小文件示例：

```markdown
---
name: research-brief
version: 1.0.0
kind: instruction
description: 生成带来源的研究简报。
---
优先读取一手来源，区分事实与推断，并记录引用。
```

本地 Skill 只提供可审阅指令，通过 `skill list/read` Tool 使用，不执行目录中的代码。应用内“MCP 与 Skill”页会只读展示实际加载结果；新增文件后需要重启 Agent Core。

目标 SkillGrant 配置包含：

- 启用状态和版本。
- Workspace 级能力授权。
- 文件、网络和凭证范围。
- 非敏感用户设置。
- 超时和资源限制。

`import` 用于本地包，`install` 用于受支持的注册源。当前 MCP transport 只承诺 stdio。SKILL.md 格式见 [Skill Lifecycle](../agent-capabilities/skills/skill-lifecycle.md)。

Phase 1 可由部署者在 YAML 中显式配置受信 stdio Server；Agent Core 启动时完成握手和工具注册，关闭时终止子进程。普通用户界面暂不提供任意命令编辑入口：

```yaml
mcp:
  servers:
    local_tools:
      enabled: true
      command: "python3"
      args: ["-m", "my_mcp_server", "--workspace", "{workspace}"]
      cwd: "{workspace}"
      env_allowlist: ["MY_MCP_TOKEN"]
```

`command` 以 argv 方式直接执行，不经过 shell；`cwd` 必须位于 Workspace。`env_allowlist` 只声明可从启动环境传入的变量名，Secret 值不得写入 YAML。工具会命名为 `<server>__<tool>`，并与 Native Tool 经过同一 ToolPolicy、审批和审计入口。SkillGrant、健康重启、空闲回收和非 stdio transport 属于后续阶段。

“MCP 与 Skill”页面当前只读展示实际加载的 Local Skill、Server、transport、状态和工具名称。它不会修改 YAML，也不代表 Skill import/install 已经实现。

## 9. 凭证

- 桌面模式使用操作系统密钥存储。
- 服务器模式使用 Vault/KMS/Secret Manager。
- 加密文件仅作为显式 fallback。
- UI 和 API 只显示凭证引用及元数据，不回显 Secret。

## 10. Memory（Phase 2）

“用户记忆”页面已经支持当前用户在 Workspace 内手动添加、查询、修改和遗忘长期信息，数据由 Agent Core 持久化，写操作进入审计日志。自动从对话提取记忆、语义检索和注入模型上下文尚未启用。

“Embedding 与索引”入口已提前注册，但目前是只读状态页，没有可保存的 Provider 控件。保留期、自动抽取、Embedding Provider 和索引重建需要等对应 API、版本化索引、删除闭环和测试完成后再开放。

Phase 2 配置不得改变以下不变量：

- Secret 不进入 Memory。
- Workspace 之间默认隔离。
- 用户可查看、修改、导出和遗忘 User Memory。
- 原始消息/文档删除后派生索引必须清理。

详见 [Memory](../agent-capabilities/memory/memory-system.md)。

## 11. 生效范围

- 新会话设置通常不改变已经运行的 Task。
- 权限缩减和凭证撤销应立即阻止新的 ToolCall。
- 需要重启进程或重建索引的配置必须在 UI/CLI 中明确提示。
- 无法识别的配置字段应报错或告警，不静默忽略。
