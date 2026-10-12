<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { t } from '@/i18n'
import { useMemoryStore } from '@/stores/memory'
import { useSettingsStore } from '@/stores/settings'
import { useUIStore } from '@/stores/ui'
import { useWorkspaceStore } from '@/stores/workspace'
import { api, type UserMemory } from '@/api/client'
import { memoryGroup } from '@/utils/work-records'
import MemoryGroup from '@/components/message/MemoryGroup.vue'
import type { MemoryDraft } from '@/components/message/MemoryEditor.vue'
import InkLoader from '@/components/common/InkLoader.vue'
import AppIcon from '@/components/common/AppIcon.vue'
const memory = useMemoryStore(),
  settings = useSettingsStore(),
  ui = useUIStore(),
  workspace = useWorkspaceStore(),
  route = useRoute()
const selectedScope = ref(workspace.selectedId)
const runtimeMemory = ref(false)
const unassigned = '__unassigned__'
function reload() {
  return memory.load(search.value, selectedScope.value === unassigned ? null : selectedScope.value)
}
watch(() => workspace.selectedId, (id) => { selectedScope.value = id })
watch(selectedScope, () => {
  draft.value = undefined
  search.value = ''
  void reload()
})
const search = ref(memory.query),
  name = ref(settings.profile.assistantName)
const draft = ref<MemoryDraft>(),
  notice = ref('')
const nameSaveFailed = ref(false)
let noticeTimer: ReturnType<typeof setTimeout> | undefined
let alive = true
const groups = computed(() => [
  {
    id: 'persona',
    title: '人设',
    hint: '写下希望它如何与你相处。',
    items: memory.orderedItems.filter((item) => memoryGroup(item) === 'persona'),
  },
  {
    id: 'preference',
    title: '偏好',
    hint: '记录你的习惯、偏好和需要留意的限制。',
    items: memory.orderedItems.filter((item) => memoryGroup(item) === 'preference'),
  },
  {
    id: 'memory',
    title: '记忆',
    hint: '留存重要事实、项目背景或值得记住的片段。',
    items: memory.orderedItems.filter((item) => memoryGroup(item) === 'memory'),
  },
])
const focusedId = computed(() => (typeof route.query.focus === 'string' ? route.query.focus : ''))
const editingGroup = computed(() =>
  draft.value
    ? draft.value.persona
      ? 'persona'
      : ['preference', 'constraint'].includes(draft.value.category)
        ? 'preference'
        : 'memory'
    : '',
)
watch(focusedId, (id) => {
  if (id) {
    search.value = ''
    void reload()
  }
})
watch(
  [focusedId, () => memory.items, () => memory.loading],
  async () => {
    if (!focusedId.value || memory.loading) return
    await nextTick()
    const element = document.getElementById('memory-' + focusedId.value)
    element?.focus({ preventScroll: true })
    element?.scrollIntoView({ block: 'center' })
  },
  { flush: 'post' },
)
onMounted(async () => {
  if (focusedId.value) search.value = ''
  await workspace.load()
  await Promise.all([reload(), settings.loadPreferences(), api.getCapabilities().then((flags) => {
    runtimeMemory.value = flags.scoped_memory === true
  }).catch(() => { runtimeMemory.value = false })])
  name.value = settings.profile.assistantName
})
onUnmounted(() => {
  alive = false
  if (noticeTimer) clearTimeout(noticeTimer)
})
function noted() {
  if (!alive) return
  notice.value = t('已记下')
  if (noticeTimer) clearTimeout(noticeTimer)
  noticeTimer = setTimeout(() => {
    notice.value = ''
    noticeTimer = undefined
  }, 2200)
}
function startCreate(group = 'memory') {
  draft.value = {
    category: group === 'preference' ? 'preference' : 'fact',
    content: '',
    confidence: 1,
    persona: group === 'persona',
  }
}
function startEdit(item: UserMemory) {
  draft.value = {
    id: item.id,
    category: item.category,
    content: item.content.replace(/^人设：/, ''),
    confidence: item.confidence,
    persona: item.content.startsWith('人设：'),
  }
}
async function save(value: MemoryDraft) {
  if (memory.saving || !value.content.trim()) return
  const saved = await memory.save({
    id: value.id,
    category: value.category,
    confidence: value.confidence,
    content: value.persona ? '人设：' + value.content.trim() : value.content.trim(),
  })
  if (saved) {
    draft.value = undefined
    noted()
  }
}
async function saveName() {
  if (settings.saving) return
  const saved = await settings.savePreferences(name.value)
  nameSaveFailed.value = !saved
  if (saved) noted()
}
function retryName() {
  if (nameSaveFailed.value) void saveName()
  else void settings.loadPreferences()
}
</script>
<template>
  <main class="page-shell memory-page">
    <header class="memory-heading">
      <h1>{{ $t('它记得') }}</h1>
      <form
        class="memory-search"
        @submit.prevent="reload()"
      >
        <input
          v-model="search"
          type="search"
          :aria-label="$t('搜索记忆')"
          :placeholder="$t('找一条记忆…')"
          maxlength="200"
        ><button
          class="secondary-button"
          :disabled="memory.loading"
        >
          {{ $t('搜索') }}
        </button>
      </form>
    </header>
    <section class="memory-scope">
      <label>{{ $t('记忆归属') }}
        <select v-model="selectedScope" :disabled="memory.saving || memory.savingSettings">
          <option v-for="folder in workspace.folders" :key="folder.id" :value="folder.id">
            {{ folder.name }}
          </option>
          <option :value="unassigned">{{ $t('未归属的旧记忆') }}</option>
        </select>
      </label>
      <p v-if="selectedScope === unassigned">{{ $t('这些记录仅供查看和编辑，不会自动带入任何对话。') }}</p>
      <template v-else>
        <button class="secondary-button" type="button" role="switch" :aria-checked="memory.enabled"
          :disabled="!runtimeMemory || !memory.settingsReady || memory.loading || memory.savingSettings"
          @click="memory.setEnabled(!memory.enabled)">
          {{ memory.enabled ? $t('本工作区记忆：开启') : $t('本工作区记忆：关闭') }}
        </button>
        <p v-if="runtimeMemory">{{ $t('默认关闭。开启后，还需在具体对话中开启；仅将本文件夹的已保存记忆提供给本对话已选择的模型服务。') }}</p>
        <p v-else>{{ $t('当前服务未启用跨对话使用，已保存的记忆仍可管理。') }}</p>
        <p>{{ $t('关闭或删除只影响后续请求，不会清除历史回复；需要干净上下文时，请新建关闭记忆的对话。') }}</p>
        <p v-if="memory.settingsError" role="alert">{{ memory.settingsError }}</p>
      </template>
    </section>
    <p
      class="memory-notice"
      role="status"
      aria-live="polite"
    >
      {{ notice }}
    </p>
    <div
      v-if="memory.loading"
      class="memory-loading"
      :aria-label="$t('正在读取记忆')"
    >
      <InkLoader /><InkLoader /><InkLoader />
    </div>
    <p
      v-if="memory.error"
      class="memory-error"
      role="alert"
    >
      {{ memory.error
      }}<button
        class="secondary-button"
        :disabled="memory.loading"
        @click="reload()"
      >
        {{ $t('重试') }}
      </button>
    </p>
    <section
      class="memory-identity"
      :aria-label="$t('身份')"
    >
      <div class="identity-profile">
        <div class="identity-avatar">
          <AppIcon
            v-if="ui.appearance.avatar === '助'"
            :size="48"
          /><span
            v-else
            class="avatar-letter"
          >{{ ui.appearance.avatar }}</span><strong>{{ settings.profile.assistantName }}</strong>
        </div>
        <label>{{ $t('助手名字') }}<input
          v-model="name"
          maxlength="32"
        ></label>
        <button
          class="secondary-button"
          :disabled="!name.trim() || settings.saving"
          :aria-busy="settings.saving || undefined"
          @click="saveName"
        >
          {{ settings.saving ? $t('正在保存…') : $t('保存称呼') }}
        </button>
        <label>{{ $t('头像字')
        }}<input
          :value="ui.appearance.avatar"
          @input="
            ui.setAppearance({
              avatar: Array.from(($event.target as HTMLInputElement).value)[0] || '助',
            })
          "
        ></label>
        <p
          v-if="settings.error"
          class="memory-error"
          role="alert"
        >
          {{ settings.error
          }}<button
            class="secondary-button"
            :disabled="settings.saving"
            @click="retryName"
          >
            {{ $t('重试') }}
          </button>
        </p>
      </div>
      <MemoryGroup
        :title="groups[0].title"
        :hint="groups[0].hint"
        :items="groups[0].items"
        :editor="editingGroup === 'persona' ? draft : undefined"
        :focused-id="focusedId"
        :saving="memory.saving"
        :loading="memory.loading"
        :error="Boolean(memory.error)"
        :searched="Boolean(memory.query)"
        @create="startCreate('persona')"
        @edit="startEdit"
        @save="save"
        @cancel="draft = undefined"
      />
    </section>
    <div class="memory-columns">
      <MemoryGroup
        v-for="group in groups.slice(1)"
        :key="group.id"
        :title="group.title"
        :hint="group.hint"
        :items="group.items"
        :editor="editingGroup === group.id ? draft : undefined"
        :focused-id="focusedId"
        :saving="memory.saving"
        :loading="memory.loading"
        :error="Boolean(memory.error)"
        :searched="Boolean(memory.query)"
        @create="startCreate(group.id)"
        @edit="startEdit"
        @save="save"
        @cancel="draft = undefined"
      />
    </div>
  </main>
</template>
<style scoped lang="scss">
@use '@/styles/memory';
</style>
