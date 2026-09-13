# Skill 生命周期管理

> NanamiGopher Agent 的 Skill 开发、安装、管理和热更新规范。

---

## 1. 概述

Skill 是 NanamiGopher Agent 的能力扩展单元。每个 Skill 封装为一个 MCP Server，通过标准化的 SKILL.md 元数据和 MCP 协议与 Agent 内核交互。Skill 生命周期涵盖从开发到卸载的完整过程。

```
开发 → 测试 → 安装 → 注册 → 运行 → 更新 → 卸载
                              │
                              └── 热更新 (Phase 3)
```

---

## 2. ISkillRegistry 接口

### 2.1 接口定义

```python
class ISkillRegistry(ABC):
    """Skill 注册表接口，管理所有已注册的 Skill。"""

    @abstractmethod
    def register(self, skill: SkillDefinition) -> str:
        """注册一个新的 Skill，返回 Skill ID。"""

    @abstractmethod
    def unregister(self, skill_id: str) -> bool:
        """注销一个已注册的 Skill。"""

    @abstractmethod
    def resolve(self, name: str) -> Optional[SkillDefinition]:
        """根据名称解析 Skill 定义。"""

    @abstractmethod
    def list(self, filters: Dict[str, Any] = None) -> List[SkillDefinition]:
        """列出所有 Skill，支持按权限、版本等过滤。"""

    @abstractmethod
    def get_version(self, skill_id: str) -> str:
        """获取 Skill 的版本号。"""

    @abstractmethod
    def check_dependency(self, skill_id: str,
                         required_by: str) -> bool:
        """检查 Skill 是否被其他 Skill 依赖。"""
```

### 2.2 SkillDefinition 结构

```python
@dataclass
class SkillDefinition:
    """Skill 的定义元数据。"""
    id: str                        # 唯一标识符
    name: str                      # 名称（与 SKILL.md 一致）
    version: str                   # 语义化版本号
    description: str               # 功能描述
    permission_level: int          # 权限等级（1-5）
    entry_command: str             # 入口命令
    parameters: List[ParameterDef] # 参数定义
    dependencies: List[str]        # 依赖的 Skill ID
    env_vars: Dict[str, str]       # 环境变量
    timeout: int                   # 超时秒数
    installed_at: datetime         # 安装时间
    updated_at: datetime           # 最后更新时间
    manifest_path: str             # SKILL.md 文件路径
```

### 2.3 内部结构

```
SkillRegistry
  │
  ├─ _skills: Dict[str, SkillDefinition]    # 按 ID 索引
  ├─ _by_name: Dict[str, str]               # 名称 → ID 映射
  ├─ _dependency_graph: Dict[str, Set[str]] # 依赖图
  └─ _event_bus: EventBus                   # 事件总线（注册/卸载/更新）
```

---

## 3. Skill 开发流程

### 3.1 开发步骤

```
Step 1: 创建 SKILL.md
    │
    ├─ 定义 Skill 名称、版本、权限
    ├─ 描述功能和参数
    ├─ 指定入口命令
    │
    ▼
Step 2: 实现 MCP Server
    │
    ├─ 实现 stdio 通信
    ├─ 实现 tools/list 端点
    ├─ 实现 tools/call 端点
    ├─ 处理错误和超时
    │
    ▼
Step 3: 本地测试
    │
    ├─ 使用 MCP Test Client 连接
    ├─ 验证工具发现
    ├─ 验证工具调用
    ├─ 验证错误处理
    │
    ▼
Step 4: 安装到 NanamiGopher
    │
    ├─ 将 SKILL.md 放入 skills/ 目录
    ├─ 注册 Skill 到 SkillRegistry
    ├─ 验证权限映射
    └─ 完成
```

### 3.2 示例：创建一个文件管理 Skill

#### 3.2.1 SKILL.md

```markdown
# File Manager Skill

## 描述
提供文件读写、目录操作和文件搜索功能。

## 名称
skill-file-manager

## 版本
1.0.0

## 权限
L3

## 参数
- path: string - 文件绝对路径
- content: string - 写入的文件内容
- action: string - 操作类型（read/write/list/search）

## 入口命令
python /opt/nanamigopher/skills/file-manager/server.py

## 环境变量
WORKSPACE_ROOT=${WORKSPACE_ROOT}

## 依赖
无

## 超时
30s
```

#### 3.2.2 MCP Server 实现（Python 示例）

```python
import json
import sys

def handle_initialize(params):
    """处理初始化请求。"""
    return {
        "protocolVersion": "2024-11-05",
        "serverInfo": {
            "name": "file-manager",
            "version": "1.0.0"
        },
        "capabilities": {
            "tools": {"listChanged": False}
        }
    }

def handle_tools_list(params):
    """处理工具列表请求。"""
    return {
        "tools": [
            {
                "name": "file_read",
                "description": "Read the contents of a file.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path to read."
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "file_write",
                "description": "Write content to a file.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "File path to write."
                        },
                        "content": {
                            "type": "string",
                            "description": "Content to write."
                        }
                    },
                    "required": ["path", "content"]
                }
            }
        ]
    }

def handle_tools_call(params):
    """处理工具调用请求。"""
    tool_name = params["name"]
    arguments = params["arguments"]

    if tool_name == "file_read":
        with open(arguments["path"], "r") as f:
            content = f.read()
        return {"content": [{"type": "text", "text": content}]}
    elif tool_name == "file_write":
        with open(arguments["path"], "w") as f:
            f.write(arguments["content"])
        return {"content": [{"type": "text", "text": "File written successfully."}]}
    else:
        return {"error": f"Unknown tool: {tool_name}"}

def main():
    """stdio 通信主循环。"""
    for line in sys.stdin:
        request = json.loads(line.strip())
        method = request.get("method")

        if method == "initialize":
            response = handle_initialize(request.get("params", {}))
        elif method == "tools/list":
            response = handle_tools_list(request.get("params", {}))
        elif method == "tools/call":
            response = handle_tools_call(request.get("params", {}))
        else:
            response = {"error": f"Unknown method: {method}"}

        # 发送响应
        json.dump({"jsonrpc": "2.0", "result": response}, sys.stdout)
        sys.stdout.write("\n")
        sys.stdout.flush()

if __name__ == "__main__":
    main()
```

---

## 4. Skill 安装/卸载/更新流程

### 4.1 安装流程

```
安装请求
  │
  ├─ 验证 SKILL.md 格式
  │   ├─ 必需字段是否存在
  │   ├─ 版本号是否符合语义化规范
  │   └─ 权限等级是否合法
  │
  ├─ 检查依赖
  │   ├─ 依赖的 Skill 是否已安装
  │   └─ 存在未满足的依赖 → 安装依赖或报错
  │
  ├─ 检查冲突
  │   ├─ 同名 Skill 是否已存在
  │   └─ 如果存在 → 执行更新流程
  │
  ├─ 复制文件到 skills/ 目录
  │
  ├─ 注册到 SkillRegistry
  │   ├─ 创建 SkillDefinition
  │   ├─ 建立名称 → ID 映射
  │   └─ 构建依赖图
  │
  ├─ 启动 MCP Server
  │   ├─ 创建子进程
  │   ├─ 发送 initialize 握手
  │   └─ 执行工具发现
  │
  └─ 安装完成，触发 on_installed 事件
```

### 4.2 卸载流程

```
卸载请求
  │
  ├─ 检查依赖关系
  │   ├─ 是否有其他 Skill 依赖此 Skill
  │   └─ 如果有 → 拒绝卸载或级联卸载
  │
  ├─ 停止 MCP Server
  │   ├─ 发送 shutdown 请求
  │   └─ 等待进程退出或强制 kill
  │
  ├─ 从 SkillRegistry 移除
  │   ├─ 删除 SkillDefinition
  │   ├─ 清理名称映射
  │   └─ 更新依赖图
  │
  ├─ 删除 Skill 文件
  │
  └─ 卸载完成，触发 on_uninstalled 事件
```

### 4.3 更新流程

```
更新请求（新版本）
  │
  ├─ 验证新版本 SKILL.md
  │
  ├─ 兼容性检查
  │   ├─ 检查 Major 版本是否变更（可能不兼容）
  │   ├─ Minor/Patch 变更 → 直接更新
  │   └─ Major 变更 → 提示用户确认
  │
  ├─ 备份旧版本
  │   ├─ 保存当前 SKILL.md
  │   └─ 保存当前 MCP Server 状态
  │
  ├─ 停止当前 MCP Server
  │
  ├─ 替换文件
  │
  ├─ 重新注册到 SkillRegistry
  │
  ├─ 启动新版 MCP Server
  │
  ├─ 验证新工具列表
  │   ├─ 工具名称是否变更
  │   ├─ 参数是否兼容
  │   └─ 发现不兼容变更 → 回滚
  │
  └─ 更新完成
```

---

## 5. Skill 版本管理

### 5.1 语义化版本

Skill 版本遵循 [SemVer 2.0.0](https://semver.org/)：

```
MAJOR.MINOR.PATCH
  │      │    │
  │      │    └─ 向下兼容的问题修复
  │      └───── 向下兼容的功能新增
  └─────────── 不兼容的 API 变更
```

### 5.2 版本兼容性矩阵

| 变更类型 | 版本更新 | 兼容性 |
|----------|----------|--------|
| 新增工具 | MINOR | 完全兼容 |
| 修改工具描述 | PATCH | 完全兼容 |
| 新增可选参数 | MINOR | 完全兼容 |
| 修改参数类型 | MAJOR | 不兼容 |
| 删除工具 | MAJOR | 不兼容 |
| 更改权限等级 | MAJOR | 不兼容 |
| 入口命令变更 | MAJOR | 不兼容 |

### 5.3 版本检查

```python
def check_compatibility(current: str, target: str) -> CompatibilityResult:
    """检查两个版本之间的兼容性。"""
    current_major, current_minor, current_patch = parse_version(current)
    target_major, target_minor, target_patch = parse_version(target)

    if current_major != target_major:
        return CompatibilityResult(
            compatible=False,
            breaking_changes=["Major version changed - potential breaking changes"],
            upgrade_type="major"
        )
    elif current_minor != target_minor:
        return CompatibilityResult(
            compatible=True,
            breaking_changes=[],
            upgrade_type="minor"
        )
    else:
        return CompatibilityResult(
            compatible=True,
            breaking_changes=[],
            upgrade_type="patch"
        )
```

---

## 6. Skill 依赖解析

### 6.1 依赖图

```
skill-a (L2)
  │
  ├─ 依赖 skill-b (L3)
  │   │
  │   └─ 依赖 skill-c (L1)
  │
  └─ 依赖 skill-d (L2)
```

依赖图以有向无环图（DAG）形式存储：

```python
_dependency_graph = {
    "skill-a": {"skill-b", "skill-d"},
    "skill-b": {"skill-c"},
    "skill-c": set(),
    "skill-d": set(),
}
```

### 6.2 依赖解析算法

```python
def resolve_dependencies(skill_id: str) -> List[str]:
    """按拓扑排序解析 Skill 的所有依赖。"""
    visited = set()
    result = []

    def visit(sid):
        if sid in visited:
            return
        visited.add(sid)
        for dep in _dependency_graph.get(sid, set()):
            visit(dep)
        result.append(sid)

    visit(skill_id)
    return result[::-1]  # 反向：先安装依赖
```

### 6.3 冲突检测

| 冲突类型 | 检测方式 | 处理策略 |
|----------|----------|----------|
| 同名不同版本 | 名称索引检查 | 拒绝安装或升级 |
| 依赖循环 | DFS 环检测 | 拒绝安装并报错 |
| 权限不匹配 | 权限等级比较 | 取最高权限等级 |
| 端口/资源冲突 | 系统资源扫描 | 跳过或告警 |

---

## 7. Skill 权限配置

### 7.1 权限等级映射

每个 Skill 通过 SKILL.md 声明权限等级，映射到统一的 L1-L5 体系：

| SKILL.md 权限 | 系统权限等级 | 允许的操作 |
|---------------|-------------|------------|
| L1 | P1 | 只读操作（file_read, web_fetch, glob） |
| L2 | P2 | 轻度写入（file_write, web_search, grep） |
| L3 | P3 | 命令执行（bash 基础命令） |
| L4 | P4 | 系统管理（文件删除、配置修改） |
| L5 | P5 | 高危操作（sudo、网络配置、进程管理） |

### 7.2 权限校验流程

```
Skill 调用请求
  │
  ├─ 获取 Skill 声明的权限等级（SKILL.md）
  │
  ├─ 获取当前用户的权限等级（PermissionManager）
  │
  ├─ 比较权限等级
  │   ├─ 用户权限 >= Skill 权限 → 允许
  │   └─ 用户权限 < Skill 权限 → 拒绝
  │
  └─ 记录审计日志
```

### 7.3 权限继承

如果 Skill A 依赖 Skill B，则 Skill A 的最低权限等级为两者中的最大值：

```python
def compute_effective_permission(skill_id: str) -> int:
    """计算 Skill 的有效权限等级（含依赖）。"""
    skill_def = registry.resolve(skill_id)
    max_permission = skill_def.permission_level

    for dep_id in skill_def.dependencies:
        dep_permission = compute_effective_permission(dep_id)
        max_permission = max(max_permission, dep_permission)

    return max_permission
```

---

## 8. Skill 热更新（Phase 3）

### 8.1 热更新机制

在 Phase 3 中，Skill 支持不停机的热更新：

```
热更新触发
  │
  ├─ 下载新版本 Skill 包
  │
  ├─ 验证新版本（签名检查、兼容性测试）
  │
  ├─ 创建新版本实例
  │   ├─ 启动新的 MCP Server（新版本）
  │   └─ 等待健康检查通过
  │
  ├─ 流量切换
  │   ├─ 新请求路由到新版本
  │   └─ 现有请求继续由旧版本处理
  │
  ├─ 旧版本实例回收
  │   ├─ 等待所有旧连接断开
  │   └─ 优雅关闭旧 MCP Server
  │
  └─ 热更新完成
```

### 8.2 回滚策略

```
热更新失败
  │
  ├─ 新版本健康检查未通过
  │   ├─ 停止新版本
  │   └─ 继续使用旧版本
  │
  ├─ 新版本运行中出现严重错误
  │   ├─ 自动触发回滚
  │   ├─ 恢复旧版本实例
  │   └─ 记录回滚原因
  │
  └─ 手动回滚
      ├─ 用户发起回滚请求
      └─ 恢复到上一个稳定版本
```

### 8.3 热更新配置

```yaml
hot_reload:
  enabled: false              # Phase 3 启用
  health_check_timeout: 10    # 健康检查超时（秒）
  drain_timeout: 30           # 连接排空超时（秒）
  rollback_on_failure: true   # 失败时自动回滚
  max_versions: 3             # 保留的最大历史版本数
```

---

## 附录：Skill 生命周期 Checklist

- [ ] SKILL.md 是否包含所有必需字段？
- [ ] MCP Server 是否正确实现 tools/list 和 tools/call？
- [ ] 依赖解析是否避免了循环依赖？
- [ ] 版本兼容性检查是否正确处理 Major/Minor/Patch？
- [ ] 权限等级映射是否准确？
- [ ] 卸载流程是否正确检查依赖关系？
- [ ] 热更新是否支持流量切换和回滚？
- [ ] 审计日志是否记录了所有安装/卸载/更新事件？
