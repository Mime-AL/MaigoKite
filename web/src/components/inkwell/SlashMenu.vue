<script setup lang="ts">
export interface SlashCommand {
  id: string
  label: string
}
defineProps<{ items: SlashCommand[]; selected: number }>()
const emit = defineEmits<{ (event: 'select', item: SlashCommand): void }>()
</script>
<template>
  <div class="slash-menu" role="listbox" aria-label="命令">
    <button
      v-for="(item, index) in items"
      :key="item.id"
      role="option"
      :aria-selected="index === selected"
      @mousedown.prevent
      @click="emit('select', item)"
    >
      <code>/{{ item.id }}</code
      ><span>{{ item.label }}</span>
    </button>
  </div>
</template>
<style scoped lang="scss">
@use '@/styles/mixins' as mixins;
.slash-menu {
  position: absolute;
  bottom: calc(100% + 8px);
  inset-inline: 0;
  max-height: 280px;
  overflow: auto;
  padding: 6px;
  border: 1px solid var(--rule);
  border-radius: var(--radius-md);
  background: var(--paper);
  box-shadow: var(--shadow-float);
  z-index: 10;
}
button {
  @include mixins.interactive-row;
  display: flex;
  width: 100%;
  gap: 20px;
  border: 0;
  padding: 10px;
  background: var(--transparent);
  color: var(--ink-2);
  text-align: left;
  font-size: var(--text-sm);
}
button[aria-selected='true'] {
  background: var(--accent-selected);
}
code {
  width: 90px;
  font-family: var(--font-mono);
  color: var(--ink-3);
}
</style>
