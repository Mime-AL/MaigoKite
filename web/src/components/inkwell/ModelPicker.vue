<script setup lang="ts">
import { t } from '@/i18n'
import { computed, nextTick, onScopeDispose, ref, watch } from 'vue'
import { groupModelProfiles, type ModelOption } from '@/config/model-groups'
import { useDialog } from '@/composables/useDialog'
import IconSymbol from '@/components/common/IconSymbol.vue'

const props = withDefaults(defineProps<{
  modelValue: string
  models: ModelOption[]
  disabled?: boolean
}>(), { disabled: false })
const emit = defineEmits<{ (event: 'update:modelValue', value: string): void }>()
// getRandomValues also works when the personal web UI is served over LAN HTTP.
const id = `model-picker-${Array.from(crypto.getRandomValues(new Uint32Array(2)), value => value.toString(16)).join('-')}`
const trigger = ref<HTMLButtonElement | null>(null)
const dialog = ref<HTMLDialogElement | null>(null)
const search = ref<HTMLInputElement | null>(null)
const open = ref(false), query = ref(''), activeId = ref('')
const position = ref({ left: '0px', top: '0px' })
const groups = computed(() => groupModelProfiles(props.models))
const current = computed(() => props.models.find(item => item.id === props.modelValue))
const currentGroup = computed(() => groups.value.find(group => group.models.some(item => item.id === props.modelValue)))
const label = computed(() => current.value?.model || (props.models.length ? t("选择模型") : t("未配置模型")))
const visibleGroups = computed(() => {
  const terms = query.value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean)
  return groups.value.map(group => ({
    ...group,
    models: group.models.filter(item => terms.every(term =>
      `${group.name} ${group.providerName} ${item.model}`.toLocaleLowerCase().includes(term))),
  })).filter(group => group.models.length)
})
const choices = computed(() => visibleGroups.value.flatMap(group => group.models))
useDialog(dialog, () => open.value)

function close() { open.value = false }
function place() {
  const anchor = trigger.value?.getBoundingClientRect(), panel = dialog.value
  if (!anchor || !panel) return
  const gap = 8
  position.value = {
    left: `${Math.max(gap, Math.min(anchor.right - panel.offsetWidth, window.innerWidth - panel.offsetWidth - gap))}px`,
    top: `${Math.max(44, anchor.top - panel.offsetHeight - gap)}px`,
  }
}
async function show() {
  if (props.disabled || !props.models.length) return
  query.value = ''
  activeId.value = current.value?.id || props.models[0].id
  open.value = true
  await nextTick()
  place()
  search.value?.focus()
  scrollToActive()
}
function scrollToActive() {
  dialog.value?.querySelector<HTMLElement>('[data-highlighted="true"]')?.scrollIntoView({ block: 'nearest' })
}
function choose(value: string) {
  if (props.disabled || !props.models.some(item => item.id === value)) return
  if (value !== props.modelValue) emit('update:modelValue', value)
  close()
}
function onKey(event: KeyboardEvent) {
  if (event.isComposing || event.ctrlKey || event.metaKey || event.altKey) return
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault()
    const index = choices.value.findIndex(item => item.id === activeId.value)
    const count = choices.value.length
    activeId.value = count ? choices.value[(index + (event.key === 'ArrowDown' ? 1 : count - 1) + count) % count].id : ''
    search.value?.focus()
  } else if (event.key === 'Enter' && event.target === search.value) {
    event.preventDefault()
    if (activeId.value) choose(activeId.value)
  }
}
watch(query, () => { activeId.value = choices.value[0]?.id || '' })
watch(choices, () => {
  if (!choices.value.some(item => item.id === activeId.value)) activeId.value = choices.value[0]?.id || ''
})
watch(activeId, async () => { await nextTick(); scrollToActive() })
watch(visibleGroups, async () => { if (open.value) { await nextTick(); place() } })
watch(() => props.disabled, disabled => { if (disabled) close() })
watch(() => props.modelValue, close)
watch(open, visible => {
  if (visible) {
    window.addEventListener('resize', place)
    window.addEventListener('scroll', place, true)
  } else {
    window.removeEventListener('resize', place)
    window.removeEventListener('scroll', place, true)
  }
})
onScopeDispose(() => {
  window.removeEventListener('resize', place)
  window.removeEventListener('scroll', place, true)
})
</script>

<template>
  <button
    ref="trigger"
    type="button"
    class="model-trigger"
    :disabled="disabled || !models.length"
    :title="current ? `${currentGroup?.name || current.name} · ${current.model}` : label"
    :aria-label="$t('当前对话模型：{0}', [label])"
    aria-haspopup="dialog"
    :aria-expanded="open"
    :aria-controls="open ? id : undefined"
    @click="show"
  >
    <IconSymbol name="cube" :size="14" />
    <span>{{ label }}</span>
    <IconSymbol class="model-chevron" name="chevron" :size="12" />
  </button>
  <Teleport to="body">
    <dialog
      :id="id"
      ref="dialog"
      class="model-menu"
      :style="position"
      :aria-label="$t('选择对话模型')"
      @cancel.prevent="close"
      @close="close"
      @click.self="close"
      @keydown="onKey"
      @keydown.esc.stop
    >
      <label class="model-search">
        <IconSymbol name="search" :size="15" />
        <input
          ref="search"
          v-model="query"
          type="text"
          role="combobox"
          :aria-label="$t('搜索模型或服务')"
          aria-autocomplete="list"
          :aria-expanded="open"
          :aria-controls="`${id}-list`"
          :aria-activedescendant="activeId ? `${id}-${activeId}` : undefined"
          :placeholder="$t('搜索模型或服务…')"
          autocomplete="off"
        />
      </label>
      <div :id="`${id}-list`" class="model-list" role="listbox" :aria-label="$t('已配置的模型')">
        <section v-for="(group, index) in visibleGroups" :key="group.id" role="group" :aria-labelledby="`${id}-group-${index}`" class="model-group">
          <header :id="`${id}-group-${index}`">
            <strong>{{ group.name }}</strong>
            <small v-if="group.providerName !== group.name">{{ group.providerName }}</small>
          </header>
          <button
            v-for="item in group.models"
            :id="`${id}-${item.id}`"
            :key="item.id"
            type="button"
            role="option"
            tabindex="-1"
            class="model-option"
            :title="item.model"
            :aria-selected="item.id === modelValue"
            :data-highlighted="item.id === activeId"
            @pointermove="activeId = item.id"
            @click="choose(item.id)"
          >
            <span>{{ item.model }}</span>
            <small v-if="item.isDefault">{{ $t('默认') }}</small>
            <IconSymbol v-if="item.id === modelValue" name="check" :size="15" />
          </button>
        </section>
      </div>
      <p v-if="!choices.length" class="model-empty" role="status">{{ $t('没有匹配的模型。') }}</p>
      <footer>
        <router-link to="/settings?tab=models" @click="close">
          <IconSymbol name="settings" :size="14" />{{ $t('管理模型') }}</router-link>
        <span>{{ $t('↑ ↓ 选择 · Enter 确认') }}</span>
      </footer>
    </dialog>
  </Teleport>
</template>

<style scoped lang="scss">
@use '@/styles/model-picker';
</style>
