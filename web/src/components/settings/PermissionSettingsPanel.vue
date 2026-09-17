<script setup lang="ts">
import { reactive, watch } from 'vue'
import IconSymbol from '@/components/common/IconSymbol.vue'
import { useSettingsStore } from '@/stores/settings'
import type { PermissionMode } from '@/api/client'

const settings = useSettingsStore()
const draft = reactive({ default_mode: 'workspace' as PermissionMode })
const modes: Array<{
  id: PermissionMode
  label: string
  badge?: string
  description: string
  behavior: string
}> = [
  {
    id: 'read_only', label: '只读',
    description: '安全地检查项目，不自动修改内容。',
    behavior: '读取与搜索自动执行；编辑、命令和联网操作会请求批准。',
  },
  {
    id: 'workspace', label: '工作区', badge: '推荐',
    description: '适合日常编码，在当前工作区自主完成任务。',
    behavior: '读取、编辑和安全命令自动执行；联网与高风险命令会请求批准。',
  },
  {
    id: 'full_access', label: '完全访问',
    description: '减少中断，在应用允许的范围内自动执行。',
    behavior: '普通工具与联网操作自动执行；重大影响操作仍会请求批准。',
  },
]

watch(() => settings.permissions, value => {
  draft.default_mode = value.default_mode
}, { immediate: true, deep: true })

function save() {
  void settings.savePermissionSettings({ default_mode: draft.default_mode })
}
</script>

<template>
  <section class="permission-settings glass-card">
    <header class="panel-heading">
      <span><IconSymbol name="shield" :size="21" /></span>
      <div><h2>执行权限</h2><p>为新对话选择一个清晰的权限档位；聊天框中仍可按对话切换。</p></div>
    </header>

    <section class="mode-section">
      <div class="mode-grid">
        <button v-for="mode in modes" :key="mode.id" type="button" :class="{ active: draft.default_mode === mode.id }" @click="draft.default_mode = mode.id">
          <span><strong>{{ mode.label }}</strong><b v-if="mode.badge">{{ mode.badge }}</b></span>
          <small>{{ mode.description }}</small>
          <p>{{ mode.behavior }}</p>
        </button>
      </div>
    </section>

    <section class="safety-note">
      <IconSymbol name="shield" :size="17" />
      <div><strong>系统安全边界始终生效</strong><p>路径越界、破坏性系统命令等硬性规则不会因选择“完全访问”而被绕过。</p></div>
    </section>

    <footer><button class="primary-button" type="button" :disabled="settings.saving" @click="save">{{ settings.saving ? '正在保存…' : '保存权限策略' }}</button></footer>
  </section>
</template>

<style scoped lang="scss">
.permission-settings { overflow: hidden; }
.panel-heading { display: flex; align-items: center; gap: 12px; padding: 19px 21px; border-bottom: 1px solid var(--border-color); }
.panel-heading > span { display: grid; width: 42px; height: 42px; place-items: center; border-radius: 13px; color: var(--primary-color); background: var(--primary-soft); }
h2, h3, p { margin: 0; } h2 { font-size: 16px; } h3 { font-size: 12px; }
.panel-heading p { margin-top: 4px; color: var(--text-secondary); font-size: 10px; }
.mode-section { padding: 19px 21px; }
.mode-section { border-bottom: 1px solid var(--border-color); }
.mode-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }
.mode-grid button { display: flex; min-height: 150px; flex-direction: column; padding: 15px; border: 1px solid var(--border-color); border-radius: 14px; color: var(--text-primary); background: var(--surface-muted); cursor: pointer; text-align: left; }
.mode-grid button.active { border-color: var(--primary-color); background: var(--primary-soft); box-shadow: 0 0 0 2px var(--focus-ring); }
.mode-grid button > span { display: flex; align-items: center; gap: 7px; }
.mode-grid strong { font-size: 12px; }
.mode-grid button > span b { padding: 3px 6px; border-radius: 999px; color: var(--primary-color); background: var(--surface-solid); font-size: 8px; }
.mode-grid small { margin-top: 8px; color: var(--text-secondary); font-size: 9.5px; line-height: 1.45; }
.mode-grid button p { margin-top: auto; padding-top: 14px; color: var(--text-tertiary); font-size: 8.5px; line-height: 1.45; }
.safety-note { display: flex; align-items: flex-start; gap: 10px; margin: 16px 21px; padding: 13px; border-radius: 12px; color: var(--text-secondary); background: var(--surface-muted); }
.safety-note strong { color: var(--text-primary); font-size: 10px; }.safety-note p { margin-top: 3px; font-size: 9px; line-height: 1.45; }
footer { display: flex; justify-content: flex-end; padding: 14px 20px; border-top: 1px solid var(--border-color); background: var(--surface-muted); }
@media (max-width: 800px) { .mode-grid { grid-template-columns: 1fr; }.mode-grid button { min-height: 120px; } }
</style>
