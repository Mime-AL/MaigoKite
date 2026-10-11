<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { t } from '@/i18n'
import { useWorkspaceStore } from '@/stores/workspace'
import IconSymbol from '@/components/common/IconSymbol.vue'
import WorkspaceSelector from '@/components/sidebar/WorkspaceSelector.vue'
import { starterShortcut, welcomeStarters } from '@/utils/welcome-presentation'
defineProps<{ greeting: string; quote: string }>()
const emit = defineEmits<{ (event: 'draft', content: string): void }>()
const workspace = useWorkspaceStore()
const available = computed(() => Boolean(workspace.current?.root_path?.trim()))
const unavailable = computed(() =>
  workspace.loading
    ? t('正在读取工作区…')
    : workspace.error
      ? t('工作区读取失败')
      : t('选择工作区后可用'),
)
function choose(index: number) {
  const item = welcomeStarters[index]
  if (!item || (item.workspace && !available.value)) return
  emit('draft', t(item.prompt))
}
function onKey(event: KeyboardEvent) {
  const index = starterShortcut(event)
  if (index === undefined || (welcomeStarters[index].workspace && !available.value)) return
  event.preventDefault()
  choose(index)
}
onMounted(() => window.addEventListener('keydown', onKey))
onUnmounted(() => window.removeEventListener('keydown', onKey))
</script>
<template>
  <section
    class="welcome-sheet"
    :aria-label="greeting"
  >
    <header class="workpaper-meta">
      <span><IconSymbol
        name="folder"
        :size="14"
      /><strong>{{
        workspace.current?.name || $t('未选择工作区')
      }}</strong><small v-if="available">{{ $t('当前工作区') }}</small></span>
      <WorkspaceSelector
        collapsed
        presentation-trigger
      />
    </header>
    <svg
      class="workpaper-ink"
      viewBox="0 0 42 232"
      fill="none"
      aria-hidden="true"
    >
      <path
        class="ink-hair"
        pathLength="1"
        d="M27 1C28 40 5 69 8 113S29 170 18 213Q15 223 30 218"
      />
      <path
        class="ink-brush"
        pathLength="1"
        d="M25 58C10 92 12 117 16 145S23 185 18 214"
      />
    </svg>
    <div class="workpaper-hero">
      <h1>{{ greeting }}</h1>
      <aside class="workpaper-epigraph">
        <p>{{ quote }}</p>
        <small lang="en">{{ $t("BanG Dream! It's MyGO!!!!!") }}</small>
      </aside>
    </div>
    <nav
      class="workpaper-starters"
      :aria-label="$t('起手式')"
    >
      <button
        v-for="(item, index) in welcomeStarters"
        :key="item.title"
        type="button"
        :disabled="item.workspace && !available"
        :aria-describedby="'starter-hint-' + index"
        @click="choose(index)"
      >
        <IconSymbol
          :name="item.icon"
          :size="18"
        />
        <strong>{{ $t(item.title) }} <kbd>{{ index + 1 }}</kbd></strong>
        <small :id="'starter-hint-' + index">{{
          item.workspace && !available ? unavailable : $t(item.hint)
        }}</small>
      </button>
    </nav>
    <div class="sheet-unfinished">
      <slot />
    </div>
  </section>
</template>
<style scoped lang="scss">
@use '@/styles/welcome-sheet';
</style>
