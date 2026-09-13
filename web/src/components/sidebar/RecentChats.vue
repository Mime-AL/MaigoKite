/**
 * 最近对话列表组件
 *
 * 展示最近 30 天的对话列表，点击跳转到对应对话页。
 */

<script setup lang="ts">
import { useSessionStore } from '@/stores/session'

const sessionStore = useSessionStore()
</script>

<template>
  <div class="recent-chats">
    <div
      v-for="session in sessionStore.sessions"
      :key="session.id"
      class="chat-item"
      :class="{ active: session.id === sessionStore.activeSessionId }"
    >
      <router-link :to="`/chat/${session.id}`">
        {{ session.title || '未命名对话' }}
      </router-link>
    </div>
  </div>
</template>

<style scoped lang="scss">
.recent-chats {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.chat-item {
  a {
    display: block;
    padding: 6px 12px;
    border-radius: 4px;
    color: #bac2de;
    text-decoration: none;
    font-size: 14px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;

    &:hover {
      background-color: #313244;
    }
  }

  &.active a {
    background-color: #45475a;
    color: #cdd6f4;
  }
}
</style>
