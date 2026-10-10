<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import { useSettingsStore } from '@/stores/settings'
import { useUIStore } from '@/stores/ui'
import { useRunStore } from '@/stores/run'
import { useWorkspaceStore } from '@/stores/workspace'
import { useAutoFollow } from '@/composables/useAutoFollow'
import { railNodes } from '@/stores/run-projection'
import { remainingMessages } from '@/stores/session-projection'
import type { PermissionMode, ResponseMode } from '@/api/client'
import UserMessage from '@/components/chat-area/UserMessage.vue'
import AgentMessage from '@/components/chat-area/AgentMessage.vue'
import RailTrack from '@/components/rail/RailTrack.vue'
import RailMinimap from '@/components/rail/RailMinimap.vue'
import InputBox from '@/components/chat-area/InputBox.vue'
import InkLoader from '@/components/common/InkLoader.vue'
const route = useRoute(),
  router = useRouter(),
  session = useSessionStore(),
  settings = useSettingsStore(),
  ui = useUIStore(),
  run = useRunStore(),
  workspace = useWorkspaceStore()
const sessionId = computed(() => String(route.params.id || ''))
const scroll = ref<HTMLElement | null>(null),
  composer = ref<InstanceType<typeof InputBox> | null>(null),
  visibleCount = ref(20),
  sending = ref(false),
  restoring = ref(false)
const mode = ref<PermissionMode>('workspace')
const draftModel = ref(''),
  draftResponse = ref<ResponseMode>('balanced')
const turns = computed(() => run.turns[sessionId.value] || [])
const nodes = computed(() =>
  turns.value.flatMap((t) => [
    ...railNodes(t).map((n) => ({ id: n.id, turnId: t.id })),
    ...(t.summary ? [{ id: 'end', turnId: t.id }] : []),
  ]),
)
const savedMessages = computed(() =>
  sessionId.value ? session.messages[sessionId.value] || [] : [],
)
const unprojectedMessages = computed(() => remainingMessages(savedMessages.value, turns.value))
const timeline = computed(() =>
  [
    ...turns.value.map((turn) => ({
      key: 'turn-' + turn.id,
      time: turn.startedAt,
      turn,
      message: undefined,
    })),
    ...unprojectedMessages.value.map((message) => ({
      key: 'message-' + message.id,
      time: Date.parse(message.created_at),
      message,
      turn: undefined,
    })),
  ].sort((a, b) => a.time - b.time),
)
const visibleTimeline = computed(() => timeline.value.slice(-visibleCount.value))
const lastMessage = computed(
  () => savedMessages.value.filter((m) => m.role === 'user').slice(-1)[0]?.content || '',
)
const contextPct = computed(() => turns.value.slice(-1)[0]?.summary?.contextPct ?? null)
const queued = computed(() => session.queuedMessages[sessionId.value] || [])
const { following, onScroll, resume } = useAutoFollow(scroll, () => {
  const latest = timeline.value[timeline.value.length - 1]
  const turn = latest?.turn
  return [
    sessionId.value,
    timeline.value.length,
    latest?.key,
    latest?.message?.content.length,
    turn?.text.length,
    turn?.thinking.length,
    turn?.timeline.length,
    turn?.steps[turn.steps.length - 1]?.status,
    turn?.status,
  ].join('|')
})
const greeting = computed(() => {
  const hour = new Date().getHours()
  return hour < 6
    ? '夜深了'
    : hour < 11
      ? '早上好'
      : hour < 14
        ? '中午好'
        : hour < 18
          ? '午后好'
          : '晚上好'
})
const unfinished = computed(() =>
  session.sessions
    .filter((item) => !item.archived && (item.folder_id || '') === workspace.selectedId)
    .flatMap((item) => run.turns[item.id] || [])
    .filter((t) => ['waiting', 'failed', 'cancelled'].includes(t.status) && t.userText)
    .slice(-3),
)
let controls: Promise<unknown> = Promise.resolve()
let controlError = ''
let controlGeneration = 0
watch(
  sessionId,
  (id) => {
    controlGeneration++
    controlError = ''
    controls = Promise.resolve()
    visibleCount.value = 20
    if (id) void session.switchSession(id)
    else session.activeSessionId = null
    resume()
  },
  { immediate: true },
)
onMounted(() => {
  if (!settings.loaded) void settings.loadSettings()
})
async function send(content: string) {
  if (sending.value) return
  sending.value = true
  let id = sessionId.value
  try {
    await controls
    if (controlError) throw new Error(controlError)
    if (!id) {
      const item = await session.createSession('新对话')
      id = item.id
      await router.replace('/chat/' + id)
      await session.setPermissionMode(mode.value, id)
      await session.setConversationRuntime(
        draftModel.value || settings.defaultModelId,
        draftResponse.value,
        id,
      )
    }
    await session.sendToSession(id, content)
    resume()
  } catch (reason) {
    session.error = reason instanceof Error ? reason.message : String(reason)
    composer.value?.restoreDraft(content)
  } finally {
    sending.value = false
  }
}
async function restore() {
  if (restoring.value) return
  restoring.value = true
  try {
    await session.manageSession(sessionId.value, { archived: false })
    session.showArchived = false
  } catch (reason) {
    session.error = reason instanceof Error ? reason.message : String(reason)
  } finally { restoring.value = false }
}
function configure(action: () => Promise<unknown>) {
  const generation = controlGeneration
  controls = controls
    .then(action)
    .then(() => {
      if (generation === controlGeneration) controlError = ''
    })
    .catch((reason) => {
      if (generation === controlGeneration) controlError = session.error = String(reason)
    })
}
function permission(value: PermissionMode) {
  mode.value = value
  const id = sessionId.value
  if (id) configure(() => session.setPermissionMode(value, id))
}
function model(value: string) {
  draftModel.value = value
  const id = sessionId.value
  if (id)
    configure(() =>
      session.setConversationRuntime(
        value,
        session.sessions.find((item) => item.id === id)?.response_mode || 'balanced',
        id,
      ),
    )
}
function response(value: ResponseMode) {
  draftResponse.value = value
  const id = sessionId.value
  if (id)
    configure(() =>
      session.setConversationRuntime(
        session.sessions.find((item) => item.id === id)?.model_id || settings.defaultModelId,
        value,
        id,
      ),
    )
}
function editQueued(index: number) {
  const content = queued.value[index]
  if (content === undefined || !composer.value) return
  composer.value.restoreDraft(content)
  session.removeQueued(sessionId.value, index)
}
async function jump(node: { id: string; turnId: string }) {
  const index = timeline.value.findIndex((item) => item.turn?.id === node.turnId)
  visibleCount.value = Math.max(visibleCount.value, timeline.value.length - index)
  await nextTick()
  document
    .querySelector<HTMLElement>(
      '[data-rail-node="' + CSS.escape(node.turnId + ':' + node.id) + '"]',
    )
    ?.scrollIntoView({ block: 'center' })
}
</script>
<template>
  <div class="chat-page" :class="{ empty: !timeline.length }">
    <div class="conversation">
      <div ref="scroll" class="message-list" @scroll.passive="onScroll">
        <section v-if="!turns.length && !unprojectedMessages.length" class="welcome-state">
          <span class="welcome-date">{{
            new Date().toLocaleDateString('zh-CN', {
              month: 'long',
              day: 'numeric',
              weekday: 'long',
            })
          }}</span>
          <h1>{{ greeting }}，{{ ui.appearance.greetingName }}</h1>
          <p>把想做的事写下来。</p>
          <nav v-if="unfinished.length" class="unfinished">
            <span>上次没做完的事</span
            ><router-link
              v-for="turn in unfinished"
              :key="turn.id"
              :to="'/chat/' + turn.sessionId"
              >{{ turn.userText }}</router-link
            >
          </nav>
        </section>
        <div v-else class="messages-inner">
          <button v-if="timeline.length > visibleCount" class="earlier" @click="visibleCount += 20">
            再看前面的内容
          </button>
          <section v-for="item in visibleTimeline" :key="item.key" class="turn">
            <template v-if="item.message"
              ><UserMessage
                v-if="item.message.role === 'user'"
                :content="item.message.content" /><AgentMessage
                v-else
                :content="item.message.content"
                :assistant-name="settings.profile.assistantName"
            /></template>
            <template v-else-if="item.turn"
              ><UserMessage v-if="item.turn.userText" :content="item.turn.userText" />
              <RailTrack :turn="item.turn"
                ><AgentMessage
                  v-if="item.turn.text"
                  :content="item.turn.text"
                  :assistant-name="settings.profile.assistantName"
                  :is-streaming="item.turn.status === 'running'" /><InkLoader
                  v-else-if="item.turn.status === 'running'" /></RailTrack
            ></template>
          </section>
        </div>
      </div>
      <RailMinimap :nodes="nodes" @jump="jump" />
      <button v-if="!following" class="follow-button" @click="resume">
        ↓ {{ session.isSending ? '查看最新进展' : '回到最新消息' }}
      </button>
    </div>
    <p v-if="session.error" class="chat-error" role="alert">{{ session.error }}</p>
    <div v-if="queued.length" class="queued-messages">
      <p v-for="(content, index) in queued" :key="index">
        <span
          >{{ session.queuedPaused[sessionId] ? '待确认发送：' : '当前回合成功后发送：'
          }}{{ content }}</span
        ><button aria-label="取回排队消息编辑" @click="editQueued(index)">编辑</button
        ><button aria-label="移除排队消息" @click="session.removeQueued(sessionId, index)">
          ×
        </button>
      </p>
      <button
        v-if="session.queuedPaused[sessionId]"
        :disabled="session.isSending"
        @click="session.resumeQueued(sessionId)"
      >
        确认继续发送
      </button>
    </div>
    <div v-if="session.activeSession?.archived" class="archived-notice">
      <span>此对话已归档，可查看历史记录。</span>
      <button class="secondary-button" :disabled="restoring" :aria-busy="restoring || undefined" @click="restore">{{ restoring ? '正在恢复…' : '恢复对话' }}</button>
    </div>
    <InputBox
      v-else
      ref="composer"
      :session-id="sessionId"
      :assistant-name="settings.profile.assistantName"
      :is-sending="session.isSending"
      :is-submitting="sending"
      :is-stopping="session.isStopping"
      :model-id="
        sessionId
          ? session.activeSession?.model_id || settings.defaultModelId
          : draftModel || settings.defaultModelId
      "
      :model-options="settings.modelProfiles"
      :response-mode="
        sessionId ? session.activeSession?.response_mode || 'balanced' : draftResponse
      "
      :permission-mode="session.activeSession?.permission_mode || mode"
      :last-message="lastMessage"
      :context-pct="contextPct"
      @send="send"
      @cancel="session.cancelActiveTask"
      @permission-mode-change="permission"
      @model-change="model"
      @response-mode-change="response"
    />
  </div>
</template>
<style scoped lang="scss">
@use '@/styles/chat';
</style>
