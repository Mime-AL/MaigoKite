<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSettingsStore } from '@/stores/settings'
import ModelSettingsPanel from '@/components/settings/ModelSettingsPanel.vue'
import ToolSettingsPanel from '@/components/settings/ToolSettingsPanel.vue'
import PermissionSettingsPanel from '@/components/settings/PermissionSettingsPanel.vue'
import RuntimeStatusPanel from '@/components/settings/RuntimeStatusPanel.vue'
import AppearanceSettingsPanel from '@/components/settings/AppearanceSettingsPanel.vue'
const route = useRoute(),
  router = useRouter(),
  settings = useSettingsStore()
const tabs = [
  { id: 'general', label: '外观与称呼' },
  { id: 'models', label: '模型' },
  { id: 'tools', label: '工具' },
  { id: 'permissions', label: '权限' },
  { id: 'workspace', label: '工作区' },
]
const activeTab = ref(
  tabs.some((t) => t.id === route.query.tab) ? String(route.query.tab) : 'general',
)
watch(
  () => route.query.tab,
  (value) => {
    activeTab.value = tabs.some((t) => t.id === value) ? String(value) : 'general'
  },
)
function selectTab(id: string) {
  activeTab.value = id
  void router.replace({ query: { ...route.query, tab: id } })
}
onMounted(() => {
  void settings.loadPreferences()
  void settings.loadPermissionSettings()
  if (!settings.loaded) void settings.loadSettings()
})
</script>
<template>
  <main class="page-shell settings-page">
    <header>
      <h1 class="page-title">设置</h1>
      <p class="page-subtitle">让它按你的方式工作。</p>
    </header>
    <nav class="settings-tabs" aria-label="设置分类">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        :aria-pressed="activeTab === tab.id"
        @click="selectTab(tab.id)"
      >
        {{ tab.label }}
      </button>
    </nav>
    <AppearanceSettingsPanel v-if="activeTab === 'general'" /><ModelSettingsPanel
      v-else-if="activeTab === 'models'"
    /><ToolSettingsPanel v-else-if="activeTab === 'tools'" /><PermissionSettingsPanel
      v-else-if="activeTab === 'permissions'"
    /><RuntimeStatusPanel v-else />
    <p v-if="settings.error" class="error-banner" role="alert">{{ settings.error }}</p>
    <p v-else-if="settings.success" class="notice" role="status">{{ settings.success }}</p>
  </main>
</template>
<style scoped lang="scss">
@use '@/styles/mixins' as mixins;
.settings-page {
  display: grid;
  gap: 28px;
}
.settings-tabs {
  display: flex;
  align-items: center;
  gap: 20px;
  border-bottom: 1px solid var(--rule);
  overflow-x: auto;
}
.settings-tabs button {
  @include mixins.interactive-row;
  border: 0;
  border-bottom: 2px solid var(--transparent);
  border-radius: var(--radius-none);
  padding: 10px 8px 14px;
  color: var(--ink-3);
  background: var(--transparent);
  white-space: nowrap;
  font-size: var(--text-sm);
}
.settings-tabs button[aria-pressed='true'] {
  color: var(--accent);
  border-bottom-color: var(--accent);
  font-weight: var(--weight-semibold);
}
.notice {
  color: var(--ink-2);
  font-size: var(--text-sm);
}
</style>
