# Git 工作流

> **版本**: v1.0  
> **日期**: 2026-07-21

---

## 1. 分支策略

采用 **GitHub Flow** 简化分支模型，适合单人全栈开发：

```
main (生产分支)
  ├── feature/tool-system
  ├── feature/memory-system
  ├── feature/frontend-ui
  └── hotfix/security-patch
```

### 1.1 分支命名规范

| 类型 | 格式 | 示例 |
|------|------|------|
| 新功能 | `feature/模块名-功能描述` | `feature/tool-system-native-tools` |
| Bug 修复 | `fix/问题描述` | `fix/injection-filter-bypass` |
| 重构 | `refactor/模块名-描述` | `refactor/memory-system-split` |
| 文档 | `docs/描述` | `docs/architecture-update` |
| 发布 | `release/版本号` | `release/0.1.0` |
| 紧急修复 | `hotfix/描述` | `hotfix/critical-memory-leak` |

### 1.2 分支生命周期

```
创建分支 → 开发 → 提交 PR → 代码审查 → 合并到 main → 删除分支
```

- 每个分支应有明确的目标，完成后立即删除
- 分支开发周期不超过 2 周
- 每天至少推送一次代码到远程分支

---

## 2. 提交规范

### 2.1 提交消息格式

遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Type 枚举**：

| Type | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档变更 |
| `style` | 代码格式（不影响功能） |
| `refactor` | 重构 |
| `test` | 测试相关 |
| `chore` | 构建/工具变更 |
| `perf` | 性能优化 |

**Scope**（可选）：

| Scope | 说明 |
|-------|------|
| `gateway` | Go API Gateway |
| `agent` | Python Agent Core |
| `frontend` | Vue 3 前端 |
| `tools` | 工具系统 |
| `memory` | 记忆系统 |
| `security` | 安全模块 |
| `config` | 配置管理 |
| `mcp` | MCP 协议 |

**示例**：

```
feat(tools): 添加 file_read 原生工具

实现 BaseTool 接口，支持路径参数校验和 UTF-8 解码。

- 添加 FileReadTool 类
- 添加路径白名单检查
- 添加单元测试

Closes #12
```

### 2.2 提交原则

1. **原子提交** — 每次提交只做一件事
2. **自解释** — 提交消息应能独立理解变更内容
3. **小步快跑** — 避免一次性提交几千行代码
4. **测试通过** — 提交前确保相关测试通过

---

## 3. PR 规范

### 3.1 PR 模板

```markdown
## 变更类型
- [ ] feat: 新功能
- [ ] fix: Bug 修复
- [ ] docs: 文档
- [ ] refactor: 重构
- [ ] test: 测试
- [ ] chore: 构建/工具

## 变更描述
简要描述本次 PR 的变更内容。

## 相关 Issue
Closes #123

## 测试说明
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 手动测试步骤：
  1. ...
  2. ...

## 截图（如适用）
（附 UI 变更截图）

## 检查清单
- [ ] 代码符合编码规范
- [ ] 已更新相关文档
- [ ] 无未使用的导入/变量
- [ ] 无 console.log/debugger
```

### 3.2 PR 审查流程

1. 作者自审：提交前运行全部测试
2. 自动检查：CI 自动运行 lint、test、build
3. 人工审查：至少一人审查（单人开发可自行审查）
4. 合并：审查通过后 squash merge 到 main

---

## 4. 标签与版本

### 4.1 语义化版本

遵循 [SemVer 2.0.0](https://semver.org/)：

```
主版本.次版本.修订号
MAJOR.MINOR.PATCH

MAJOR: 不兼容的 API 变更
MINOR: 向后兼容的功能新增
PATCH: 向后兼容的问题修复
```

### 4.2 标签格式

```bash
# 发布标签
git tag -a v0.1.0 -m "Release v0.1.0: Initial MVP"
git push origin v0.1.0

# 开发里程碑
git tag -a phase1-complete -m "Phase 1 complete: Framework MVP"
```

---

## 5. 冲突解决

### 5.1 预防冲突

1. 每天 `git pull --rebase origin main` 同步最新代码
2. 功能分支尽量短，减少冲突概率
3. 大重构前先与相关人员（如果有）沟通

### 5.2 解决冲突

```bash
# 1. 拉取最新 main
git fetch origin
git rebase origin/main

# 2. 解决冲突文件中的 <<<<<<< ===== >>>>>>> 标记

# 3. 标记为已解决
git add <resolved-files>

# 4. 继续 rebase
git rebase --continue

# 5. 强制推送（如果已经在远程有分支）
git push --force-with-lease
```

---

## 6. 常用 Git 命令速查

```bash
# 查看状态
git status
git diff

# 查看日志
git log --oneline --graph --all
git log --since="2026-07-01"

# 暂存变更
git stash
git stash pop

# 撤销提交
git reset --soft HEAD~1    # 保留变更，撤销提交
git reset --hard HEAD~1    # 丢弃所有变更

# 查看远程
git remote -v
git branch -vv

# 清理无用分支
git fetch --prune
git branch -d $(git branch --merged | grep -v main)
```
