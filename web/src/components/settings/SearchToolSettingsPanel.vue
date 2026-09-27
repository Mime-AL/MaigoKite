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
        <div><strong>DuckDuckGo</strong><small>无需配置，作为本地默认兜底。</small></div>
        <span class="status ready"><i />可用</span>
      </div>
    </article>

    <article class="provider-row configurable">
      <div class="provider-summary">
        <span class="provider-mark tavily">T</span>
        <div><strong>Tavily</strong><small>面向 Agent 的搜索 API，配置后优先使用。</small></div>
        <span class="status" :class="tavilyConfigured ? 'ready' : 'missing'"><i />{{ tavilyConfigured ? '已配置' : '未配置' }}</span>
      </div>
      <div class="credential-form">
        <input v-model="tavilyKey" type="password" autocomplete="new-password" :placeholder="tavilyConfigured ? '输入新 Key 可替换现有凭证' : 'Tavily API Key'">
        <button class="primary-button" type="button" :disabled="!tavilyKey.trim() || !!busyService" @click="saveTavily">{{ busyService === 'tavily' ? '保存中…' : '保存' }}</button>
        <button v-if="tavilyConfigured" class="plain-button danger" type="button" :disabled="!!busyService" @click="remove('tavily')">移除</button>
      </div>
    </article>

    <article class="provider-row configurable">
      <div class="provider-summary">
        <span class="provider-mark google">G</span>
        <div><strong>Google Programmable Search</strong><small>需要 API Key 和搜索引擎 ID（CX）。</small></div>
        <span class="status" :class="googleConfigured ? 'ready' : 'missing'"><i />{{ googleConfigured ? '已配置' : '未配置' }}</span>
      </div>
      <div class="credential-form google-form">
        <input v-model="googleKey" type="password" autocomplete="new-password" :placeholder="googleConfigured ? '输入新 Key 可替换现有凭证' : 'Google API Key'">
        <input v-model="googleCx" type="text" autocomplete="off" placeholder="搜索引擎 ID（CX）">
        <button class="primary-button" type="button" :disabled="!googleKey.trim() || !googleCx.trim() || !!busyService" @click="saveGoogle">{{ busyService === 'google' ? '保存中…' : '保存' }}</button>
        <button v-if="googleConfigured" class="plain-button danger" type="button" :disabled="!!busyService" @click="remove('google')">移除</button>
      </div>
    </article>

  </section>
</template>

<style scoped lang="scss">
.tool-settings { overflow: hidden; }
.tool-heading { display: flex; align-items: center; gap: 13px; padding: 20px 22px; border-bottom: 1px solid var(--border-color); }
.tool-heading h2 { margin: 0; font-size: 16px; letter-spacing: -0.025em; }
.tool-heading p { margin: 4px 0 0; color: var(--text-secondary); font-size: 10.5px; }
.section-icon { display: grid; width: 43px; height: 43px; flex: none; place-items: center; border-radius: 13px; color: #1689f8; background: rgba(22, 137, 248, 0.12); }
.provider-row { padding: 16px 22px; border-bottom: 1px solid var(--border-color); }
.provider-summary { display: flex; align-items: center; gap: 11px; }
.provider-summary > div { min-width: 0; display: flex; flex: 1; flex-direction: column; }
.provider-summary strong { font-size: 12px; }
.provider-summary small { margin-top: 3px; color: var(--text-tertiary); font-size: 9.5px; }
.provider-mark { display: grid; width: 34px; height: 34px; flex: none; place-items: center; border-radius: 10px; color: #fff; font-size: 12px; font-weight: 750; }
.provider-mark.duck { background: linear-gradient(145deg, #ef8738, #e05c28); }
.provider-mark.tavily { background: linear-gradient(145deg, #161b22, #4c5667); }
.provider-mark.google { background: linear-gradient(145deg, #4285f4, #34a853); }
.status { display: inline-flex; align-items: center; gap: 5px; flex: none; color: var(--text-tertiary); font-size: 9.5px; font-weight: 650; }
.status i { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.status.ready { color: var(--success); }
.status.missing { color: var(--warning); }
.credential-form { display: flex; gap: 8px; margin: 13px 0 0 45px; }
.credential-form input { min-width: 0; height: 36px; flex: 1; padding: 0 11px; border: 1px solid var(--border-strong); border-radius: 10px; outline: none; color: var(--text-primary); background: var(--surface-muted); font-size: 10.5px; }
.credential-form input:focus { border-color: var(--primary-color); box-shadow: 0 0 0 3px var(--focus-ring); }
.credential-form button { min-height: 36px; padding: 0 13px; border-radius: 10px; font-size: 10.5px; }
.plain-button { border: 1px solid var(--border-color); background: transparent; cursor: pointer; }
.plain-button.danger { color: var(--danger); }
@media (max-width: 700px) {
  .credential-form, .google-form { margin-left: 0; flex-wrap: wrap; }
  .credential-form input { flex-basis: 100%; }
}
</style>
