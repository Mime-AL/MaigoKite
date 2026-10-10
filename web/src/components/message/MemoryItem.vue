<script setup lang="ts">
import type { UserMemory } from '@/api/client'
import { useMemoryStore } from '@/stores/memory'
import { useSessionStore } from '@/stores/session'
defineProps<{ item: UserMemory }>()
const emit = defineEmits<{ (event: 'edit', item: UserMemory): void }>()
const memory = useMemoryStore(),
  session = useSessionStore()
async function remove(item: UserMemory) {
  if (window.confirm('遗忘这条记忆？')) await memory.remove(item.id)
}
</script>
<template>
  <article class="memory-item" :id="`memory-${item.id}`" tabindex="-1">
    <p>{{ item.content.replace(/^人设：/, '') }}</p>
    <router-link
      v-if="session.sessions.some((s) => s.id === item.source_id)"
      :to="`/chat/${item.source_id}`"
      >来源会话</router-link
    ><small v-else>{{ item.source_type === 'user' ? '由你写下' : '助手记下' }}</small>
    <footer>
      <button
        :aria-pressed="memory.pinnedIds.includes(item.id)"
        @click="memory.togglePinned(item.id)"
      >
        {{ memory.pinnedIds.includes(item.id) ? '已置顶' : '置顶' }}</button
      ><button @click="emit('edit', item)">编辑</button
      ><button class="danger" :disabled="memory.saving" @click="remove(item)">遗忘</button>
    </footer>
  </article>
</template>
<style scoped lang="scss">
@use '@/styles/mixins' as mixins;
.memory-item {
  padding: 16px 0;
  border-bottom: 1px solid var(--rule);
}
p {
  margin: 0 0 8px;
  font-size: var(--text-md);
  line-height: var(--leading-body);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
small,
a {
  font-size: var(--text-xs);
  color: var(--ink-3);
}
footer {
  display: flex;
  gap: 12px;
  padding-top: 10px;
}
button {
  @include mixins.interactive-row;
  border: 0;
  padding: 4px 6px;
  font-size: var(--text-xs);
  color: var(--ink-2);
  background: var(--transparent);
}
.danger {
  color: var(--seal);
}
button[aria-pressed='true'] {
  color: var(--accent);
}
</style>
