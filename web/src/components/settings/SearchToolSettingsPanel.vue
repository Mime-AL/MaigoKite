<script setup lang="ts">
import { computed, ref } from 'vue'
import IconSymbol from '@/components/common/IconSymbol.vue'
import { useSettingsStore } from '@/stores/settings'

const settings = useSettingsStore()
const tavilyKey = ref('')
const googleKey = ref('')
const googleCx = ref('')
const busyService = ref('')

const tavilyConfigured = computed(() => settings.credentials.tavily?.configured === true)
const googleConfigured = computed(() => settings.credentials.google?.configured === true)

async function saveTavily() {
  const value = tavilyKey.value.trim()
  if (!value || busyService.value) return
  busyService.value = 'tavily'
  if (await settings.saveCredential('tavily', value)) tavilyKey.value = ''
  busyService.value = ''
}

async function saveGoogle() {
  const key = googleKey.value.trim()
  const cx = googleCx.value.trim()
  if (!key || !cx || busyService.value) return
  busyService.value = 'google'
  if (await settings.saveCredential('google', `${key}:${cx}`)) {
    googleKey.value = ''
    googleCx.value = ''
  }
  busyService.value = ''
}

async function remove(service: 'tavily' | 'google') {
  if (busyService.value) return
  busyService.value = service
  await settings.deleteCredential(service)
  busyService.value = ''
}
</script>

<template>
  <section class="tool-settings glass-card">
    <header class="tool-heading">
      <span class="section-icon"><IconSymbol name="globe" :size="21" /></span>
      <div>
        <h2>联网搜索</h2>
        <p>默认使用无需密钥的 DuckDuckGo；配置服务后会优先使用可用的 API。</p>
      </div>
    </header>

    <article class="provider-row">
      <div class="provider-summary">
        <span class="provider-mark duck">D</span>
        <div><strong>DuckDuckGo</strong><small>无需密钥，能否访问取决于当前网络。</small></div>
        <span class="status"><i />无需配置</span>
      </div>
    </article>

    <article class="provider-row configurable">
      <div class="provider-summary">
        <span class="provider-mark tavily">T</span>
        <div><strong>Tavily</strong><small>面向 Agent 的搜索 API，配置后优先使用。</small></div>
        <span class="status" :class="tavilyConfigured ? 'ready' : 'missing'"
          ><i />{{ tavilyConfigured ? '已配置' : '未配置' }}</span
        >
      </div>
      <div class="credential-form">
        <input
          v-model="tavilyKey"
          type="password"
          autocomplete="new-password"
          :placeholder="tavilyConfigured ? '输入新 Key 可替换现有凭证' : 'Tavily API Key'"
        />
        <button class="primary-button" type="button" :disabled="!tavilyKey.trim() || !!busyService" @click="saveTavily">
          {{ busyService === 'tavily' ? '保存中…' : '保存' }}
        </button>
        <button
          v-if="tavilyConfigured"
          class="plain-button danger"
          type="button"
          :disabled="!!busyService"
          @click="remove('tavily')"
        >
          移除
        </button>
      </div>
    </article>

    <article class="provider-row configurable">
      <div class="provider-summary">
        <span class="provider-mark google">G</span>
        <div><strong>Google Programmable Search</strong><small>需要 API Key 和搜索引擎 ID（CX）。</small></div>
        <span class="status" :class="googleConfigured ? 'ready' : 'missing'"
          ><i />{{ googleConfigured ? '已配置' : '未配置' }}</span
        >
      </div>
      <div class="credential-form google-form">
        <input
          v-model="googleKey"
          type="password"
          autocomplete="new-password"
          :placeholder="googleConfigured ? '输入新 Key 可替换现有凭证' : 'Google API Key'"
        />
        <input v-model="googleCx" type="text" autocomplete="off" placeholder="搜索引擎 ID（CX）" />
        <button
          class="primary-button"
          type="button"
          :disabled="!googleKey.trim() || !googleCx.trim() || !!busyService"
          @click="saveGoogle"
        >
          {{ busyService === 'google' ? '保存中…' : '保存' }}
        </button>
        <button
          v-if="googleConfigured"
          class="plain-button danger"
          type="button"
          :disabled="!!busyService"
          @click="remove('google')"
        >
          移除
        </button>
      </div>
    </article>
  </section>
</template>

<style scoped lang="scss">
@use '@/styles/search-tool-settings';
</style>
