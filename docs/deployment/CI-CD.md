# NanamiGopher 持续集成/持续部署 (CI-CD)

本文档介绍 NanamiGopher 的 CI/CD 流水线配置，涵盖代码检查、测试、构建、发布和回滚全流程。

## 流水线概览

```
┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌──────────────┐    ┌─────────────┐
│  代码提交     │ -> │  代码检查     │ -> │   测试       │ -> │   构建打包    │ -> │   发布      │
│  (Push/PR)   │    │  (Lint/Vet)  │    │ (Unit/Int/E2E)│    │ (Build/Pack) │    │ (Release)   │
└─────────────┘    └──────────────┘    └─────────────┘    └──────────────┘    └─────────────┘
```

## GitHub Actions 配置

### 主流水线：`.github/workflows/ci-cd.yml`

```yaml
name: NanamiGopher CI/CD

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  GO_VERSION: "1.22"
  PYTHON_VERSION: "3.11"
  NODE_VERSION: "20"
  PNPM_VERSION: "9"

jobs:
  # ============================================================
  # 阶段一：代码检查
  # ============================================================
  lint:
    name: Code Linting
    runs-on: ubuntu-latest
    strategy:
      matrix:
        component: [gateway, agent-core, frontend]
    steps:
      - uses: actions/checkout@v4

      - name: Set up Go ${{ env.GO_VERSION }}
        if: matrix.component == 'gateway'
        uses: actions/setup-go@v5
        with:
          go-version: ${{ env.GO_VERSION }}

      - name: Set up Python ${{ env.PYTHON_VERSION }}
        if: matrix.component == 'agent-core'
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Set up Node.js ${{ env.NODE_VERSION }}
        if: matrix.component == 'frontend'
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: pnpm

      - name: Setup pnpm
        if: matrix.component == 'frontend'
        uses: pnpm/action-setup@v4
        with:
          version: ${{ env.PNPM_VERSION }}

      - name: Run Go vet & staticcheck
        if: matrix.component == 'gateway'
        run: |
          cd gateway
          go vet ./...
          go install honnef.co/go/tools/cmd/staticcheck@latest
          staticcheck ./...

      - name: Run Python lint (ruff + mypy)
        if: matrix.component == 'agent-core'
        run: |
          cd agent-core
          pip install ruff mypy
          ruff check .
          mypy .

      - name: Run ESLint & type check
        if: matrix.component == 'frontend'
        run: |
          cd frontend
          pnpm install --frozen-lockfile
          pnpm run lint
          pnpm run typecheck

  # ============================================================
  # 阶段二：测试
  # ============================================================
  test:
    name: Run Tests
    runs-on: ubuntu-latest
    needs: lint
    services:
      chromadb:
        image: chromadb/chroma:0.5.0
        ports:
          - 8321:8321
    steps:
      - uses: actions/checkout@v4

      - name: Set up Go ${{ env.GO_VERSION }}
        uses: actions/setup-go@v5
        with:
          go-version: ${{ env.GO_VERSION }}

      - name: Set up Python ${{ env.PYTHON_VERSION }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Set up Node.js ${{ env.NODE_VERSION }}
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: pnpm

      - name: Setup pnpm
        uses: pnpm/action-setup@v4
        with:
          version: ${{ env.PNPM_VERSION }}

      # --- Go 单元测试 ---
      - name: Go unit tests
        run: |
          cd gateway
          go test -v -race -coverprofile=coverage.out -covermode=atomic ./...
        env:
          AGENT_CORE_URL: http://localhost:8081

      # --- Python 单元测试 ---
      - name: Python unit tests
        run: |
          cd python
          uv sync --all-extras
          uv run pytest -v --cov=. --cov-report=xml --cov-report=html
        env:
          CHROMADB_HOST: localhost
          CHROMADB_PORT: 8321

      # --- 前端单元测试 ---
      - name: Frontend unit tests
        run: |
          cd frontend
          pnpm install --frozen-lockfile
          pnpm run test:unit

      # --- 集成测试 ---
      - name: Integration tests
        run: |
          cd gateway
          go test -tags=integration -v ./integration/...
        env:
          AGENT_CORE_URL: http://localhost:8081
          CHROMADB_HOST: localhost
          CHROMADB_PORT: 8321

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        with:
          files: ./gateway/coverage.out,./agent-core/coverage.xml
          fail_ci_if_error: false

  # ============================================================
  # 阶段三：构建 Docker 镜像
  # ============================================================
  build-docker:
    name: Build Docker Images
    runs-on: ubuntu-latest
    needs: test
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push gateway image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./Dockerfile.gateway
          push: true
          tags: |
            ghcr.io/${{ github.repository }}/gateway:${{ github.sha }}
            ghcr.io/${{ github.repository }}/gateway:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Build and push agent-core image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./Dockerfile.agent
          push: true
          tags: |
            ghcr.io/${{ github.repository }}/agent-core:${{ github.sha }}
            ghcr.io/${{ github.repository }}/agent-core:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Build and push frontend image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: ./Dockerfile.frontend
          push: true
          tags: |
            ghcr.io/${{ github.repository }}/frontend:${{ github.sha }}
            ghcr.io/${{ github.repository }}/frontend:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max

  # ============================================================
  # 阶段四：Electron 桌面端打包
  # ============================================================
  electron-build:
    name: Build Desktop Apps
    runs-on: ${{ matrix.os }}
    needs: test
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest-xlarge, windows-latest]
      fail-fast: false
    steps:
      - uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: pnpm

      - name: Setup pnpm
        uses: pnpm/action-setup@v4
        with:
          version: ${{ env.PNPM_VERSION }}

      - name: Install dependencies
        run: pnpm install --frozen-lockfile
        working-directory: ./electron

      - name: Build Electron app
        run: pnpm run build
        working-directory: ./electron
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: nanamigopher-${{ matrix.os }}
          path: |
            electron/dist/*
          retention-days: 30

  # ============================================================
  # 阶段五：发布（仅 main 分支且手动触发）
  # ============================================================
  release:
    name: Semantic Release
    runs-on: ubuntu-latest
    needs: [build-docker, electron-build]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    permissions:
      contents: write
      packages: write
      issues: write
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}

      - name: Setup pnpm
        uses: pnpm/action-setup@v4
        with:
          version: ${{ env.PNPM_VERSION }}

      - name: Install dependencies
        run: pnpm install --frozen-lockfile

      - name: Run semantic-release
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          NPM_TOKEN: ${{ secrets.NPM_TOKEN }}
        run: npx semantic-release
```

## 代码检查配置

### Go 代码检查

```toml
# .golangci.yml
linters:
  enable:
    - govet
    - staticcheck
    - errcheck
    - gosimple
    - revive
    - unused

run:
  timeout: 5m

issues:
  exclude-rules:
    - path: _test\.go
      linters:
        - revive
```

### Python 代码检查

```ini
# pyproject.toml (ruff 配置)
[tool.ruff]
line-length = 120
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "A", "C4", "SIM"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
```

### 前端代码检查

```json
// frontend/eslint.config.js
import eslint from "@eslint/js";
import tseslint from "typescript-eslint";
import vuePlugin from "eslint-plugin-vue";

export default tseslint.config(
  eslint.configs.recommended,
  ...tseslint.configs.recommended,
  vuePlugin.configs["flat/recommended"],
  {
    rules: {
      "no-console": process.env.NODE_ENV === "production" ? "warn" : "off",
      "no-debugger": process.env.NODE_ENV === "production" ? "warn" : "off",
    },
  }
);
```

## 测试策略

### 测试分层

```
测试金字塔
    /\
   /  \       E2E 测试 (少量)
  /----\     集成测试 (中等数量)
 /======\    单元测试 (大量)
```

| 层级 | 框架 | 位置 | 覆盖率目标 |
|------|------|------|-----------|
| 单元测试 | Go testing / pytest / Vitest | 各组件内 | > 80% |
| 集成测试 | Go testing (tags/integration) | integration/ | > 60% |
| E2E 测试 | Playwright | electron/tests/e2e/ | 核心流程 |

### 关键测试用例

**Go API Gateway:**
- 健康检查端点返回 200
- 请求转发到 Agent Core 成功
- WebSocket 连接建立和消息推送
- 错误处理和超时场景

**Python Agent Core:**
- 向量检索正确性
- 模型调用和响应处理
- 文件存储读写
- 并发请求处理

**Vue 前端:**
- 组件渲染和交互
- API 调用 Mock
- 路由导航
- 状态管理

**Electron E2E:**
- 应用启动和关闭
- 主要功能流程
- 跨进程通信

## 构建配置

### Electron 构建参数

```javascript
// electron/build.config.js
module.exports = {
  appId: "com.nanami.nanamigopher",
  productName: "NanamiGopher",
  files: ["dist/**/*", "node_modules/**/*"],
  directories: {
    output: "release",
  },
  mac: {
    target: [
      { target: "dmg", arch: ["x64", "arm64"] },
      { target: "zip", arch: ["x64", "arm64"] },
    ],
    category: "public.app-category.productivity",
  },
  win: {
    target: [
      { target: "nsis", arch: "x64" },
      { target: "zip", arch: "x64" },
    ],
  },
  linux: {
    target: [
      { target: "AppImage", arch: "x64" },
      { target: "deb", arch: "x64" },
    ],
    category: "Utility",
  },
};
```

### Docker 镜像标签策略

| 分支 | 镜像标签 | 示例 |
|------|---------|------|
| `main` | `{sha}` + `latest` | `ghcr.io/org/nanamigopher/gateway:abc1234` |
| `develop` | `{branch}-{sha}` | `ghcr.io/org/nanamigopher/gateway:develop-abc1234` |
| Tag (v1.0.0) | `{tag}` + `latest` | `ghcr.io/org/nanamigopher/gateway:v1.0.0` |

## 发布流程

### Semantic Release 配置

```javascript
// electron/semantic-release.config.js
module.exports = {
  branches: ["main"],
  plugins: [
    "@semantic-release/commit-analyzer",
    "@semantic-release/release-notes-generator",
    "@semantic-release/github",
    [
      "@semantic-release/exec",
      {
        publishCmd:
          "GOOS=linux go build -ldflags='-w -s' -o release/gateway ./cmd/gateway && cd frontend && pnpm build && cd ../electron && pnpm run build",
      },
    ],
  ],
  repositoryUrl: "https://github.com/nanami-project/nanamigopher",
};
```

### 版本号规则

遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

| Commit 前缀 | 版本变更 | 示例 |
|-------------|---------|------|
| `feat:` | 次版本 (minor) | v1.1.0 |
| `fix:` | 补丁版本 (patch) | v1.0.1 |
| `perf:` | 补丁版本 (patch) | v1.0.2 |
| `refactor:` | 无版本变更 | - |
| `chore:` | 无版本变更 | - |
| `BREAKING CHANGE:` | 主版本 (major) | v2.0.0 |

### GitHub Releases 自动生成

Semantic Release 会自动：
1. 根据 commit 历史计算新版本号
2. 生成 Release Notes
3. 创建 Git Tag
4. 上传构建产物到 GitHub Releases
5. 发布 Docker 镜像到 GHCR

## 回滚策略

### Docker 镜像回滚

当新版本出现问题时，快速回滚到上一个稳定版本：

```bash
# 查看已有镜像标签
docker images | grep nanamigopher

# 回滚到上一个已知稳定的标签
docker compose pull gateway:v1.2.3 agent-core:v1.2.3 frontend:v1.2.3
docker compose up -d --force-recreate

# 或通过 k8s 回滚
kubectl rollout undo deployment/nanamigopher-gateway
kubectl rollout undo deployment/nanamigopher-agent-core
```

### Electron 桌面端回滚

1. 在 GitHub Releases 中找到上一个稳定版本
2. 下载对应平台的安装包
3. 通知用户手动更新

### 自动化回滚

在 CI/CD 流水线中配置自动回滚条件：

```yaml
# 在 GitHub Actions 中添加手动审批步骤
release:
  needs: test
  if: github.ref == 'refs/heads/main'
  environment:
    name: production
    # 需要人工审批后才能部署到生产
```

### 回滚 Checklist

- [ ] 确认新版本的问题和影响范围
- [ ] 确定需要回滚的服务（gateway / agent-core / frontend）
- [ ] 获取上一个稳定版本的镜像标签
- [ ] 执行回滚命令
- [ ] 验证回滚后的服务状态
- [ ] 检查日志确认无异常
- [ ] 通知相关团队成员
- [ ] 记录回滚原因和处理过程

## 所需 GitHub Secrets

| Secret 名称 | 说明 |
|------------|------|
| `GITHUB_TOKEN` | 自动配置，用于 GitHub API 和包注册 |
| `NPM_TOKEN` | 用于发布 npm 包（如有） |
| `OPENAI_API_KEY` | Agent Core 使用的 API 密钥（测试环境） |
| `DOCKER_USERNAME` | Docker Hub 用户名（如使用 Docker Hub） |
| `DOCKER_PASSWORD` | Docker Hub 密码 |

## 监控指标

CI/CD 流水线应关注以下指标：

| 指标 | 说明 | 告警阈值 |
|------|------|---------|
| 构建时长 | 从提交到完成的总时间 | > 30 分钟 |
| 测试通过率 | 所有测试的通过率 | < 100% |
| 代码覆盖率 | 新增代码的覆盖率 | < 80% |
| 镜像大小 | Docker 镜像大小 | gateway > 200MB, agent-core > 500MB |
| 发布频率 | 每天/每周发布次数 | 无固定标准 |
