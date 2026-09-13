# 开发环境

> **版本**: v1.0  
> **日期**: 2026-07-21

---

## 1. 环境要求

### 1.1 系统要求

| 组件 | 最低版本 | 推荐版本 | 说明 |
|------|---------|---------|------|
| OS | macOS 12+ / Ubuntu 20.04+ / Windows 10+ | 最新稳定版 | 桌面端支持 |
| Go | 1.22+ | 1.23+ | API Gateway |
| Python | 3.11+ | 3.12+ | Agent Core |
| Node.js | 18+ | 22+ LTS | 前端构建 |
| npm/pnpm | 9+ | 10+ | 包管理 |
| Electron | 28+ | 30+ | 桌面容器 |
| SQLite | 3.35+ | 3.45+ | 结构化存储 |

### 1.2 可选依赖

| 组件 | 用途 | 安装方式 |
|------|------|---------|
| Ollama | 本地 LLM 推理 | `curl -fsSL https://ollama.ai/install.sh \| sh` |
| ChromaDB | 向量数据库（默认） | `uv add chromadb` |
| Qdrant | 向量数据库（备选） | Docker: `docker run qdrant/qdrant` |
| Playwright | 浏览器自动化 | `npx playwright install` |
| PaddleOCR | OCR 识别 | `uv add paddlepaddle paddleocr` |
| uv | Python 包管理器 | `pip install uv` 或 `curl -LsSf https://astral.sh/uv/install.sh | sh` |

---

## 2. 环境初始化

### 2.1 一键安装脚本

```bash
#!/bin/bash
# scripts/setup.sh

set -e

echo "=== NanamiGopher 环境初始化 ==="

# 1. 检查依赖
echo "[1/6] 检查依赖..."
command -v go >/dev/null 2>&1 || { echo "需要 Go 1.22+"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "需要 Python 3.11+"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "需要 Node.js 18+"; exit 1; }
command -v pnpm >/dev/null 2>&1 || { echo "需要 pnpm"; exit 1; }

# 2. 初始化 Go 项目
echo "[2/6] 初始化 Go 项目..."
cd nanamigopher
go mod tidy

# 3. 初始化 Python 环境
echo "[3/6] 初始化 Python 环境..."
uv venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows
uv sync --all-extras

# 4. 初始化前端
echo "[4/6] 初始化前端..."
cd web
pnpm install

# 5. 创建数据目录
echo "[5/6] 创建数据目录..."
mkdir -p ~/.nanamigopher/data
mkdir -p ~/.nanamigopher/logs
mkdir -p ~/.nanamigopher/skills

# 6. 复制默认配置
echo "[6/6] 复制默认配置..."
cp config/config.dev.yaml ~/.nanamigopher/config.yaml 2>/dev/null || true

echo "=== 环境初始化完成 ==="
echo ""
echo "下一步:"
echo "  cd web && pnpm dev          # 启动前端开发服务器"
echo "  go run cmd/nanamigopher/    # 启动 Go API Gateway"
echo "  cd python && uvicorn agent.main:app  # 启动 Agent Core (可选)"
```

### 2.2 手动安装步骤

```bash
# 1. 克隆仓库
git clone https://github.com/your-org/nanamigopher.git
cd nanamigopher

# 2. 安装 Go 依赖
go mod download
go mod tidy

# 3. 安装 Python 依赖
uv venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate    # Windows
uv sync --all-extras

# 4. 安装前端依赖
cd web
pnpm install
cd ..

# 5. 创建配置
mkdir -p ~/.nanamigopher
cp config/config.dev.yaml ~/.nanamigopher/config.yaml
```

---

## 3. 开发服务器

### 3.1 启动所有服务

```bash
#!/bin/bash
# scripts/dev.sh

# 终端 1: Go API Gateway
echo "Starting Go API Gateway on port 8080..."
go run cmd/nanamigopher/main.go

# 终端 2: Python Agent Core (gRPC)
echo "Starting Python Agent Core on port 8081..."
cd python
uvicorn agent.main:app --host 0.0.0.0 --port 8081 --reload

# 终端 3: 前端开发服务器
echo "Starting Vue 3 dev server on port 5173..."
cd web
pnpm dev
```

### 3.2 单个服务启动

```bash
# Go API Gateway
go run cmd/nanamigopher/main.go

# Python Agent Core (gRPC 模式)
cd python
python -m agent.main

# Python Agent Core (开发模式，自动重载)
cd python
watchmedo auto-restart --pattern "*.py" --recursive -- python -m agent.main

# 前端开发服务器
cd web
pnpm dev          # localhost:5173

# Electron 桌面应用
cd web
pnpm electron:dev
```

---

## 4. 环境变量

### 4.1 必需环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `NANAMIGOPHER_CONFIG` | 配置文件路径 | `~/.nanamigopher/config.yaml` |
| `NANAMIGOPHER_DATA_DIR` | 数据目录 | `~/.nanamigopher/data` |
| `NANAMIGOPHER_LOG_DIR` | 日志目录 | `~/.nanamigopher/logs` |

### 4.2 可选环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OLLAMA_HOST` | Ollama 服务地址 | `http://localhost:11434` |
| `OPENAI_API_KEY` | OpenAI API Key | (必填如果使用 OpenAI) |
| `ANTHROPIC_API_KEY` | Anthropic API Key | (必填如果使用 Claude) |
| `CHROMA_DB_URL` | ChromaDB 连接地址 | `http://localhost:8000` |
| `QDRANT_URL` | Qdrant 连接地址 | `http://localhost:6333` |

### 4.3 使用 .env 文件

```bash
# python/.env
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
OLLAMA_HOST=http://localhost:11434

# 在 Python 中加载
from dotenv import load_dotenv
load_dotenv()
```

---

## 5. IDE 配置

### 5.1 VS Code 推荐扩展

```json
// .vscode/extensions.json
{
  "recommendations": [
    "golang.go",
    "ms-python.python",
    "ms-python.vscode-pylance",
    "Vue.volar",
    "esbenp.prettier-vscode",
    "dbaeumer.vscode-eslint",
    "eamodio.gitlens"
  ]
}
```

### 5.2 VS Code 工作区配置

```json
// .vscode/settings.json
{
  "go.toolsManagement.autoUpdate": true,
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.testing.pytestEnabled": true,
  "python.linting.ruffEnabled": true,
  "[python]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "charliermarsh.ruff"
  },
  "[go]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "golang.go"
  },
  "[vue]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "files.exclude": {
    "**/node_modules": true,
    "**/.venv": true,
    "**/__pycache__": true
  }
}
```

### 5.3 VS Code 任务配置

```json
// .vscode/tasks.json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Go: Build",
      "type": "shell",
      "command": "go",
      "args": ["build", "./..."],
      "group": { "kind": "build", "isDefault": true }
    },
    {
      "label": "Python: Test",
      "type": "shell",
      "command": "pytest",
      "args": ["python/tests/", "-v"],
      "problemMatcher": []
    },
    {
      "label": "Vue: Dev",
      "type": "shell",
      "command": "pnpm",
      "args": ["dev"],
      "cwd": "${workspaceFolder}/web",
      "presentation": { "reveal": "always", "panel": "new" }
    },
    {
      "label": "Full: Start All",
      "type": "shell",
      "command": "./scripts/dev.sh",
      "presentation": { "reveal": "always", "panel": "new" }
    }
  ]
}
```

---

## 6. 调试配置

### 6.1 Go 调试

```json
// .vscode/launch.json (Go)
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Launch Go API Gateway",
      "type": "go",
      "request": "launch",
      "mode": "debug",
      "program": "${workspaceFolder}/cmd/nanamigopher/main.go"
    }
  ]
}
```

### 6.2 Python 调试

```json
// .vscode/launch.json (Python)
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Launch Agent Core",
      "type": "python",
      "request": "launch",
      "module": "agent.main",
      "console": "integratedTerminal",
      "env": {
        "PYTHONPATH": "${workspaceFolder}/python"
      }
    },
    {
      "name": "Pytest: Current File",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["${file}", "-v"],
      "console": "integratedTerminal"
    }
  ]
}
```

### 6.3 Chrome DevTools（Electron）

```bash
# 启用 Electron 开发者工具
# web/electron/main.ts
app.whenReady().then(() => {
  if (process.env.NODE_ENV === 'development') {
    win.webContents.openDevTools()
  }
})
```

---

## 7. 常见问题排查

### 7.1 Go 依赖问题

```bash
# 清理并重新下载依赖
go clean -modcache
go mod tidy
go mod download

# 检查过时依赖
go list -m -u all
```

### 7.2 Python 虚拟环境问题

```bash
# 重建虚拟环境
rm -rf .venv
uv venv
source .venv/bin/activate
uv sync --all-extras

# 检查 Python 版本和已安装的包
python3 --version
uv pip list
```

### 7.3 前端构建问题

```bash
# 清理 node_modules 并重装
rm -rf node_modules pnpm-lock.yaml
pnpm install

# 清理 Vite 缓存
rm -rf .vite
pnpm dev
```

### 7.4 端口冲突

```bash
# 查看占用端口的进程
lsof -i :8080    # Go API Gateway
lsof -i :8081    # Python Agent Core
lsof -i :5173    # Vue Dev Server

# 杀死进程
kill -9 <PID>
```
