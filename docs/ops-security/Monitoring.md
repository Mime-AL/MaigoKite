# NanamiGopher 监控告警

## 概述

NanamiGopher 的可观测性体系基于 `IObservability` 接口构建，覆盖基础设施、应用和业务三个层次，通过 EventBus 事件驱动实现实时数据推送，最终接入 Prometheus + Grafana 进行长期指标存储与可视化。

---

## 1. 监控层次

### 1.1 层次划分

```
┌─────────────────────────────────────────┐
│           L3 业务监控                     │
│  Task 成功率、Token 消耗、工具调用分布     │
├─────────────────────────────────────────┤
│           L2 应用监控                     │
│  API 延迟、错误率、并发数、队列深度       │
├─────────────────────────────────────────┤
│           L1 基础设施监控                 │
│  CPU、内存、磁盘 I/O、网络带宽            │
└─────────────────────────────────────────┘
```

### 1.2 IObservability 演进路线

| Phase | 观测后端 | 能力 |
|-------|----------|------|
| Phase 1 | ConsoleObserver | 控制台输出，开发调试用 |
| Phase 2 | 自定义 Observer | 可扩展的多后端接入框架 |
| Phase 3 | Langfuse + Prometheus | 生产级链路追踪与指标采集 |

---

## 2. 关键指标

### 2.1 Token 消耗

| 指标名 | 类型 | 单位 | 说明 |
|--------|------|------|------|
| `nanamigopher_tokens_total` | Counter | count | 累计消耗 token 数 |
| `nanamigopher_tokens_per_task` | Histogram | tokens | 单次 Task 的 token 分布 |
| `nanamigopher_tokens_by_model` | Gauge | count | 各模型的当前 token 用量 |

- 按 `model`、`task_id`、`direction`(input/output) 打标签。
- 设置月度预算告警，超过 80% 时发出预警。

### 2.2 延迟指标

| 指标名 | 类型 | 单位 | 说明 |
|--------|------|------|------|
| `nanamigopher_request_duration_seconds` | Histogram | seconds | 请求端到端延迟 |
| `nanamigopher_tool_duration_seconds` | Histogram | seconds | 工具调用延迟 |
| `nanamigopher_llm_latency_seconds` | Histogram | seconds | LLM 首 token 延迟 |

- P50、P95、P99 分位数分别记录。
- 延迟超阈值时触发告警（见第 4 节）。

### 2.3 成功率与错误率

| 指标名 | 类型 | 说明 |
|--------|------|------|
| `nanamigopher_task_success_total` | Counter | 成功完成的 Task 数 |
| `nanamigopher_task_failed_total` | Counter | 失败的 Task 数 |
| `nanamigopher_error_rate_ratio` | Gauge | 错误率（失败/总数） |

- 错误按 `error_type`（timeout、permission_denied、rate_limit、internal）分类。

### 2.4 资源指标

| 指标名 | 类型 | 单位 | 说明 |
|--------|------|------|------|
| `nanamigopher_memory_bytes` | Gauge | bytes | 当前内存占用 |
| `nanamigopher_cpu_usage_ratio` | Gauge | ratio | CPU 使用率（0-1） |
| `nanamigopher_disk_usage_bytes` | Gauge | bytes | 磁盘使用量 |
| `nanamigopher_concurrent_tasks` | Gauge | count | 并发 Task 数 |

---

## 3. Inspector 监控页面

Inspector 是基于 EventBus 事件驱动的实时监控面板，提供可视化的 Task 运行状态与数据分析。

### 3.1 事件驱动架构

```
EventBus ──WebSocket──→ Inspector 前端
  │                       │
  ├── task.started        ├── 对话卡片创建
  ├── tool.called         ├── 时间线追加
  ├── llm.token           ├── Token 计数器更新
  ├── task.completed      ├── 卡片标记完成
  └── task.failed         └── 卡片标记失败 + 错误展示
```

### 3.2 WebSocket 容错机制

- 默认使用 WebSocket 实现实时推送。
- 当检测到 WebSocket 断线时，自动降级为 HTTP 长轮询（Polling），轮询间隔 5 秒。
- WebSocket 重连成功后，自动切回实时推送模式。
- 断线期间的事件通过补全机制获取，确保数据不丢失。

### 3.3 监控页面组件

#### 对话卡片

每个活跃 Task 对应一张卡片，展示：

- Task ID 与创建时间
- 当前状态（running / completed / failed）
- 已消耗 Token 数
- 最后活动时间
- 快速操作按钮（终止、查看详情）

#### 时间线视图

按时间顺序展示 Task 的执行链路：

```
[10:00:01] task.started    task_id=abc123
[10:00:02] tool.called     tool=glob pattern="**/*.ts"
[10:00:03] tool.called     tool=grep pattern="import"
[10:00:05] llm.token       model=gpt-4 tokens=1250
[10:00:12] tool.called     tool=bash cmd="npm test"
[10:00:15] task.completed  duration=14.2s
```

#### 自定义维度筛选

支持按以下维度过滤和分组：

- `model`：按使用的 LLM 模型筛选
- `tool`：按工具调用类型筛选
- `status`：成功 / 失败 / 运行中
- `time_range`：最近 1 小时 / 24 小时 / 7 天
- `user`：按用户分组（多租户场景）

### 3.4 仪表盘示例

```
┌──────────────────────────────────────────────────────┐
│  NanamiGopher Inspector                              │
├─────────────┬─────────────┬─────────────┬────────────┤
│ 活跃 Task   │ 今日成功    │ 今日失败    │ 平均延迟   │
│    12       │   347       │     5       │  2.3s      │
├─────────────┴─────────────┴─────────────┴────────────┤
│                                                     │
│  Token 消耗趋势          │  工具调用分布              │
│  ████████░░  125K        │  [bash ████] 35%         │
│  GPT-4: 80K               │  [glob ██]    25%        │
│  GPT-3.5: 45K             │  [file_edit ██] 20%      │
│                           │  [其他 ██]    20%        │
│                                                     │
├─────────────────────────────────────────────────────┤
│  活跃 Task 卡片                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │ abc123  │ running │ 450 tokens │ 10:00:01    │   │
│  │ def456  │ done    │ 1.2K tokens│ 09:58:30    │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

---

## 4. 告警策略

### 4.1 告警分级

| 级别 | 名称 | 颜色 | 响应要求 | 示例 |
|------|------|------|----------|------|
| P0 | Critical | 红色 | 5 分钟内响应 | 服务宕机、数据损坏 |
| P1 | High | 橙色 | 30 分钟内响应 | 错误率 > 10%、Token 预算耗尽 |
| P2 | Medium | 黄色 | 4 小时内响应 | 延迟 P99 > 10s、磁盘使用 > 80% |
| P3 | Low | 蓝色 | 下一个工作日 | 磁盘使用 > 60%、证书即将过期 |

### 4.2 告警规则

```yaml
alerts:
  - name: high_error_rate
    condition: nanamigopher_error_rate_ratio > 0.1
    duration: 5m
    severity: P1
    message: "Task 错误率超过 10%，持续 5 分钟"

  - name: high_latency_p99
    condition: histogram_quantile(0.99, nanamigopher_request_duration_seconds) > 10
    duration: 10m
    severity: P2
    message: "请求 P99 延迟超过 10 秒，持续 10 分钟"

  - name: token_budget_warning
    condition: nanamigopher_tokens_total > monthly_budget * 0.8
    duration: 1h
    severity: P1
    message: "月度 Token 预算使用超过 80%"

  - name: disk_usage_critical
    condition: nanamigopher_disk_usage_bytes / disk_total_bytes > 0.9
    duration: 5m
    severity: P0
    message: "磁盘使用率超过 90%"

  - name: service_down
    condition: up == 0
    duration: 1m
    severity: P0
    message: "NanamiGopher 服务不可达"
```

### 4.3 通知方式

| 渠道 | 适用级别 | 说明 |
|------|----------|------|
| PagerDuty | P0、P1 | 即时电话/短信通知值班人员 |
| Slack | P0-P2 | 频道消息通知 #ops-alerts |
| Email | P2、P3 | 日报/周报汇总邮件 |
| Webhook | 自定义 | 支持对接内部工单系统 |

---

## 5. Prometheus + Grafana 集成方案

### 5.1 指标暴露

NanamiGopher 通过 `/metrics` 端点暴露 Prometheus 格式指标：

```
GET /metrics
Content-Type: text/plain; version=0.0.4

# HELP nanamigopher_task_success_total Total successful tasks
# TYPE nanamigopher_task_success_total counter
nanamigopher_task_success_total{model="gpt-4"} 1234
nanamigopher_task_success_total{model="gpt-3.5-turbo"} 5678

# HELP nanamigopher_request_duration_seconds Request duration in seconds
# TYPE nanamigopher_request_duration_seconds histogram
nanamigopher_request_duration_seconds_bucket{le="0.5"} 100
nanamigopher_request_duration_seconds_bucket{le="1.0"} 250
nanamigopher_request_duration_seconds_bucket{le="+Inf"} 300
nanamigopher_request_duration_seconds_sum 450.2
nanamigopher_request_duration_seconds_count 300
```

### 5.2 Prometheus 配置

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: "nanamigopher"
    static_configs:
      - targets: ["localhost:8080"]
    metrics_path: "/metrics"
    scrape_interval: 10s
```

### 5.3 Grafana 仪表盘

内置仪表盘模板（JSON 导入）：

- **Overview**：总览 Dashboard，包含活跃 Task、Token 趋势、错误率
- **Performance**：延迟分布、吞吐量、资源使用
- **LLM**：各模型 Token 消耗对比、调用频次
- **Tools**：工具调用 Top N、成功率分析
- **Alerts**：当前告警与历史告警记录

---

## 6. 日志聚合方案

### 6.1 日志流向

```
NanamiGopher ──structured JSON──→ 本地文件 (/var/log/nanamigopher/)
                                    │
                                    ├── ELK Stack (Elasticsearch + Logstash + Kibana)
                                    │
                                    └── Loki + Promtail（轻量替代方案）
```

### 6.2 日志标签

所有日志事件携带以下标准标签，便于索引与查询：

| 标签 | 来源 | 示例 |
|------|------|------|
| `trace_id` | 请求链路追踪 | `a1b2c3d4-e5f6-7890-abcd-ef1234567890` |
| `task_id` | Task 标识 | `task_1784045621099` |
| `level` | 日志级别 | `INFO` |
| `service` | 服务名称 | `nanamigopher` |
| `tool` | 工具名称（如有） | `bash` |
| `model` | LLM 模型（如有） | `gpt-4` |

### 6.3 查询示例（Loki）

```logql
# 查找某个 Task 的所有日志
{service="nanamigopher", task_id="task_1784045621099"}

# 查找所有失败的 Task
{service="nanamigopher", level="ERROR"} |= "task.failed"

# 查找某个模型的高延迟调用
{service="nanamigopher", model="gpt-4"} | json | duration > 10
```

---

## 附录

### 监控健康检查端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 基础健康检查（返回 200/503） |
| `/ready` | GET | 就绪检查（依赖项可用性） |
| `/metrics` | GET | Prometheus 指标 |
| `/inspector/events` | WS | Inspector 实时事件推送 |
