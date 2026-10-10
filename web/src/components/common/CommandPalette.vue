<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useUIStore } from '@/stores/ui'
import { useSessionStore } from '@/stores/session'
import { useMemoryStore } from '@/stores/memory'
import Kbd from './Kbd.vue'
import { useDialog } from '@/composables/useDialog'
const ui = useUIStore(),
  session = useSessionStore(),
  memory = useMemoryStore(),
  router = useRouter()
const query = ref(''),
  input = ref<HTMLInputElement | null>(null),
  selected = ref(0),
  dialog = ref<HTMLDialogElement | null>(null)
useDialog(dialog, () => ui.commandOpen || ui.shortcutsOpen)
function close() {
  ui.commandOpen = ui.shortcutsOpen = false
}
const mod = /Mac/.test(navigator.platform) ? '⌘' : 'Ctrl'
const shortcuts = [
  [`${mod}+K`, '万能面板'],
  [`${mod}+N`, '新页'],
  [`${mod}+B`, '侧栏'],
  [`${mod}+.`, '抽屉'],
  [`${mod}+J`, '等你'],
  [`${mod}+/`, '快捷键表'],
  ['[ / ]', '跳转墨线节点'],
  ['Y / N', '允许 / 驳回'],
  ['Esc', '中断 / 关闭浮层'],
]
const items = computed(() =>
  [
    { id: 'new', label: '新页', to: '/chat', kind: '命令' },
    { id: 'settings', label: '设置', to: '/settings', kind: '命令' },
    { id: 'memory', label: '它记得', to: '/memory', kind: '命令' },
    { id: 'overview', label: '概览', to: '/overview', kind: '命令' },
    { id: 'integrations', label: '扩展', to: '/integrations', kind: '命令' },
    { id: 'audit', label: '审计日志', to: '/audit', kind: '命令' },
    { id: 'data', label: '数据概览', to: '/data', kind: '命令' },
    { id: 'indexes', label: '知识库', to: '/embedding-indexes', kind: '命令' },
    ...session.sessions.map((s) => ({
      id: s.id,
      label: s.title,
      to: `/chat/${s.id}`,
      kind: '会话',
    })),
    ...memory.items.map((m) => ({
      id: m.id,
      label: m.content,
      to: `/memory?focus=${encodeURIComponent(m.id)}`,
      kind: '记忆',
    })),
  ]
    .filter((item) => item.label.toLocaleLowerCase().includes(query.value.toLocaleLowerCase()))
    .slice(0, 40),
)
watch(
  () => ui.commandOpen,
  async (open) => {
    if (open) {
      query.value = ''
      selected.value = 0
      if (!memory.items.length) void memory.load()
      await nextTick()
      input.value?.focus()
    }
  },
)
watch(query, () => {
  selected.value = 0
})
watch(selected, async () => {
  await nextTick()
  dialog.value?.querySelector('.selected')?.scrollIntoView({ block: 'nearest' })
})
function choose(to: string) {
  ui.commandOpen = false
  void router.push(to)
}
function onKey(event: KeyboardEvent) {
  if (event.isComposing) return
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault()
    selected.value = Math.max(
      0,
      Math.min(items.value.length - 1, selected.value + (event.key === 'ArrowDown' ? 1 : -1)),
    )
  }
  if (event.key === 'Enter' && items.value[selected.value]) choose(items.value[selected.value].to)
}
</script>
<template>
  <dialog
    ref="dialog"
    class="palette-shade"
    :aria-label="ui.commandOpen ? '万能面板' : '快捷键表'"
    @cancel.prevent="close"
    @keydown.esc.stop
    @click.self="close"
  >
    <section v-if="ui.commandOpen" class="palette">
      <input
        ref="input"
        v-model="query"
        placeholder="找会话、命令、记忆…"
        aria-label="搜索"
        @keydown="onKey"
      />
      <div class="results">
        <button
          v-for="(item, index) in items"
          :key="item.id"
          :class="{ selected: selected === index }"
          @click="choose(item.to)"
        >
          <small>{{ item.kind }}</small
          ><span>{{ item.label }}</span>
        </button>
        <p v-if="!items.length" class="empty-copy">没有找到相关内容。</p>
      </div>
    </section>
    <section v-else class="palette shortcut-sheet">
      <header>
        快捷键<button class="icon-button" aria-label="关闭快捷键表" @click="close">×</button>
      </header>
      <p v-for="[keys, label] in shortcuts" :key="keys">
        <span>{{ label }}</span
        ><Kbd :keys="keys" />
      </p>
    </section>
  </dialog>
</template>
<style scoped lang="scss">
@use '@/styles/mixins' as mixins;
.palette-shade {
  position: fixed;
  inset: 0;
  z-index: 60;
  margin: 0;
  border: 0;
  width: 100%;
  height: 100%;
  max-width: none;
  max-height: none;
  color: var(--ink);
  background: transparent;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: min(20vh, 140px) 20px 20px;
}
.palette-shade:not([open]) {
  display: none;
}
.palette-shade::backdrop {
  background: var(--backdrop);
}
.palette {
  width: min(540px, 100%);
  overflow: hidden;
  border: 1px solid var(--rule);
  border-radius: var(--radius-md);
  background: var(--paper);
  box-shadow: var(--shadow-float);
}
input {
  width: 100%;
  border: 0;
  border-bottom: 1px solid var(--rule);
  padding: 18px 20px;
  border-radius: var(--radius-none);
  outline: 0;
  font-size: var(--text-md);
}
.results {
  max-height: 45vh;
  overflow: auto;
  padding: 6px;
}
button {
  width: 100%;
  display: flex;
  gap: 16px;
  padding: 12px;
  border: 0;
  background: var(--transparent);
  color: var(--ink-2);
  text-align: left;
  font-size: var(--text-sm);
}
.results button {
  @include mixins.interactive-row;
}
button.selected {
  background: var(--accent-selected);
}
small {
  color: var(--ink-3);
  min-width: 30px;
  font-size: var(--text-xs);
}
button span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.shortcut-sheet {
  padding: 20px;
}
.shortcut-sheet header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.shortcut-sheet .icon-button {
  width: 30px;
}
.shortcut-sheet p {
  display: flex;
  justify-content: space-between;
  font-size: var(--text-sm);
  color: var(--ink-2);
}
</style>
