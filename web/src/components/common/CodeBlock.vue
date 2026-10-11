<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { t } from '@/i18n'
import { codeLines, visibleCodeLines } from '@/utils/code-presentation'
import IconSymbol from './IconSymbol.vue'
const props = withDefaults(
  defineProps<{
    content: string
    title?: string
    language?: string
    kind?: 'code' | 'terminal' | 'diff'
    previewLines?: number
  }>(),
  { kind: 'code', previewLines: 20, title: '', language: '' },
)
const expanded = ref(false),
  copied = ref(false),
  error = ref('')
let timer: ReturnType<typeof setTimeout> | undefined
const lines = computed(() => codeLines(props.content, props.kind === 'diff'))
const visible = computed(() => visibleCodeLines(lines.value, expanded.value, props.previewLines))
const caption = computed(
  () =>
    props.title ||
    props.language ||
    t(props.kind === 'diff' ? '变更' : props.kind === 'terminal' ? '输出' : '代码'),
)
async function copy() {
  error.value = ''
  try {
    if (!navigator.clipboard?.writeText) throw new Error('clipboard unavailable')
    await navigator.clipboard.writeText(props.content)
    copied.value = true
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      copied.value = false
    }, 1800)
  } catch {
    error.value = t('无法复制，请选中文字后复制。')
  }
}
onBeforeUnmount(() => {
  if (timer) clearTimeout(timer)
})
</script>
<template>
  <section
    class="code-block"
    :class="kind"
  >
    <header class="code-heading">
      <span>{{ caption }}</span><small>{{ $t('{0} 行', [lines.length]) }}</small>
      <button
        class="copy-button"
        :aria-label="$t('复制代码')"
        @click="copy"
      >
        <IconSymbol
          :name="copied ? 'check' : 'copy'"
          :size="14"
        />{{
          $t(copied ? '已复制' : '复制')
        }}
      </button>
    </header>
    <!-- Literal text only; untrusted tool output never becomes markup. -->
    <div
      class="code-scroll"
      tabindex="0"
      :aria-label="caption"
    >
      <div class="code-body">
        <code
          v-for="line in visible"
          :key="line.index"
          class="code-line"
          :class="line.kind"
        >
          <span
            v-if="kind === 'diff'"
            class="code-number"
            aria-hidden="true"
          >{{ line.before ?? '' }}</span>
          <span
            class="code-number"
            aria-hidden="true"
          >{{ kind === 'diff' ? line.after ?? '' : line.index }}</span>
          <span class="code-text">{{ line.text || ' ' }}{{ '\n' }}</span>
        </code>
      </div>
    </div>
    <footer
      v-if="lines.length > previewLines"
      class="code-footer"
    >
      <button
        :aria-expanded="expanded"
        @click="expanded = !expanded"
      >
        {{ $t(expanded ? '收起' : '全部') }}
      </button>
      <small v-if="expanded && lines.length > 200">{{ $t('显示最后 {0} 行', [200]) }}</small>
    </footer>
    <p
      v-if="error"
      class="copy-error"
      role="alert"
    >
      {{ error }}
    </p>
    <span
      v-if="copied"
      class="sr-only"
      role="status"
    >{{ $t('已复制') }}</span>
  </section>
</template>
<style scoped lang="scss">
@use '@/styles/code-block';
</style>
