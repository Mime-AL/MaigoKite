# Skill 生命周期管理

> **状态**：Phase 2 Planned
> **架构版本**：v1
> **最后核验**：2026-09-18
> **权威范围**：Skill 类型、Manifest、安装、授权、更新与卸载

MCP运行时见 [MCP Integration](../mcp/mcp-integration.md)，工具风险见 [Tool Permission](../security/tool-permission.md)。

Phase 1 仅支持由部署配置声明的受信 stdio MCP Server，并复用统一工具权限与审计链路；尚未交付 Skill 导入、安装、版本、Grant、依赖解析和管理页面/API。以下内容是 Phase 2 的目标契约，不能作为当前功能说明。

## 1. Skill 类型

| kind | 含义 | 是否启动进程 |
|---|---|---|
| instruction | 提示、流程和使用说明 | 否 |
| mcp-server | 通过 MCP 暴露工具的独立服务 | 是 |
| workflow | 可版本化工作流定义 | 视节点而定 |
| bundle | 包含多个受声明资源的发行包 | 视内容而定 |

Native Tool 是受信内置代码，不通过第三方 Skill 安装流程注册。

## 2. Manifest

每个 Skill 包必须包含一个 `SKILL.md`。元数据使用受约束的 front matter，正文用于人类可读说明：

```yaml
---
name: file-manager
version: 1.0.0
kind: mcp-server
description: Read and edit files in an approved workspace.
publisher: example
entrypoint:
  command: python
  args: [server.py]
transport: stdio
capabilities:
  - files.read
  - files.write
resources:
  filesystem: [workspace]
credentials: []
dependencies: []
timeout_seconds: 30
---
```

规则：

- `name + version + content_hash` 唯一标识不可变版本。
- entrypoint 必须拆分 command/args，不允许 shell 字符串。
- capability 是请求，最终权限由 SkillGrant 和 ToolPolicy 决定。
- Phase 2 首版仅允许 `mcp-server` 使用 stdio。
- JSON Schema 另存或嵌入受验证字段，不从自然语言参数列表猜测。

## 3. 注册模型

```text
Skill             稳定名称与发布者
SkillVersion      不可变包、manifest、hash、信任状态
SkillGrant        Workspace 安装状态、配置、能力和资源授权
RuntimeInstance   当前 MCP 进程状态（非长期授权）
```

同一 SkillVersion 可被多个 Workspace 安装，但 Grant、配置和凭证范围相互隔离。

## 4. 导入与安装

- `import`：用户提供本地包或目录归档。
- `install`：从受支持的注册源按不可变版本获取。

二者进入同一验证流程：

```text
获取内容
→ 规范化并计算 hash
→ 验证 manifest/schema
→ 验证来源/签名/信任策略
→ 解析依赖
→ 静态安全检查
→ 展示能力、资源和凭证请求
→ 用户/管理员确认
→ 创建 SkillVersion 与 SkillGrant
→ 按 kind 激活
```

验证失败不创建活动 Grant，也不执行入口命令。

## 5. 依赖

- 依赖必须包含版本范围和来源。
- 解析结果生成 lock，安装后使用确定版本。
- 循环依赖和冲突依赖拒绝安装。
- 依赖的能力不能隐式扩大顶层 Skill 的授权。
- 更新依赖导致能力变化时重新审批。

## 6. 授权与配置

SkillGrant 保存：

```text
workspace_id
skill_version_id
status
approved_capabilities
filesystem_scope
network_scope
credential_references
resource_limits
configuration
approved_by / approved_at
```

配置不包含 Secret 值。用户配置和 manifest 分离，更新版本时不覆盖用户配置；不兼容配置通过显式迁移处理。

## 7. 更新

```text
获取新版本
→ 完整验证
→ 比较 manifest、能力和依赖
→ 必要时重新审批
→ 创建新 SkillVersion
→ 启动并健康检查新实例
→ 原子切换 Grant
→ 停止旧实例
```

旧版本在保留期内可回滚。回滚不绕过当前安全策略；已撤销凭证不会因回滚恢复。

## 8. 卸载

1. 阻止新调用。
2. 取消或等待活动调用。
3. 停止 RuntimeInstance。
4. 禁用 SkillGrant。
5. 撤销临时凭证和缓存。
6. 按保留策略删除用户配置与生成数据。
7. 保留必要审计记录。

若其他活动 Skill 依赖该 Grant，默认拒绝卸载并展示依赖关系；级联卸载必须再次确认。

## 9. 状态

```text
imported → pending_approval → active
                      ├── rejected
active → disabled → active
active → updating → active / rollback / failed
active → uninstalling → uninstalled
failed/quarantined → disabled / repaired
```

Manifest 版本、Grant 状态和 MCP运行状态不得混为一个 `is_active` 布尔字段。

## 10. 验收清单

- [ ] SKILL.md 格式只在本文完整定义。
- [ ] import 和 install 输入不同但共享验证流程。
- [ ] SkillVersion 不可变并有内容 hash。
- [ ] Workspace 授权相互隔离。
- [ ] 更新扩大能力时重新审批。
- [ ] 安装前不执行第三方入口命令。
- [ ] 卸载能够停止运行时并撤销凭证。
