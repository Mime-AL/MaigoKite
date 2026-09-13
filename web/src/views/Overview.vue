/**
 * 总览页
 *
 * 展示最近对话、活跃会话、快速操作入口。
 */

<script setup lang="ts">
import { useSessionStore } from '@/stores/session'
import { useSkillStore } from '@/stores/skill'
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

const sessionStore = useSessionStore()
const skillStore = useSkillStore()
const router = useRouter()

onMounted(async () => {
  await sessionStore.loadSessions()
  await skillStore.loadSkills()
})

function createNewSession() {
  sessionStore.createSession('').then((session) => {
    router.push(`/chat/${session.id}`)
  })
}
</script>

<template>
  <div class="overview">
    <h1>欢迎使用 NanamiGopher</h1>
    <div class="quick-actions">
      <button class="btn-primary" @click="createNewSession">新建对话</button>
    </div>
    <section class="recent-sessions">
      <h2>最近对话</h2>
      <ul>
        <li v-for="session in sessionStore.sessions.slice(0, 5)" :key="session.id">
          <router-link :to="`/chat/${session.id}`">{{ session.title || '未命名对话' }}</router-link>
        </li>
      </ul>
    </section>
  </div>
</template>

<style scoped lang="scss">
.overview {
  padding: 24px;
}

.quick-actions {
  margin: 16px 0;
}

.btn-primary {
  padding: 8px 20px;
  background-color: #0066cc;
  color: #fff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.recent-sessions {
  margin-top: 24px;

  h2 {
    margin-bottom: 12px;
  }

  ul {
    list-style: none;
    padding: 0;
  }

  li {
    padding: 8px 0;
    border-bottom: 1px solid #eee;
  }
}
</style>
