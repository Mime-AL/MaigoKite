# 记忆系统设计

> NanamiGopher Agent 的记忆系统架构与实现规范。

---

## 1. 总体架构

NanamiGopher 的记忆系统分为两个维度：

- **IMemorySystem**：短期记忆体系，管理对话上下文与用户画像
- **IKnowledgeBase**：长期知识体系，管理文档库与语义检索

```
┌─────────────────────────────────────────────┐
│              Agent Runtime                   │
├─────────────────────────────────────────────┤
│         IMemorySystem                        │
│  ┌──────────────┬──────────────┬──────────┐ │
│  │ ShortTerm    │ Conversation │ User     │ │
│  │ Memory       │ Memory       │ Memory   │ │
│  └──────────────┴──────────────┴──────────┘ │
│                                              │
│         IKnowledgeBase                       │
│  ┌──────────────┬──────────────┬──────────┐ │
│  │ DocumentStore│ Retriever    │ VectorStore│ │
│  └──────────────┴──────────────┴──────────┘ │
└─────────────────────────────────────────────┘
```

---

## 2. IMemorySystem 接口族

### 2.1 IShortTermMemory（对话历史记忆）

**职责**：保存当前对话的完整消息历史（含用户消息、Assistant 回复、工具调用记录），用于拼装发送给 LLM 的 context window。

```python
class IShortTermMemory(ABC):
    """短期记忆接口，管理当前对话的完整消息历史。"""

    @abstractmethod
    def append(self, entry: MemoryEntry) -> None:
        """追加一条记忆条目。"""

    @abstractmethod
    def query(self, context: str, top_k: int = 5) -> List[MemoryEntry]:
        """根据上下文检索最相关的记忆条目。"""

    @abstractmethod
    def clear(self) -> None:
        """清空所有短期记忆。"""

    @abstractmethod
    def size(self) -> int:
        """返回当前记忆条目数量。"""
```

**MemoryEntry 结构**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `timestamp` | datetime | 记录时间 |
| `source` | str | 来源（tool_call / user_input / system） |
| `content` | str | 记忆内容 |
| `embedding` | Optional[List[float]] | 可选的向量表示 |
| `priority` | int | 优先级（1-10） |

**容量策略**：
- 默认最大条目数：100
- 超过上限时按 priority 降序淘汰低优先级条目
- 支持 TTL（Time-To-Live），默认 30 分钟过期

### 2.2 IConversationMemory（当前对话上下文）

**职责**：保存历史会话的压缩摘要，用于跨会话内容回溯。当前对话完整历史由 IShortTermMemory 维护；本接口负责对超出 context window 的早期轮次进行摘要压缩并持久化。

```python
class IConversationMemory(ABC):
    """对话记忆接口，管理历史会话的压缩摘要（跨会话持久化）。"""

    @abstractmethod
    def add_turn(self, user_message: str, assistant_response: str,
                 tool_calls: List[ToolCall] = None) -> None:
        """添加一轮对话（用户提问 + 助手回复）。"""

    @abstractmethod
    def get_context_window(self) -> List[Message]:
        """获取当前上下文窗口内的所有消息。"""

    @abstractmethod
    def trim_to_max_tokens(self, max_tokens: int) -> None:
        """按 token 限制裁剪上下文窗口。"""

    @abstractmethod
    def summarize(self) -> str:
        """生成对话摘要，用于上下文压缩。"""
```

**滑动窗口策略**：
- 固定窗口大小：默认 4096 tokens
- 保留策略：最近 N 轮完整对话 + 早期对话的摘要
- 摘要生成：使用 LLM 对超出窗口的早期对话进行压缩

**上下文压缩示例**：

```
原始对话（8192 tokens）:
  T1: 用户询问文件内容 → Agent 读取并回复
  T2: 用户要求修改 → Agent 编辑文件并回复
  T3: 用户追问原因 → Agent 解释逻辑
  T4: 用户确认 → Agent 完成任务

压缩后（4096 tokens）:
  Summary: "用户请求读取并修改某配置文件，已完成编辑。"
  T3-T4: 完整保留（最近对话）
```

### 2.3 IUserMemory（用户画像记忆）

**职责**：持久化用户偏好、习惯和工作风格。

```python
class IUserMemory(ABC):
    """用户记忆接口，管理用户偏好和画像。"""

    @abstractmethod
    def set_preference(self, key: str, value: Any) -> None:
        """设置用户偏好。"""

    @abstractmethod
    def get_preference(self, key: str, default: Any = None) -> Any:
        """获取用户偏好。"""

    @abstractmethod
    def update_profile(self, profile_update: Dict[str, Any]) -> None:
        """更新用户画像信息。"""

    @abstractmethod
    def get_profile(self) -> Dict[str, Any]:
        """获取完整的用户画像。"""

    @abstractmethod
    def save(self) -> None:
        """持久化用户记忆到存储后端。"""

    @abstractmethod
    def load(self) -> None:
        """从存储后端加载用户记忆。"""
```

**用户画像字段**：

| 字段 | 类型 | 示例 |
|------|------|------|
| `language` | str | `"zh-CN"` |
| `coding_style` | str | `"PEP-8"`, `"Google Style"` |
| `preferred_tools` | List[str] | `["file_read", "bash"]` |
| `working_directory` | str | `"/home/user/project"` |
| `timezone` | str | `"Asia/Shanghai"` |
| `communication_style` | str | `"concise"`, `"detailed"` |

**持久化**：
- 存储位置：用户配置目录下的 `user_memory.json`
- 自动保存：每次偏好变更后立即持久化
- 加密存储：敏感信息（如 API Key）使用 AES-256 加密

---

## 3. IKnowledgeBase 接口族

### 3.1 IDocumentStore（文档存储）

**职责**：管理文档的入库、分块、元数据管理。

```python
class IDocumentStore(ABC):
    """文档存储接口，管理知识库中的文档。"""

    @abstractmethod
    def add_document(self, content: str, metadata: Dict[str, Any] = None) -> str:
        """添加文档并返回文档 ID。"""

    @abstractmethod
    def chunk_document(self, content: str, chunk_size: int = 512,
                       overlap: int = 50) -> List[DocumentChunk]:
        """将文档切分为适合检索的块。"""

    @abstractmethod
    def get_document(self, doc_id: str) -> Optional[Document]:
        """根据 ID 获取文档。"""

    @abstractmethod
    def list_documents(self, filters: Dict[str, Any] = None) -> List[Document]:
        """列出文档，支持元数据过滤。"""

    @abstractmethod
    def delete_document(self, doc_id: str) -> bool:
        """删除文档。"""
```

**文档分块策略**：

| 策略 | 适用场景 | 参数 |
|------|----------|------|
| 固定长度 | 通用文本 | `chunk_size=512`, `overlap=50` |
| 段落分割 | 技术文档 | 按空行分割 |
| 标题分割 | 结构化文档 | 按 Markdown 标题层级 |
| 语义分割 | 长篇文章 | 基于语义边界检测 |

**DocumentChunk 结构**：

```python
@dataclass
class DocumentChunk:
    id: str                    # 块唯一标识
    content: str               # 块文本内容
    metadata: Dict[str, Any]   # 元数据（来源、页码、标题等）
    embedding: List[float]     # 向量表示（由 Embedding Provider 生成）
    parent_doc_id: str         # 所属原文档 ID
    chunk_index: int           # 块序号
```

### 3.2 IRetriever（检索器）

**职责**：实现多级检索策略，从直接匹配到语义检索再到综合排序。

```python
class IRetriever(ABC):
    """检索器接口，实现多层次的知识检索。"""

    @abstractmethod
    def search(self, query: str, top_k: int = 10) -> List[RetrievalResult]:
        """执行检索，返回相关文档块。"""

    @abstractmethod
    def hybrid_search(self, query: str, top_k: int = 10) -> List[RetrievalResult]:
        """混合检索：关键词 + 语义向量。"""
```

**多级检索流程**：

```
查询输入
  │
  ├─ Level 1: 直接匹配（精确关键词）
  │   └─ BM25 / 倒排索引
  │       └─ 命中 → 高权重返回
  │
  ├─ Level 2: 语义检索（向量相似度）
  │   └─ Embedding → 向量数据库
  │       └─ Cosine Similarity / Inner Product
  │
  └─ Level 3: 综合排序
      └─ 融合 Level 1 + Level 2 结果
          └─ Reciprocal Rank Fusion (RRF)
              └─ 返回 top_k 最终结果
```

**降级机制**：

| 场景 | 降级策略 |
|------|----------|
| 向量数据库不可用 | 回退到纯关键词检索 |
| Embedding 服务超时 | 使用 TF-IDF 近似 |
| 检索结果为空 | 扩大检索范围，降低阈值 |
| 查询过长 | 自动截断至有效长度 |

**RetrievalResult 结构**：

```python
@dataclass
class RetrievalResult:
    chunk_id: str              # 匹配的文档块 ID
    content: str               # 匹配的内容片段
    score: float               # 相关性分数（0-1）
    metadata: Dict[str, Any]   # 文档元数据
    rank: int                  # 排名
```

### 3.3 IVectorStore（向量存储）

**职责**：管理文档块的向量表示及其索引。

```python
class IVectorStore(ABC):
    """向量存储接口。"""

    @abstractmethod
    def upsert(self, vectors: List[VectorEntry]) -> None:
        """插入或更新向量。"""

    @abstractmethod
    def query(self, query_vector: List[float], top_k: int) -> List[QueryResult]:
        """向量相似度查询。"""

    @abstractmethod
    def delete(self, ids: List[str]) -> None:
        """删除指定 ID 的向量。"""

    @abstractmethod
    def dimension(self) -> int:
        """返回向量维度。"""
```

**支持的向量存储后端**：

| 后端 | 适用场景 | 特点 |
|------|----------|------|
| ChromaDB | 本地开发 / 小规模 | 嵌入式、零配置 |
| Qdrant | 生产环境 / 大规模 | 高性能、分布式 |
| FAISS | 纯向量检索 | 极致速度、内存受限 |

---

## 4. Embedding Provider 工厂模式

### 4.1 接口定义

```python
class IEmbeddingProvider(ABC):
    """Embedding 模型提供商接口。"""

    @abstractmethod
    def embed(self, texts: List[str]) -> List[List[float]]:
        """将文本列表转换为向量。"""

    @abstractmethod
    def dimension(self) -> int:
        """返回向量维度。"""

    @abstractmethod
    def model_name(self) -> str:
        """返回模型名称。"""
```

### 4.2 工厂类

```python
class EmbeddingProviderFactory:
    """Embedding 提供商工厂。"""

    PROVIDERS = {
        "bge": BGEProvider,
        "openai": OpenAIProvider,
        "gte": GTEProvider,
    }

    @classmethod
    def create(cls, provider_name: str, config: Dict[str, Any] = None) -> IEmbeddingProvider:
        """根据 provider_name 创建对应的 Embedding 提供商。"""
        provider_class = cls.PROVIDERS.get(provider_name.lower())
        if provider_class is None:
            raise ValueError(f"Unknown embedding provider: {provider_name}")
        return provider_class(config=config)
```

### 4.3 各 Provider 实现

#### BGEProvider（BGE-M3）

- **模型**：BAAI/bge-m3
- **维度**：1024
- **适用场景**：多语言、中英文混合
- **部署方式**：本地 CPU / GPU
- **优势**：免费、离线可用、中文效果好

#### OpenAIProvider

- **模型**：text-embedding-3-large（256/1024/3072 维度可选）
- **维度**：可配置
- **适用场景**：高质量语义检索
- **部署方式**：OpenAI API
- **优势**：精度高、速度快

#### GTEProvider（GTE）

- **模型**：Alibaba-GTE / text-embedding-v2
- **维度**：1024
- **适用场景**：阿里云生态集成
- **部署方式**：阿里云 API / 本地部署
- **优势**：国内访问稳定、支持中文

---

## 5. 分层检索策略

### 5.1 检索决策树

```
收到检索请求
  │
  ├─ 查询是否为精确路径/文件名？
  │   ├─ 是 → 使用 glob/grep 直接匹配（Level 0）
  │   └─ 否 ↓
  │
  ├─ 是否有元数据过滤器？
  │   ├─ 是 → 先过滤文档集合，再在子集中检索
  │   └─ 否 ↓
  │
  ├─ 知识库规模 < 1000 条？
  │   ├─ 是 → 全量向量检索 + RRF 融合
  │   └─ 否 ↓
  │
  └─ 启用多级检索
      ├─ Level 1: BM25 关键词检索
      ├─ Level 2: 向量语义检索
      └─ Level 3: RRF 融合排序
```

### 5.2 检索参数配置

```yaml
retrieval:
  default_top_k: 10
  max_tokens_per_chunk: 512
  chunk_overlap: 50
  rrf_k: 60                    # RRF 融合参数 k
  similarity_threshold: 0.7    # 最低相似度阈值
  fallback_to_keyword: true    # 向量检索无结果时回退到关键词
```

---

## 6. 记忆清理和过期策略

### 6.1 短期记忆清理

| 触发条件 | 动作 | 频率 |
|----------|------|------|
| 条目数超过上限 | 删除最低 priority 的条目 | 实时 |
| TTL 过期 | 删除超过生存时间的条目 | 每 5 分钟 |
| 对话切换 | 清空上一轮对话的短期记忆 | 对话结束时 |

### 6.2 对话记忆清理

| 策略 | 说明 |
|------|------|
| Token 上限 | 达到 max_tokens 时触发摘要压缩 |
| 轮数上限 | 超过 max_turns 时裁剪最早的非摘要轮次 |
| 手动清除 | 用户显式请求时清空对话上下文 |

### 6.3 用户记忆清理

| 场景 | 动作 |
|------|------|
| 用户注销 | 删除全部用户记忆 |
| 偏好变更 | 更新对应字段，保留其他偏好 |
| 数据导出 | 提供用户记忆的导出接口 |

### 6.4 知识库清理

| 策略 | 说明 |
|------|------|
| 文档过期 | 基于 metadata 中的 expiry_date 字段自动清理 |
| 重复检测 | 插入前计算相似度，重复度 > 95% 则拒绝 |
| 低质量过滤 | 嵌入内容少于 50 字的块标记为低质量 |

---

## 7. 存储后端配置

### 7.1 本地模式（开发环境）

```yaml
memory:
  short_term:
    backend: "local"
    storage_path: "~/.nanamigopher/memory/short_term"
    max_entries: 100
    ttl_seconds: 1800
  conversation:
    backend: "local"
    max_tokens: 4096
    max_turns: 20
  user:
    backend: "json"
    storage_path: "~/.nanamigopher/memory/user.json"
  knowledge_base:
    vector_store: "chromadb"
    embedding_provider: "bge"
    storage_path: "~/.nanamigopher/memory/knowledge"
```

### 7.2 团队部署模式（Phase 4 可选，需启用 Team 协作功能）

> 仅在多用户团队协作场景（US-P4-004）下启用，个人用户始终使用 §7.1 本地模式。

```yaml
memory:
  short_term:
    backend: "redis"
    redis_url: "redis://localhost:6379/0"
    ttl_seconds: 3600
  conversation:
    backend: "postgres"
    connection_string: "postgresql://..."
  user:
    backend: "postgres"
    connection_string: "postgresql://..."
  knowledge_base:
    vector_store: "qdrant"
    qdrant_url: "http://localhost:6333"
    embedding_provider: "openai"
```

---

## 附录：Memory 系统 Checklist

- [ ] IShortTermMemory 是否实现了容量上限和 TTL 机制？
- [ ] IConversationMemory 是否支持滑动窗口和上下文压缩？
- [ ] IUserMemory 是否实现了持久化和加密存储？
- [ ] IDocumentStore 是否支持多种文档分块策略？
- [ ] IRetriever 是否实现了三级检索和降级机制？
- [ ] IVectorStore 是否支持多种后端（ChromaDB / Qdrant）？
- [ ] EmbeddingProviderFactory 是否正确路由到对应 Provider？
- [ ] 记忆清理策略是否覆盖了所有存储后端？
