<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import IconSymbol from '@/components/common/IconSymbol.vue'
import ModelSettingsPanel from '@/components/settings/ModelSettingsPanel.vue'
import PermissionSettingsPanel from '@/components/settings/PermissionSettingsPanel.vue'
import RuntimeStatusPanel from '@/components/settings/RuntimeStatusPanel.vue'
import SearchToolSettingsPanel from '@/components/settings/SearchToolSettingsPanel.vue'
import { useSettingsStore } from '@/stores/settings'

type SettingsTab = 'models' | 'tools' | 'permissions' | 'workspace' | 'general'

const settings = useSettingsStore()
const route = useRoute()
const router = useRouter()
const isSettingsTab = (value: unknown): value is SettingsTab =>
  ['models', 'tools', 'permissions', 'workspace', 'general'].includes(String(value))
const activeTab = ref<SettingsTab>(isSettingsTab(route.query.tab) ? route.query.tab : 'models')
const profileDraft = reactive({ assistantName: settings.profile.assistantName })
const tabs: Array<{ id: SettingsTab; label: string; icon: string }> = [
  { id: 'models', label: '模型服务', icon: 'brain' },
  { id: 'tools', label: '联网工具', icon: 'globe' },
  { id: 'permissions', label: '权限', icon: 'shield' },
  { id: 'workspace', label: '工作区', icon: 'folder' },
  { id: 'general', label: '通用', icon: 'settings' },
]

watch(
  () => route.query.tab,
  (tab) => {
    if (isSettingsTab(tab)) activeTab.value = tab
  },
)

function selectTab(tab: SettingsTab) {
  activeTab.value = tab
  void router.replace({ query: { ...route.query, tab } })
}

onMounted(async () => {
  await Promise.all([settings.loadSettings(), settings.loadPreferences(), settings.loadPermissionSettings()])
  profileDraft.assistantName = settings.profile.assistantName
})

async function handleSavePreferences() {
  const saved = await settings.savePreferences(profileDraft.assistantName)
  if (saved) profileDraft.assistantName = settings.profile.assistantName
}
</script>

<template>
  <main class="page-shell settings-page">
    <header class="settings-heading">
      <div>
        <p class="page-eyebrow">Preferences</p>
        <h1 class="page-title">设置</h1>
        <p class="page-subtitle">管理模型、联网工具、执行权限，并查看当前工作区运行状态。</p>
      </div>
      <span class="version">NanamiGopher · Phase 1</span>
    </header>

    <nav class="settings-tabs" aria-label="设置分类">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        type="button"
        :class="{ active: activeTab === tab.id }"
        @click="selectTab(tab.id)"
      >
        <IconSymbol :name="tab.icon" :size="16" />
        {{ tab.label }}
      </button>
    </nav>

    <ModelSettingsPanel v-if="activeTab === 'models'" />
    <SearchToolSettingsPanel v-else-if="activeTab === 'tools'" />
    <PermissionSettingsPanel v-else-if="activeTab === 'permissions'" />
    <RuntimeStatusPanel v-else-if="activeTab === 'workspace'" />

    <section v-else class="general-card glass-card">
      <header>
        <span class="section-icon"><IconSymbol name="sparkles" :size="21" /></span>
        <div><h2>界面称呼</h2><p>设置你希望在对话和工作区中看到的助手名称。</p></div>
      </header>
      <label class="setting-row">
        <span><strong>助手称呼</strong><small>按用户保存，不会修改项目名或模型配置。</small></span>
        <input v-model.trim="profileDraft.assistantName" type="text" maxlength="32" placeholder="例如：小七">
      </label>
      <div class="identity-preview">
        <span>{{ Array.from(profileDraft.assistantName || '助')[0] }}</span>
        <div><strong>{{ profileDraft.assistantName || '助手' }}</strong><small>界面预览</small></div>
      </div>
      <footer>
        <button
          class="primary-button"
          type="button"
          :disabled="!profileDraft.assistantName.trim() || settings.saving"
          @click="handleSavePreferences"
        >
          {{ settings.saving ? '正在保存…' : '保存称呼' }}
        </button>
      </footer>
    </section>

    <div v-if="settings.error" class="notice" role="alert">
      <IconSymbol name="alert" :size="16" /><span>{{ settings.error }}</span>
    </div>
    <div v-else-if="settings.success" class="notice success-notice" role="status">
      <IconSymbol name="check" :size="16" /><span>{{ settings.success }}</span>
    </div>
  </main>
</template>

<style scoped lang="scss">
.settings-page { display: flex; flex-direction: column; gap: 22px; }
.settings-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 20px; }
.version { margin-bottom: 4px; padding: 6px 10px; border-radius: 999px; color: var(--text-tertiary); background: var(--surface-strong); font-size: 9px; font-weight: 650; }
.settings-tabs { display: inline-flex; align-self: flex-start; gap: 3px; padding: 4px; border: 1px solid var(--border-color); border-radius: 14px; background: var(--surface-strong); }
.settings-tabs button { display: flex; height: 34px; align-items: center; gap: 7px; padding: 0 14px; border: 0; border-radius: 10px; color: var(--text-secondary); background: transparent; cursor: pointer; font-size: 11px; font-weight: 600; }
.settings-tabs button.active { color: var(--text-primary); background: var(--surface-solid); box-shadow: 0 2px 8px rgba(28, 35, 48, 0.1); }
.general-card { overflow: hidden; }
.general-card > header { display: flex; align-items: center; gap: 13px; padding: 20px 22px; border-bottom: 1px solid var(--border-color); }
.general-card > header h2 { margin: 0; font-size: 16px; letter-spacing: -0.025em; }
.general-card > header p { margin: 4px 0 0; color: var(--text-secondary); font-size: 10.5px; }
.section-icon { display: grid; width: 43px; height: 43px; flex: none; place-items: center; border-radius: 13px; color: #8a63d2; background: rgba(138, 99, 210, 0.13); }
.setting-row { display: flex; min-height: 72px; align-items: center; justify-content: space-between; gap: 28px; margin-left: 22px; padding: 14px 22px 14px 0; border-bottom: 1px solid var(--border-color); }
.setting-row > span { min-width: 0; display: flex; flex-direction: column; }
.setting-row strong { font-size: 11.5px; font-weight: 650; }
.setting-row small { margin-top: 4px; color: var(--text-tertiary); font-size: 9.5px; line-height: 1.35; }
.setting-row input { width: min(320px, 48%); height: 38px; padding: 0 12px; border: 1px solid var(--border-strong); border-radius: 10px; outline: none; color: var(--text-primary); background: var(--surface-muted); font-size: 10.5px; transition: border-color 150ms ease, box-shadow 150ms ease; }
.setting-row input:focus { border-color: var(--primary-color); box-shadow: 0 0 0 3px var(--focus-ring); }
.identity-preview { display: flex; align-items: center; gap: 11px; margin: 16px 22px; padding: 13px; border-radius: 13px; background: var(--surface-muted); }
.identity-preview > span { display: grid; width: 38px; height: 38px; place-items: center; border-radius: 12px; color: #fff; background: linear-gradient(145deg, #4b91ff, #8a69e8); font-weight: 750; }
.identity-preview > div { display: flex; flex-direction: column; }
.identity-preview strong { font-size: 12px; }
.identity-preview small { margin-top: 3px; color: var(--text-tertiary); font-size: 9.5px; }
.general-card footer { display: flex; justify-content: flex-end; padding: 15px 20px; background: var(--surface-muted); }
.general-card footer .primary-button { min-height: 34px; font-size: 10.5px; }
.notice { display: flex; align-items: flex-start; gap: 9px; padding: 12px 14px; border-radius: 12px; color: var(--warning); background: var(--warning-soft); font-size: 10.5px; line-height: 1.45; }
.success-notice { color: var(--success); background: var(--success-soft); }
</style>
