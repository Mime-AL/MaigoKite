# 模型接入与路由

> **状态**：Phase 1 Current + Phase 2 Planned
>
> **权威范围**：模型配置所有权、显式选择、未来路由与降级边界
>
> **最后核验**：2026-09-18

具体模型名、Base URL、上下文长度、价格和速度不是架构常量。它们来自用户配置、Provider 目录或运行时观测，不能固化为 Agent 内置模型表。

## 1. 阶段边界

| 能力 | Phase 1 | Phase 2 |
|---|---|---|
| 多个 Chat 配置与一个默认配置 | Current | 延续 |
| 会话显式选择 Chat 配置 | Current | 延续 |
| `fast / balanced / thorough` 输出预算 | Current | 延续 |
| 使用草稿 Base URL 手动获取模型目录 | Current | 延续并增强 |
| 后台自动发现与能力探测 | 不支持 | Planned |
| 自动路由、fallback、成本/延迟决策 | 不支持 | Planned |
| Embedding Provider 与向量索引设置 | 不支持 | Planned |
| Image 模型接入与设置 | 不支持 | Planned |

### 1.1 Phase 1 当前实现

- 每个 Workspace 最多保存 32 个 Chat 模型配置，并指定一个默认配置。
- 支持 OpenAI、Anthropic、Ollama 和 OpenAI-compatible 协议；LM Studio、vLLM 等属于协议预设，不是硬编码模型。
- 配置保存显示名称、Provider、服务端模型 ID 和 Base URL。生成参数由运行时使用稳定默认值，普通设置页不要求用户维护服务端能力参数。
- 用户可以用尚未保存的表单值主动读取 Provider 模型目录；这不是后台自动发现，也不推断模型能力、价格或质量。
- API Key 按模型配置 ID 存入 CredentialStore，只把“是否已配置”返回前端；Secret 仅在调用前同步到 Agent Core 内存。
- 新会话继承 Workspace 默认模型，当前会话可以显式覆盖。单个任务固定使用会话选定模型。

## 2. Phase 2 目标：ModelRegistry

本节是目标结构，不是当前 YAML Schema、数据库 Schema 或已交付设置页面。

### 2.1 概念结构

```yaml
models:
  registry:
    <profile_id>:
      kind: chat                 # chat / embedding / image
      provider: <adapter_id>
      model: <provider_model_id>
      endpoint: <user_or_deployment_value>
      credential_ref: <secret_reference>
      capabilities: {}           # Provider 探测或管理员声明，可为空
      metadata_source: provider  # provider / operator / observed

  routing:
    chat:
      default_profile_id: <profile_id>
      fallback_profile_ids: []
    embedding:
      default_profile_id: null
      fallback_profile_ids: []
    image:
      default_profile_id: null
      fallback_profile_ids: []
```

占位符表示运行时数据，不代表内置模型。Registry 只保存选择所需的稳定引用；Provider 请求格式仍由 Adapter 负责。

### 2.2 配置所有权

| 数据 | 权威来源 | 是否允许硬编码到 Agent |
|---|---|---|
| Provider、模型 ID、Base URL、默认模型 | 用户或部署配置 | 否 |
| API Key、Token | CredentialStore | 否 |
| 上下文窗口、输入类型、Tool Calling 等能力 | Provider 探测或管理员声明 | 仅协议级默认值 |
| Temperature、输出上限、超时 | 运行时策略与 Provider 约束 | 不作为模型目录事实 |
| 价格 | Provider 账单/可更新的价格元数据 | 否 |
| 延迟、成功率、限流情况 | Telemetry 观测 | 否 |
| 路由权重、预算和数据驻留约束 | Workspace Policy | 否 |

能力元数据必须带来源和更新时间。未知能力保持 `unknown`，不能根据模型名称字符串猜测。

## 3. Phase 2 目标：路由决策

```text
任务请求
→ 读取会话显式选择
→ 若存在显式选择，验证可用性并使用
→ 否则读取 Workspace 默认配置
→ 按任务所需能力过滤候选
→ 应用数据驻留、预算和权限约束
→ 使用可观测数据排序
→ 选定单个配置并记录决策依据
```

约束：

- 用户显式选择优先，除非配置已删除、凭证失效或违反强制策略。
- 自动路由只在 Phase 2 开启，Phase 1 不根据语言、模型名称或 Prompt 长度静默换模型。
- 路由结果绑定到任务；任务执行中不因普通延迟随意更换模型。
- 路由日志只保存配置引用和决策元数据，不保存 Secret 或完整 Prompt。

## 4. Phase 2 目标：失败与降级

可降级错误包括连接超时、限流和 Provider 5xx；认证失败、无权限、数据驻留冲突及请求校验失败默认不跨 Provider 重试。

```text
主配置调用失败
→ 错误分类
→ 判断请求是否安全重试
→ 验证 fallback 的能力、权限和数据边界
→ 切换并通知用户
→ 记录原配置、替代配置和原因
```

- fallback 列表保存配置 ID，不保存厂商或模型常量。
- 带副作用工具调用的续接必须复用已持久化 ToolCall 状态，不能重新执行已完成副作用。
- 降级导致能力、费用或数据位置变化时必须向用户显示。
- 重试次数、退避和超时由运行时策略控制，不写入模型目录条目。

## 5. Phase 2 目标：Embedding 与 Image

Embedding 和 Image 使用与 Chat 相同的 Registry 标识、Credential Reference 和 Workspace 隔离，但拥有独立 Adapter；不能因为三个类型都叫“模型”就复用请求结构。

Embedding 设置启用前必须同时具备：

- Provider Adapter 和连接验证。
- 维度、最大输入和批处理能力探测。
- 索引版本与重建流程。
- Secret 隔离及费用/资源提示。
- 对应 API、持久化 Schema 和测试。

Image 设置启用前必须同时具备：

- Provider Adapter、输出类型和尺寸能力探测。
- 生成内容的存储、清理和审计边界。
- 对应 API、持久化 Schema 和测试。

以上闭环未完成前，前端不得展示可保存的 Embedding/Image 设置表单。

## 6. API 与界面边界

Phase 1 设置页只消费已经存在的 Chat 模型 API；Provider 预设只填充协议类型和常见 Base URL，不承诺具体模型可用。

Phase 2 增加 Registry、能力探测、路由策略或 Embedding/Image 页面时，必须同步交付：

1. Gateway REST 契约。
2. Agent Core 领域接口和持久化。
3. Credential Reference 流程。
4. 前端加载、保存、错误和空状态。
5. 单元、集成和端到端测试。
6. Current/Planned 文档更新。

允许提前注册明确标注状态的只读页面；在完整闭环完成前，不允许加入可保存的空设置、静态模型清单或只能修改前端内存的控件。

## 7. 验收清单

### Phase 1

- [x] Chat 配置、默认配置和会话覆盖使用同一配置 ID。
- [x] 模型目录由用户主动从实际服务读取，不维护内置模型清单。
- [x] Secret 不进入普通配置、事件或数据库。
- [x] Provider/Base URL 变化时不复用旧凭证。
- [x] 未声称已经支持自动路由、fallback、Embedding 或 Image 设置。

### Phase 2

- [ ] ModelRegistry 的能力元数据包含来源与更新时间。
- [ ] 路由仅使用满足能力和强制策略的候选配置。
- [ ] fallback 对用户可见并保持工具副作用幂等。
- [ ] 成本和延迟来自可更新数据源或观测，不写死在代码中。
- [ ] Embedding/Image 在完整后端契约交付后再启用可保存的设置表单。
