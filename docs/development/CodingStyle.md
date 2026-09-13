# 编码规范

> **版本**: v1.0  
> **日期**: 2026-07-21  
> **适用范围**: Go 后端、Python Agent Core、Vue 3 前端

---

## 1. 通用原则

1. **可读性优先** — 代码是写给人看的，其次才是给机器执行
2. **一致性优先** — 宁可遵循不合理的规范，也不要各自为政
3. **少即是多** — 能用标准库解决的不要引入第三方依赖
4. **显式优于隐式** — 不要依赖魔法，每个行为都应该有迹可循

---

## 2. Go 编码规范

### 2.1 项目结构

```
cmd/
  nanamigopher/        # 主程序入口
  nanamigopher-server/ # 服务器入口
internal/
  config/              # 配置管理
  permission/          # 权限校验
  security/            # 安全过滤
  websocket/           # WebSocket 处理
pkg/
  proto/               # gRPC 协议定义
  middleware/          # HTTP 中间件
api/
  handler/             # HTTP Handler
  router/              # 路由配置
  dto/                 # 数据传输对象
grpc/
  service/             # gRPC 服务实现
web/                   # 前端静态文件
```

### 2.2 命名规范

```go
// 包名：全小写，简短，不使用下划线
package config

// 接口名：单方法接口以 -er 结尾
type Reader interface {
    Read(p []byte) (n int, err error)
}

// 接口名：多方法接口直接使用名词
type ConfigManager interface {
    Get(key string) any
    Set(key string, value any)
    Reload()
}

// 变量名：简短变量用单字母，长变量用全称
var cfg ConfigManager          // 局部作用域用短名
var configManager ConfigManager // 全局作用域用全称

// 常量名：分组使用 const block
const (
    DefaultPort = 8080
    MaxRetries  = 3
)

// 错误名：自定义错误以 Error 结尾
var ErrNotFound = errors.New("resource not found")
```

### 2.3 错误处理

```go
// 使用 fmt.Errorf 与 %w 包装错误
result, err := doSomething()
if err != nil {
    return fmt.Errorf("doSomething failed: %w", err)
}

// 使用 errors.Is 和 errors.As 检查错误
if errors.Is(err, ErrNotFound) {
    // 处理未找到
}

// 不要吞掉错误
// 错误:
// if err != nil {
//     return
// }
// 正确:
if err != nil {
    return fmt.Errorf("failed to process request: %w", err)
}
```

### 2.4 并发规范

```go
// 使用 context 控制超时和取消
ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
defer cancel()

result, err := doSomething(ctx)

// 使用 sync.Once 确保一次性初始化
var once sync.Once
var instance *Singleton

func GetInstance() *Singleton {
    once.Do(func() {
        instance = &Singleton{}
    })
    return instance
}

// Channel 优先于共享内存
func worker(ctx context.Context, jobs <-chan Job, results chan<- Result) {
    for {
        select {
        case job, ok := <-jobs:
            if !ok {
                return
            }
            results <- process(job)
        case <-ctx.Done():
            return
        }
    }
}
```

### 2.5 测试规范

```go
// 表驱动测试
func TestConfig_Get(t *testing.T) {
    tests := []struct {
        name     string
        key      string
        expected any
    }{
        {"get existing key", "models.provider", "openai"},
        {"get nested key", "models.prefer_local", true},
        {"get nonexistent key", "nonexistent.key", nil},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            cm := NewConfigManager("test.yaml")
            result := cm.Get(tt.key)
            assert.Equal(t, tt.expected, result)
        })
    }
}
```

---

## 3. Python 编码规范

### 3.1 项目结构

```
python/
  agent/
    __init__.py
    core.py              # AgentCore 主类
    task_manager.py      # 任务管理
    execution_engine.py  # 执行引擎
    skill_registry.py    # Skill 注册表
    memory/              # 记忆系统
      __init__.py
      system.py
      short_term.py
      conversation.py
      user.py
    knowledge_base/      # 知识库
      __init__.py
      store.py
      retriever.py
      vector_store.py
    tools/               # 工具系统
      __init__.py
      base.py            # BaseTool 接口
      native/            # 原生 Tool
        file_read.py
        file_write.py
        bash.py
        ...
      mcp_wrapper.py     # MCP 工具封装
    models/              # 模型层
      __init__.py
      chat_provider.py
      embedding_provider.py
      factory.py
    security/            # 安全模块
      __init__.py
      injection_filter.py
      permission.py
    inspector/           # Inspector 监控
      __init__.py
      events.py
      timeline.py
    sub_agent_manager.py # SubAgent 管理
  tests/
    unit/
    integration/
    security/
    performance/
    fixtures/
```

### 3.2 命名规范

```python
# 模块名：全小写，使用下划线
from agent.memory.system import MemorySystem

# 类名：大驼峰
class SkillRegistry:
    pass

# 函数/方法名：小写+下划线
def get_skill(self, name: str) -> Skill:
    pass

# 常量名：大写+下划线
DEFAULT_TIMEOUT = 30
MAX_CONCURRENT_SUBAGENTS = 5

# 私有成员：前缀下划线
def _internal_helper(self):
    pass

# 类型注解：始终使用
def process_message(
    self,
    session_id: str,
    content: str,
    attachments: list[Attachment] | None = None
) -> AsyncGenerator[MessageChunk, None]:
    pass
```

### 3.3 异步编程

```python
# 使用 async/await 而非 asyncio.run
async def execute_tool(self, tool: BaseTool, args: dict) -> ToolResult:
    return await tool.execute(self.context, args)

# 使用 asyncio.gather 并发执行
results = await asyncio.gather(
    subagent_a.execute(),
    subagent_b.execute(),
    subagent_c.execute(),
    return_exceptions=True
)

# 使用 asyncio.wait_for 设置超时
try:
    result = await asyncio.wait_for(tool.execute(ctx, args), timeout=60)
except asyncio.TimeoutError:
    logger.warning("Tool execution timed out")
```

### 3.4 依赖注入

```python
# 通过构造函数注入依赖，便于测试
class AgentCore:
    def __init__(
        self,
        task_manager: ITaskManager,
        memory_system: IMemorySystem,
        knowledge_base: IKnowledgeBase | None,
        model_factory: ModelProviderFactory,
        skill_registry: ISkillRegistry,
        config_manager: IConfigManager,
        observability: IObservability,
    ):
        self.task_manager = task_manager
        self.memory_system = memory_system
        self.knowledge_base = knowledge_base
        self.model_factory = model_factory
        self.skill_registry = skill_registry
        self.config_manager = config_manager
        self.observability = observability
```

### 3.5 日志规范

```python
import logging

# 使用结构化日志
logger = logging.getLogger(__name__)

# 信息级别使用
logger.info("Tool executed", extra={
    "tool_name": "file_read",
    "path": "/path/to/file",
    "duration_ms": 12
})

# 错误级别使用
logger.error("Tool execution failed", exc_info=True, extra={
    "tool_name": "bash",
    "error": "command not found"
})
```

---

## 4. Vue 3 前端编码规范

### 4.1 项目结构

```
web/
  src/
    main.ts
    App.vue
    router/
      index.ts              # 路由配置
    stores/
      session.ts            # Pinia 会话状态
      memory.ts             # 记忆状态
      skill.ts              # Skill 状态
      inspector.ts          # Inspector 状态
    views/
      Overview.vue          # 总览页
      Chat.vue              # 对话页
      Inspector.vue         # Inspector 监控页
      Settings.vue          # 设置页
      ...
    components/
      sidebar/              # 左侧导航栏
        Sidebar.vue
        NavMenu.vue
        RecentChats.vue
      chat-area/            # 对话区域
        MessageList.vue
        CodeChangesPanel.vue
        ToolOutputPanel.vue
        StepStatusPanel.vue
        TaskViewPanel.vue
        InputBox.vue
      file-explorer/        # 右侧文件管理器
        FileExplorer.vue
        FileTree.vue
        FilePreview.vue
      inspector/            # Inspector 组件
        InspectorView.vue
        InspectorCard.vue
        TimelineNode.vue
        DimensionSelector.vue
    composables/            # 组合式函数
      useWebSocket.ts
      useSession.ts
      useFileTree.ts
    types/                  # TypeScript 类型定义
      index.ts
      api.d.ts
      store.d.ts
    utils/
      format.ts
      validate.ts
    assets/
      styles/
        globals.scss
        variables.scss
  vite.config.ts
  tsconfig.json
```

### 4.2 组件规范

```vue
<!-- 使用 <script setup> 语法 -->
<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useWebSocket } from '@/composables/useWebSocket'

interface Props {
  sessionId: string
  autoScroll?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  autoScroll: true
})

const emit = defineEmits<{
  (e: 'message-send', content: string): void
  (e: 'message-cancel'): void
}>()

const messageList = ref<Message[]>([])
const isConnected = ref(false)

const { connect, disconnect, send } = useWebSocket(props.sessionId)

onMounted(() => {
  connect()
})

onUnmounted(() => {
  disconnect()
})
</script>

<template>
  <div class="chat-area">
    <MessageList
      ref="messageListRef"
      :messages="messageList"
      :auto-scroll="autoScroll"
    />
    <InputBox
      @send="handleSend"
      @cancel="emit('message-cancel')"
    />
  </div>
</template>

<style scoped lang="scss">
.chat-area {
  display: flex;
  flex-direction: column;
  height: 100%;
}
</style>
```

### 4.3 状态管理规范

```typescript
// 使用 Pinia 管理全局状态
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useSessionStore = defineStore('session', () => {
  const sessions = ref<Session[]>([])
  const activeSessionId = ref<string | null>(null)

  const activeSession = computed(() =>
    sessions.value.find(s => s.id === activeSessionId.value)
  )

  function createSession(title: string) {
    const session: Session = {
      id: `sess_${Date.now()}`,
      title,
      messages: [],
      createdAt: new Date()
    }
    sessions.value.push(session)
    activeSessionId.value = session.id
    return session
  }

  function sendMessage(content: string) {
    if (!activeSessionId.value) return
    const session = sessions.value.find(s => s.id === activeSessionId.value)
    if (session) {
      session.messages.push({ role: 'user', content })
    }
  }

  return { sessions, activeSessionId, activeSession, createSession, sendMessage }
})
```

### 4.4 TypeScript 规范

```typescript
// 使用 interface 定义对象类型，type 定义联合类型
interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
}

type ToolResult = {
  data: Record<string, any>
  summary: string
  raw: string | null
  metadata: Record<string, any>
}

// 使用泛型提高复用性
function fetchData<T>(url: string): Promise<T> {
  return fetch(url).then(res => res.json())
}

// 使用类型守卫
function isErrorResult(result: ToolResult | ErrorResult): result is ErrorResult {
  return 'error' in result
}
```

---

## 5. 代码格式化

### 5.1 Go

```bash
# 使用 gofmt（go fmt 的底层）
gofmt -w .

# 使用 goimports 自动管理 import
go install golang.org/x/tools/cmd/goimports@latest
goimports -w .

# 使用 staticcheck 进行静态分析
go install honnef.co/go/tools/cmd/staticcheck@latest
staticcheck ./...
```

### 5.2 Python

```bash
# ruff: 超快的 Python lint + formatter
pip install ruff
ruff check .          # lint
ruff format .         # format

# mypy: 类型检查
pip install mypy
mypy python/
```

### 5.3 Vue / TypeScript

```json
// .editorconfig
root = true

[*]
charset = utf-8
indent_style = space
indent_size = 2
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true

[*.vue]
indent_size = 2

[*.{ts,tsx}]
indent_size = 2

[*.{js,jsx}]
indent_size = 2
```

```bash
# ESLint + Prettier
npx eslint --fix .
npx prettier --write .
```

---

## 6. Git 提交规范

### 6.1 提交消息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

**type** 枚举：

| Type | 说明 |
|------|------|
| feat | 新功能 |
| fix | Bug 修复 |
| docs | 文档变更 |
| style | 代码格式（不影响功能） |
| refactor | 重构（既不是新功能也不是修复） |
| test | 测试相关 |
| chore | 构建/辅助工具变更 |
| perf | 性能优化 |

**示例**：

```
feat(tools): 添加 file_read 原生工具

实现 BaseTool 接口，支持路径参数校验和 UTF-8 解码。

- 添加 FileReadTool 类
- 添加路径白名单检查
- 添加单元测试

Closes #12
```

### 6.2 分支命名

```
feature/xxx            # 新功能
fix/xxx               # Bug 修复
refactor/xxx          # 重构
docs/xxx              # 文档
chore/xxx             # 杂项
release/x.y.z         # 发布
hotfix/xxx            # 紧急修复
```

---

## 7. 安全编码规范

1. **不要硬编码密钥** — 使用 CredentialStore + 系统密钥链
2. **输入永远不可信** — 所有用户输入必须经过校验和转义
3. **最小权限原则** — 工具权限分级，默认拒绝
4. **日志脱敏** — 不在日志中记录 API Key、密码等敏感信息
5. **依赖审计** — 定期运行 `pip audit` / `go vet` / `npm audit`

---

## 8. 文档规范

1. **所有公开 API 必须有 docstring / godoc**
2. **复杂逻辑必须有注释说明"为什么"，而不是"做什么"**
3. **README 必须包含**：项目简介、安装步骤、快速开始、配置说明
4. **CHANGELOG 遵循 [Keep a Changelog](https://keepachangelog.com/) 格式**
