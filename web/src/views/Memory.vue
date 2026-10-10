<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useMemoryStore } from '@/stores/memory'
import { useSettingsStore } from '@/stores/settings'
import type { MemoryCategory, UserMemory } from '@/api/client'
import MemoryItem from '@/components/message/MemoryItem.vue'
import InkLoader from '@/components/common/InkLoader.vue'
import { useUIStore } from '@/stores/ui'
const memory = useMemoryStore(),
  settings = useSettingsStore(),
  ui = useUIStore()
const route = useRoute()
const search = ref(memory.query),
  editing = ref(false),
  name = ref(settings.profile.assistantName)
const draft = reactive<{
  id?: string
  category: MemoryCategory
  content: string
  confidence: number
  persona: boolean
}>({ category: 'preference', content: '', confidence: 1, persona: false })
const columns = computed(() => [
  {
    id: 'persona',
    title: '人设',
    description: '名字、语气、相处方式',
    items: memory.orderedItems.filter((m) => m.content.startsWith('人设：')),
  },
  {
    id: 'preference',
    title: '偏好',
    description: '常用习惯、希望遵循的规则',
    items: memory.orderedItems.filter(
      (m) => !m.content.startsWith('人设：') && ['preference', 'constraint'].includes(m.category),
    ),
  },
  {
    id: 'memory',
    title: '记忆',
    description: '那些值得留下的事',
    items: memory.orderedItems.filter(
      (m) => !m.content.startsWith('人设：') && !['preference', 'constraint'].includes(m.category),
    ),
  },
])
const focusedId = computed(() => (typeof route.query.focus === 'string' ? route.query.focus : ''))
watch(focusedId, (id) => {
  if (id) {
    search.value = ''
    void memory.load('')
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
  await Promise.all([memory.load(search.value), settings.loadPreferences()])
  name.value = settings.profile.assistantName
})
function startCreate(column = 'memory') {
  delete draft.id
  draft.category = column === 'preference' ? 'preference' : 'fact'
  draft.persona = column === 'persona'
  draft.content = ''
  draft.confidence = 1
  editing.value = true
}
function startEdit(item: UserMemory) {
  draft.id = item.id
  draft.category = item.category
  draft.persona = item.content.startsWith('人设：')
  draft.content = item.content.replace(/^人设：/, '')
  draft.confidence = item.confidence
  editing.value = true
}
async function submit() {
  const content = draft.content.trim()
  if (!content) return
  const saved = await memory.save({
    id: draft.id,
    category: draft.category,
    content: draft.persona ? '人设：' + content : content,
    confidence: draft.confidence,
  })
  if (saved) editing.value = false
}
</script>
<template>
  <main class="page-shell memory-page">
    <header class="page-header">
      <div>
        <h1 class="page-title">它记得</h1>
        <p class="page-subtitle">留下习惯，也可以让它遗忘。</p>
      </div>
      <button class="primary-button" @click="startCreate()">添加记忆</button>
    </header>
    <form class="memory-search" @submit.prevent="memory.load(search)">
      <input v-model="search" type="search" placeholder="找一条记忆…" maxlength="200" /><button
        class="secondary-button"
        :disabled="memory.loading"
      >
        搜索
      </button>
    </form>
    <InkLoader v-if="memory.loading" />
    <p v-if="memory.error" class="error-banner" role="alert">{{ memory.error }}</p>
    <form v-if="editing" class="memory-editor glass-card" @submit.prevent="submit">
      <h2>{{ draft.id ? '编辑' : '写下一条' }}</h2>
      <label
        >类型<select v-model="draft.category">
          <option value="preference">偏好</option>
          <option value="constraint">约束</option>
          <option value="fact">事实</option>
          <option value="project">项目</option>
          <option value="other">其他</option>
        </select></label
      >
      <label>内容<textarea v-model="draft.content" rows="4" maxlength="4000" required /></label>
      <footer>
        <button class="secondary-button" type="button" @click="editing = false">取消</button
        ><button class="primary-button" :disabled="memory.saving || !draft.content.trim()" :aria-busy="memory.saving || undefined">
          {{ memory.saving ? '正在保存…' : '保存' }}
        </button>
      </footer>
    </form>
    <div class="memory-columns">
      <section v-for="column in columns" :key="column.id">
        <header>
          <h2>{{ column.title }}</h2>
          <button
            class="icon-button"
            :aria-label="'添加' + column.title"
            @click="startCreate(column.id)"
          >
            +
          </button>
        </header>
        <p class="column-description">{{ column.description }}</p>
        <div v-if="column.id === 'persona'" class="persona-name">
          <label>助手名字<input v-model="name" maxlength="32" /></label
          ><button
            class="secondary-button"
            :disabled="!name.trim() || settings.saving"
            :aria-busy="settings.saving || undefined"
            @click="settings.savePreferences(name)"
          >
            {{ settings.saving ? '正在保存…' : '保存称呼' }}</button
          ><label
            >头像字<input
              :value="ui.appearance.avatar"
              @input="
                ui.setAppearance({
                  avatar: Array.from(($event.target as HTMLInputElement).value)[0] || '助',
                })
              "
          /></label>
        </div>
        <MemoryItem
          v-for="item in column.items"
          :key="item.id"
          :item="item"
          :class="{ 'focused-memory': focusedId === item.id }"
          @edit="startEdit"
        />
        <p v-if="!column.items.length && !memory.loading" class="empty-copy">
          {{ column.id === 'persona' ? '写下希望它怎样与你相处。' : '这里还没有记忆。' }}
        </p>
      </section>
    </div>
    <p v-if="settings.error" class="error-banner">{{ settings.error }}</p>
  </main>
</template>
<style scoped lang="scss">
.memory-page {
  display: grid;
  gap: 28px;
}
.focused-memory {
  outline: 1px solid var(--accent);
  outline-offset: 4px;
}
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.memory-search {
  display: flex;
  gap: 8px;
}
.memory-search input {
  flex: 1;
  min-width: 0;
}
.memory-columns {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 32px;
}
.memory-columns > section {
  min-width: 0;
}
.memory-columns header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--rule);
  padding-bottom: 10px;
}
h2 {
  margin: 0;
  font-size: var(--text-md);
  font-weight: var(--weight-semibold);
}
.column-description {
  margin: 10px 0 20px;
  color: var(--ink-3);
  font-size: var(--text-xs);
}
.persona-name {
  display: grid;
  gap: 12px;
  margin: 20px 0;
}
label {
  display: grid;
  gap: 8px;
  font-size: var(--text-sm);
  color: var(--ink-2);
}
input {
  width: 100%;
}
.persona-name .secondary-button {
  justify-self: start;
}
.memory-editor {
  display: grid;
  gap: 16px;
  padding: 24px;
}
textarea {
  width: 100%;
}
footer {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
@media (max-width: 950px) {
  .memory-columns {
    grid-template-columns: 1fr;
  }
}
</style>
