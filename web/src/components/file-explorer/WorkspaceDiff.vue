<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api, type WorkspaceChange } from '@/api/client'
import IconSymbol from '@/components/common/IconSymbol.vue'

const changes = ref<WorkspaceChange[]>([])
const selectedPath = ref('')
const loading = ref(false)
const error = ref('')
const gitAvailable = ref(true)
const changesTruncated = ref(false)
const diffLoading = ref(false)
const selected = computed(() => changes.value.find(item => item.path === selectedPath.value))

function lineClass(line: string) {
  if (line.startsWith('+++') || line.startsWith('---')) return 'header'
  if (line.startsWith('+')) return 'addition'
  if (line.startsWith('-')) return 'deletion'
  if (line.startsWith('@@')) return 'hunk'
  return ''
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const result = await api.listWorkspaceChanges()
    changes.value = result.changes
    gitAvailable.value = result.git
    changesTruncated.value = result.truncated
    if (!changes.value.some(item => item.path === selectedPath.value)) {
      selectedPath.value = changes.value[0]?.path || ''
    }
    if (selectedPath.value) await selectChange(selectedPath.value)
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : String(reason)
  } finally { loading.value = false }
}

async function selectChange(path: string) {
  selectedPath.value = path
  diffLoading.value = true
  error.value = ''
  try {
    const detail = await api.getWorkspaceDiff(path)
    const index = changes.value.findIndex(item => item.path === path)
    if (index >= 0) changes.value[index] = detail
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : String(reason)
  } finally { diffLoading.value = false }
}

onMounted(load)
defineExpose({ load })
</script>

<template>
  <section class="workspace-diff">
    <header><span>{{ changes.length }}<template v-if="changesTruncated">+</template> 个变更</span><button class="icon-button" type="button" title="刷新变更" @click="load"><IconSymbol name="refresh" :size="14" /></button></header>
    <p v-if="loading && !changes.length" class="state">正在读取 Git 变更…</p>
    <p v-else-if="error" class="state error">{{ error }}</p>
    <p v-else-if="!gitAvailable" class="state">当前工作区不是 Git 仓库。</p>
    <p v-else-if="!changes.length" class="state">工作区没有未提交变更。</p>
    <template v-else>
      <div class="change-list">
        <button v-for="item in changes" :key="item.path" type="button" :class="{ active: item.path === selectedPath }" @click="selectChange(item.path)">
          <i :class="item.status">{{ item.status.slice(0, 1).toUpperCase() }}</i><span>{{ item.path }}</span><b v-if="item.additions">+{{ item.additions }}</b><em v-if="item.deletions">−{{ item.deletions }}</em>
        </button>
      </div>
      <article v-if="selected" class="diff-preview">
        <header><strong>{{ selected.path }}</strong><small>{{ selected.status }}<template v-if="selected.diff_truncated"> · 预览已截断</template></small></header>
        <p v-if="diffLoading">正在生成差异…</p>
        <pre v-else-if="selected.diff"><code v-for="(line, index) in selected.diff.split('\n')" :key="index" :class="lineClass(line)">{{ line || ' ' }}
</code></pre>
        <p v-else>该变更没有可显示的文本差异。</p>
      </article>
    </template>
  </section>
</template>

<style scoped lang="scss">
.workspace-diff { min-height: 0; display: flex; flex: 1; flex-direction: column; }.workspace-diff > header { display: flex; height: 39px; flex: none; align-items: center; justify-content: space-between; padding: 0 10px 0 15px; border-block: 1px solid var(--border-color); color: var(--text-secondary); font-size: 10px; }.state { padding: 28px 16px; color: var(--text-tertiary); font-size: 10px; text-align: center; }.state.error { color: var(--danger); }.change-list { max-height: 42%; flex: none; padding: 7px; overflow: auto; border-bottom: 1px solid var(--border-color); }.change-list button { display: flex; width: 100%; height: 29px; align-items: center; gap: 5px; padding: 0 6px; border: 0; border-radius: 7px; color: var(--text-secondary); background: transparent; cursor: pointer; text-align: left; }.change-list button.active,.change-list button:hover { background: var(--surface-strong); }.change-list i { width: 16px; color: var(--warning); font-size: 8px; font-style: normal; font-weight: 800; }.change-list i.added,.change-list i.untracked { color: var(--success); }.change-list i.deleted { color: var(--danger); }.change-list span { min-width: 0; flex: 1; overflow: hidden; font-family: var(--font-mono); font-size: 8.5px; text-overflow: ellipsis; white-space: nowrap; }.change-list b,.change-list em { font-family: var(--font-mono); font-size: 8px; font-style: normal; }.change-list b { color: var(--success); }.change-list em { color: var(--danger); }.diff-preview { min-height: 0; display: flex; flex: 1; flex-direction: column; overflow: hidden; }.diff-preview > header { display: flex; flex: none; align-items: center; justify-content: space-between; gap: 8px; padding: 9px 11px; }.diff-preview strong { min-width: 0; overflow: hidden; font-family: var(--font-mono); font-size: 9px; text-overflow: ellipsis; white-space: nowrap; }.diff-preview small { color: var(--text-tertiary); font-size: 8px; }.diff-preview pre { min-height: 0; flex: 1; margin: 0; padding: 8px 0 18px; overflow: auto; background: var(--surface-solid); font-family: var(--font-mono); font-size: 8px; line-height: 1.55; }.diff-preview code { display: block; min-width: max-content; padding: 0 9px; white-space: pre; }.diff-preview code.addition { color: #18794e; background: rgba(41,170,100,.12); }.diff-preview code.deletion { color: #b42318; background: rgba(230,70,70,.1); }.diff-preview code.hunk { color: var(--primary-color); background: var(--primary-soft); }.diff-preview code.header { color: var(--text-tertiary); font-weight: 700; }.diff-preview > p { padding: 20px; color: var(--text-tertiary); font-size: 9px; }
</style>
