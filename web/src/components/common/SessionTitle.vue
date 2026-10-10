<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { t } from '@/i18n'
import { useSessionStore } from '@/stores/session'
const props = defineProps<{ title: string; sessionId?: string; serif?: boolean }>()
const session = useSessionStore()
const host = ref<HTMLElement | null>(null), input = ref<HTMLInputElement | null>(null)
const editing = ref(false), draft = ref(''), busy = ref(false), failure = ref('')
const parts = ref<[string, string]>([props.title, ''])
const label = computed(() => props.sessionId ? t('双击重命名对话') : props.title)
let observer: ResizeObserver | undefined
function measure() {
  if (!host.value || editing.value) return
  const context = document.createElement('canvas').getContext('2d')
  if (!context) return
  context.font = getComputedStyle(host.value).font
  const width = host.value.clientWidth
  if (!width || context.measureText(props.title).width <= width) { parts.value = [props.title, '']; return }
  const chars = Array.from(props.title)
  for (let count = chars.length - 1; count > 1; count--) {
    const front = Math.ceil(count * 0.6), back = count - front
    const first = chars.slice(0, front).join(''), last = chars.slice(-back).join('')
    if (context.measureText(first + '…' + last).width <= width) { parts.value = [first, last]; return }
  }
  parts.value = ['', chars.slice(-1).join('')]
}
async function rename() {
  if (!props.sessionId || busy.value) return
  draft.value = props.title; failure.value = ''; editing.value = true
  await nextTick(); input.value?.focus(); input.value?.select()
}
async function save() {
  const id = props.sessionId, title = draft.value.trim()
  if (!editing.value || busy.value || !id || !title) return
  if (title === props.title) { editing.value = false; return }
  busy.value = true; failure.value = ''
  try { await session.manageSession(id, { title }); editing.value = false }
  catch (reason) { failure.value = reason instanceof Error ? reason.message : String(reason) }
  finally { busy.value = false }
}
watch(() => props.title, () => { void nextTick(measure) })
watch(() => props.sessionId, () => { editing.value = false; failure.value = '' })
watch(editing, () => { void nextTick(measure) })
onMounted(() => {
  if (typeof ResizeObserver !== 'undefined') { observer = new ResizeObserver(measure); if (host.value) observer.observe(host.value) }
  measure()
})
onBeforeUnmount(() => observer?.disconnect())
</script>
<template>
  <div ref="host" class="session-title" :class="{ serif }">
    <form v-if="editing" @submit.prevent="save">
      <input ref="input" v-model="draft" maxlength="200" :disabled="busy" :aria-label="$t('对话名称')"
        @blur="save" @keydown.esc.stop.prevent="editing = false" />
    </form>
    <span v-else :title="title" :aria-label="title" :tabindex="sessionId ? 0 : undefined"
      :role="sessionId ? 'button' : undefined" :aria-description="label" @dblclick="rename"
      @keydown.enter.prevent="rename" @keydown.space.prevent="rename">
      <span aria-hidden="true">{{ parts[0] }}<template v-if="parts[1]">…{{ parts[1] }}</template></span>
    </span>
    <p v-if="failure" class="rename-error" role="alert">{{ failure }}</p>
  </div>
</template>
<style scoped lang="scss">
.session-title { position: relative; flex: 1; min-width: 0; font-size: var(--session-title-size); }
.serif { font-family: var(--font-serif); }
.session-title > span { display: block; overflow: hidden; white-space: nowrap; -webkit-app-region: no-drag; }
input { width: 100%; min-width: 0; padding: var(--space-2) var(--space-3); -webkit-app-region: no-drag; }
.rename-error { position: absolute; top: 100%; z-index: 2; padding: var(--space-3); background: var(--paper-raised); box-shadow: var(--shadow-float); font: var(--text-sm) var(--font-sans); }
</style>
