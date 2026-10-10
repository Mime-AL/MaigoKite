<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { useUIStore } from '@/stores/ui'
import { useSessionStore } from '@/stores/session'
import { useWorkspaceStore } from '@/stores/workspace'
import { useRouter } from 'vue-router'
import Pulse from '@/components/shell/Pulse.vue'
import { desktopEffects } from '@/composables/useElectron'
useUIStore()
const session = useSessionStore(),
  workspace = useWorkspaceStore(),
  router = useRouter()
const text = ref(''),
  input = ref<HTMLInputElement | null>(null),
  sending = ref(false),
  error = ref('')
onMounted(async () => {
  await nextTick()
  input.value?.focus()
})
async function send(newSession = false) {
  if (!text.value.trim() || sending.value) return
  sending.value = true
  error.value = ''
  try {
    if (desktopEffects) await desktopEffects.sendCapsule({ content: text.value.trim(), newSession })
    else {
      await session.loadSessions()
      const recent = session.sessions.find((item) => !item.archived && (item.folder_id || '') === workspace.selectedId)
      const id = newSession || !recent ? (await session.createSession('新对话')).id : recent.id
      await session.sendToSession(id, text.value.trim())
      await router.push(`/chat/${id}`)
    }
    text.value = ''
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : String(reason)
  } finally {
    sending.value = false
  }
}
function keydown(event: KeyboardEvent) {
  if (event.isComposing) return
  if (event.key === 'Escape') void window.electronAPI?.windowControl('hide')
  if (event.key === 'Enter') {
    event.preventDefault()
    void send(event.ctrlKey || event.metaKey)
  }
}
function drop(event: DragEvent) {
  const file = event.dataTransfer?.files[0] as (File & { path?: string }) | undefined
  const value = file?.path || event.dataTransfer?.getData('text/plain')
  if (value) text.value += `${text.value ? ' ' : ''}${value}`
}
</script>
<template>
  <form class="capsule" @submit.prevent="send()" @dragover.prevent @drop.prevent="drop">
    <Pulse :state="sending ? 'thinking' : 'idle'" /><input
      ref="input"
      v-model="text"
      :placeholder="error || $t('输入消息…')"
      maxlength="10000"
      :aria-label="$t('速记内容')"
      :title="error"
      @keydown="keydown"
    /><button :disabled="!text.trim() || sending" :title="$t('Enter 发送 · Ctrl/⌘+Enter 新页')">↵</button>
  </form>
</template>
<style scoped lang="scss">
.capsule {
  height: var(--capsule-height);
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 0 20px;
  background: var(--paper);
  border: 1px solid var(--rule);
  border-radius: var(--radius-md);
  -webkit-app-region: drag;
}
input {
  flex: 1;
  min-width: 0;
  border: 0;
  outline: 0;
  background: var(--transparent);
  font-size: var(--text-md);
  -webkit-app-region: no-drag;
}
input::placeholder {
  color: var(--ink-3);
}
button {
  border: 0;
  background: var(--transparent);
  color: var(--ink-3);
  padding: 8px;
  -webkit-app-region: no-drag;
}
</style>
