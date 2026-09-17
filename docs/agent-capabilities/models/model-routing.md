# 模型路由策略

> 状态：Current
> NanamiGopher Agent 的模型选择、路由与成本优化规范；具体模型和地址属于部署配置，不是架构常量。本文明确区分 Phase 1 已实现子集与 Phase 2 目标，避免把目标架构误写成当前能力。

---

## 1. 概述

NanamiGopher 的目标架构采用多模型路由，根据任务类型、复杂度和成本约束选择模型；完整 ModelRegistry、fallback 与成本路由属于 Phase 2。

### 1.1 Phase 1 当前实现

- 每个 Workspace 可保存最多 32 个 Chat 模型配置并指定一个默认模型；新会话继承默认值，现有会话可显式选择其他配置。
- 支持 OpenAI、Anthropic、Ollama 和 OpenAI-compatible（LM Studio、vLLM 等）接口。
- 非敏感配置集合保存在 `workspace_settings`；API Key 按模型配置 ID 隔离保存在 CredentialStore，并只同步到 Agent Core 内存。
- 支持在保存前执行一次最小模型调用验证连接。
- 聊天输入框支持会话级模型覆盖和 `fast / balanced / thorough` 输出预算；不支持多模型自动路由、自动 fallback、模型发现以及 Embedding/Image 的 UI 接入。

以下 ModelRegistry、路由、降级和成本章节描述 Phase 2 目标设计，不能作为 Phase 1 已交付声明。

---

## 2. ModelRegistry 配置结构

### 2.1 配置层次

```yaml
models:
  # 默认模型配置
  defaults:
    chat: "qwen2.5"
    embedding: "bge"
    image: null

  # 备用模型（主模型失败时降级）
  fallbacks:
    chat:
      primary: "qwen2.5"
      secondary: "gpt-4o"
      tertiary: "claude"
    embedding:
      primary: "bge"
      secondary: "openai"
      tertiary: "gte"

  # Chat 模型详细配置
  chat:
    qwen2.5:
      provider: "vllm"
      endpoint: "http://localhost:8000/v1/chat/completions"
      model_name: "Qwen/Qwen2.5-7B-Instruct"
      max_tokens: 4096
      temperature: 0.7
      timeout: 30
      cost_per_token: 0.0000001
      speed_tier: "fast"          # fast / medium / slow
      quality_tier: "standard"    # standard / high / highest

    gpt-4o:
      provider: "openai"
      endpoint: "https://api.openai.com/v1/chat/completions"
      model_name: "gpt-4o"
      max_tokens: 8192
      temperature: 0.7
      timeout: 60
      cost_per_token: 0.000025
      speed_tier: "medium"
      quality_tier: "high"

    claude:
      provider: "anthropic"
      endpoint: "https://api.anthropic.com/v1/messages"
      model_name: "claude-3-sonnet-20240229"
      max_tokens: 8192
      temperature: 0.7
      timeout: 60
      cost_per_token: 0.000003
      speed_tier: "medium"
      quality_tier: "high"

    llama:
      provider: "vllm"
      endpoint: "http://localhost:8001/v1/chat/completions"
      model_name: "meta-llama/Llama-3-8B-Instruct"
      max_tokens: 4096
      temperature: 0.7
      timeout: 30
      cost_per_token: 0.0
      speed_tier: "fast"
      quality_tier: "standard"

  # Embedding 模型详细配置
  embedding:
    bge:
      provider: "local"
      model_name: "BAAI/bge-m3"
      dimension: 1024
      max_length: 8192
      cost_per_token: 0.0
      deployment: "cpu"

    openai:
      provider: "openai"
      model_name: "text-embedding-3-large"
      dimension: 3072
      max_length: 8191
      cost_per_token: 0.00000013
      deployment: "api"

    gte:
      provider: "aliyun"
      model_name: "text-embedding-v2"
      dimension: 1024
      max_length: 2048
      cost_per_token: 0.00000007
      deployment: "api"

  # Image 模型（可选）
  image:
    flux:
      provider: "local"
      model_name: "black-forest-labs/FLUX.1-dev"
      max_resolution: "1536x1536"
      cost_per_image: 0.0
    dall_e:
      provider: "openai"
      model_name: "dall-e-3"
      max_resolution: "1024x1024"
      cost_per_image: 0.04
```

### 2.2 模型能力标签

每个模型附带能力标签，用于路由决策：

| 标签 | 说明 |
|------|------|
| `reasoning` | 擅长逻辑推理 |
| `coding` | 擅长代码生成 |
| `creative` | 擅长创意写作 |
| `multilingual` | 多语言支持 |
| `fast` | 响应速度快 |
| `cheap` | 成本低 |
| `local` | 可本地部署 |

---

## 3. ModelProviderFactory 创建流程

### 3.1 工厂类设计

```python
class ModelProviderFactory:
    """模型提供商工厂，负责创建和管理模型实例。"""

    _registry: Dict[str, Type[IModelProvider]] = {}

    @classmethod
    def register(cls, provider_name: str, provider_class: Type[IModelProvider]):
        """注册新的模型提供商。"""
        cls._registry[provider_name.lower()] = provider_class

    @classmethod
    def create(cls, provider_name: str, config: Dict[str, Any]) -> IModelProvider:
        """根据 provider_name 创建模型实例。"""
        provider_class = cls._registry.get(provider_name.lower())
        if not provider_class:
            raise UnknownProviderError(f"Provider '{provider_name}' not registered")
        return provider_class(config=config)

    @classmethod
    def create_from_registry(cls, model_key: str, registry: ModelRegistry) -> IModelProvider:
        """从 ModelRegistry 配置创建模型实例。"""
        model_config = registry.get_model(model_key)
        return cls.create(model_config.provider, model_config.to_dict())
```

### 3.2 提供商注册

| 提供商 | 注册名称 | 支持模型 |
|--------|----------|----------|
| vLLM | `vllm` | 本地部署的 HuggingFace 模型 |
| OpenAI | `openai` | GPT-4o、text-embedding-3、DALL-E |
| Anthropic | `anthropic` | Claude 系列 |
| Alibaba | `aliyun` | GTE Embedding |
| Local | `local` | 本地 CPU/GPU 推理 |

### 3.3 创建时序

```
用户请求 / 系统调度
  │
  ├─ 确定模型类型（chat / embedding / image）
  │
  ├─ 查找 ModelRegistry 获取配置
  │   ├─ 使用默认模型
  │   └─ 或根据路由策略选择
  │
  ├─ ModelProviderFactory.create()
  │   ├─ 根据 provider 类型选择对应工厂
  │   ├─ 传入配置参数
  │   └─ 返回 IModelProvider 实例
  │
  ├─ 缓存实例（避免重复创建）
  │
  └─ 返回模型实例供调用
```

---

## 4. 路由策略

### 4.1 任务复杂度评估

系统根据任务特征自动选择模型：

```python
def route_task(task: Task, context: dict = None) -> str:
    """根据任务特征选择最优模型。"""

    # 复杂度由 5 维度加权评分得出，仅三级：simple / standard / complex
    complexity = assess_complexity(task.content, context or {})
    language = detect_language(task.content)

    if complexity == "simple":
        # 简单任务 → 快速低成本模型
        if (context or {}).get("budget") == "minimal":
            return "llama"       # 本地模型，零成本
        return "qwen2.5"         # 平衡型模型

    elif complexity == "standard":
        # 中等任务 → 标准模型；语言类型仅在此处影响选择
        if language == "zh":
            return "qwen2.5"     # 中文优化
        return "gpt-4o"          # 通用能力强

    else:  # complex
        # 复杂任务 → 强模型
        if task.requires_reasoning:
            return "claude"      # 推理能力强
        return "gpt-4o"          # 综合能力最强
```

### 4.2 复杂度评估维度

| 维度 | 权重 | 说明 | 实现阶段 |
|------|------|------|----------|
| 指令长度 | 20% | Token 数量越多越复杂 | Phase 2 目标 |
| 工具调用数 | 25% | 需要调用的工具数量（来源：`context["tool_hints"]`） | Phase 2 目标 |
| 推理深度 | 30% | 是否需要多步推理 | Phase 2 目标 |
| 语言类型 | —（不参与评分） | 中文任务偏好 qwen2.5，仅影响模型选择 | Phase 2 目标 |
| 预算约束 | 10% | 用户设定的成本上限 | Phase 2 目标 |

> **实现边界**：Phase 1 不运行本节算法，只使用默认模型或用户为会话显式选择的模型。复杂度评估、语言偏好、预算路由和 fallback 均为 Phase 2 目标。

### 4.3 路由决策表

| 任务类型 | 复杂度 | 首选模型 | 备选模型 |
|----------|--------|----------|----------|
| 文件读取 | simple | llama | qwen2.5 |
| 代码生成 | complex | gpt-4o | claude |
| 网页搜索 | simple | qwen2.5 | llama |
| 知识检索 | standard | qwen2.5 | gpt-4o |
| 多步规划 | complex | claude | gpt-4o |
| 总结摘要 | simple | llama | qwen2.5 |
| 创意写作 | standard | gpt-4o | claude |
| 数据分析 | complex | claude | gpt-4o |

---

## 5. 降级策略

### 5.1 降级决策树

```
主模型调用
  │
  ├─ 成功 → 返回结果
  │
  ├─ API 超时 (>timeout)
  │   ├─ 有备用模型 → 切换到备用模型
  │   └─ 无备用 → 返回超时错误
  │
  ├─ 速率限制 (429)
  │   ├─ 等待重试（指数退避）
  │   └─ 仍失败 → 切换到备用模型
  │
  ├─ 认证失败 (401)
  │   ├─ 检查凭证是否过期
  │   ├─ 刷新凭证后重试
  │   └─ 仍失败 → 切换到备用模型
  │
  ├─ 模型返回错误响应
  │   ├─ 解析错误 → 修正请求格式后重试
  │   └─ 模型内部错误 → 切换到备用模型
  │
  └─ 成本超支
      ├─ 降级到更便宜的模型
      └─ 通知用户
```

### 5.2 降级规则

| 故障类型 | 动作 | 重试次数 | 超时时间 |
|----------|------|----------|----------|
| 连接超时 | 切换到下一个备用模型 | 1 | 原 timeout × 1.5 |
| 速率限制 | 指数退避重试 | 3 | 1s, 2s, 4s |
| 服务器错误 (5xx) | 切换到备用模型 | 2 | 原 timeout |
| 认证失败 | 刷新凭证后重试 | 1 | 原 timeout |
| 模型输出截断 | 追加续接请求 | 1 | 原 timeout |
| 成本超限 | 降级到低成本模型 | 0 | - |

### 5.3 本地模型优先策略

当满足以下条件时，优先使用本地模型：

1. 网络不可达（离线模式）
2. 任务复杂度为 simple 或 standard
3. 本地模型质量评分 >= 阈值（默认 0.7）
4. 用户明确偏好本地推理（隐私需求）

```python
def should_use_local_model(task: Task) -> bool:
    """判断是否应优先使用本地模型。"""
    if not network_available():
        return True
    if task.privacy_level == "high":
        return True
    if assess_complexity(task.content, {}) in ("simple", "standard"):
        local_quality = get_local_model_quality_score()
        return local_quality >= QUALITY_THRESHOLD
    return False
```

---

## 6. 成本优化

### 6.1 Token 统计

每个模型调用记录 Token 使用情况：

```python
@dataclass
class TokenUsage:
    model_name: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float
    timestamp: datetime
```

**统计维度**：
- 按模型分类统计
- 按任务/会话分组统计
- 按日/周/月聚合统计

### 6.2 成本计算公式

```
单次调用成本 = total_tokens × cost_per_token
日成本 = Σ(当日所有调用成本)
月成本 = Σ(当月所有调用成本)
```

### 6.3 模型选择建议

| 场景 | 推荐模型 | 理由 |
|------|----------|------|
| 日常对话 | qwen2.5 | 成本低、中文好 |
| 代码审查 | gpt-4o | 代码理解能力强 |
| 逻辑推理 | claude | 推理质量最高 |
| 离线场景 | llama | 无需网络、零成本 |
| 嵌入检索 | bge | 免费、中文效果好 |
| 图像生成 | flux (本地) | 免费、可控 |

### 6.4 成本限制配置

```yaml
cost_limits:
  daily_chat: 1.00          # 每日 Chat 模型费用上限
  monthly_embedding: 5.00   # 每月 Embedding 费用上限
  per_request_max_tokens: 8192  # 单次请求最大 Token 数
  fallback_on_limit_exceed: true  # 超限时自动降级
```

---

## 7. 支持模型列表

### 7.1 Chat 模型

| 模型 | 提供商 | 最大 Token | 速度 | 成本 | 语言能力 |
|------|--------|-----------|------|------|----------|
| qwen2.5 | Qwen / vLLM | 32K | 快 | 极低 | 中英双语优 |
| gpt-4o | OpenAI | 128K | 中 | 高 | 多语言优 |
| claude-3-sonnet | Anthropic | 200K | 中 | 中 | 多语言良 |
| llama-3-8b | Meta / vLLM | 8K | 快 | 免费 | 英语优 |
| gemini-pro | Google | 128K | 快 | 低 | 多语言良 |

### 7.2 Embedding 模型

| 模型 | 提供商 | 维度 | 最大长度 | 成本 | 部署方式 |
|------|--------|------|----------|------|----------|
| BGE-M3 | BAAI | 1024 | 8192 | 免费 | 本地 CPU/GPU |
| text-embedding-3-large | OpenAI | 3072 | 8191 | 低 | API |
| text-embedding-v2 | Alibaba | 1024 | 2048 | 极低 | API |

### 7.3 Image 模型（可选）

| 模型 | 提供商 | 最大分辨率 | 成本 | 部署方式 |
|------|--------|-----------|------|----------|
| FLUX.1-dev | Black Forest Labs | 1536x1536 | 免费 | 本地 GPU |
| DALL-E 3 | OpenAI | 1024x1024 | 中 | API |

---

## 附录：模型路由 Checklist

- [ ] ModelRegistry 是否配置了默认模型和备用模型？
- [ ] ModelProviderFactory 是否正确路由到对应提供商？
- [ ] 路由策略是否覆盖 simple / standard / complex 三级复杂度？
- [ ] 降级策略是否处理了超时、限流、认证失败等场景？
- [ ] 本地模型优先策略是否生效？
- [ ] Token 统计是否准确记录？
- [ ] 成本限制是否可配置？
- [ ] 所有支持的模型是否已在配置中声明？
