<script setup lang="ts">
import { ref } from 'vue'
import { useDialog } from '@/composables/useDialog'
import { useInboxStore } from '@/stores/inbox'
import { useSessionStore } from '@/stores/session'
import { useUIStore } from '@/stores/ui'
import ApprovalCard from '@/components/chat-area/ApprovalCard.vue'
import QuestionCard from './QuestionCard.vue'
const inbox = useInboxStore(),
  session = useSessionStore(),
  ui = useUIStore()
const dialog = ref<HTMLDialogElement | null>(null)
useDialog(dialog, () => ui.inboxOpen)
</script>
<template>
  <dialog
    ref="dialog"
    class="inbox-shade"
    aria-label="等你收件箱"
    @cancel.prevent="ui.inboxOpen = false"
    @keydown.esc.stop
    @click.self="ui.inboxOpen = false"
  >
    <section class="inbox-popover">
      <header>
        <strong>等你 · {{ inbox.items.length }}</strong
        ><button class="icon-button" aria-label="关闭收件箱" @click="ui.inboxOpen = false">
          ×
        </button>
      </header>
      <p v-if="!inbox.items.length && !inbox.error" class="empty-copy">暂时没有需要你处理的事。</p>
      <article v-for="item in inbox.items" :key="item.id">
        <router-link :to="`/chat/${item.sessionId}`" @click="ui.inboxOpen = false">{{
          session.sessions.find((s) => s.id === item.sessionId)?.title || '对话'
        }}</router-link>
        <ApprovalCard v-if="item.mode === 'approval'" :item="item" /><QuestionCard
          v-else
          :item="item"
        />
      </article>
      <p v-if="inbox.error" class="empty-copy" role="alert">
        {{ inbox.error }} <button class="secondary-button" @click="inbox.refresh">重新读取</button>
      </p>
    </section>
  </dialog>
</template>
<style scoped lang="scss">
.inbox-shade {
  position: fixed;
  inset: var(--titlebar-height) 0 0;
  z-index: 40;
  background: var(--transparent);
  margin: 0;
  padding: 0;
  border: 0;
  width: 100%;
  height: calc(100% - var(--titlebar-height));
  max-width: none;
  max-height: none;
  color: var(--ink);
}
.inbox-shade::backdrop {
  background: var(--transparent);
}
.inbox-popover {
  position: absolute;
  top: 8px;
  right: 18px;
  width: min(440px, calc(100vw - 36px));
  max-height: 75vh;
  overflow: auto;
  padding: 18px;
  border: 1px solid var(--rule);
  border-radius: var(--radius-md);
  background: var(--paper);
  box-shadow: var(--shadow-float);
}
header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
header strong {
  font-size: var(--text-md);
}
article > a {
  font-size: var(--text-xs);
}
</style>
