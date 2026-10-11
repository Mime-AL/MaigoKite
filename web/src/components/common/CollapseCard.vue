<script setup lang="ts">
import { ref, watch } from 'vue'
import IconSymbol from './IconSymbol.vue'

const props = withDefaults(
  defineProps<{ title: string; defaultExpanded?: boolean; icon?: string }>(),
  {
    defaultExpanded: false,
    icon: 'activity',
  },
)
const isExpanded = ref(props.defaultExpanded)
watch(
  () => props.defaultExpanded,
  (value) => {
    isExpanded.value = value
  },
)
</script>

<template>
  <section class="collapse-card">
    <button
      class="card-header"
      type="button"
      :aria-expanded="isExpanded"
      @click="isExpanded = !isExpanded"
    >
      <span class="title-icon"><IconSymbol
        :name="icon"
        :size="15"
      /></span>
      <span>{{ title }}</span>
      <IconSymbol
        name="chevron"
        :size="14"
        class="chevron"
        :class="{ expanded: isExpanded }"
      />
    </button>
    <div
      v-if="isExpanded"
      class="card-body"
    >
      <slot />
    </div>
  </section>
</template>

<style scoped lang="scss">
.collapse-card {
  width: min(var(--measure-760px), calc(100% - var(--rail-node-height)));
  margin: var(--size-10) auto 0;
  overflow: hidden;
  border: var(--hairline) solid var(--rule);
  border-radius: var(--radius-lg);
  background: var(--paper-2);
}
.card-header {
  display: flex;
  width: 100%;
  height: var(--measure-42px);
  align-items: center;
  gap: var(--measure-9px);
  padding: 0 var(--space-4);
  border: 0;
  background: var(--transparent);
  color: var(--ink-2);
  cursor: pointer;
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  text-align: left;
}
.card-header:hover {
  color: var(--ink);
  background: var(--paper-3);
}
.title-icon {
  display: grid;
  width: var(--measure-25px);
  height: var(--measure-25px);
  place-items: center;
  border-radius: var(--radius-sm);
  color: var(--accent);
  background: var(--accent-soft);
}
.chevron {
  margin-left: auto;
  transition: transform var(--motion-pulse) var(--ease);
}
.chevron.expanded {
  transform: rotate(var(--measure-90deg));
}
.card-body {
  padding: var(--size-10) var(--measure-13px) var(--measure-13px);
  border-top: var(--hairline) solid var(--rule);
}
</style>
