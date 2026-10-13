<script setup lang="ts">
import { useUIStore, type EnterBehavior } from '@/stores/ui'
import InkSelect from '@/components/common/InkSelect.vue'
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
      <InkSelect
        :value="ui.appearance.enterBehavior || 'send'"
        :options="[{ value: 'send', label: $t('发送消息') }, { value: 'newline', label: $t('换行') }]"
        @change="change"
      />
    </label>
    <p class="panel-copy">
      {{ ui.appearance.enterBehavior === 'newline'
        ? $t('使用发送按钮或 {0} + Enter 发送。', [modifier])
        : $t('Shift + Enter 换行；{0} + Enter 也可发送。', [modifier]) }}
    </p>
  </div>
</template>
