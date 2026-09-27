<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import IconSymbol from '@/components/common/IconSymbol.vue'
import type { MemoryCategory, UserMemory } from '@/api/client'
import { useMemoryStore } from '@/stores/memory'

const memory = useMemoryStore()
const search = ref('')
const editorOpen = ref(false)
const draft = reactive<{ id?: string; category: MemoryCategory; content: string; confidence: number }>({
  category: 'preference', content: '', confidence: 1,
})
const categories: Array<{ value: MemoryCategory; label: string }> = [
  { value: 'preference', label: '偏好' },
  { value: 'fact', label: '事实' },
  { value: 'constraint', label: '约束' },
  { value: 'project', label: '项目' },
  { value: 'other', label: '其他' },
]

onMounted(() => { void memory.load() })

function resetDraft() {
  delete draft.id
  draft.category = 'preference'
  draft.content = ''
  draft.confidence = 1
}

function startCreate() {
  resetDraft()
  editorOpen.value = true
}

function startEdit(item: UserMemory) {
  draft.id = item.id
  draft.category = item.category
  draft.content = item.content
  draft.confidence = item.confidence
  editorOpen.value = true
}

async function submit() {
  if (!draft.content.trim()) return
  const saved = await memory.save({ ...draft, content: draft.content.trim() })
  if (saved) {
    editorOpen.value = false
    resetDraft()
  }
}

async function remove(item: UserMemory) {
  if (!window.confirm(`确认遗忘“${item.content.slice(0, 30)}”吗？`)) return
  await memory.remove(item.id)
}

function categoryLabel(category: MemoryCategory) {
  return categories.find(item => item.value === category)?.label || category
}
</script>

<template>
  <main class="page-shell memory-page">
    <header class="page-header">
      <div>
        <h1 class="page-title">记忆</h1>
        <p class="page-subtitle">管理希望助手在以后对话中记住的信息。</p>
      </div>
      <button class="primary-button" type="button" @click="startCreate">
        <IconSymbol name="plus" :size="16" />添加记忆
      </button>
    </header>

    <form class="search-bar glass-card" @submit.prevent="memory.load(search)">
      <IconSymbol name="search" :size="17" />
      <input v-model="search" type="search" maxlength="200" placeholder="搜索记忆内容">
      <button class="secondary-button" type="submit" :disabled="memory.loading">搜索</button>
    </form>

    <form v-if="editorOpen" class="memory-editor glass-card" @submit.prevent="submit">
      <header><h2>{{ draft.id ? '编辑记忆' : '添加记忆' }}</h2><span>内容只属于当前用户与工作区</span></header>
      <div class="editor-grid">
        <label><span>类型</span><select v-model="draft.category"><option v-for="item in categories" :key="item.value" :value="item.value">{{ item.label }}</option></select></label>
        <label class="content-field"><span>内容</span><textarea v-model="draft.content" maxlength="4000" rows="4" placeholder="例如：回答时优先使用中文" /></label>
      </div>
      <footer><button class="secondary-button" type="button" @click="editorOpen = false">取消</button><button class="primary-button" type="submit" :disabled="memory.saving || !draft.content.trim()">{{ memory.saving ? '保存中…' : '保存' }}</button></footer>
    </form>

    <p v-if="memory.error" class="error-banner" role="alert"><IconSymbol name="alert" :size="15" />{{ memory.error }}</p>
    <section class="memory-list glass-card">
      <div v-if="memory.loading" class="empty-state">正在读取记忆…</div>
      <div v-else-if="!memory.items.length" class="empty-state rich-empty"><span><IconSymbol name="brain" :size="25" /></span><strong>还没有记忆</strong><p>添加希望助手以后记住的信息。</p></div>
      <template v-else>
        <article v-for="item in memory.items" :key="item.id" class="memory-row">
          <span class="memory-kind">{{ categoryLabel(item.category) }}</span>
          <div><p>{{ item.content }}</p><small>{{ item.source_type === 'user' ? '由你添加' : '已保存' }}</small></div>
          <div class="row-actions"><button type="button" @click="startEdit(item)">编辑</button><button class="danger" type="button" @click="remove(item)">遗忘</button></div>
        </article>
      </template>
    </section>
  </main>
</template>

<style scoped lang="scss">
.memory-page { display: flex; flex-direction: column; gap: 18px; }
.page-header { display: flex; align-items: flex-end; justify-content: space-between; gap: 24px; }
.page-header .primary-button { flex: none; gap: 7px; }
.error-banner { display: flex; align-items: flex-start; gap: 8px; margin: 0; padding: 11px 13px; border-radius: 12px; color: var(--danger); background: var(--danger-soft); font-size: 10.5px; line-height: 1.45; }
.search-bar { display: flex; align-items: center; gap: 10px; padding: 9px 11px 9px 15px; }
.search-bar input { min-width: 0; flex: 1; border: 0; outline: 0; color: var(--text-primary); background: transparent; }
.search-bar .secondary-button { min-height: 34px; }
.memory-editor { overflow: hidden; }
.memory-editor > header { display: flex; align-items: baseline; justify-content: space-between; padding: 17px 20px; border-bottom: 1px solid var(--border-color); }
.memory-editor h2 { margin: 0; font-size: 15px; }
.memory-editor header span { color: var(--text-tertiary); font-size: 9.5px; }
.editor-grid { display: grid; grid-template-columns: 180px 1fr; gap: 14px; padding: 18px 20px; }
.editor-grid label { display: flex; flex-direction: column; gap: 7px; color: var(--text-secondary); font-size: 10px; }
.content-field { grid-column: 2; }
.editor-grid select, .editor-grid textarea { width: 100%; border: 1px solid var(--border-strong); border-radius: 10px; outline: none; color: var(--text-primary); background: var(--surface-muted); }
.editor-grid select { height: 38px; padding: 0 10px; }
.editor-grid textarea { resize: vertical; padding: 10px; line-height: 1.5; }
.memory-editor footer { display: flex; justify-content: flex-end; gap: 8px; padding: 13px 20px; background: var(--surface-muted); }
.memory-list { overflow: hidden; }
.memory-row { display: grid; grid-template-columns: 62px minmax(0, 1fr) auto; align-items: start; gap: 13px; padding: 16px 18px; border-bottom: 1px solid var(--border-color); }
.memory-row:last-child { border-bottom: 0; }
.memory-kind { display: inline-flex; justify-content: center; padding: 5px 7px; border-radius: 8px; color: var(--primary-color); background: var(--primary-soft); font-size: 9px; font-weight: 700; }
.memory-row p { margin: 0; font-size: 12px; line-height: 1.55; }
.memory-row small { display: block; margin-top: 6px; color: var(--text-tertiary); font-size: 9px; }
.row-actions { display: flex; gap: 4px; }
.row-actions button { padding: 5px 8px; border: 0; border-radius: 7px; color: var(--text-secondary); background: transparent; cursor: pointer; font-size: 9.5px; }
.row-actions button:hover { background: var(--surface-strong); }
.row-actions .danger { color: var(--danger); }
.empty-state { display: grid; min-height: 190px; place-items: center; color: var(--text-tertiary); }
.rich-empty { align-content: center; justify-items: center; gap: 6px; text-align: center; }
.rich-empty span { display: grid; width: 50px; height: 50px; place-items: center; border-radius: 15px; color: var(--primary-color); background: var(--primary-soft); }
.rich-empty strong { color: var(--text-primary); }
.rich-empty p { margin: 0; font-size: 10px; }
@media (max-width: 800px) { .page-header { align-items: flex-start; flex-direction: column; } .editor-grid { grid-template-columns: 1fr; } .content-field { grid-column: auto; } .memory-row { grid-template-columns: 56px 1fr; } .row-actions { grid-column: 2; } }
</style>
