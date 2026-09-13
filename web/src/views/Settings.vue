/**
 * 设置页
 *
 * 模型配置、API Key 管理、权限策略、搜索引擎配置。
 */

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useSettingsStore } from '@/stores/settings'

const settings = useSettingsStore()
const activeTab = ref<'models' | 'credentials' | 'search' | 'permissions'>('models')
const saving = ref(false)

onMounted(() => {
  settings.loadSettings()
})

async function handleSaveModels() {
  await settings.saveModels({
    prefer_local: settings.models.preferLocal,
    chat: settings.models.chat,
    embedding: settings.models.embedding,
  })
}

async function handleSaveCredential(service: string) {
  const key = service === 'duckduckgo' ? '' : (settings.searchEngines.providers[service as keyof typeof settings.searchEngines.providers]?.apiKey || '')
  if (key) {
    await settings.saveCredential(service, key)
  }
}

async function handleSavePermissions() {
  await settings.savePermissions(settings.permissions)
}
</script>

<template>
  <div class="settings-page">
    <h1>设置</h1>

    <!-- Tab 导航 -->
    <div class="settings-tabs">
      <button
        :class="{ active: activeTab === 'models' }"
        @click="activeTab = 'models'"
      >
        模型配置
      </button>
      <button
        :class="{ active: activeTab === 'credentials' }"
        @click="activeTab = 'credentials'"
      >
        API Key
      </button>
      <button
        :class="{ active: activeTab === 'search' }"
        @click="activeTab = 'search'"
      >
        搜索引擎
      </button>
      <button
        :class="{ active: activeTab === 'permissions' }"
        @click="activeTab = 'permissions'"
      >
        权限
      </button>
    </div>

    <!-- 模型配置 -->
    <section v-if="activeTab === 'models'" class="settings-section">
      <h2>模型配置</h2>
      <p class="hint">
        模型名称由用户在设置页面自行配置，配置文件不绑定任何具体模型。
      </p>

      <div class="form-group">
        <label>优先使用本地模型</label>
        <input type="checkbox" v-model="settings.models.preferLocal" />
      </div>

      <div class="form-group">
        <label>本地模型回退顺序</label>
        <div class="fallback-order">
          <span
            v-for="(model, idx) in settings.models.localFallbackOrder"
            :key="idx"
            class="fallback-tag"
          >
            {{ model }}
          </span>
        </div>
      </div>

      <div class="form-group">
        <label>Chat 模型（默认）</label>
        <input
          v-model="settings.models.chat.default"
          type="text"
          placeholder="例如: qwen2.5:32b, gpt-4o"
        />
      </div>

      <div class="form-group">
        <label>Chat 模型（备用）</label>
        <input
          v-model="settings.models.chat.fallback"
          type="text"
          placeholder="例如: gpt-4o"
        />
      </div>

      <div class="form-group">
        <label>Embedding 提供商</label>
        <select v-model="settings.models.embedding.provider">
          <option value="">未配置</option>
          <option value="bge">BGE-M3（本地）</option>
          <option value="openai">OpenAI Embeddings</option>
        </select>
      </div>

      <div class="form-group" v-if="settings.models.embedding.provider === 'bge'">
        <label>BGE 设备</label>
        <select v-model="settings.models.embedding.bge?.device">
          <option value="cpu">CPU</option>
          <option value="cuda">CUDA (GPU)</option>
        </select>
      </div>

      <button
        class="btn-primary"
        :disabled="saving || !settings.models.chat.default"
        @click="handleSaveModels"
      >
        {{ saving ? '保存中...' : '保存模型配置' }}
      </button>
    </section>

    <!-- API Key 管理 -->
    <section v-if="activeTab === 'credentials'" class="settings-section">
      <h2>API Key 管理</h2>
      <p class="hint">
        所有第三方服务的 API Key 通过操作系统密钥链（Keychain）安全存储。
      </p>

      <div
        v-for="service in ['tavily', 'google', 'duckduckgo']"
        :key="service"
        class="credential-card"
      >
        <div class="credential-header">
          <span class="credential-name">{{ service }}</span>
          <span
            class="credential-status"
            :class="credentials[service]?.configured ? 'configured' : 'not-configured'"
          >
            {{ credentials[service]?.configured ? '已配置' : '未配置' }}
          </span>
        </div>

        <div class="credential-body">
          <input
            v-if="!credentials[service]?.configured"
            v-model="searchProviders[service]?.apiKey"
            type="password"
            :placeholder="`输入 ${service} API Key`"
          />
          <template v-else>
            <p class="masked-key">****{{ credentials[service]?.updated_at ? credentials[service].updated_at.slice(-8) : '' }}</p>
            <button class="btn-small" @click="handleSaveCredential(service)">更新</button>
            <button class="btn-small btn-danger" @click="settings.deleteCredential(service)">删除</button>
          </template>
        </div>
      </div>
    </section>

    <!-- 搜索引擎配置 -->
    <section v-if="activeTab === 'search'" class="settings-section">
      <h2>搜索引擎配置</h2>

      <div class="form-group">
        <label>默认搜索引擎</label>
        <select v-model="settings.searchEngines.default">
          <option value="duckduckgo">DuckDuckGo（免费）</option>
          <option value="tavily">Tavily</option>
          <option value="google">Google Custom Search</option>
        </select>
      </div>

      <div
        v-for="(provider, name) in settings.searchEngines.providers"
        :key="name"
        class="form-group"
      >
        <label>
          <input type="checkbox" v-model="provider.enabled" />
          启用 {{ name }}
        </label>
        <input
          v-if="provider.enabled && provider.apiKey !== undefined"
          v-model="provider.apiKey"
          type="password"
          :placeholder="`API Key (${name})`"
        />
      </div>

      <button
        class="btn-primary"
        :disabled="saving"
        @click="handleSaveModels"
      >
        保存搜索引擎配置
      </button>
    </section>

    <!-- 权限设置 -->
    <section v-if="activeTab === 'permissions'" class="settings-section">
      <h2>权限设置</h2>

      <div class="form-group">
        <label>默认权限模式</label>
        <select v-model="settings.permissions.defaultMode">
          <option value="manual">Manual（每次确认）</option>
          <option value="accept_edits">Accept Edits（仅编辑确认）</option>
          <option value="plan">Plan（仅规划）</option>
          <option value="auto">Auto（自动执行）</option>
        </select>
      </div>

      <div class="form-group">
        <label>
          <input type="checkbox" v-model="settings.permissions.circuitBreakerEnabled" />
          启用熔断器
        </label>
      </div>

      <button
        class="btn-primary"
        :disabled="saving"
        @click="handleSavePermissions"
      >
        保存权限设置
      </button>
    </section>

    <!-- 全局错误提示 -->
    <div v-if="settings.error" class="error-banner">
      {{ settings.error }}
    </div>
  </div>
</template>

<script lang="ts">
// 局部计算属性辅助
import { computed } from 'vue'

const credentials = computed(() => settings.credentials)
const searchProviders = computed(() => settings.searchEngines.providers)
</script>

<style scoped lang="scss">
.settings-page {
  padding: 24px;
  max-width: 800px;
}

.settings-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
  border-bottom: 1px solid var(--border-color);

  button {
    padding: 8px 16px;
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    cursor: pointer;
    font-size: 14px;
    color: var(--text-secondary);

    &.active {
      color: var(--text-primary);
      border-bottom-color: var(--primary-color);
    }

    &:hover {
      color: var(--text-primary);
    }
  }
}

.settings-section {
  margin-bottom: 32px;

  h2 {
    font-size: 18px;
    margin-bottom: 16px;
  }

  .hint {
    font-size: 13px;
    color: var(--text-secondary);
    margin-bottom: 16px;
  }
}

.form-group {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;

  label {
    min-width: 160px;
    font-weight: 500;
  }

  input[type="text"],
  input[type="password"],
  select {
    flex: 1;
    padding: 8px 12px;
    border: 1px solid var(--border-color);
    border-radius: 6px;
    background: var(--bg-input);
    color: var(--text-primary);
    font-size: 14px;

    &:focus {
      outline: none;
      border-color: var(--primary-color);
    }
  }

  input[type="checkbox"] {
    width: 18px;
    height: 18px;
  }
}

.fallback-order {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.fallback-tag {
  padding: 4px 12px;
  background: var(--bg-muted);
  border-radius: 12px;
  font-size: 13px;
}

.credential-card {
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
}

.credential-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.credential-name {
  font-weight: 600;
  text-transform: capitalize;
}

.credential-status {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;

  &.configured {
    background: #d4edda;
    color: #155724;
  }

  &.not-configured {
    background: #f8d7da;
    color: #721c24;
  }
}

.credential-body {
  display: flex;
  gap: 8px;
  align-items: center;

  input {
    flex: 1;
  }
}

.btn-small {
  padding: 4px 12px;
  font-size: 12px;
  border-radius: 4px;
  border: 1px solid var(--border-color);
  background: var(--bg-muted);
  cursor: pointer;

  &.btn-danger {
    color: #dc3545;
    border-color: #dc3545;
  }
}

.btn-primary {
  padding: 8px 24px;
  background: var(--primary-color);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  &:hover:not(:disabled) {
    opacity: 0.9;
  }
}

.error-banner {
  margin-top: 16px;
  padding: 12px;
  background: #fff3f3;
  color: #c00;
  border-radius: 6px;
  font-size: 14px;
}
</style>
