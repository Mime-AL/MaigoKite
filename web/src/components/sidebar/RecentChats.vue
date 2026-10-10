<script setup lang="ts">
import { useSessionStore } from '@/stores/session'
import IconSymbol from '@/components/common/IconSymbol.vue'

const sessionStore = useSessionStore()
</script>

<template>
  <div class="recent-chats">
    <router-link
      v-for="session in sessionStore.sessions.slice(0, 8)"
      :key="session.id"
      :to="`/chat/${session.id}`"
      class="chat-item"
      :class="{ active: session.id === sessionStore.activeSessionId }"
    >
      <span class="chat-dot" />
      <span class="chat-title">{{ session.title || '未命名对话' }}</span>
      <IconSymbol name="chevron" :size="13" />
    </router-link>
    <p v-if="sessionStore.sessions.length === 0" class="empty">还没有对话</p>
  </div>
</template>

<style scoped lang="scss">
.recent-chats {
  max-height: 100%;
  overflow-y: auto;
}
.chat-item {
  display: flex;
  height: 32px;
  align-items: center;
  gap: 8px;
  padding: 0 8px;
  border-radius: var(--radius-md);
  color: var(--text-secondary);
  font-size: var(--text-xs);
  transition:
    background var(--motion-pulse) var(--ease),
    color var(--motion-pulse) var(--ease);
}
.chat-item:hover,
.chat-item.active {
  color: var(--text-primary);
  background: var(--surface-strong);
}
.chat-item :deep(.icon-symbol) {
  opacity: 0;
  transition: opacity var(--motion-pulse) var(--ease);
}
.chat-item:hover :deep(.icon-symbol),
.chat-item.active :deep(.icon-symbol) {
  opacity: 0.75;
}
.chat-dot {
  width: 5px;
  height: 5px;
  flex: none;
  border-radius: var(--radius-round);
  background: var(--text-tertiary);
}
.chat-item.active .chat-dot {
  background: var(--primary-color);
  box-shadow: var(--shadow-card);
}
.chat-title {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.empty {
  margin: 2px 8px;
  color: var(--text-tertiary);
  font-size: var(--text-xs);
}
</style>
