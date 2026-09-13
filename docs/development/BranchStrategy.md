# 分支策略

> **版本**: v1.0  
> **日期**: 2026-07-21

---

## 1. 策略概述

本项目采用 **GitHub Flow** 简化分支模型，适合单人全栈开发场景。

核心原则：
- `main` 分支始终可部署
- 功能开发在独立分支上进行
- 通过 PR 合并到 main
- 分支生命周期短（不超过 2 周）

---

## 2. 分支类型

### 2.1 永久分支

| 分支 | 说明 |
|------|------|
| `main` | 生产分支，始终可部署，受保护 |

### 2.2 临时分支

| 类型 | 前缀 | 来源 | 目标 | 示例 |
|------|------|------|------|------|
| 功能分支 | `feature/` | `main` | `main` | `feature/tool-system` |
| 修复分支 | `fix/` | `main` | `main` | `fix/injection-bypass` |
| 重构分支 | `refactor/` | `main` | `main` | `refactor/memory-split` |
| 热修复分支 | `hotfix/` | `main` | `main` | `hotfix/critical-leak` |
| 发布分支 | `release/` | `main` | `main` | `release/0.1.0` |

---

## 3. 工作流

### 3.1 功能开发流程

```bash
# 1. 从 main 创建功能分支
git checkout main
git pull origin main
git checkout -b feature/tool-system

# 2. 开发并提交
git add .
git commit -m "feat(tools): add file_read native tool"

# 3. 同步 main 最新变更
git fetch origin
git rebase origin/main

# 4. 推送到远程
git push -u origin feature/tool-system

# 5. 创建 PR 并申请审查
#    gh pr create --title "feat(tools): add file_read native tool" \
#                 --body "..."

# 6. PR 合并后删除分支
git branch -d feature/tool-system
```

### 3.2 热修复流程

```bash
# 1. 从 main 创建热修复分支
git checkout main
git pull origin main
git checkout -b hotfix/critical-memory-leak

# 2. 快速修复并提交
git add .
git commit -m "fix(memory): prevent memory leak in short_term"

# 3. 推送并创建紧急 PR
git push -u origin hotfix/critical-memory-leak
gh pr create --label hotfix

# 4. 合并后立即部署
```

### 3.3 发布流程

```bash
# 1. 从 main 创建发布分支
git checkout main
git pull origin main
git checkout -b release/0.1.0

# 2. 更新版本号、Changelog
#    运行完整测试套件
./scripts/run_tests.sh

# 3. 创建版本标签
git tag -a v0.1.0 -m "Release v0.1.0: Initial MVP"

# 4. 推送标签
git push origin main
git push origin v0.1.0

# 5. 合并并删除分支
git checkout main
git merge --no-ff release/0.1.0
git branch -d release/0.1.0
```

---

## 4. 分支保护规则

### 4.1 main 分支保护

- 禁止直接推送到 main
- PR 合并前必须通过 CI 检查
- PR 至少需要一人审查（单人开发可自行审查）
- 不允许 force push

### 4.2 CI 检查清单

```yaml
checks:
  - lint:        # 代码风格检查
      go:  "gofmt -l ."
      python: "ruff check ."
      vue:    "eslint src/"
  - test:        # 测试通过
      go:  "go test ./..."
      python: "pytest tests/"
  - build:       # 构建成功
      vue:  "vite build"
  - security:    # 安全扫描
      python: "pip audit"
      go:   "govulncheck ./..."
```

---

## 5. 合并策略

| 场景 | 合并策略 | 说明 |
|------|---------|------|
| 功能分支 | Squash Merge | 将所有提交压缩为一个，保持 main 整洁 |
| 修复分支 | Merge Commit | 保留完整提交历史 |
| 热修复分支 | Fast-Forward | 紧急情况下快速合并 |
| 发布分支 | Merge Commit | 保留发布标记 |

---

## 6. 回滚策略

### 6.1 代码回滚

```bash
# 方式 1: 创建反向提交（推荐）
git revert <commit-hash>
git push origin main

# 方式 2: 回退到指定版本
git checkout main
git reset --hard <commit-hash>
git push --force-with-lease origin main
```

### 6.2 发布回滚

```bash
# 1. 找到上一个稳定版本
git tag -l "v*" | sort -V

# 2. 创建回滚发布
git checkout -b hotfix/rollback-to-v0.0.9 main
git reset --hard v0.0.9
git push origin hotfix/rollback-to-v0.0.9

# 3. 合并并发布新版本
git checkout main
git merge --no-ff hotfix/rollback-to-v0.0.9
git tag -a v0.1.1 -m "Rollback to v0.0.9"
git push origin main --tags
```

---

## 7. 注意事项

1. **不要在 main 上直接开发** — 所有开发在功能分支上进行
2. **分支名要有意义** — 一眼能看出分支目的
3. **及时同步 main** — 每天至少 rebase 一次
4. **PR 描述要清晰** — 包含变更目的、测试方法、相关 Issue
5. **合并后删除分支** — 保持仓库整洁
