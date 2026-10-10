<script setup lang="ts">
import { ref, watch } from 'vue'
import { useUIStore, accents, type Accent, type ThemeMode } from '@/stores/ui'
import { useSettingsStore } from '@/stores/settings'
import { desktopEffects } from '@/composables/useElectron'
const ui = useUIStore(),
  settings = useSettingsStore()
const isElectron = Boolean(desktopEffects)
const name = ref(settings.profile.assistantName),
  shortcut = ref(ui.appearance.capsuleShortcut),
  feedback = ref('')
const savingShortcut = ref(false)
watch(
  () => settings.profile.assistantName,
  (value) => {
    name.value = value
  },
)
const swatches: Record<Accent, string> = {
  stone: '--stone',
  blue: '--accent-blue',
  green: '--accent-green',
  earth: '--accent-earth',
  lotus: '--accent-lotus',
  ink: '--accent-black',
}
async function saveName() {
  if (name.value.trim() && !settings.saving) await settings.savePreferences(name.value.trim())
}
async function saveShortcut() {
  if (savingShortcut.value) return
  savingShortcut.value = true
  feedback.value = '正在设置…'
  try {
    await ui.setCapsuleShortcut(shortcut.value)
    feedback.value = '快捷键已更新。'
  } catch (reason) {
    feedback.value = reason instanceof Error ? reason.message : String(reason)
  } finally {
    savingShortcut.value = false
  }
}
</script>
<template>
  <section class="appearance-settings glass-card">
    <header><h2>你的助手，你的纸页</h2></header>
    <label class="setting-row"
      ><span>助手名字</span>
      <div>
        <input v-model="name" maxlength="32" placeholder="例如：小墨" /><button
          class="secondary-button"
          :disabled="settings.saving || !name.trim()"
          :aria-busy="settings.saving || undefined"
          @click="saveName"
        >
          {{ settings.saving ? '正在保存…' : '保存' }}
        </button>
      </div></label
    >
    <label class="setting-row"
      ><span>怎么称呼你</span
      ><input
        :value="ui.appearance.greetingName"
        maxlength="32"
        @input="ui.setAppearance({ greetingName: ($event.target as HTMLInputElement).value })"
    /></label>
    <label class="setting-row"
      ><span>头像字</span
      ><input
        class="avatar-input"
        :value="ui.appearance.avatar"
        @input="
          ui.setAppearance({
            avatar: Array.from(($event.target as HTMLInputElement).value)[0] || '助',
          })
        "
    /></label>
    <label class="setting-row"
      ><span>纸页</span
      ><select
        :value="ui.appearance.theme"
        @change="
          ui.setAppearance({ theme: ($event.target as HTMLSelectElement).value as ThemeMode })
        "
      >
        <option value="system">跟随系统</option>
        <option value="light">宣纸</option>
        <option value="dark">松烟</option>
      </select></label
    >
    <div class="setting-row">
      <span>强调色</span>
      <div class="accent-presets">
        <button
          v-for="accent in accents"
          :key="accent.id"
          :title="accent.label"
          :aria-label="accent.label"
          :aria-pressed="ui.appearance.accent === accent.id"
          :style="{ '--swatch': `var(${swatches[accent.id]})` }"
          @click="ui.setAppearance({ accent: accent.id })"
        >
          <i /><span>{{ accent.label }}</span>
        </button>
      </div>
    </div>
    <label class="setting-row"
      ><span>纸纹</span
      ><input
        type="checkbox"
        :checked="ui.appearance.texture"
        @change="ui.setAppearance({ texture: ($event.target as HTMLInputElement).checked })"
    /></label>
    <label v-if="isElectron" class="setting-row"
      ><span>速记快捷键</span>
      <div>
        <input v-model="shortcut" maxlength="80" placeholder="Alt+Space" /><button
          class="secondary-button"
          :disabled="savingShortcut || !shortcut.trim()"
          :aria-busy="savingShortcut || undefined"
          @click="saveShortcut"
        >
          {{ savingShortcut ? '正在设置…' : '设置' }}
        </button>
      </div></label
    >
    <p v-if="feedback" class="feedback" role="status">{{ feedback }}</p>
  </section>
</template>
<style scoped lang="scss">
@use '@/styles/mixins' as mixins;
.appearance-settings {
  padding: 20px 24px;
}
h2 {
  margin: 0 0 16px;
  font-size: var(--text-md);
  font-weight: var(--weight-semibold);
}
.setting-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
  padding: 16px 0;
  border-bottom: 1px solid var(--rule);
  font-size: var(--text-sm);
}
.setting-row:last-child {
  border: 0;
}
.setting-row > div {
  display: flex;
  align-items: center;
  gap: 8px;
}
input:not([type='checkbox']),
select {
  width: min(260px, 50%);
  font-size: var(--text-sm);
}
.setting-row > div input {
  width: 190px;
}
.avatar-input {
  max-width: 56px;
  text-align: center;
}
.accent-presets {
  flex-wrap: wrap;
}
.accent-presets button {
  @include mixins.interactive-row;
  border: 1px solid var(--transparent);
  padding: 5px 8px;
  background: var(--transparent);
  color: var(--ink-2);
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--text-xs);
}
.accent-presets button[aria-pressed='true'] {
  border-color: var(--accent);
  color: var(--ink);
  background: var(--accent-selected);
}
.accent-presets i {
  width: 9px;
  height: 9px;
  border-radius: var(--radius-round);
  background: var(--swatch);
}
.feedback {
  font-size: var(--text-sm);
  color: var(--ink-2);
}
@media (max-width: 720px) {
  .setting-row {
    align-items: flex-start;
    flex-wrap: wrap;
  }
  .setting-row > div {
    flex-wrap: wrap;
  }
}
</style>
