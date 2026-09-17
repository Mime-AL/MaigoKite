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
.recent-chats { max-height: 100%; overflow-y: auto; }
.chat-item { display: flex; height: 32px; align-items: center; gap: 8px; padding: 0 8px; border-radius: 9px; color: var(--text-secondary); font-size: 12px; transition: background 140ms ease, color 140ms ease; }
.chat-item:hover, .chat-item.active { color: var(--text-primary); background: var(--surface-strong); }
.chat-item :deep(.icon-symbol) { opacity: 0; transition: opacity 140ms ease; }
.chat-item:hover :deep(.icon-symbol), .chat-item.active :deep(.icon-symbol) { opacity: 0.75; }
.chat-dot { width: 5px; height: 5px; flex: none; border-radius: 50%; background: var(--text-tertiary); }
.chat-item.active .chat-dot { background: var(--primary-color); box-shadow: 0 0 0 3px var(--primary-soft); }
.chat-title { min-width: 0; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.empty { margin: 2px 8px; color: var(--text-tertiary); font-size: 11px; }
</style>
