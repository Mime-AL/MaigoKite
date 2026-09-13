# NanamiGopher 日志管理

## 概述

NanamiGopher 采用结构化日志（JSON 格式）记录系统运行状态，支持本地持久化存储与可选云端同步。所有日志遵循统一的分级、格式与脱敏规范，确保可追溯性与合规性。

---

## 1. 日志分级

系统使用五级日志体系，每级对应不同的严重程度与处理方式。

| 级别 | 名称 | 用途 | 默认输出 | 示例 |
|------|------|------|----------|------|
| DEBUG | 调试 | 详细诊断信息，仅开发环境启用 | stdout + debug.log | 变量值、中间状态 |
| INFO | 信息 | 正常业务流程记录 | stdout + info.log | Task 创建、工具调用 |
| WARN | 警告 | 潜在问题，不影响当前流程 | stdout + warn.log | 重试、降级、超时接近 |
| ERROR | 错误 | 单个操作失败，可恢复 | stdout + error.log | 工具执行异常、API 限流 |
| FATAL | 致命 | 系统无法继续运行 | stdout + fatal.log | 数据库损坏、内存溢出 |

### 1.1 级别控制

- 生产环境默认级别：`INFO`
- 开发环境默认级别：`DEBUG`
- 通过环境变量 `LOG_LEVEL` 动态调整：

```bash
export LOG_LEVEL=WARN  # 仅输出 WARN 及以上级别
```

### 1.2 级别升级规则

- `ERROR` 级别的日志自动附加 `trace_id` 与 `task_id` 用于关联排查。
- `FATAL` 级别触发优雅停机流程，记录停机前的最后一条日志后退出。

---

## 2. 结构化日志格式

所有日志统一使用 JSON 格式输出，便于机器解析与聚合。

### 2.1 日志 Schema

```json
{
  "timestamp": "2026-07-21T10:00:01.123Z",
  "level": "INFO",
  "service": "nanamigopher",
  "version": "1.0.0",
  "trace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "task_id": "task_1784045621099",
  "user_id": "user_001",
  "component": "eventbus",
  "event": "task.started",
  "message": "Task started",
  "metadata": {
    "model": "gpt-4",
    "prompt_tokens": 1200,
    "tools_requested": ["glob", "grep", "bash"]
  },
  "duration_ms": null
}
```

### 2.2 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `timestamp` | ISO 8601 | 是 | 日志产生时间（UTC） |
| `level` | string | 是 | 日志级别 |
| `service` | string | 是 | 服务名称，固定为 `nanamigopher` |
| `version` | string | 是 | 服务版本号 |
| `trace_id` | string | 是 | 全局链路追踪 ID |
| `task_id` | string | 否 | 当前 Task 标识 |
| `user_id` | string | 否 | 当前操作用户标识 |
| `component` | string | 是 | 日志来源模块 |
| `event` | string | 否 | 关联的事件名称（来自 EventBus） |
| `message` | string | 是 | 人类可读的描述 |
| `metadata` | object | 否 | 扩展字段，按需添加 |
| `duration_ms` | number/null | 否 | 操作耗时（毫秒） |

---

## 3. 日志内容规范

### 3.1 Trace ID 与 Task ID

每个请求分配唯一的 `trace_id`，每个 Task 分配唯一的 `task_id`。两者贯穿整个请求生命周期，用于关联所有相关日志。

```
trace_id: 请求级唯一标识（一个 trace 可能包含多个 Task）
task_id:  Task 级唯一标识（一个 task 属于一个 trace）
```

### 3.2 各模块日志规范

#### EventBus 日志

EventBus 产生的事件自动转化为结构化日志：

| 事件 | 级别 | 日志内容 |
|------|------|----------|
| `task.started` | INFO | 记录 model、tools_requested、user_id |
| `tool.called` | INFO | 记录 tool_name、tool_args（脱敏后）、trace_id |
| `llm.token` | DEBUG | 记录 model、prompt_tokens、completion_tokens、total_tokens |
| `task.completed` | INFO | 记录 duration_ms、tokens_used、status |
| `task.failed` | ERROR | 记录 error_code、error_message、stack_trace（脱敏） |

#### 工具调用日志

```json
{
  "timestamp": "2026-07-21T10:00:03.456Z",
  "level": "INFO",
  "component": "tool_executor",
  "event": "tool.called",
  "message": "Executing tool: bash",
  "metadata": {
    "tool_name": "bash",
    "tool_args_masked": true,
    "command_preview": "npm test --coverage",
    "timeout_seconds": 30
  }
}
```

- 敏感参数（如密码、密钥）在日志中显示为 `[REDACTED]`。
- 命令参数仅记录预览（前 50 字符），完整内容不入日志。

#### 安全审计日志

```json
{
  "timestamp": "2026-07-21T10:00:05.789Z",
  "level": "WARN",
  "component": "security_filter",
  "event": "input.filtered",
  "message": "Input filtered by regex rule",
  "metadata": {
    "rule_id": "CMD_INJECTION_001",
    "matched_pattern": "; rm -rf",
    "action": "blocked",
    "trace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }
}
```

---

## 4. 日志存储

### 4.1 本地存储

| 文件 | 内容 | 保留期限 |
|------|------|----------|
| `nanamigopher.log` | 所有级别合并日志 | 30 天 |
| `debug.log` | DEBUG 级别 | 7 天 |
| `info.log` | INFO 级别 | 30 天 |
| `warn.log` | WARN 级别 | 90 天 |
| `error.log` | ERROR 级别 | 180 天 |
| `fatal.log` | FATAL 级别 | 永久归档 |
| `audit.log` | 安全审计日志 | 365 天 |

存储路径：`/var/log/nanamigopher/`（可通过配置修改）

### 4.2 可选云端同步

- 默认仅本地存储。
- 开启云端同步后，日志经压缩与加密后上传至指定 S3 兼容存储。
- 同步频率：每 5 分钟批量上传一次。
- 传输通道：HTTPS（TLS 1.3）。

```yaml
logging:
  cloud_sync:
    enabled: false
    endpoint: "https://storage.example.com"
    bucket: "nanamigopher-logs"
    region: "us-east-1"
    sync_interval: 300s
```

---

## 5. 日志轮转策略

采用文件大小与时间双条件轮转，满足任一条件即触发轮转。

### 5.1 轮转规则

| 条件 | 阈值 | 动作 |
|------|------|------|
| 文件大小 | 单个日志文件 > 100MB | 轮转并压缩当前文件 |
| 时间跨度 | 自然日变更（00:00 UTC） | 创建新日志文件 |
| 保留数量 | 最多保留 30 个归档文件 | 删除最旧的归档 |

### 5.2 轮转流程

```
nanamigopher.log (100MB+)
    │
    ├─→ nanamigopher.log.1.gz  (最新归档，gzip 压缩)
    ├─→ nanamigopher.log.2.gz
    ├─→ ...
    └─→ nanamigopher.log.30.gz (最旧，达到上限后删除)
```

### 5.3 配置示例

```yaml
logging:
  rotation:
    max_size_mb: 100
    max_age_days: 30
    max_backups: 30
    compress: true
    rotate_daily: true
```

---

## 6. 敏感信息脱敏

### 6.1 脱敏规则

所有日志在输出前必须经过脱敏过滤器，以下类型的数据会被自动处理：

| 数据类型 | 脱敏方式 | 示例 |
|----------|----------|------|
| API Key / Secret | 替换为 `[REDACTED]` | `sk-xxxx...` → `[REDACTED]` |
| Access Token | 保留前 8 位 + `[REDACTED]` | `eyJhbGci...` → `eyJhbGci...[REDACTED]` |
| 邮箱地址 | 隐藏域名部分 | `user@example.com` → `u***@****ple.com` |
| 手机号 | 保留前 3 后 4 位 | `13812345678` → `138****5678` |
| 身份证 / 证件号 | 完全隐藏 | `110101****1234` → `[REDACTED]` |
| 文件绝对路径 | 保留目录结构，隐藏文件名 | `/workspace/src/main.ts` → `/workspace/src/[REDACTED]` |
| 密码字段 | 完全隐藏 | `"password": "xxx"` → `"password": "[REDACTED]"` |

### 6.2 脱敏实施

脱敏在日志序列化之前执行，确保原始敏感数据不会出现在任何日志输出中：

```
日志事件对象
    │
    ▼
脱敏过滤器（脱敏所有已知的敏感字段）
    │
    ▼
JSON 序列化
    │
    ▼
写入日志文件 / 发送到输出
```

### 6.3 自定义脱敏规则

可通过正则表达式添加自定义脱敏规则：

```yaml
logging:
  redaction:
    rules:
      - pattern: "\\b[A-Za-z0-9._+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{2,}\\b"
        replacement: "[EMAIL_REDACTED]"
      - pattern: "(sk-[a-zA-Z0-9]{20,})"
        replacement: "[REDACTED]"
```

---

## 附录

### 日志查询最佳实践

```bash
# 查看某个 Trace 的全部日志
grep "a1b2c3d4-e5f6-7890-abcd-ef1234567890" /var/log/nanamigopher/nanamigopher.log

# 统计今日错误数
grep '"level":"ERROR"' /var/log/nanamigopher/error.log.*.gz | wc -l

# 提取某个 Task 的工具调用链
grep "task_1784045621099" /var/log/nanamigopher/info.log | grep tool.called
```

### 合规要求

- 所有日志保留期限满足最低合规要求（见第 4.1 节）。
- 日志中包含用户数据时，需遵循数据隐私政策（本地优先、可选加密同步）。
- 安全审计日志（audit.log）独立存储，不可被常规运维操作覆盖或删除。
