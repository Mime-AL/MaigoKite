<script setup lang="ts">
import { computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import { useSettingsStore } from '@/stores/settings'
import IconSymbol from '@/components/common/IconSymbol.vue'
import MessageList from '@/components/chat-area/MessageList.vue'
import InputBox from '@/components/chat-area/InputBox.vue'
import type { PermissionMode, ResponseMode } from '@/api/client'

const route = useRoute()
const sessionStore = useSessionStore()
const settingsStore = useSettingsStore()
const sessionId = computed(() => String(route.params.id || ''))
const title = computed(() => sessionStore.activeSession?.title || '新对话')
function updatePermissionMode(permissionMode: PermissionMode) {
  void sessionStore.setPermissionMode(permissionMode)
}

function updateModel(modelId: string) {
  void sessionStore.setConversationRuntime(
    modelId,
    sessionStore.activeSession?.response_mode || 'balanced',
  )
}

function updateResponseMode(responseMode: ResponseMode) {
  void sessionStore.setConversationRuntime(
    sessionStore.activeSession?.model_id || settingsStore.defaultModelId,
    responseMode,
  )
}

onMounted(() => {
  if (sessionId.value) void sessionStore.switchSession(sessionId.value)
  if (!settingsStore.loaded) void settingsStore.loadSettings()
})
watch(sessionId, id => { if (id) void sessionStore.switchSession(id) })
onUnmounted(() => sessionStore.disconnect())
</script>

<template>
  <div class="chat-page">
    <header class="chat-context">
      <div class="agent-avatar"><IconSymbol name="sparkles" :size="18" /></div>
      <div class="chat-title">
        <strong>{{ title }}</strong>
        <span><i /> {{ settingsStore.profile.assistantName }}</span>
      </div>
    </header>

    <div class="conversation">
      <MessageList :session-id="sessionId" :assistant-name="settingsStore.profile.assistantName" @suggest="sessionStore.sendMessage" />
    </div>

    <p v-if="sessionStore.error" class="chat-error"><IconSymbol name="alert" :size="15" />{{ sessionStore.error }}</p>
    <InputBox
      :session-id="sessionId"
      :assistant-name="settingsStore.profile.assistantName"
      :is-sending="sessionStore.isSending"
      :model-id="sessionStore.activeSession?.model_id || settingsStore.defaultModelId"
      :model-options="settingsStore.modelProfiles"
      :response-mode="sessionStore.activeSession?.response_mode || 'balanced'"
      :permission-mode="sessionStore.activeSession?.permission_mode || 'workspace'"
      @model-change="updateModel"
      @response-mode-change="updateResponseMode"
      @permission-mode-change="updatePermissionMode"
      @send="sessionStore.sendMessage"
      @cancel="sessionStore.cancelActiveTask"
    />
  </div>
</template>

<style scoped lang="scss">
.chat-page { display: flex; height: 100%; min-height: 0; flex-direction: column; background: var(--surface-solid); }
.chat-context { display: flex; height: 64px; flex: none; align-items: center; gap: 11px; padding: 0 clamp(18px, 3vw, 34px); border-bottom: 1px solid var(--border-color); }
.agent-avatar { display: grid; width: 36px; height: 36px; place-items: center; border-radius: 12px; color: #fff; background: linear-gradient(145deg, #5f7cff, #8e6ee8); box-shadow: 0 6px 14px rgba(105, 104, 224, 0.23), inset 0 1px rgba(255, 255, 255, 0.32); }
.chat-title { min-width: 0; display: flex; flex: 1; flex-direction: column; }
.chat-title strong { overflow: hidden; font-size: 13px; font-weight: 650; text-overflow: ellipsis; white-space: nowrap; }
.chat-title span { display: flex; align-items: center; gap: 5px; margin-top: 3px; color: var(--text-tertiary); font-size: 9.5px; text-transform: capitalize; }
.chat-title i { width: 5px; height: 5px; border-radius: 50%; background: var(--success); }
.conversation { min-height: 0; display: flex; flex: 1; flex-direction: column; overflow: hidden; }
.chat-error { display: flex; flex: none; align-items: center; gap: 7px; margin: 0 auto 8px; padding: 8px 12px; border-radius: 10px; color: var(--danger); background: var(--danger-soft); font-size: 11px; }
</style>
