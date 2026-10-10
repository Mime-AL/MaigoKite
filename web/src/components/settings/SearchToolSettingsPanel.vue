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
        <h2>{{ $t('联网搜索') }}</h2>
        <p>{{ $t('已配置的搜索服务优先使用。') }}</p>
      </div>
    </header>

    <article class="provider-row">
      <div class="provider-summary">
        <span class="provider-mark duck">D</span>
        <div><strong>DuckDuckGo</strong></div>
        <span class="status"><i />{{ $t('无需配置') }}</span>
      </div>
    </article>

    <article class="provider-row configurable">
      <div class="provider-summary">
        <span class="provider-mark tavily">T</span>
        <div><strong>Tavily</strong></div>
        <span class="status" :class="tavilyConfigured ? 'ready' : 'missing'"
          ><i />{{ tavilyConfigured ? $t('已配置') : $t('未配置') }}</span
        >
      </div>
      <div class="credential-form">
        <input
          v-model="tavilyKey"
          type="password"
          autocomplete="new-password"
          :placeholder="tavilyConfigured ? $t('输入新 Key 可替换现有凭证') : 'Tavily API Key'"
        />
        <button class="primary-button" type="button" :disabled="!tavilyKey.trim() || !!busyService" @click="saveTavily">
          {{ busyService === 'tavily' ? $t('保存中…') : $t('保存') }}
        </button>
        <button
          v-if="tavilyConfigured"
          class="plain-button danger"
          type="button"
          :disabled="!!busyService"
          @click="remove('tavily')"
        >{{ $t('移除') }}</button>
      </div>
    </article>

    <article class="provider-row configurable">
      <div class="provider-summary">
        <span class="provider-mark google">G</span>
        <div><strong>Google Programmable Search</strong></div>
        <span class="status" :class="googleConfigured ? 'ready' : 'missing'"
          ><i />{{ googleConfigured ? $t('已配置') : $t('未配置') }}</span
        >
      </div>
      <div class="credential-form google-form">
        <input
          v-model="googleKey"
          type="password"
          autocomplete="new-password"
          :placeholder="googleConfigured ? $t('输入新 Key 可替换现有凭证') : 'Google API Key'"
        />
        <input v-model="googleCx" type="text" autocomplete="off" :placeholder="$t('搜索引擎 ID（CX）')" />
        <button
          class="primary-button"
          type="button"
          :disabled="!googleKey.trim() || !googleCx.trim() || !!busyService"
          @click="saveGoogle"
        >
          {{ busyService === 'google' ? $t('保存中…') : $t('保存') }}
        </button>
        <button
          v-if="googleConfigured"
          class="plain-button danger"
          type="button"
          :disabled="!!busyService"
          @click="remove('google')"
        >{{ $t('移除') }}</button>
      </div>
    </article>
  </section>
</template>

<style scoped lang="scss">
@use '@/styles/search-tool-settings';
</style>
