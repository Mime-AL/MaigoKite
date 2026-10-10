<script setup lang="ts">
import { computed } from 'vue'
import { useRunStore } from '@/stores/run'
import { useSessionStore } from '@/stores/session'
const run = useRunStore(),
  session = useSessionStore()
const items = computed(() => run.turns[session.activeSessionId || '']?.slice(-1)[0]?.plan || [])
const progress = computed(() =>
  items.value.length ? (items.value.filter((i) => i.status === 'completed').length / items.value.length) * 100 : 0,
)
</script>
<template>
  <section class="plan-tab">
    <p v-if="!items.length" class="empty-copy">{{ $t('还没有执行计划。') }}</p>
    <template v-else
      ><div class="plan-progress"><i :style="{ width: `${progress}%` }" /></div>
      <ul>
        <li v-for="(item, index) in items" :key="index" :class="item.status">
          <span>{{ item.status === 'completed' ? '✓' : item.status === 'in_progress' ? '●' : '○' }}</span
          >{{ item.content }}
        </li>
      </ul></template
    >
  </section>
</template>
<style scoped lang="scss">
.plan-tab {
  padding: 20px;
}
.plan-progress {
  height: 2px;
  background: var(--rule);
}
i {
  display: block;
  height: 100%;
  background: var(--accent);
  transition: width var(--duration) var(--ease);
}
ul {
  list-style: none;
  padding: 0;
}
li {
  display: flex;
  gap: 12px;
  padding: 10px 0;
  font-size: var(--text-sm);
  color: var(--ink-2);
}
.completed {
  color: var(--ink-2);
}
.in_progress span {
  color: var(--accent);
}
</style>
