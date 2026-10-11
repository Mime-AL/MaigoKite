<script setup lang="ts">
import { useUIStore, type EnterBehavior } from '@/stores/ui'
const ui = useUIStore()
const modifier = /Mac|iPhone|iPad/.test(navigator.platform) ? '⌘' : 'Ctrl'
function change(event: Event) {
  ui.setAppearance({ enterBehavior: (event.target as HTMLSelectElement).value as EnterBehavior })
}
</script>
<template>
  <div data-settings-field="enter-behavior">
    <label class="setting-row">
      <span>{{ $t('Enter 键行为') }}</span>
      <select
        :value="ui.appearance.enterBehavior || 'send'"
        @change="change"
      >
        <option value="send">{{ $t('发送消息') }}</option>
        <option value="newline">{{ $t('换行') }}</option>
      </select>
    </label>
    <p class="panel-copy">
      {{ ui.appearance.enterBehavior === 'newline'
        ? $t('使用发送按钮或 {0} + Enter 发送。', [modifier])
        : $t('Shift + Enter 换行；{0} + Enter 也可发送。', [modifier]) }}
    </p>
  </div>
</template>
