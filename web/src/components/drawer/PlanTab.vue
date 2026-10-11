<script setup lang="ts">
import { computed } from 'vue'
import { useRunStore } from '@/stores/run'
import { useSessionStore } from '@/stores/session'
import IconSymbol from '@/components/common/IconSymbol.vue'
import InkLoader from '@/components/common/InkLoader.vue'
const run = useRunStore(),
  session = useSessionStore()
const turn = computed(() => run.turns[session.activeSessionId || '']?.slice(-1)[0])
const items = computed(() => turn.value?.plan || [])
const progress = computed(() =>
  items.value.length
    ? (items.value.filter((i) => i.status === 'completed').length / items.value.length) * 100
    : 0,
)
</script>
<template>
  <section class="plan-tab">
    <p v-if="turn?.planError" class="empty-copy" role="alert">
      {{ turn.planError
      }}<button
        class="text-button"
        @click="session.refreshTaskDetails(session.activeSessionId!, turn.id)"
      >
        {{ $t('重试') }}
      </button>
    </p>
    <InkLoader v-else-if="turn?.planLoading && !items.length" />
    <div v-else-if="!items.length" class="plan-empty">
      <IconSymbol name="check" :size="24" /><strong>{{ $t('还没有执行计划。') }}</strong>
      <p>{{ $t('任务需要分步进行时，Agent 的计划会显示在这里。') }}</p>
    </div>
    <template v-else
      ><p class="plan-count">
        {{
          $t('已完成 {0} / {1} 步', [
            items.filter((item) => item.status === 'completed').length,
            items.length,
          ])
        }}
      </p>
      <div class="plan-progress"><i :style="{ transform: `scaleX(${progress / 100})` }" /></div>
      <ul>
        <li v-for="(item, index) in items" :key="index" :class="item.status">
          <span>{{
            item.status === 'completed' ? '✓' : item.status === 'in_progress' ? '●' : '○'
          }}</span
          >{{ item.content }}
        </li>
      </ul></template
    >
  </section>
</template>
<style scoped lang="scss">
@use '@/styles/mixins' as mixins;
.text-button {
  @include mixins.text-action;
}
.plan-tab {
  padding: var(--space-6);
}
.plan-progress {
  height: var(--space-1);
  background: var(--rule);
}
i {
  display: block;
  height: 100%;
  background: var(--accent);
  transform-origin: left;
  transition: transform var(--duration) var(--ease);
}
ul {
  list-style: none;
  padding: 0;
}
li {
  display: flex;
  gap: var(--space-4);
  padding: var(--space-4) 0;
  font-size: var(--text-sm);
  color: var(--ink-2);
}
.completed {
  color: var(--ink-2);
}
.in_progress span {
  color: var(--accent);
}
.plan-empty {
  padding-block: var(--space-8);
  color: var(--ink-2);
  font-size: var(--text-sm);
  line-height: var(--leading-body);
}
.plan-empty strong {
  display: block;
  margin-top: var(--space-4);
  font-weight: var(--weight-medium);
}
.plan-count {
  font-size: var(--text-xs);
  color: var(--ink-2);
}
@media (prefers-reduced-motion: reduce) {
  i {
    transition: none;
  }
}
</style>
