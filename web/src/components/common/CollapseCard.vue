<script setup lang="ts">
import { ref, watch } from 'vue'
import IconSymbol from './IconSymbol.vue'

const props = withDefaults(defineProps<{ title: string; defaultExpanded?: boolean; icon?: string }>(), {
  defaultExpanded: false,
  icon: 'activity',
})
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
    <button class="card-header" type="button" :aria-expanded="isExpanded" @click="isExpanded = !isExpanded">
      <span class="title-icon"><IconSymbol :name="icon" :size="15" /></span>
      <span>{{ title }}</span>
      <IconSymbol name="chevron" :size="14" class="chevron" :class="{ expanded: isExpanded }" />
    </button>
    <div v-if="isExpanded" class="card-body"><slot /></div>
  </section>
</template>

<style scoped lang="scss">
.collapse-card {
  width: min(760px, calc(100% - 40px));
  margin: 10px auto 0;
  overflow: hidden;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  background: var(--surface-muted);
}
.card-header {
  display: flex;
  width: 100%;
  height: 42px;
  align-items: center;
  gap: 9px;
  padding: 0 12px;
  border: 0;
  background: var(--transparent);
  color: var(--text-secondary);
  cursor: pointer;
  font-size: var(--text-xs);
  font-weight: var(--weight-semibold);
  text-align: left;
}
.card-header:hover {
  color: var(--text-primary);
  background: var(--surface-strong);
}
.title-icon {
  display: grid;
  width: 25px;
  height: 25px;
  place-items: center;
  border-radius: var(--radius-sm);
  color: var(--primary-color);
  background: var(--primary-soft);
}
.chevron {
  margin-left: auto;
  transition: transform var(--motion-pulse) var(--ease);
}
.chevron.expanded {
  transform: rotate(90deg);
}
.card-body {
  padding: 10px 13px 13px;
  border-top: 1px solid var(--border-color);
}
</style>
