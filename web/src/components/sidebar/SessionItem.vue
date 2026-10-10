<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import type { Conversation } from '@/api/client'
import { useSessionStore } from '@/stores/session'
import { useWorkspaceStore } from '@/stores/workspace'
import { useRunStore } from '@/stores/run'
import { useDialog } from '@/composables/useDialog'
import Pulse from '@/components/shell/Pulse.vue'
import IconSymbol from '@/components/common/IconSymbol.vue'
const props = defineProps<{ item: Conversation; collapsed: boolean }>()
const emit = defineEmits<{ select: [] }>()
const session = useSessionStore(),
  workspace = useWorkspaceStore(),
  run = useRunStore(),
  router = useRouter()
const open = ref(false),
  dialog = ref<HTMLDialogElement | null>(null),
  confirming = ref(false)
const title = ref(''),
  folder = ref(''),
  error = ref(''),
  busy = ref<'save' | 'archive' | 'delete' | ''>('')
const running = computed(
  () =>
    Boolean(session.runningTaskIds[props.item.id]?.length) ||
    (run.turns[props.item.id] || []).some((turn) => ['running', 'waiting'].includes(turn.status)),
)
useDialog(dialog, () => open.value)
watch(open, (value) => {
  if (value) {
    title.value = props.item.title
    folder.value = props.item.folder_id || ''
    confirming.value = false
    error.value = ''
  }
})
async function act(action: 'save' | 'archive' | 'delete') {
  if (busy.value) return
  busy.value = action
  error.value = ''
  try {
    if (action === 'delete') await session.deleteSession(props.item.id)
    else
      await session.manageSession(
        props.item.id,
        action === 'archive'
          ? { archived: !props.item.archived }
          : {
              title: title.value.trim(),
              ...(folder.value !== (props.item.folder_id || '') ? { folder_id: folder.value } : {}),
            },
      )
    if (
      (action === 'delete' || action === 'archive') &&
      router.currentRoute.value.params.id === props.item.id
    )
      await router.push('/chat')
    open.value = false
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : String(reason)
  } finally {
    busy.value = ''
  }
}
</script>
<template>
  <div class="session-row">
    <router-link
      :to="'/chat/' + item.id"
      class="session-link"
      :title="item.title"
      @click="emit('select')"
    >
      <Pulse :state="run.pulse(item.id)" /><span v-if="!collapsed">{{
        item.title || '未命名对话'
      }}</span>
    </router-link>
    <button
      v-if="!collapsed"
      class="icon-button session-menu"
      :aria-label="'管理对话：' + item.title"
      @click="open = true"
    >
      <IconSymbol name="more" :size="16" />
    </button>
    <Teleport to="body">
      <dialog
        ref="dialog"
        class="session-dialog"
        aria-label="管理对话"
        @cancel.prevent="open = false"
        @click.self="open = false"
      >
        <header>
          <strong>{{ confirming ? '删除对话？' : '管理对话' }}</strong
          ><button class="icon-button" aria-label="关闭" @click="open = false">×</button>
        </header>
        <template v-if="confirming">
          <p>将删除「{{ item.title }}」的消息和执行记录，无法恢复。工作区文件不会删除。</p>
          <footer>
            <button class="secondary-button" :disabled="!!busy" @click="confirming = false">
              取消
            </button>
            <button
              class="danger-button"
              :disabled="!!busy || running"
              :aria-busy="busy === 'delete' || undefined"
              @click="act('delete')"
            >
              {{ busy === 'delete' ? '正在删除…' : '确认删除' }}
            </button>
          </footer>
        </template>
        <template v-else>
          <form @submit.prevent="act('save')">
            <label
              >对话名称<input v-model="title" maxlength="200" required :disabled="!!busy"
            /></label>
            <label
              >所属工作区<select v-model="folder" :disabled="!!busy || running">
                <option v-for="entry in workspace.folders" :key="entry.id" :value="entry.id">
                  {{ entry.name }}
                </option>
              </select></label
            >
            <p v-if="running" class="empty-copy">请先停止或完成任务，再移动、归档或删除对话。</p>
            <footer>
              <button
                class="primary-button"
                :disabled="!!busy || !title.trim()"
                :aria-busy="busy === 'save' || undefined"
              >
                {{ busy === 'save' ? '正在保存…' : '保存修改' }}
              </button>
            </footer>
          </form>
          <div class="management-actions">
            <button
              class="secondary-button"
              :disabled="!!busy || running"
              :aria-busy="busy === 'archive' || undefined"
              @click="act('archive')"
            >
              {{ item.archived ? '恢复对话' : '归档对话' }}
            </button>
            <button class="danger-button" :disabled="!!busy || running" @click="confirming = true">
              删除对话
            </button>
          </div>
        </template>
        <p v-if="error" class="error-banner" role="alert">{{ error }}</p>
      </dialog>
    </Teleport>
  </div>
</template>
<style scoped lang="scss">
@use '@/styles/mixins' as mixins;
.session-row {
  display: flex;
  align-items: center;
  gap: 2px;
}
.session-link {
  @include mixins.interactive-row;
  display: flex;
  flex: 1;
  min-width: 0;
  align-items: center;
  gap: 10px;
  height: 36px;
  padding: 0 8px 0 6px;
  border-left: 2px solid var(--transparent);
  color: var(--ink-2);
  border-radius: var(--radius-sm);
  text-decoration: none;
}
.session-link span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font: var(--text-sm) var(--font-serif);
}
.session-link.router-link-active {
  background: var(--accent-selected);
  color: var(--accent);
  border-left-color: var(--accent);
}
.session-menu {
  width: 26px;
  min-height: 28px;
  flex: none;
  color: var(--ink-3);
}
.session-dialog {
  width: min(380px, calc(100vw - 32px));
  padding: 20px;
  border: 1px solid var(--rule);
  border-radius: var(--radius-md);
  color: var(--ink);
  background: var(--paper);
  box-shadow: var(--shadow-float);
}
.session-dialog::backdrop {
  background: var(--backdrop);
}
header,
footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}
label {
  display: grid;
  gap: 8px;
  margin: 16px 0;
  font-size: var(--text-sm);
}
input,
select {
  width: 100%;
}
p {
  font-size: var(--text-sm);
  line-height: var(--leading-normal);
  overflow-wrap: anywhere;
}
footer {
  justify-content: flex-end;
}
.management-actions {
  display: flex;
  gap: 8px;
  justify-content: space-between;
  border-top: 1px solid var(--rule);
  padding-top: 16px;
  margin-top: 20px;
}
</style>
