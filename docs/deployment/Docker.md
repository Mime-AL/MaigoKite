# NanamiGopher Docker 容器化部署

本文档介绍如何使用 Docker 和 Docker Compose 将 NanamiGopher 部署到容器环境中。

## 概述

NanamiGopher 采用多服务架构，每个服务都有独立的容器镜像：

| 服务 | 语言 | 端口 | 说明 |
|------|------|------|------|
| api-gateway | Go (Gin) | 8080 | HTTP API 网关 |
| agent-core | Python | 8081 | Agent 核心逻辑 |
| frontend | Vue 3 + Vite | 3000 (开发) / Nginx (生产) | Web 前端 |
| chromadb | Python (ChromaDB) | 8321 | 向量数据库 |
| sqlite-data | - | - | SQLite 数据持久化 |

## 多阶段构建策略

### 1. Go API Gateway 镜像

```dockerfile
# Dockerfile.gateway
FROM golang:1.22-alpine AS builder

WORKDIR /app

# 缓存依赖
COPY go.mod go.sum ./
RUN go mod download

# 构建
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o /nanami-gateway ./cmd/gateway

# 最终镜像
FROM alpine:3.19
RUN apk --no-cache add ca-certificates tzdata
WORKDIR /root/

COPY --from=builder /nanami-gateway .
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD wget -qO- http://localhost:8080/health || exit 1

CMD ["./nanami-gateway"]
```

关键点：
- 使用 `alpine` 最小化镜像体积
- `CGO_ENABLED=0` 静态编译，避免依赖问题
- `-ldflags="-w -s"` 去除调试信息，减小体积
- 内置 `HEALTHCHECK` 指令

### 2. Python Agent Core 镜像

```dockerfile
# Dockerfile.agent
FROM python:3.11-slim AS builder

WORKDIR /app

# 安装 uv（更快的 Python 包管理器）
RUN pip install --no-cache-dir uv

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# 使用 uv 安装依赖（基于 pyproject.toml）
COPY pyproject.toml ./
RUN uv sync --frozen --no-dev --prefix=/install

# 最终镜像
FROM python:3.11-slim
WORKDIR /app

# 从 builder 阶段复制已安装的包
COPY --from=builder /install /usr/local

# 复制源代码
COPY . .

EXPOSE 8081

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8081/health')" || exit 1

CMD ["python", "-m", "agent_core"]
```

关键点：
- 分离构建阶段和运行阶段，避免在最终镜像中保留编译工具链
- 使用 `--prefix` 将依赖安装到独立目录后复制到最终镜像
- `slim` 基础镜像比 `alpine` 更适合 Python，减少兼容性问题

### 3. Vue 3 + Vite 前端镜像

```dockerfile
# Dockerfile.frontend
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile

COPY . .
RUN pnpm build

# 生产镜像
FROM nginx:1.25-alpine
COPY --from=builder /app/dist /usr/share/nginx/html

# 自定义 Nginx 配置
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

关键点：
- 利用 Nginx 作为静态文件服务器
- 需要配合 `nginx.conf` 处理 SPA 路由回退

## docker-compose.yml 完整配置

```yaml
# docker-compose.yml
version: "3.9"

services:
  api-gateway:
    build:
      context: .
      dockerfile: Dockerfile.gateway
    ports:
      - "8080:8080"
    environment:
      - AGENT_CORE_URL=http://agent-core:8081
      - DATABASE_URL=sqlite:////data/nanami.db
      - CHROMADB_URL=http://chromadb:8321
      - LOG_LEVEL=info
    volumes:
      - sqlite-data:/data
    depends_on:
      agent-core:
        condition: service_healthy
      chromadb:
        condition: service_healthy
    restart: on-failure
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost:8080/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s

  agent-core:
    build:
      context: ./agent-core
      dockerfile: ../../Dockerfile.agent
    expose:
      - "8081"
    environment:
      - PYTHONUNBUFFERED=1
      - MODEL_PROVIDER=openai
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
      - VECTOR_STORE=chroma
      - CHROMADB_HOST=chromadb
      - CHROMADB_PORT=8321
    depends_on:
      chromadb:
        condition: service_healthy
    restart: on-failure
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8081/health')"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 15s

  chromadb:
    image: chromadb/chroma:0.5.0
    expose:
      - "8321"
    volumes:
      - chroma-data:/chroma/chroma
    environment:
      - ANONYMIZED_TELEMETRY=false
      - PERSIST_DIR=/chroma/chroma
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8321/api/v1/heartbeat"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s

  frontend:
    build:
      context: ./frontend
      dockerfile: ../../Dockerfile.frontend
    ports:
      - "80:80"
    depends_on:
      - api-gateway
    restart: unless-stopped

volumes:
  sqlite-data:
    driver: local
  chroma-data:
    driver: local
```

## 环境变量配置

### 运行时环境变量

| 变量名 | 说明 | 默认值 | 示例 |
|--------|------|--------|------|
| `AGENT_CORE_URL` | Agent Core 地址 | `http://localhost:8081` | `http://agent-core:8081` |
| `DATABASE_URL` | SQLite 数据库路径 | `sqlite:///nanami.db` | `sqlite:////data/nanami.db` |
| `CHROMADB_URL` | ChromaDB 地址 | `http://localhost:8321` | `http://chromadb:8321` |
| `LOG_LEVEL` | 日志级别 | `info` | `debug` / `warn` / `error` |
| `MODEL_PROVIDER` | AI 模型提供商 | `openai` | `anthropic` / `ollama` |
| `OPENAI_API_KEY` | OpenAI API 密钥 | 无 | 需手动设置 |
| `PYTHONUNBUFFERED` | Python 输出刷新 | `0` | `1` |
| `VECTOR_STORE` | 向量存储后端 | `chroma` | `chroma` / `faiss` |
| `CHROMADB_HOST` | ChromaDB 主机 | `localhost` | `chromadb` |
| `CHROMADB_PORT` | ChromaDB 端口 | `8321` | `8321` |

### 敏感信息处理

建议使用 `.env` 文件管理敏感信息，并将其加入 `.gitignore`：

```bash
# .env（不要提交到版本控制）
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
```

在 `docker-compose.yml` 中引用：

```yaml
environment:
  - OPENAI_API_KEY=${OPENAI_API_KEY}
```

## 数据卷挂载

### SQLite 数据持久化

```yaml
volumes:
  - sqlite-data:/data
```

```yaml
# docker-compose.yml 顶部声明
volumes:
  sqlite-data:
    driver: local
```

SQLite 数据库文件位于容器内的 `/data/nanami.db`，映射到 Docker 卷 `sqlite-data`。

### ChromaDB 向量数据持久化

```yaml
volumes:
  - chroma-data:/chroma/chroma
```

ChromaDB 的持久化目录默认为 `/chroma/chroma`，映射到 Docker 卷 `chroma-data`。

### 查看数据卷

```bash
# 列出所有卷
docker volume ls

# 查看卷详情
docker volume inspect nanamigopher_sqlite-data
docker volume inspect nanamigopher_chroma-data

# 备份 SQLite 数据
docker run --rm \
  -v nanamigopher_sqlite-data:/data \
  -v $(pwd)/backup:/backup \
  alpine cp /data/nanami.db /backup/nanami-backup-$(date +%Y%m%d).db

# 备份 ChromaDB 数据
docker run --rm \
  -v nanamigopher_chroma-data:/data \
  -v $(pwd)/backup:/backup \
  alpine cp -r /data /backup/chroma-backup-$(date +%Y%m%d)
```

## 健康检查与重启策略

### 健康检查

各服务均配置了 `healthcheck`，检查间隔为 30 秒，超时 5 秒，重试 3 次。

- **api-gateway**: 通过 HTTP GET `/health` 端点检查
- **agent-core**: 通过 Python urllib 检查 `/health` 端点
- **chromadb**: 通过 curl 检查 `/api/v1/heartbeat` 端点

### 重启策略

| 服务 | 策略 | 说明 |
|------|------|------|
| api-gateway | `on-failure` | 仅在非零退出码时重启 |
| agent-core | `on-failure` | 仅在非零退出码时重启 |
| chromadb | `unless-stopped` | 除非手动停止，否则始终重启 |
| frontend | `unless-stopped` | 除非手动停止，否则始终重启 |

### 启动顺序控制

使用 `depends_on` + `condition: service_healthy` 确保服务按正确顺序启动：

```yaml
depends_on:
  agent-core:
    condition: service_healthy
  chromadb:
    condition: service_healthy
```

## 常用命令

```bash
# 构建并启动所有服务
docker compose up -d --build

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f api-gateway
docker compose logs -f agent-core
docker compose logs -f chromadb

# 停止所有服务
docker compose down

# 停止并删除数据卷（谨慎使用）
docker compose down -v

# 重新构建并启动
docker compose up -d --force-recreate --build

# 进入运行中的容器
docker compose exec api-gateway sh
docker compose exec agent-core bash
```

## 开发环境优化

在开发环境中，可以使用 `docker-compose.dev.yml` 覆盖配置，启用热重载：

```yaml
# docker-compose.dev.yml
version: "3.9"
services:
  api-gateway:
    build:
      context: .
      dockerfile: Dockerfile.gateway.dev
    volumes:
      - ./gateway:/app
    command: ["go", "run", "./cmd/gateway"]

  agent-core:
    build:
      context: ./agent-core
      dockerfile: Dockerfile.agent.dev
    volumes:
      - ./agent-core:/app
    command: ["python", "-m", "uvicorn", "agent_core.main:app", "--reload", "--host", "0.0.0.0", "--port", "8081"]

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.frontend.dev
    volumes:
      - ./frontend:/app
    command: ["pnpm", "dev"]
```

## 网络配置

如果需要外部访问，确保防火墙开放相应端口：

```bash
# 开放端口
sudo ufw allow 80/tcp       # 前端
sudo ufw allow 8080/tcp     # API Gateway
sudo ufw allow 8081/tcp     # Agent Core（内部使用，不建议对外暴露）
```

## 资源限制

建议在生产环境中为各容器设置资源限制：

```yaml
services:
  api-gateway:
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 512M
        reservations:
          cpus: "0.25"
          memory: 128M

  agent-core:
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 2G
        reservations:
          cpus: "0.5"
          memory: 512M

  chromadb:
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 1G
        reservations:
          cpus: "0.25"
          memory: 256M
```
