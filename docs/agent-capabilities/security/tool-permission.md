# 工具权限安全

> NanamiGopher Agent 的工具权限分级、沙箱隔离与安全过滤规范。

---

## 1. 概述

NanamiGopher 采用多层安全防护体系，确保 Agent 在执行工具调用时不会造成意外损害。安全体系涵盖权限分级、沙箱隔离、内容过滤和审计日志四个维度。

```
┌─────────────────────────────────────────────────────┐
│                   安全防护体系                        │
├─────────────┬─────────────┬──────────────┬───────────┤
│  权限分级    │  沙箱隔离    │  安全过滤     │  审计日志  │
│  L1-L5      │  Sandbox    │  截断+检测    │  AuditLog │
│  Permission │  隔离执行环境 │  正则+语义    │  全量记录  │
└─────────────┴─────────────┴──────────────┴───────────┘
```

---

## 2. L1-L5 权限分级

### 2.1 权限等级定义

| 等级 | 名称 | 风险级别 | 描述 |
|------|------|----------|------|
| L1 | 只读 | 低 | 仅允许读取操作，不涉及任何修改 |
| L2 | 只读 Shell | 低 | 允许执行无副作用的 Shell 查询命令（ls、pwd、git status 等） |
| L3 | Shell 命令 | 中 | 允许执行有副作用的 Shell 命令（npm run、python 脚本等）及网络访问 |
| L4 | 文件修改 | 中高 | 允许创建、修改、删除文件及系统配置变更 |
| L5 | 危险操作 | 高 | 允许执行破坏性系统级操作，需严格确认 + 熔断器 |

### 2.2 工具权限映射

| 工具名 | 权限等级 | 说明 |
|--------|----------|------|
| `file_read` | L1 | 读取文件内容 |
| `glob` | L1 | 文件模式匹配（只读） |
| `grep` | L1 | 搜索文件内容（只读） |
| `todo_write` | L1 | 管理待办事项 |
| `sleep` | L1 | 暂停执行（无害） |
| `bash` | L3 | 执行 Shell 命令（含网络、进程操作） |
| `web_search` | L3 | 执行网络搜索（外部网络访问） |
| `web_fetch` | L3 | 抓取网页内容（外部网络访问） |
| `file_write` | L4 | 写入/创建文件 |
| `file_edit` | L4 | 编辑已有文件 |

> 注：Phase 1 中 `bash` 工具默认限制为 L3 权限，仅允许执行预定义的白名单命令集。

### 2.3 权限校验流程

```
工具调用请求
  │
  ├─ 获取工具声明的最低权限等级（BaseTool.permission_level()）
  │
  ├─ 获取当前用户的权限等级（PermissionManager.get_user_level(user_id)）
  │
  ├─ 比较权限等级
  │   ├─ user_level >= tool_level → 继续
  │   └─ user_level < tool_level → 拒绝
  │       └─ 返回 PermissionDenied 错误
  │
  ├─ 检查权限模式（见第 3 节）
  │
  └─ 执行工具调用
```

---

## 3. 权限模式与权限分级映射

### 3.1 四种权限模式

| 模式 | 说明 | 对应权限等级 |
|------|------|-------------|
| `Manual` | 每次工具调用都需要用户确认 | L1-L2 免确认，L3+ 需确认 |
| `AcceptEdits` | 允许自动执行低风险操作，危险操作需确认 | L1-L2 自动，L3 需确认，L4+ 弹窗 |
| `Plan` | Agent 先提交执行计划，用户审批后执行 | 所有等级均需计划审批 |
| `Auto` | 完全自动执行，无用户干预 | 仅在 L1 级别生效 |

### 3.2 模式与等级的组合决策

```
权限模式 = Auto
  ├─ L1 工具 → 自动执行
  └─ L2+ 工具 → 降级为 Manual（拒绝执行）

权限模式 = Plan
  ├─ 所有工具 → 生成执行计划
  ├─ 用户审批 → 执行
  └─ 用户拒绝 → 中止

权限模式 = AcceptEdits
  ├─ L1 工具 → 自动执行
  ├─ L2 工具 → 自动执行
  ├─ L3 工具 → 弹窗确认
  └─ L4+ 工具 → 降级为 Manual

权限模式 = Manual
  ├─ 所有工具 → 每次调用弹出确认请求
```

### 3.3 模式配置

```yaml
permission_modes:
  default: "AcceptEdits"
  overrides:
    - tool_pattern: "bash"
      mode: "Manual"
      permission_level: 3
    - tool_pattern: "file_*"
      mode: "AcceptEdits"
      permission_level: 2
    - tool_pattern: "*"
      mode: "Auto"
      permission_level: 1
```

---

## 4. 白名单机制

### 4.1 白名单设计原则

白名单不是"一票放行"，而是**降级因子**：即使命令在白名单中，仍需经过权限检查和沙箱隔离。

```
白名单命令
  │
  ├─ 权限检查 → 未通过 → 拒绝
  ├─ 沙箱检查 → 未通过 → 拒绝
  └─ 全部通过 → 放行执行
```

### 4.2 白名单配置

```yaml
whitelist:
  # L1 级别（只读）
  safe_commands:
    - "ls"
    - "cat"
    - "grep"
    - "find"
    - "wc"
    - "head"
    - "tail"
    - "echo"
    - "pwd"
    - "whoami"

  # L2 级别（写入）
  write_commands:
    - "mkdir"
    - "touch"
    - "cp"
    - "mv"
    - "tee"

  # L3 级别（执行）
  exec_commands:
    - "python"
    - "node"
    - "npm"
    - "pip"
    - "make"
    - "docker"

  # 白名单降级因子
  whitelist_degradation:
    enabled: true
    max_safe_commands: 20          # 白名单命令上限
    require_sandbox: true          # 即使白名单也需沙箱
    require_permission_check: true # 即使白名单也需权限检查
```

### 4.3 黑名单机制

```yaml
blacklist:
  # 绝对禁止的命令
  forbidden:
    - "rm -rf /"
    - "mkfs"
    - "dd if=/dev/zero"
    - "chmod 777"
    - "sudo"
    - "su "
    - "wget http://*"
    - "curl http://*"

  # 需要额外检查的参数模式
  restricted_patterns:
    - pattern: "rm.*-"
      requires_confirmation: true
    - pattern: "chmod.*7[0-7]{2}"
      requires_confirmation: true
    - pattern: ".*\\|.*"
      requires_confirmation: true
```

---

## 5. 沙箱隔离

### 5.1 沙箱架构演进

| Phase | 沙箱类型 | 安全性 | 性能 | 适用场景 |
|-------|----------|--------|------|----------|
| Phase 1 | LocalSandbox | 中 | 高 | 开发环境、受信任任务 |
| Phase 3 | DockerSandbox | 高 | 中 | 生产环境、不可信任务 |

### 5.2 LocalSandbox（Phase 1）

```python
class LocalSandbox:
    """本地沙箱，通过资源限制实现隔离。"""

    def __init__(self, config: SandboxConfig):
        self.config = config
        self.cgroup_enabled = self._check_cgroup()

    def execute(self, command: str, timeout: int = 30) -> ToolResult:
        """在沙箱中执行命令。"""
        # 1. 资源限制
        resource_limits = {
            "cpu": self.config.cpu_limit,        # CPU 使用上限
            "memory": self.config.memory_limit,   # 内存上限（默认 512MB）
            "disk": self.config.disk_limit,       # 磁盘写入上限
            "time": timeout,                       # 时间上限
            "processes": self.config.max_processes, # 最大进程数
        }

        # 2. 网络隔离（默认禁用网络）
        if not self.config.allow_network:
            resource_limits["network"] = "disabled"

        # 3. 文件系统限制
        chroot_dir = self.config.workdir
        readonly_mounts = self.config.readonly_paths

        # 4. 执行命令
        return self._run_with_limits(command, resource_limits)
```

**LocalSandbox 配置**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `cpu_limit` | 1.0 | CPU 核心数上限 |
| `memory_limit` | 512MB | 内存使用上限 |
| `disk_limit` | 100MB | 磁盘写入上限 |
| `max_processes` | 10 | 最大子进程数 |
| `allow_network` | false | 是否允许网络访问 |
| `workdir` | 临时目录 | 工作目录 |
| `readonly_paths` | `["/etc", "/usr"]` | 只读挂载路径 |

### 5.3 DockerSandbox（Phase 3）

```python
class DockerSandbox:
    """Docker 容器沙箱，提供进程级隔离。"""

    def __init__(self, config: DockerSandboxConfig):
        self.config = config
        self.client = docker.from_env()

    def execute(self, command: str, timeout: int = 30) -> ToolResult:
        """在 Docker 容器中执行命令。"""
        # 1. 创建隔离容器
        container = self.client.containers.run(
            self.config.image,
            command,
            detach=True,
            mem_limit=self.config.memory_limit,
            cpu_quota=self.config.cpu_quota,
            volumes={self.config.host_workdir: {"bind": "/workspace", "mode": "rw"}},
            read_only=True,
            network_disabled=not self.config.allow_network,
            security_opt=[f"no-new-privileges:{not self.config.allow_new_privileges}"],
            tmpfs={"/tmp": "size=50M"},
        )

        # 2. 等待执行完成
        result = container.wait(timeout=timeout)

        # 3. 清理容器
        container.remove()

        # 4. 返回结果
        logs = container.logs(stdout=True, stderr=True).decode()
        return ToolResult(data=logs, summary=f"Exit code: {result.get('StatusCode', -1)}")
```

**DockerSandbox 配置**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `image` | `alpine:latest` | 基础镜像 |
| `memory_limit` | 1GB | 内存限制 |
| `cpu_quota` | 100000 | CPU 配额（微秒） |
| `allow_network` | false | 是否允许网络 |
| `allow_new_privileges` | false | 是否允许提升权限 |
| `read_only_rootfs` | true | 只读根文件系统 |
| `workdir` | `/workspace` | 工作目录挂载点 |

---

## 6. 安全过滤

### 6.1 过滤策略：先截断后检测

```
输入数据
  │
  ├─ Step 1: 截断（Truncation）
  │   ├─ 超过最大长度的输入 → 截断到安全长度
  │   └─ 默认上限：8192 字符
  │
  ├─ Step 2: 正则检测（Regex Detection）
  │   ├─ 匹配已知攻击模式（SQL 注入、XSS、命令注入）
  │   ├─ 命中黑名单 → 拒绝输入
  │   └─ 命中灰名单 → 标记警告
  │
  └─ Step 3: 向量语义检测（Semantic Detection）
      ├─ 将输入转为向量
      ├─ 与已知恶意模式向量比较相似度
      ├─ 相似度 > 阈值 → 拒绝输入
      └─ 相似度在灰色区间 → 标记警告
```

### 6.2 正则检测规则

```python
REGEX_PATTERNS = {
    "sql_injection": [
        r"(?i)(union\s+select|drop\s+table|;\s*delete\s+from)",
        r"(?i)(or|and)\s+\d+\s*=\s*\d+",
    ],
    "command_injection": [
        r";\s*(rm|chmod|chown|sudo|wget|curl)",
        r"\|\s*(nc|ncat|bash|sh)",
        r"`[^`]*\$(?:HOME|USER|PWD)[^`]*`",
    ],
    "xss": [
        r"<script[^>]*>",
        r"javascript\s*:",
        r"on(?:load|error|click)\s*=",
    ],
    "path_traversal": [
        r"\.\./",
        r"%2e%2e[/\\]",
    ],
}
```

### 6.3 向量语义检测

```python
class SemanticFilter:
    """基于向量相似度的语义安全检测。"""

    def __init__(self, embedding_provider: IEmbeddingProvider):
        self.provider = embedding_provider
        self.malicious_vectors = self._load_malicious_patterns()
        self.similarity_threshold = 0.85

    def check(self, text: str) -> FilterResult:
        """检测文本是否包含恶意语义。"""
        # 1. 生成文本向量
        text_vector = self.provider.embed([text])[0]

        # 2. 计算与恶意模式的相似度
        similarities = [
            cosine_similarity(text_vector, malicious_vec)
            for malicious_vec in self.malicious_vectors
        ]

        max_similarity = max(similarities) if similarities else 0.0

        # 3. 判定结果
        if max_similarity >= self.similarity_threshold:
            return FilterResult(
                safe=False,
                reason=f"Malicious pattern detected (similarity: {max_similarity:.2f})",
                confidence=max_similarity,
            )
        elif max_similarity >= 0.6:
            return FilterResult(
                safe=None,  # 灰色地带，标记警告
                reason=f"Suspicious pattern (similarity: {max_similarity:.2f})",
                confidence=max_similarity,
            )
        else:
            return FilterResult(safe=True, reason="No threat detected")
```

---

## 7. 审计日志

### 7.1 日志记录范围

所有工具调用均记录审计日志，无论成功或失败：

| 事件 | 记录内容 |
|------|----------|
| 工具调用 | 工具名、参数、调用者、时间戳 |
| 权限检查 | 用户权限等级、工具权限等级、结果 |
| 沙箱执行 | 沙箱类型、资源限制、执行结果 |
| 安全过滤 | 过滤结果、命中规则、置信度 |
| 工具结果 | 返回数据摘要、耗时、Token 用量 |
| 错误事件 | 错误类型、错误信息、堆栈跟踪 |

### 7.2 AuditLog 结构

```python
@dataclass
class AuditLogEntry:
    """审计日志条目。"""
    log_id: str                        # 唯一日志 ID（UUID）
    timestamp: datetime                 # 事件时间
    trace_id: str                       # 追踪 ID（关联同一请求的所有日志）
    task_id: str                        # 任务 ID
    step_id: str                        # 步骤 ID
    user_id: str                        # 用户 ID
    tool_name: str                      # 工具名称
    tool_type: str                      # 工具类型（native / mcp）
    permission_level: int               # 工具权限等级
    user_permission_level: int          # 用户权限等级
    permission_result: str              # 权限检查结果（allowed / denied）
    sandbox_type: str                   # 沙箱类型（none / local / docker）
    input_summary: str                  # 输入摘要（脱敏）
    output_summary: str                 # 输出摘要（脱敏）
    status: str                         # 执行状态（success / failed / denied）
    error_message: Optional[str]        # 错误信息
    duration_ms: int                    # 执行耗时（毫秒）
    tokens_used: int                    # Token 用量
    security_flags: List[str]           # 安全标记（blocked / warned / clean）
    metadata: Dict[str, Any]            # 额外元数据
```

### 7.3 日志存储

```yaml
audit_log:
  storage: "local"                    # local / elasticsearch / s3
  retention_days: 90                  # 日志保留天数
  max_file_size_mb: 100               # 单文件最大大小
  rotation: "daily"                   # 日志轮转策略
  sensitive_fields_mask:              # 敏感字段脱敏
    - "input_summary"
    - "output_summary"
    - "metadata"
```

### 7.4 日志查询

```python
class AuditLogQuerier:
    """审计日志查询接口。"""

    def query(self, filters: LogFilters) -> List[AuditLogEntry]:
        """根据条件查询审计日志。"""
        pass

    def export(self, log_ids: List[str], format: str = "json") -> bytes:
        """导出审计日志。"""
        pass

    def alert(self, threshold: AlertThreshold) -> List[AuditLogEntry]:
        """检测异常调用模式并告警。"""
        # 检测：短时间内大量危险操作
        # 检测：权限等级频繁跳变
        # 检测：来自同一用户的异常高频调用
        pass
```

---

## 8. 安全事件响应

### 8.1 事件分级

| 级别 | 描述 | 响应动作 |
|------|------|----------|
| P1 - 紧急 | 检测到恶意输入或越权操作 | 立即阻断、通知管理员 |
| P2 - 高 | 沙箱逃逸尝试 | 隔离容器、记录证据 |
| P3 - 中 | 权限模式违规 | 降级为 Manual 模式 |
| P4 - 低 | 安全警告（灰色地带） | 记录日志、标记审查 |

### 8.2 自动响应

```
安全事件检测
  │
  ├─ P1 事件
  │   ├─ 立即终止当前工具调用
  │   ├─ 阻断用户后续调用（冷却期 300s）
  │   ├─ 发送告警通知
  │   └─ 保存完整证据链
  │
  ├─ P2 事件
  │   ├─ 隔离沙箱环境
  │   ├─ 记录完整日志
  │   └─ 通知管理员
  │
  ├─ P3 事件
  │   ├─ 自动降级权限模式
  │   └─ 记录日志
  │
  └─ P4 事件
      └─ 记录日志，标记待审查
```

---

## 附录：安全 Checklist

- [ ] 所有工具是否都映射了正确的 L1-L5 权限等级？
- [ ] 权限模式（Manual/AcceptEdits/Plan/Auto）是否正确配置？
- [ ] 白名单是否设置了降级因子（仍需权限检查和沙箱）？
- [ ] LocalSandbox 是否正确限制了资源使用？
- [ ] DockerSandbox（Phase 3）是否配置了只读根文件系统？
- [ ] 安全过滤是否实现了"先截断后检测"策略？
- [ ] 正则检测和向量语义检测是否覆盖了常见攻击模式？
- [ ] 审计日志是否记录了所有工具调用（包括失败和拒绝）？
- [ ] 日志是否对敏感字段进行了脱敏处理？
- [ ] 安全事件响应是否覆盖了 P1-P4 所有级别？
