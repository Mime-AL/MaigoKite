# NanamiGopher 生产环境部署指南

本文档提供 NanamiGopher 在生产环境中的完整部署指南，涵盖单机部署、服务器部署、性能调优、安全加固、监控告警和故障排查。

## 目录

- [部署模式概览](#部署模式概览)
- [单机部署（Electron 打包）](#单机部署electron-打包)
- [服务器部署](#服务器部署)
  - [Docker Compose 部署](#docker-compose-部署)
  - [Kubernetes 部署](#kubernetes-部署)
- [性能调优](#性能调优)
- [安全加固](#安全加固)
- [监控告警](#监控告警)
- [故障排查 Checklist](#故障排查-checklist)

---

## 部署模式概览

NanamiGopher 支持两种部署模式：

| 模式 | 适用场景 | 架构 | 端口 |
|------|---------|------|------|
| 单机桌面应用 | 个人使用、本地开发 | Electron 内置 Go + Python | 内嵌，无需暴露 |
| 服务器部署 | 团队使用、远程访问 | Docker Compose / K8s | 80, 8080, 8081 |

---

## 单机部署（Electron 打包）

### 前提条件

- Node.js >= 18
- pnpm >= 9
- Go >= 1.22
- Python >= 3.11

### 构建步骤

```bash
# 1. 克隆仓库
git clone https://github.com/nanami-project/nanamigopher.git
cd nanamigopher

# 2. 安装前端依赖
cd frontend && pnpm install && cd ..

# 3. 安装 Electron 依赖
cd electron && pnpm install && cd ..

# 4. 构建 Go API Gateway（嵌入到 Electron 中）
cd gateway && go build -o ../electron/resources/gateway ./cmd/gateway && cd ..

# 5. 准备 Python Agent Core（嵌入到 Electron 中）
cd agent-core && pip install --target=../electron/resources/agent-core -r requirements.txt && cd ..

# 6. 构建前端
cd frontend && pnpm build && cd ..

# 7. 打包 Electron 应用
cd electron && pnpm run package
```

### 平台特定构建

```bash
# macOS (Intel + Apple Silicon)
cd electron && pnpm run package:mac

# Windows
cd electron && pnpm run package:win

# Linux
cd electron && pnpm run package:linux
```

### 安装包位置

| 平台 | 安装包 | 路径 |
|------|--------|------|
| macOS | `.dmg` / `.zip` | `electron/release/NanamiGopher-{version}-mac.dmg` |
| Windows | `.exe` / `.zip` | `electron/release/NanamiGopher Setup {version}.exe` |
| Linux | `.AppImage` / `.deb` | `electron/release/NanamiGopher-{version}-linux.AppImage` |

### 数据目录

| 平台 | 数据路径 |
|------|---------|
| macOS | `~/Library/Application Support/NanamiGopher/` |
| Windows | `%APPDATA%\NanamiGopher\` |
| Linux | `~/.config/NanamiGopher/` |

数据文件包括：
- `nanami.db` — SQLite 数据库
- `chroma_db/` — ChromaDB 向量数据
- `uploads/` — 用户上传文件

---

## 服务器部署

### Docker Compose 部署

#### 前置准备

```bash
# 1. 安装 Docker 和 Docker Compose
# Ubuntu/Debian
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# 2. 克隆仓库
git clone https://github.com/nanami-project/nanamigopher.git
cd nanamigopher

# 3. 创建环境配置文件
cp .env.example .env
# 编辑 .env，填入 API 密钥等配置
```

#### 启动服务

```bash
# 构建并启动
docker compose up -d --build

# 验证服务状态
docker compose ps

# 查看日志
docker compose logs -f
```

#### 反向代理配置（Nginx）

```nginx
# /etc/nginx/sites-available/nanamigopher
server {
    listen 80;
    server_name nanamigopher.example.com;

    # 强制 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name nanamigopher.example.com;

    # SSL 证书
    ssl_certificate     /etc/letsencrypt/live/nanamigopher.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/nanamigopher.example.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    # 前端
    location / {
        proxy_pass http://localhost:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API Gateway
    location /api/ {
        proxy_pass http://localhost:8080/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300s;
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://localhost:8080/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400s;
    }
}
```

#### 获取 SSL 证书（Let's Encrypt）

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d nanamigopher.example.com
```

### Kubernetes 部署

#### Namespace 和资源定义

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: nanamigopher
```

#### Deployment

```yaml
# k8s/deployments.yaml
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
  namespace: nanamigopher
spec:
  replicas: 2
  selector:
    matchLabels:
      app: api-gateway
  template:
    metadata:
      labels:
        app: api-gateway
    spec:
      containers:
        - name: gateway
          image: ghcr.io/nanami-project/nanamigopher/gateway:latest
          ports:
            - containerPort: 8080
          envFrom:
            - configMapRef:
                name: nanamigopher-config
            - secretRef:
                name: nanamigopher-secrets
          resources:
            requests:
              cpu: 250m
              memory: 128Mi
            limits:
              cpu: 1000m
              memory: 512Mi
          readinessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 30
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-core
  namespace: nanamigopher
spec:
  replicas: 1
  selector:
    matchLabels:
      app: agent-core
  template:
    metadata:
      labels:
        app: agent-core
    spec:
      containers:
        - name: agent
          image: ghcr.io/nanami-project/nanamigopher/agent-core:latest
          ports:
            - containerPort: 8081
          envFrom:
            - configMapRef:
                name: nanamigopher-config
            - secretRef:
                name: nanamigopher-secrets
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              cpu: 2000m
              memory: 2Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: nanamigopher
spec:
  replicas: 1
  selector:
    matchLabels:
      app: frontend
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
        - name: nginx
          image: ghcr.io/nanami-project/nanamigopher/frontend:latest
          ports:
            - containerPort: 80
```

#### Service

```yaml
# k8s/services.yaml
apiVersion: v1
kind: Service
metadata:
  name: api-gateway
  namespace: nanamigopher
spec:
  selector:
    app: api-gateway
  ports:
    - port: 8080
      targetPort: 8080
---
apiVersion: v1
kind: Service
metadata:
  name: agent-core
  namespace: nanamigopher
spec:
  selector:
    app: agent-core
  ports:
    - port: 8081
      targetPort: 8081
---
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: nanamigopher
spec:
  selector:
    app: frontend
  ports:
    - port: 80
      targetPort: 80
```

#### Ingress

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: nanamigopher-ingress
  namespace: nanamigopher
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - nanamigopher.example.com
      secretName: nanamigopher-tls
  rules:
    - host: nanamigopher.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend
                port:
                  number: 80
          - path: /api/
            pathType: Prefix
            backend:
              service:
                name: api-gateway
                port:
                  number: 8080
          - path: /ws/
            pathType: Prefix
            backend:
              service:
                name: api-gateway
                port:
                  number: 8080
```

#### ConfigMap 和 Secret

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: nanamigopher-config
  namespace: nanamigopher
data:
  AGENT_CORE_URL: http://agent-core:8081
  CHROMADB_URL: http://chromadb:8321
  LOG_LEVEL: info
  VECTOR_STORE: chroma
  CHROMADB_HOST: chromadb
  CHROMADB_PORT: "8321"

---
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: nanamigopher-secrets
  namespace: nanamigopher
type: Opaque
stringData:
  OPENAI_API_KEY: "sk-xxx"
  DATABASE_URL: "sqlite:////data/nanami.db"
```

---

## 性能调优

### Go API Gateway 调优

#### 连接池配置

```go
// gateway/internal/config/config.go
type DBConfig struct {
    MaxOpenConns    int `mapstructure:"MAX_OPEN_CONNS"`    // 默认: 25
    MaxIdleConns    int `mapstructure:"MAX_IDLE_CONNS"`    // 默认: 25
    ConnMaxLifetime int `mapstructure:"CONN_MAX_LIFETIME"` // 默认: 300 (秒)
    ConnMaxIdleTime int `mapstructure:"CONN_MAX_IDLE_TIME"`// 默认: 90 (秒)
}
```

推荐配置（根据并发量调整）：

| 并发用户数 | MaxOpenConns | MaxIdleConns |
|-----------|-------------|-------------|
| < 100 | 25 | 10 |
| 100 - 500 | 50 | 25 |
| 500 - 1000 | 100 | 50 |
| > 1000 | 200 | 100 |

#### Gin 并发优化

```go
// 设置 Gin 引擎最大协程数
engine := gin.Default()
engine.SetMaxMultipartMemory(32 << 20) // 32 MB 上传限制

// 启用 Gzip 压缩
engine.Use(gzip(gzip.DefaultCompression))
```

#### Go Runtime 调优

```bash
# 设置 GOMAXPROCS 为 CPU 核心数
export GOMAXPROCS=$(nproc)

# 内存限制
export GOMEMLIMIT=512MiB
```

### Python Agent Core 调优

#### 并发配置

```python
# agent-core/pyproject.toml 或环境变量
# uvicorn 配置
HOST=0.0.0.0
PORT=8081
WORKERS=2  # 根据 CPU 核心数设置
THREADS=4  # 每个 worker 的线程数
```

#### ChromaDB 性能优化

```yaml
# ChromaDB 配置
ANONYMIZED_TELEMETRY: "false"
# 增加内存限制
CHROMA_SERVER_MEMORY_LIMIT: "2GB"
# 批量插入优化
CHROMA_SERVER_UPsert_BATCH_SIZE: "100"
```

#### 向量检索缓存

```python
# 在 agent-core 中启用结果缓存
CACHE_TTL = 300  # 缓存有效期 5 分钟
CACHE_MAX_SIZE = 1000  # 最多缓存 1000 条结果
```

### 前端性能优化

#### Nginx 静态资源缓存

```nginx
location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
    expires 30d;
    add_header Cache-Control "public, immutable";
    gzip on;
    gzip_types text/css application/javascript image/svg+xml;
}
```

#### Vite 构建优化

```javascript
// frontend/vite.config.js
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor': ['vue', 'vue-router', 'pinia'],
          'ui': ['element-plus'],
        },
      },
    },
  },
});
```

### 资源规划参考

| 部署规模 | CPU | 内存 | 磁盘 | 适用场景 |
|---------|-----|------|------|---------|
| 小型 | 2 核 | 4 GB | 20 GB | < 50 用户 |
| 中型 | 4 核 | 8 GB | 50 GB | 50 - 200 用户 |
| 大型 | 8 核 | 16 GB | 100 GB | 200 - 1000 用户 |
| 超大型 | 16 核 | 32 GB | 200 GB | > 1000 用户 |

---

## 安全加固

### HTTPS 配置

#### 强制 HTTPS

```nginx
server {
    listen 80;
    server_name nanamigopher.example.com;
    return 301 https://$server_name$request_uri;
}
```

#### TLS 最佳实践

```nginx
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers on;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 1d;
ssl_session_tickets off;
```

### CORS 配置

```go
// gateway/internal/middleware/cors.go
func CORSMiddleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        origin := c.GetHeader("Origin")

        // 白名单域名
        allowedOrigins := []string{
            "https://nanamigopher.example.com",
            "https://www.nanamigopher.example.com",
        }

        originAllowed := false
        for _, o := range allowedOrigins {
            if origin == o {
                originAllowed = true
                break
            }
        }

        if originAllowed {
            c.Header("Access-Control-Allow-Origin", origin)
            c.Header("Access-Control-Allow-Credentials", "true")
            c.Header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
            c.Header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        }

        if c.Request.Method == "OPTIONS" {
            c.AbortWithStatus(204)
            return
        }

        c.Next()
    }
}
```

### Content Security Policy (CSP)

```nginx
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self' wss://nanamigopher.example.com; frame-ancestors 'none'; base-uri 'self'; form-action 'self';" always;
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

### 速率限制

```go
// gateway/internal/middleware/rate_limit.go
func RateLimitMiddleware(rps float64, burst int) gin.HandlerFunc {
    limiter := ratelimit.New(ratelimit.Every(time.Duration(1/rps)*time.Second))
    burstLimiter := ratelimit.NewBurst(limiter, time.Second*10, burst)

    return func(c *gin.Context) {
        if !burstLimiter.Allow() {
            c.JSON(http.StatusTooManyRequests, gin.H{
                "error": "请求过于频繁，请稍后重试",
            })
            c.Abort()
            return
        }
        c.Next()
    }
}
```

### API 认证

```go
// 使用 JWT Token 认证
func AuthMiddleware() gin.HandlerFunc {
    return func(c *gin.Context) {
        token := c.GetHeader("Authorization")
        if token == "" {
            c.JSON(http.StatusUnauthorized, gin.H{"error": "缺少认证令牌"})
            c.Abort()
            return
        }

        claims, err := jwt.ParseWithClaims(token, &jwt.Claims{}, nil)
        if err != nil {
            c.JSON(http.StatusUnauthorized, gin.H{"error": "无效的认证令牌"})
            c.Abort()
            return
        }

        c.Set("user_id", claims.Subject)
        c.Next()
    }
}
```

### 输入验证

```go
// 防止 SQL 注入（使用 ORM 参数化查询）
// 防止 XSS（前端 CSP + 后端输出转义）
// 防止文件上传攻击
func ValidateUpload(c *gin.Context) {
    file, _ := c.FormFile("file")
    if file == nil {
        c.JSON(http.StatusBadRequest, gin.H{"error": "未上传文件"})
        c.Abort()
        return
    }

    // 检查文件大小（最大 50 MB）
    if file.Size > 50*1024*1024 {
        c.JSON(http.StatusBadRequest, gin.H{"error": "文件大小超过 50 MB"})
        c.Abort()
        return
    }

    // 检查文件类型
    allowedTypes := map[string]bool{
        "image/jpeg": true,
        "image/png":  true,
        "application/pdf": true,
        "text/plain": true,
    }

    if !allowedTypes[file.Header.Get("Content-Type")] {
        c.JSON(http.StatusBadRequest, gin.H{"error": "不支持的文件类型"})
        c.Abort()
        return
    }
}
```

---

## 监控告警

### Prometheus + Grafana 部署

#### docker-compose 监控栈

```yaml
# docker-compose.monitoring.yml
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.retention.time=30d'
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    volumes:
      - grafana-data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    restart: unless-stopped

  node-exporter:
    image: prom/node-exporter:latest
    ports:
      - "9100:9100"
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    command:
      - '--path.procfs=/host/proc'
      - '--path.sysfs=/host/sys'
    restart: unless-stopped

volumes:
  prometheus-data:
  grafana-data:
```

#### Prometheus 配置

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: "api-gateway"
    static_configs:
      - targets: ["api-gateway:8080"]
    metrics_path: "/metrics"

  - job_name: "agent-core"
    static_configs:
      - targets: ["agent-core:8081"]
    metrics_path: "/metrics"

  - job_name: "node-exporter"
    static_configs:
      - targets: ["node-exporter:9100"]

  - job_name: "prometheus"
    static_configs:
      - targets: ["localhost:9090"]
```

### 关键监控指标

#### API Gateway 指标

| 指标名称 | 类型 | 说明 | 告警阈值 |
|---------|------|------|---------|
| `http_request_duration_seconds` | Histogram | 请求延迟 P95 | > 2s |
| `http_requests_total` | Counter | 请求总数 | - |
| `http_request_errors_total` | Counter | 错误请求数 | > 5% |
| `active_connections` | Gauge | 活跃连接数 | > 10000 |
| `go_goroutines` | Gauge | Goroutine 数量 | > 10000 |
| `go_memstats_alloc_bytes` | Gauge | 内存分配量 | > 512MB |

#### Agent Core 指标

| 指标名称 | 类型 | 说明 | 告警阈值 |
|---------|------|------|---------|
| `agent_response_time_seconds` | Histogram | Agent 响应时间 | > 30s |
| `agent_requests_total` | Counter | 请求总数 | - |
| `vector_search_latency` | Histogram | 向量检索延迟 | > 1s |
| `model_api_latency` | Histogram | 模型 API 延迟 | > 10s |
| `queue_depth` | Gauge | 任务队列深度 | > 100 |

#### 系统指标

| 指标名称 | 来源 | 告警阈值 |
|---------|------|---------|
| CPU 使用率 | node-exporter | > 80% |
| 内存使用率 | node-exporter | > 85% |
| 磁盘使用率 | node-exporter | > 90% |
| 网络 I/O | node-exporter | 异常峰值 |

### Grafana Dashboard 导入

```bash
# 导入预配置的 Dashboard
curl -X POST http://admin:${GRAFANA_PASSWORD}@localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -d @monitoring/grafana/dashboards/nanamigopher.json
```

### 告警规则

```yaml
# monitoring/prometheus/alerts.yml
groups:
  - name: nanamigopher-alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_request_errors_total[5m]) / rate(http_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "错误率超过 5%"
          description: "过去 5 分钟内错误率为 {{ $value | humanizePercentage }}"

      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "P95 延迟超过 2 秒"

      - alert: ServiceDown
        expr: up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "{{ $labels.instance }} 服务宕机"

      - alert: HighMemoryUsage
        expr: process_resident_memory_bytes / 1024 / 1024 > 512
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "内存使用超过 512 MB"
```

### 告警通知集成

支持的通知渠道：

- **Email**: SMTP 配置
- **Slack**: Slack Incoming Webhook
- **Webhook**: 自定义 Webhook（可对接钉钉、企业微信等）

```yaml
# Prometheus Alertmanager 配置
alerting:
  alertmanagers:
    - static_configs:
        - targets: ["alertmanager:9093"]

rule_files:
  - "alerts.yml"

notification_routes:
  - receiver: "email-notifications"
    group_wait: 30s
    group_interval: 5m
    repeat_interval: 4h
    matchers:
      - severity =~ "warning|critical"

receivers:
  - name: "email-notifications"
    email_configs:
      - to: "admin@example.com"
        from: "alerts@example.com"
        smarthost: "smtp.example.com:587"
        auth_username: "alerts@example.com"
        auth_password: "${SMTP_PASSWORD}"
```

---

## 故障排查 Checklist

### 服务启动失败

- [ ] 检查端口是否被占用：`netstat -tlnp \| grep -E '8080|8081|8321'`
- [ ] 检查 Docker 容器状态：`docker compose ps`
- [ ] 查看容器日志：`docker compose logs -f <service>`
- [ ] 检查环境变量是否正确配置
- [ ] 确认数据库连接正常
- [ ] 检查磁盘空间：`df -h`

### API Gateway 无法访问

- [ ] 确认服务正在运行：`curl http://localhost:8080/health`
- [ ] 检查 Agent Core 连接：确认 `AGENT_CORE_URL` 配置正确
- [ ] 检查网络防火墙规则
- [ ] 检查反向代理配置（如使用 Nginx）
- [ ] 查看 API Gateway 日志中的错误信息
- [ ] 确认 JWT 密钥配置正确

### Agent Core 响应缓慢

- [ ] 检查 GPU/CPU 使用情况
- [ ] 查看向量检索延迟指标
- [ ] 检查模型 API 调用是否正常
- [ ] 确认 ChromaDB 连接正常
- [ ] 检查任务队列是否有积压
- [ ] 查看 Python 进程内存占用

### 数据库问题

- [ ] SQLite 文件是否存在且有读写权限
- [ ] ChromaDB 数据目录是否已满
- [ ] 数据库连接数是否达到上限
- [ ] 检查数据库备份是否最新
- [ ] 尝试重启 ChromaDB 服务

### 前端加载失败

- [ ] 检查 Nginx 静态文件服务是否正常
- [ ] 确认 API Gateway 地址配置正确
- [ ] 检查浏览器控制台是否有 CORS 错误
- [ ] 确认 WebSocket 连接是否正常
- [ ] 检查 CDN 缓存是否需要刷新

### 安全事件

- [ ] 检查异常登录尝试
- [ ] 审查 API 访问日志
- [ ] 确认 SSL 证书是否过期
- [ ] 检查是否有未授权的 API 调用
- [ ] 验证输入验证和速率限制是否生效

### 数据丢失/损坏

- [ ] 从最近的备份恢复数据
- [ ] 检查 SQLite 数据库完整性：`sqlite3 nanami.db "PRAGMA integrity_check;"`
- [ ] 检查 ChromaDB 集合数据完整性
- [ ] 验证文件存储目录完整性
- [ ] 联系技术支持获取帮助

### 性能问题

- [ ] 检查系统资源利用率（CPU、内存、磁盘、网络）
- [ ] 分析慢查询日志
- [ ] 检查连接池配置是否合理
- [ ] 评估是否需要水平扩展
- [ ] 审查缓存命中率

---

## 附录：部署命令速查

```bash
# ===== Docker Compose =====
docker compose up -d                    # 启动所有服务
docker compose down                     # 停止所有服务
docker compose logs -f api-gateway      # 查看日志
docker compose restart                  # 重启所有服务
docker compose pull && docker compose up -d  # 拉取最新镜像并重启

# ===== Kubernetes =====
kubectl apply -f k8s/                   # 部署所有资源
kubectl rollout status deployment/api-gateway  # 查看部署状态
kubectl logs -f deployment/api-gateway -n nanamigopher  # 查看日志
kubectl scale deployment api-gateway --replicas=3 -n nanamigopher  # 扩缩容
kubectl rollout undo deployment/api-gateway -n nanamigopher  # 回滚

# ===== 监控 =====
curl http://localhost:9090/targets      # Prometheus 目标状态
curl http://localhost:3001              # Grafana 仪表盘
```
