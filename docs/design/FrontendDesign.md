# NanamiGopher 前端设计文档

> **版本**: v1.0  
> **日期**: 2026-07-15  
> **技术栈**: Electron 28+ + Vue 3 + Vite

---

## 1. 前端架构

### 1.1 技术选型

| 技术 | 版本 | 用途 |
|------|------|------|
| Electron | 28+ | 桌面应用容器 |
| Vue 3 | 3.4+ | UI 框架（Composition API） |
| Vite | 5+ | 构建工具 |
| TypeScript | 5+ | 类型安全 |
| Pinia | 2+ | 状态管理 |
| Vue Router | 4+ | 路由管理 |
| Tailwind CSS | 3+ | 样式框架 |
| Element Plus | 2+ | UI 组件库 |
| WebSocket | native | 实时通信 |
| Axios | 1+ | HTTP 请求 |

### 1.2 项目结构

```
electron-app/
├── electron/                 # Electron 主进程
│   ├── main.ts               # 主进程入口
│   ├── preload.ts            # 预加载脚本
│   ├── ipc-handlers/         # IPC 处理器
│   │   ├── session.ts
│   │   ├── memory.ts
│   │   ├── skill.ts
│   │   └── permission.ts
│   └── utils/
│       ├── updater.ts        # 自动更新
│       └── tray.ts           # 系统托盘
├── src/                      # Vue 应用（渲染进程）
│   ├── main.ts               # Vue 入口
│   ├── App.vue               # 根组件
│   ├── router/               # 路由配置
│   │   └── index.ts
│   ├── stores/               # Pinia 状态管理
│   │   ├── session.ts        # 会话状态
│   │   ├── memory.ts         # 记忆状态
│   │   ├── skill.ts          # Skill 状态
│   │   ├── permission.ts     # 权限状态
│   │   └── ui.ts             # UI 状态
│   ├── views/                # 页面组件
│   │   ├── ChatView.vue      # 对话页面
│   │   ├── SettingsView.vue  # 设置页面
│   │   ├── SkillsView.vue    # Skill 管理页面
│   │   └── MemoriesView.vue  # 记忆管理页面
│   ├── components/           # 通用组件
│   │   ├── Sidebar/          # 侧边栏
│   │   │   ├── SessionList.vue
│   │   │   └── NewSessionBtn.vue
│   │   ├── ChatArea/         # 对话区域
│   │   │   ├── MessageList.vue
│   │   │   ├── MessageBubble.vue
│   │   │   └── InputBox.vue
│   │   ├── StepPanel/        # 步骤面板
│   │   │   ├── StepItem.vue
│   │   │   └── StepProgress.vue
│   │   ├── Approval/         # 审批组件
│   │   │   ├── ApprovalDialog.vue
│   │   │   └── ApprovalList.vue
│   │   ├── Takeover/         # 接管组件
│   │   │   └── TakeoverNotification.vue
│   │   └── Common/           # 通用组件
│   │       ├── LoadingSpinner.vue
│   │       ├── ConfirmDialog.vue
│   │       └── Toast.vue
│   ├── composables/          # 组合式函数
│   │   ├── useWebSocket.ts
│   │   ├── useSession.ts
│   │   ├── useMemory.ts
│   │   └── usePermission.ts
│   ├── services/             # API 服务
│   │   ├── api.ts            # HTTP 请求封装
│   │   ├── session-api.ts
│   │   ├── memory-api.ts
│   │   ├── skill-api.ts
│   │   └── websocket.ts
│   ├── types/                # TypeScript 类型
│   │   ├── session.ts
│   │   ├── memory.ts
│   │   ├── skill.ts
│   │   └── api.ts
│   └── utils/                # 工具函数
│       ├── format.ts
│       ├── validate.ts
│       └── constants.ts
├── public/                   # 静态资源
├── vite.config.ts            # Vite 配置
├── electron-builder.yml      # Electron 打包配置
├── package.json
└── tsconfig.json
```

---

## 2. Electron 主进程设计

### 2.1 主进程入口

```typescript
// electron/main.ts
import { app, BrowserWindow, ipcMain, Tray, Menu } from 'electron'
import path from 'path'
import { startGoGateway } from './gateway'
import { startPythonAgent } from './agent'

let mainWindow: BrowserWindow | null = null
let tray: Tray | null = null

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    titleBarStyle: 'hiddenInset',  // macOS 风格
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true
    }
  })

  // 开发环境加载 Vite dev server
  if (process.env.NODE_ENV === 'development') {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

function createTray() {
  tray = new Tray(path.join(__dirname, '../public/icon.png'))
  const contextMenu = Menu.buildFromTemplate([
    { label: '显示窗口', click: () => mainWindow?.show() },
    { label: '退出', click: () => app.quit() }
  ])
  tray.setToolTip('NanamiGopher')
  tray.setContextMenu(contextMenu)
}

// 启动 Go API Gateway
async function startGateway() {
  const gateway = await startGoGateway()
  
  gateway.on('error', (error) => {
    console.error('Gateway error:', error)
    // 显示错误通知
    if (mainWindow) {
      mainWindow.webContents.send('gateway-error', error.message)
    }
  })
  
  return gateway
}

// 启动 Python Agent Core
async function startAgent() {
  const agent = await startPythonAgent()
  
  agent.on('message', (data) => {
    // 转发给前端
    if (mainWindow) {
      mainWindow.webContents.send('agent-message', data)
    }
  })
  
  return agent
}

app.whenReady().then(async () => {
  createWindow()
  createTray()
  
  // 启动后端服务
  await startGateway()
  await startAgent()
  
  // 注册 IPC 处理器
  registerIPCHandlers()
  
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

function registerIPCHandlers() {
  // 会话管理
  ipcMain.handle('session:create', async (_, data) => {
    // 调用 Go API
    const response = await fetch('http://localhost:8080/api/v1/sessions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    return response.json()
  })
  
  ipcMain.handle('session:list', async () => {
    const response = await fetch('http://localhost:8080/api/v1/sessions')
    return response.json()
  })
  
  // 记忆管理
  ipcMain.handle('memory:search', async (_, data) => {
    const response = await fetch('http://localhost:8080/api/v1/memories/search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    return response.json()
  })
  
  // Skill 管理
  ipcMain.handle('skill:list', async () => {
    const response = await fetch('http://localhost:8080/api/v1/skills')
    return response.json()
  })
  
  // 权限管理
  ipcMain.handle('permission:check', async (_, data) => {
    const response = await fetch('http://localhost:8080/api/v1/permissions/check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    return response.json()
  })
}
```

### 2.2 预加载脚本

```typescript
// electron/preload.ts
import { contextBridge, ipcRenderer } from 'electron'

// 暴露安全的 API 到渲染进程
contextBridge.exposeInMainWorld('electronAPI', {
  // 会话管理
  createSession: (data: any) => ipcRenderer.invoke('session:create', data),
  listSessions: () => ipcRenderer.invoke('session:list'),
  
  // 记忆管理
  searchMemories: (data: any) => ipcRenderer.invoke('memory:search', data),
  
  // Skill 管理
  listSkills: () => ipcRenderer.invoke('skill:list'),
  
  // 权限管理
  checkPermission: (data: any) => ipcRenderer.invoke('permission:check', data),
  
  // 监听来自主进程的消息
  onAgentMessage: (callback: (data: any) => void) => {
    ipcRenderer.on('agent-message', (_, data) => callback(data))
  },
  
  onGatewayError: (callback: (error: string) => void) => {
    ipcRenderer.on('gateway-error', (_, error) => callback(error))
  },
  
  // WebSocket 连接
  connectWebSocket: (sessionId: string) => {
    const ws = new WebSocket(`ws://localhost:8080/api/v1/sessions/${sessionId}/stream`)
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      // 转发给渲染进程
      ipcRenderer.send('websocket-message', data)
    }
    
    return ws
  }
})
```

### 2.3 类型声明

```typescript
// electron/preload.d.ts
interface ElectronAPI {
  createSession: (data: any) => Promise<any>
  listSessions: () => Promise<any>
  searchMemories: (data: any) => Promise<any>
  listSkills: () => Promise<any>
  checkPermission: (data: any) => Promise<any>
  onAgentMessage: (callback: (data: any) => void) => void
  onGatewayError: (callback: (error: string) => void) => void
  connectWebSocket: (sessionId: string) => WebSocket
}

declare global {
  interface Window {
    electronAPI: ElectronAPI
  }
}
```

---

## 3. Vue 3 前端设计

### 3.1 路由配置

```typescript
// src/router/index.ts
import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('@/views/MainLayout.vue'),
    children: [
      {
        path: '',
        name: 'Chat',
        component: () => import('@/views/ChatView.vue'),
        meta: { title: '对话' }
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/SettingsView.vue'),
        meta: { title: '设置' }
      },
      {
        path: 'skills',
        name: 'Skills',
        component: () => import('@/views/SkillsView.vue'),
        meta: { title: 'Skill 管理' }
      },
      {
        path: 'memories',
        name: 'Memories',
        component: () => import('@/views/MemoriesView.vue'),
        meta: { title: '记忆管理' }
      },
      {
        path: 'inspector',
        name: 'Inspector',
        component: () => import('@/views/InspectorView.vue'),
        meta: { title: '执行检查器' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
```

### 3.2 状态管理（Pinia）

```typescript
// src/stores/session.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Session, Message } from '@/types/session'

export const useSessionStore = defineStore('session', () => {
  const sessions = ref<Session[]>([])
  const currentSessionId = ref<string>('')
  const messages = ref<Message[]>([])
  const isLoading = ref(false)
  
  // 计算属性
  const currentSession = computed(() => 
    sessions.value.find(s => s.id === currentSessionId.value)
  )
  
  // 动作
  async function loadSessions() {
    const result = await window.electronAPI.listSessions()
    sessions.value = result.sessions
  }
  
  async function createSession(title: string) {
    const result = await window.electronAPI.createSession({ title })
    sessions.value.unshift(result)
    currentSessionId.value = result.id
    messages.value = []
    return result
  }
  
  async function switchSession(sessionId: string) {
    currentSessionId.value = sessionId
    // 加载该会话的消息
    await loadMessages(sessionId)
  }
  
  async function sendMessage(content: string) {
    isLoading.value = true
    try {
      // 连接 WebSocket
      const ws = window.electronAPI.connectWebSocket(currentSessionId.value)
      
      // 发送消息
      ws.send(JSON.stringify({ content }))
      
      // 监听流式响应
      window.electronAPI.onAgentMessage((data) => {
        if (data.type === 'message_chunk') {
          appendMessageChunk(data.content)
        } else if (data.type === 'step_start') {
          addStep(data.step)
        } else if (data.type === 'step_complete') {
          completeStep(data.step)
        } else if (data.type === 'error') {
          handleError(data.error)
        }
      })
    } finally {
      isLoading.value = false
    }
  }
  
  function appendMessageChunk(content: string) {
    if (messages.value.length === 0) {
      messages.value.push({
        id: generateId(),
        role: 'assistant',
        content: content,
        timestamp: new Date()
      })
    } else {
      const lastMsg = messages.value[messages.value.length - 1]
      if (lastMsg.role === 'assistant') {
        lastMsg.content += content
      } else {
        messages.value.push({
          id: generateId(),
          role: 'assistant',
          content: content,
          timestamp: new Date()
        })
      }
    }
  }
  
  function addStep(step: string) {
    // 添加到步骤面板
  }
  
  function completeStep(step: string) {
    // 标记步骤完成
  }
  
  function handleError(error: any) {
    // 显示错误
  }
  
  return {
    sessions,
    currentSessionId,
    messages,
    isLoading,
    currentSession,
    loadSessions,
    createSession,
    switchSession,
    sendMessage
  }
})
```

### 3.3 主布局组件

```vue
<!-- src/views/MainLayout.vue -->
<template>
  <div class="main-layout">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <h1 class="logo">🐰 NanamiGopher</h1>
        <button class="new-session-btn" @click="createNewSession">
          + 新对话
        </button>
      </div>
      
      <div class="session-list">
        <div
          v-for="session in sessions"
          :key="session.id"
          class="session-item"
          :class="{ active: session.id === currentSessionId }"
          @click="switchSession(session.id)"
        >
          <span class="session-title">{{ session.title || '未命名对话' }}</span>
          <span class="session-date">{{ formatDate(session.created_at) }}</span>
        </div>
      </div>
      
      <div class="sidebar-footer">
        <router-link to="/settings" class="settings-link">
          ⚙️ 设置
        </router-link>
      </div>
    </aside>
    
    <!-- 主内容区 -->
    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { useSessionStore } from '@/stores/session'
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

const sessionStore = useSessionStore()
const router = useRouter()

onMounted(async () => {
  await sessionStore.loadSessions()
})

function createNewSession() {
  sessionStore.createSession('')
  router.push('/')
}

function switchSession(sessionId: string) {
  sessionStore.switchSession(sessionId)
}

function formatDate(timestamp: string) {
  return new Date(timestamp).toLocaleDateString('zh-CN')
}
</script>

<style scoped>
.main-layout {
  display: flex;
  height: 100vh;
}

.sidebar {
  width: 280px;
  background: #1a1a1a;
  color: #fff;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid #333;
}

.logo {
  font-size: 18px;
  margin: 0 0 12px 0;
}

.new-session-btn {
  width: 100%;
  padding: 8px;
  background: #0066cc;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.session-list {
  flex: 1;
  overflow-y: auto;
}

.session-item {
  padding: 12px 16px;
  cursor: pointer;
  border-bottom: 1px solid #333;
}

.session-item:hover {
  background: #2a2a2a;
}

.session-item.active {
  background: #0066cc;
}

.session-title {
  display: block;
  font-size: 14px;
}

.session-date {
  display: block;
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid #333;
}

.settings-link {
  color: #999;
  text-decoration: none;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}
</style>
```

### 3.4 对话视图

```vue
<!-- src/views/ChatView.vue -->
<template>
  <div class="chat-view">
    <!-- 步骤面板 -->
    <StepPanel v-if="steps.length > 0" :steps="steps" />
    
    <!-- 消息列表 -->
    <div class="message-list" ref="messageListRef">
      <MessageBubble
        v-for="message in messages"
        :key="message.id"
        :message="message"
      />
      
      <!-- 加载指示器 -->
      <div v-if="isLoading" class="loading-indicator">
        <LoadingSpinner />
        <span>Agent 正在思考...</span>
      </div>
    </div>
    
    <!-- 输入框 -->
    <div class="input-area">
      <InputBox
        v-model="inputContent"
        @submit="handleSendMessage"
        :disabled="isLoading"
      />
    </div>
    
    <!-- 审批对话框 -->
    <ApprovalDialog
      v-if="showApproval"
      :approval="currentApproval"
      @approve="handleApprove"
      @reject="handleReject"
    />
    
    <!-- 接管通知 -->
    <TakeoverNotification
      v-if="showTakeover"
      :takeover="currentTakeover"
      @accept="handleAcceptTakeover"
      @dismiss="handleDismissTakeover"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useSessionStore } from '@/stores/session'
import StepPanel from '@/components/StepPanel/StepPanel.vue'
import MessageBubble from '@/components/ChatArea/MessageBubble.vue'
import InputBox from '@/components/ChatArea/InputBox.vue'
import LoadingSpinner from '@/components/Common/LoadingSpinner.vue'
import ApprovalDialog from '@/components/Approval/ApprovalDialog.vue'
import TakeoverNotification from '@/components/Takeover/TakeoverNotification.vue'

const sessionStore = useSessionStore()
const inputContent = ref('')
const isLoading = ref(false)
const steps = ref<any[]>([])
const messageListRef = ref<HTMLDivElement>()

// 审批和接管状态
const showApproval = ref(false)
const currentApproval = ref(null)
const showTakeover = ref(false)
const currentTakeover = ref(null)

onMounted(() => {
  // 监听审批请求
  window.electronAPI.onAgentMessage((data) => {
    if (data.type === 'approval_request') {
      showApproval.value = true
      currentApproval.value = data.data
    } else if (data.type === 'takeover_request') {
      showTakeover.value = true
      currentTakeover.value = data.data
    }
  })
})

async function handleSendMessage() {
  if (!inputContent.value.trim() || isLoading.value) return
  
  const content = inputContent.value
  inputContent.value = ''
  
  // 添加用户消息
  sessionStore.messages.push({
    id: generateId(),
    role: 'user',
    content: content,
    timestamp: new Date()
  })
  
  isLoading.value = true
  
  try {
    await sessionStore.sendMessage(content)
  } finally {
    isLoading.value = false
  }
  
  // 滚动到底部
  await nextTick()
  scrollToBottom()
}

function handleApprove(decision: any) {
  showApproval.value = false
  // 提交审批决策
}

function handleReject() {
  showApproval.value = false
}

function handleAcceptTakeover() {
  showTakeover.value = false
  // 接受接管
}

function handleDismissTakeover() {
  showTakeover.value = false
}

function scrollToBottom() {
  if (messageListRef.value) {
    messageListRef.value.scrollTop = messageListRef.value.scrollHeight
  }
}

function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).substr(2)
}
</script>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.message-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.loading-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px;
  color: #999;
}

.input-area {
  padding: 16px;
  border-top: 1px solid #eee;
}
</style>
```

### 3.5 消息气泡组件

```vue
<!-- src/components/ChatArea/MessageBubble.vue -->
<template>
  <div class="message-bubble" :class="[message.role]">
    <div class="avatar">
      <span v-if="message.role === 'user'" class="user-avatar">👤</span>
      <span v-else class="assistant-avatar">🤖</span>
    </div>
    <div class="content">
      <div class="timestamp">{{ formatTime(message.timestamp) }}</div>
      <div class="text" v-html="renderContent(message.content)"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineProps } from 'vue'
import type { Message } from '@/types/session'

const props = defineProps<{
  message: Message
}>()

function formatTime(timestamp: Date) {
  return timestamp.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

function renderContent(content: string) {
  // 简单的 Markdown 渲染
  // 实际项目应该使用 marked 或 similar 库
  return content
    .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}
</script>

<style scoped>
.message-bubble {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.message-bubble.user {
  flex-direction: row-reverse;
}

.avatar {
  flex-shrink: 0;
}

.user-avatar,
.assistant-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  background: #f0f0f0;
}

.content {
  max-width: 70%;
}

.timestamp {
  font-size: 12px;
  color: #999;
  margin-bottom: 4px;
}

.text {
  padding: 12px;
  background: #f5f5f5;
  border-radius: 8px;
  line-height: 1.6;
}

.user .text {
  background: #0066cc;
  color: #fff;
}
</style>
```

### 3.6 步骤面板组件

```vue
<!-- src/components/StepPanel/StepPanel.vue -->
<template>
  <div class="step-panel">
    <div class="panel-header" @click="toggleCollapse">
      <h3>步骤面板</h3>
      <span class="collapse-icon">{{ collapsed ? '▶' : '▼' }}</span>
    </div>
    
    <div v-if="!collapsed" class="panel-body">
      <div
        v-for="step in steps"
        :key="step.id"
        class="step-item"
        :class="step.status"
      >
        <span class="step-icon">
          <span v-if="step.status === 'running'">🔍</span>
          <span v-else-if="step.status === 'completed'">✓</span>
          <span v-else-if="step.status === 'waiting'">⏳</span>
          <span v-else-if="step.status === 'failed'">✗</span>
        </span>
        <span class="step-name">{{ step.name }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  steps: any[]
}>()

const collapsed = ref(false)

function toggleCollapse() {
  collapsed.value = !collapsed.value
}
</script>

<style scoped>
.step-panel {
  background: #f9f9f9;
  border-bottom: 1px solid #eee;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  cursor: pointer;
}

.panel-body {
  padding: 8px 16px;
}

.step-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  font-size: 14px;
}

.step-item.running {
  color: #0066cc;
}

.step-item.completed {
  color: #28a745;
}

.step-item.waiting {
  color: #ffc107;
}

.step-item.failed {
  color: #dc3545;
}
</style>
```

---

## 5. 样式设计

### 5.1 主题配置

```typescript
// src/styles/theme.ts
export const theme = {
  colors: {
    primary: '#0066cc',
    success: '#28a745',
    warning: '#ffc107',
    danger: '#dc3545',
    text: '#333333',
    textSecondary: '#666666',
    background: '#ffffff',
    backgroundSecondary: '#f5f5f5',
    border: '#e0e0e0'
  },
  darkMode: {
    colors: {
      background: '#1a1a1a',
      backgroundSecondary: '#2a2a2a',
      text: '#ffffff',
      textSecondary: '#cccccc',
      border: '#444444'
    }
  }
}
```

### 5.2 全局样式

```scss
// src/styles/global.scss
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  -webkit-font-smoothing: antialiased;
}

#app {
  width: 100vw;
  height: 100vh;
}

::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: #f1f1f1;
}

::-webkit-scrollbar-thumb {
  background: #888;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #555;
}
```

---

## 6. Inspector 执行检查器页面设计

### 6.1 Inspector 主页面

```vue
<!-- src/views/InspectorView.vue -->
<template>
  <div class="inspector-view">
    <div class="inspector-header">
      <h2>🔍 执行检查器</h2>
      <div class="header-actions">
        <button @click="toggleSaveHistory" :class="{ active: saveHistory }">
          {{ saveHistory ? '💾 记录已开启' : '💾 记录已关闭' }}
        </button>
        <button @click="clearCompleted">清除已完成</button>
      </div>
    </div>
    
    <!-- 对话卡片列表 -->
    <div class="card-list">
      <InspectorCard
        v-for="card in activeCards"
        :key="card.session_id"
        :card="card"
        :expanded="expandedSessions.includes(card.session_id)"
        @expand="toggleExpand(card.session_id)"
        @collapse="toggleCollapse(card.session_id)"
        @stop="stopSession(card.session_id)"
        @pause="pauseSession(card.session_id)"
        @tool-detail="showToolDetail(card.session_id)"
      />
      
      <InspectorCard
        v-for="card in completedCards"
        :key="card.session_id"
        :card="card"
        :expanded="expandedSessions.includes(card.session_id)"
        @expand="toggleExpand(card.session_id)"
        @collapse="toggleCollapse(card.session_id)"
        @tool-detail="showToolDetail(card.session_id)"
      />
      
      <InspectorCard
        v-for="card in failedCards"
        :key="card.session_id"
        :card="card"
        :expanded="expandedSessions.includes(card.session_id)"
        @expand="toggleExpand(card.session_id)"
        @collapse="toggleCollapse(card.session_id)"
        @tool-detail="showToolDetail(card.session_id)"
      />
      
      <div v-if="allCards.length === 0" class="empty-state">
        <p>暂无执行的对话</p>
      </div>
    </div>
    
    <!-- 维度选择器 -->
    <DimensionSelector
      v-if="currentTimeline"
      :dimensions="currentTimelineDimensions"
      @change="updateDimensions"
    />
    
    <!-- 工具详情弹窗 -->
    <ToolDetailDialog
      v-if="showToolDialog"
      :tool-info="selectedTool"
      @close="showToolDialog = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import InspectorCard from '@/components/Inspector/InspectorCard.vue'
import DimensionSelector from '@/components/Inspector/DimensionSelector.vue'
import ToolDetailDialog from '@/components/Inspector/ToolDetailDialog.vue'

// 卡片状态
const activeCards = ref<any[]>([])
const completedCards = ref<any[]>([])
const failedCards = ref<any[]>([])
const expandedSessions = ref<string[]>([])
const currentTimeline = ref<any[]>([])
const currentTimelineDimensions = ref<string[]>(['task', 'tool', 'model'])
const saveHistory = ref(false)
const showToolDialog = ref(false)
const selectedTool = ref<any>(null)

// WebSocket 连接
let inspectorWs: WebSocket | null = null

onMounted(() => {
  connectInspector()
  loadCards()
  loadSettings()
})

onUnmounted(() => {
  inspectorWs?.close()
})

async function connectInspector() {
  inspectorWs = new WebSocket('ws://localhost:8080/api/v1/inspector/ws')
  
  inspectorWs.onmessage = (event) => {
    const data = JSON.parse(event.data)
    
    switch (data.type) {
      case 'card_update':
        handleCardUpdate(data.data)
        break
      case 'timeline_node':
        addTimelineNode(data.data)
        break
    }
  }
  
  inspectorWs.onclose = () => {
    // 断线重连
    setTimeout(connectInspector, 3000)
  }
}

async function loadCards() {
  const res = await fetch('/api/v1/inspector/cards')
  const data = await res.json()
  
  activeCards.value = data.cards.filter(c => c.status === 'running')
  completedCards.value = data.cards.filter(c => c.status === 'completed')
  failedCards.value = data.cards.filter(c => c.status === 'failed')
}

async function loadTimeline(sessionId: string) {
  const dims = currentTimelineDimensions.value.join(',')
  const res = await fetch(`/api/v1/inspector/sessions/${sessionId}/timeline?dimensions=${dims}`)
  const data = await res.json()
  currentTimeline.value = data.nodes
}

function toggleExpand(sessionId: string) {
  if (!expandedSessions.value.includes(sessionId)) {
    expandedSessions.value.push(sessionId)
    loadTimeline(sessionId)
  }
}

function toggleCollapse(sessionId: string) {
  expandedSessions.value = expandedSessions.value.filter(id => id !== sessionId)
  currentTimeline.value = []
}

function stopSession(sessionId: string) {
  // TODO: 调用停止 API
}

function pauseSession(sessionId: string) {
  // TODO: 调用暂停 API
}

function showToolDetail(sessionId: string) {
  // TODO: 加载工具详情
}

function updateDimensions(dims: string[]) {
  currentTimelineDimensions.value = dims
  // 重新加载时间线
}

function loadSettings() {
  // 加载用户设置
}

function toggleSaveHistory() {
  saveHistory.value = !saveHistory.value
  // 保存设置
}

const allCards = computed(() => [
  ...activeCards.value,
  ...completedCards.value,
  ...failedCards.value
])
</script>
```

### 6.2 Inspector 卡片组件

```vue
<!-- src/components/Inspector/InspectorCard.vue -->
<template>
  <div class="inspector-card" :class="[card.status, { expanded }]">
    <!-- 卡片头部（始终可见） -->
    <div class="card-header" @click="toggleExpand">
      <span class="status-icon">
        <span v-if="card.status === 'running'">⏳</span>
        <span v-else-if="card.status === 'completed'">✅</span>
        <span v-else-if="card.status === 'failed'">❌</span>
        <span v-else-if="card.status === 'paused'">⏸</span>
      </span>
      
      <div class="card-info">
        <h3 class="card-title">{{ card.title }}</h3>
        <div class="card-meta">
          <span v-if="card.status === 'running'">
            {{ card.current_step || '运行中' }}
          </span>
          <span v-else>{{ card.total_duration_sec || 0 }}秒</span>
        </div>
      </div>
      
      <div class="card-stats">
        <span class="stat" :title="`运行时间: ${card.running_duration_sec || card.total_duration_sec || 0}秒`">
          ⏱ {{ formatDuration(card) }}
        </span>
        <span class="stat" :title="`当前步骤: ${card.current_step || '-'}`">
          📝 {{ card.current_step ? card.current_step.substring(0, 15) + '...' : '-' }}
        </span>
        <span class="stat" :title="`Token 消耗`">
          💰 {{ formatNumber(card.token_count) }}
        </span>
        <span class="stat" :title="`工具调用次数`">
          🔧 {{ card.tool_call_count || 0 }}
        </span>
        <span class="stat" :title="`SubAgent: 运行中 ${card.subagent_running || 0} / 完成 ${card.subagent_completed || 0}`">
          👥 {{ card.subagent_running || 0 }}/{{ card.subagent_completed || 0 }}
        </span>
      </div>
      
      <span class="expand-icon">{{ expanded ? '▲' : '▼' }}</span>
    </div>
    
    <!-- 卡片操作按钮 -->
    <div class="card-actions" v-if="card.status === 'running'">
      <button @click.stop="handlePause" class="btn-pause">⏸ 暂停</button>
      <button @click.stop="handleStop" class="btn-stop">■ 停止</button>
      <button @click.stop="$emit('tool-detail')" class="btn-detail">🔍 工具详情</button>
    </div>
    
    <!-- 展开的时间线 -->
    <div v-if="expanded" class="card-timeline">
      <div v-if="timeline.length === 0" class="timeline-loading">
        加载中...
      </div>
      
      <div v-else class="timeline-nodes">
        <TimelineNode
          v-for="node in timeline"
          :key="node.node_id"
          :node="node"
          :depth="0"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import TimelineNode from './TimelineNode.vue'

const props = defineProps<{
  card: any
  expanded: boolean
}>()

const emit = defineEmits(['expand', 'collapse', 'pause', 'stop', 'tool-detail'])

const timeline = ref<any[]>([])

function toggleExpand() {
  if (props.expanded) {
    emit('collapse', props.card.session_id)
  } else {
    emit('expand', props.card.session_id)
  }
}

function handlePause() {
  emit('pause', props.card.session_id)
}

function handleStop() {
  emit('stop', props.card.session_id)
}

function formatDuration(card: any): string {
  const sec = card.running_duration_sec || card.total_duration_sec || 0
  const min = Math.floor(sec / 60)
  const s = sec % 60
  return min > 0 ? `${min}分${s}秒` : `${s}秒`
}

function formatNumber(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}K`
  return String(n)
}

watch(() => props.expanded, (val) => {
  if (val) {
    // 加载时间线数据
    fetchTimeline()
  } else {
    timeline.value = []
  }
})

async function fetchTimeline() {
  // TODO: 从 API 加载
}
</script>
```

### 6.3 时间线节点组件

```vue
<!-- src/components/Inspector/TimelineNode.vue -->
<template>
  <div class="timeline-node" :class="[node.node_type, node.status]" :style="{ marginLeft: depth * 20 + 'px' }">
    <!-- 节点头部 -->
    <div class="node-header">
      <span class="node-icon">
        <span v-if="node.node_type === 'task'">📋</span>
        <span v-else-if="node.node_type === 'subagent'">👥</span>
        <span v-else-if="node.node_type === 'tool'">🔧</span>
        <span v-else-if="node.node_type === 'model'">🤖</span>
        <span v-else-if="node.node_type === 'error'">⚠️</span>
      </span>
      <span class="node-title">{{ node.title }}</span>
      <span class="node-status">
        <span v-if="node.status === 'running'">⏳</span>
        <span v-else-if="node.status === 'completed'">✅</span>
        <span v-else-if="node.status === 'failed'">❌</span>
        <span v-else-if="node.status === 'paused'">⏸</span>
      </span>
      <span v-if="node.duration_ms" class="node-duration">
        {{ node.duration_ms }}ms
      </span>
    </div>
    
    <!-- 节点详情 -->
    <div v-if="node.details" class="node-details">
      <div v-if="node.node_type === 'tool'" class="detail-section">
        <strong>工具:</strong> {{ node.details.tool_name }}
        <div v-if="node.details.arguments" class="detail-args">
          <strong>参数:</strong> {{ JSON.stringify(node.details.arguments) }}
        </div>
        <div v-if="node.details.return_value_length" class="detail-return">
          <strong>返回:</strong> {{ node.details.return_value_length }} 字符
        </div>
      </div>
      <div v-else-if="node.node_type === 'model'" class="detail-section">
        <strong>模型:</strong> {{ node.details.model }}
        <div class="detail-stats">
          <span>输入: {{ node.details.input_tokens || 0 }} tokens</span>
          <span>输出: {{ node.details.output_tokens || 0 }} tokens</span>
          <span v-if="node.details.cost_usd">费用: ${{ node.details.cost_usd }}</span>
        </div>
      </div>
      <div v-else-if="node.node_type === 'error'" class="detail-section error-detail">
        <strong>错误:</strong> {{ node.details.error || node.details.message }}
        <div v-if="node.details.retry_count" class="retry-info">
          重试次数: {{ node.details.retry_count }}
        </div>
      </div>
    </div>
    
    <!-- 子节点 -->
    <div v-if="node.children && node.children.length > 0" class="node-children">
      <TimelineNode
        v-for="child in node.children"
        :key="child.node_id"
        :node="child"
        :depth="depth + 1"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  node: any
  depth: number
}>()
</script>
```

### 6.4 维度选择器组件

```vue
<!-- src/components/Inspector/DimensionSelector.vue -->
<template>
  <div class="dimension-selector">
    <span class="label">显示维度:</span>
    <label v-for="dim in availableDimensions" :key="dim.value" class="dimension-item">
      <input
        type="checkbox"
        :value="dim.value"
        :checked="dimensions.includes(dim.value)"
        @change="toggleDimension(dim.value)"
      />
      {{ dim.label }}
    </label>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  dimensions: string[]
}>()

const emit = defineEmits(['change'])

const availableDimensions = [
  { value: 'task', label: '📋 任务分解' },
  { value: 'subagent', label: '👥 SubAgent' },
  { value: 'tool', label: '🔧 工具调用' },
  { value: 'model', label: '🤖 模型调用' },
  { value: 'event', label: '📡 事件流' },
  { value: 'error', label: '⚠️ 异常处理' },
]

function toggleDimension(value: string) {
  const dims = props.dimensions.includes(value)
    ? props.dimensions.filter(d => d !== value)
    : [...props.dimensions, value]
  emit('change', dims)
}
</script>
```

---

## 7. 构建与部署

### 7.1 Vite 配置

```typescript
// vite.config.ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  },
  base: './',  // Electron 需要相对路径
  build: {
    outDir: 'dist',
    emptyOutDir: true
  }
})
```

### 7.2 Electron Builder 配置

```yaml
# electron-builder.yml
appId: com.nanamigopher.app
productName: NanamiGopher
directories:
  output: release
mac:
  category: public.category.developer-tools
win:
  target:
    - target: nsis
      arch: [x64]
linux:
  target:
    - target: AppImage
      arch: [x64]
files:
  - dist/**/*
  - electron/**/*
extraResources:
  - go-gateway
  - python-agent
```

### 7.3 打包脚本

```json
// package.json
{
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc && vite build",
    "electron:dev": "concurrently \"vite\" \"wait-on http://localhost:5173 && electron .\"",
    "electron:build": "npm run build && electron-builder",
    "electron:preview": "npm run build && electron ."
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "concurrently": "^8.2.0",
    "electron": "^28.0.0",
    "electron-builder": "^24.0.0",
    "typescript": "^5.0.0",
    "vite": "^5.0.0",
    "vue-tsc": "^1.8.0"
  },
  "dependencies": {
    "pinia": "^2.1.0",
    "vue": "^3.4.0",
    "vue-router": "^4.2.0",
    "element-plus": "^2.4.0"
  }
}
```

---

## 8. 附录

### 8.1 开发指南

```bash
# 安装依赖
npm install

# 开发模式
npm run electron:dev

# 构建生产版本
npm run electron:build

# 预览生产版本
npm run electron:preview
```

### 8.2 常见问题

**Q: 如何调试 Electron 应用？**

A: 在开发模式下，按 `Ctrl+Shift+I` (Windows/Linux) 或 `Cmd+Option+I` (macOS) 打开 DevTools。

**Q: 如何打包为安装包？**

A: 运行 `npm run electron:build`，安装包会在 `release/` 目录生成。

**Q: 如何切换主题？**

A: 在设置页面切换主题，配置会保存到 localStorage。
