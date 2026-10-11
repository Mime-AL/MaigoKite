<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { useSettingsStore } from '@/stores/settings'
import type { PermissionMode } from '@/api/client'
import RailGlyph from '@/components/rail/RailGlyph.vue'
import { t } from '@/i18n'
const settings = useSettingsStore()
const draft = reactive({ default_mode: 'workspace' as PermissionMode })
const feedback = ref(''),
  error = ref('')
const modes = [
  {
    id: 'read_only',
    label: '只读',
    kind: 'read',
    behavior: '读取与搜索自动执行；编辑、命令和联网操作会请求批准。',
  },
  {
    id: 'workspace',
    label: '工作区',
    kind: 'act',
    behavior: '读取、编辑和安全命令自动执行；联网与高风险命令会请求批准。',
  },
  {
    id: 'full_access',
    label: '完全访问',
    kind: 'await',
    behavior: '普通工具与联网操作自动执行；重大影响操作仍会请求批准。',
  },
] as const
watch(
  () => settings.permissions,
  (value) => {
    draft.default_mode = value.default_mode
  },
  { immediate: true },
)
watch(
  () => draft.default_mode,
  () => {
    feedback.value = ''
    error.value = ''
  },
)
async function save() {
  if (settings.saving) return
  error.value = ''
  feedback.value = ''
  if (await settings.savePermissionSettings({ default_mode: draft.default_mode }))
    feedback.value = t('已保存')
  else error.value = settings.error || t('保存失败')
}
</script>
<template>
  <section
    class="permission-settings settings-panel"
    data-settings-field="permission-mode"
  >
    <header class="panel-heading">
      <h2>{{ $t('执行权限') }}</h2>
    </header>
    <section class="setting-group">
      <h3>{{ $t('新对话的默认权限') }}</h3>
      <div
        class="mode-options mode-grid"
        role="group"
        :aria-label="$t('执行权限')"
      >
        <button
          v-for="mode in modes"
          :key="mode.id"
          type="button"
          :class="{
            active: draft.default_mode === mode.id,
            'high-risk': mode.id === 'full_access',
          }"
          :aria-pressed="draft.default_mode === mode.id"
          :disabled="settings.saving"
          @click="draft.default_mode = mode.id"
        >
          <RailGlyph :kind="mode.kind" /><span><strong>{{ $t(mode.label) }}</strong><small v-if="mode.id === 'workspace'">{{ $t('推荐') }}</small>
            <p>{{ $t(mode.behavior) }}</p></span>
        </button>
      </div>
    </section>
    <p class="panel-copy">
      {{ $t('即使选择“完全访问”，越界访问和危险的系统命令仍会受到限制。') }}
    </p>
    <footer class="permission-actions">
      <button
        class="primary-button"
        :disabled="settings.saving"
        :aria-busy="settings.saving || undefined"
        @click="save"
      >
        {{ settings.saving ? $t('正在保存…') : $t('保存权限设置') }}
      </button><span
        v-if="feedback"
        class="field-saved"
        role="status"
      >{{ feedback }}</span>
    </footer>
    <p
      v-if="error"
      class="field-error"
      role="alert"
    >
      {{ error
      }}<button
        class="text-button"
        :disabled="settings.saving"
        @click="save"
      >
        {{ $t('重试') }}
      </button>
    </p>
  </section>
</template>
<style scoped lang="scss">
@use '@/styles/mixins' as mixins;
.mode-options {
  display: grid;
  gap: var(--space-3);
  margin-top: var(--space-5);
}
.mode-options button {
  @include mixins.interactive-row;
  display: flex;
  align-items: start;
  gap: var(--space-4);
  padding: var(--space-5);
  text-align: left;
  background: var(--paper-2);
  border: var(--hairline) solid var(--rule);
  color: var(--ink);
}
.mode-options button.active {
  border-color: var(--accent);
  background: var(--accent-soft);
}
.mode-options .high-risk > svg {
  color: var(--seal);
}
.mode-options strong {
  font-size: var(--text-md);
}
.mode-options small {
  color: var(--accent);
  margin-inline-start: var(--space-3);
  font-size: var(--text-xs);
}
.mode-options p {
  margin: var(--space-2) 0 0;
  color: var(--ink-2);
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
}
.permission-actions {
  display: flex;
  align-items: center;
  gap: var(--space-4);
}
</style>
