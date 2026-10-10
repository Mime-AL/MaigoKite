<script setup lang="ts">
import { t } from '@/i18n'
import AppIcon from '@/components/common/AppIcon.vue'
import IconSymbol from '@/components/common/IconSymbol.vue'

defineProps<{ greeting: string; date: string; quote: string }>()
const emit = defineEmits<{ (event: 'draft', content: string): void }>()
// These are editable drafts, not new workflows or automatic tool invocations.
const starters = [
  { icon: 'files', title: '读读这个工作区', hint: '文件与资料', prompt: '阅读当前工作区的资料，概括主要内容和目录结构。不要修改文件。' },
  { icon: 'review', title: '理一理下一步', hint: '思路与计划', prompt: '根据当前工作区资料，整理下一步的计划。不要执行修改，有不清楚的地方请问我。' },
  { icon: 'activity', title: '看看最近的改动', hint: '变更与检查', prompt: '检查当前工作区的 Git 变更，概括改了什么和需要留意的问题。不要修改文件。' },
]
</script>

<template>
  <section class="welcome-sheet" :aria-label="greeting">
    <header class="sheet-dateline"><time>{{ date }}</time><AppIcon :size="32" /></header>
    <!-- One stroke echoes the icon's ribbon. It never sits behind readable text. -->
    <svg class="first-stroke" viewBox="0 0 190 240" fill="none" aria-hidden="true">
      <path class="hair" d="M134 4C150 50 77 74 49 121S54 174 111 182" />
      <path class="brush" d="M161 18C170 59 84 94 71 140S108 191 178 197" />
      <path class="tail" d="M178 197C129 193 107 214 121 238" />
    </svg>
    <div class="sheet-heading"><h1>{{ greeting }}</h1><p>{{ quote }}</p></div>
    <nav class="starter-list" :aria-label="$t('起手式')">
      <button v-for="item in starters" :key="item.title" @click="emit('draft', t(item.prompt))">
        <IconSymbol :name="item.icon" :size="18" />
        <span><strong>{{ $t(item.title) }}</strong><small>{{ $t(item.hint) }}</small></span>
        <IconSymbol name="chevron" :size="13" class="starter-arrow" />
      </button>
    </nav>
    <div class="sheet-unfinished"><slot /></div>
  </section>
</template>

<style scoped lang="scss">
@use '@/styles/mixins' as mixins;
.welcome-sheet {
  position: relative;
  isolation: isolate;
  width: 100%;
  padding: var(--welcome-top-space) var(--welcome-side-space) var(--space-8);
  animation: paper-arrive var(--motion-arrive) var(--ease-out) both;
}
.sheet-dateline {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-5);
  padding-bottom: var(--space-7);
  border-bottom: var(--hairline) solid var(--rule);
}
time {
  color: var(--ink-3);
  font-size: var(--type-caption);
  letter-spacing: var(--tracking-label);
}
.sheet-dateline :deep(.app-icon) {
  width: var(--welcome-icon-size);
  height: var(--welcome-icon-size);
}
.first-stroke {
  position: absolute;
  right: var(--space-7);
  top: var(--space-9);
  z-index: -1;
  width: var(--welcome-mark-width);
  height: var(--welcome-mark-height);
  color: var(--accent);
  opacity: var(--welcome-mark-opacity);
  pointer-events: none;
  transform-origin: top;
  animation: ink-reveal var(--motion-arrive) var(--ease-out) both;
}
.first-stroke path {
  stroke: currentColor;
  stroke-linecap: round;
  stroke-width: var(--welcome-mark-stroke);
}
.first-stroke .brush { stroke-width: var(--welcome-mark-bold-stroke); }
.first-stroke .tail { opacity: var(--rail-soft-opacity); }
.sheet-heading {
  position: relative;
  width: 100%;
  max-width: calc(100% - var(--welcome-mark-width));
  padding-top: var(--space-9);
}
h1 {
  margin: 0;
  color: var(--ink);
  font: var(--welcome-title-size)/var(--leading-display) var(--font-serif);
  font-weight: var(--weight-normal);
  letter-spacing: var(--tracking-display);
  overflow-wrap: anywhere;
  text-wrap: balance;
}
.sheet-heading p {
  margin: var(--space-6) 0 var(--space-9);
  color: var(--ink-2);
  font-size: var(--type-body);
  line-height: var(--leading-reading);
  text-wrap: pretty;
}
.starter-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  border-block: var(--hairline) solid var(--rule);
}
.starter-list button {
  @include mixins.interactive-row;
  display: flex;
  align-items: center;
  gap: var(--space-4);
  min-width: 0;
  padding: var(--space-6) var(--space-4);
  border: 0;
  border-radius: var(--radius-none);
  text-align: left;
  color: var(--accent);
  background: var(--transparent);
}
.starter-list button + button { border-left: var(--hairline) solid var(--rule); }
.starter-list button span { display: grid; gap: var(--space-2); min-width: 0; }
.starter-list strong {
  color: var(--ink);
  font-size: var(--type-small);
  font-weight: var(--weight-medium);
}
.starter-list small { color: var(--ink-2); font-size: var(--type-caption); }
.starter-arrow { margin-left: auto; }
.sheet-unfinished:has(*) { padding-top: var(--space-7); }
@media (max-width: 1100px) {
  .starter-list { grid-template-columns: 1fr; }
  .starter-list button { padding: var(--space-4) var(--space-3); }
  .starter-list button + button { border-left: 0; border-top: var(--hairline) solid var(--rule); }
}
@media (max-width: 720px) {
  .first-stroke { width: calc(var(--welcome-mark-width) / 2); right: var(--space-5); }
  .sheet-heading { max-width: 100%; padding-top: var(--space-8); }
  h1 { max-width: calc(100% - var(--space-10)); }
  .sheet-heading p { margin-bottom: var(--space-7); }
}
</style>
