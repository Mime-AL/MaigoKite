<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { settingsFields, searchSettings, type SettingsField } from '@/config/settings-fields'
import IconSymbol from '@/components/common/IconSymbol.vue'
const emit = defineEmits<{ locate: [field: SettingsField] }>()
const query = ref(''),
  selected = ref(0)
const input = ref<HTMLInputElement | null>(null)
defineExpose({ focus: () => input.value?.focus() })
const results = computed(() => searchSettings(query.value, settingsFields))
const labels: Record<string, string> = {
  general: '外观与称呼',
  models: '模型',
  tools: '工具',
  permissions: '权限',
  safety: '安全',
  workspace: '运行状态',
}
watch(query, () => {
  selected.value = 0
})
function locate(field: SettingsField) {
  query.value = ''
  emit('locate', field)
}
function keydown(event: KeyboardEvent) {
  if (event.isComposing) return
  if (event.key === 'Escape') {
    query.value = ''
    return
  }
  if (!results.value.length) return
  if (event.key === 'Enter') {
    event.preventDefault()
    locate(results.value[selected.value])
    return
  }
  if (!['ArrowUp', 'ArrowDown'].includes(event.key)) return
  event.preventDefault()
  selected.value =
    (selected.value + (event.key === 'ArrowDown' ? 1 : -1) + results.value.length) %
    results.value.length
  void nextTick(() =>
    document
      .getElementById('settings-result-' + selected.value)
      ?.scrollIntoView({ block: 'nearest' }),
  )
}
</script>
<template>
  <div class="settings-search">
    <label><IconSymbol
      name="search"
      :size="16"
    /><input
      ref="input"
      v-model="query"
      type="search"
      :placeholder="$t('搜索设置')"
      :aria-label="$t('搜索设置')"
      role="combobox"
      aria-autocomplete="list"
      :aria-expanded="!!query.trim()"
      aria-controls="settings-results"
      :aria-activedescendant="
        results.length && query.trim() ? 'settings-result-' + selected : undefined
      "
      @keydown="keydown"
    ></label>
    <ul
      v-if="query.trim()"
      id="settings-results"
      role="listbox"
      class="settings-results"
    >
      <li
        v-for="(field, index) in results"
        :id="'settings-result-' + index"
        :key="field.id"
        role="option"
        :aria-selected="selected === index"
      >
        <button
          type="button"
          @click="locate(field)"
        >
          <span>{{ $t(field.label) }}</span><small>{{ $t(labels[field.tab]) }}</small>
        </button>
      </li>
      <li
        v-if="!results.length"
        class="search-empty"
        role="status"
      >
        {{ $t('没有匹配的设置') }}
      </li>
    </ul>
  </div>
</template>
