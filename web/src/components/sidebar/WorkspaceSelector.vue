<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useWorkspaceStore } from '@/stores/workspace'
import { useDialog } from '@/composables/useDialog'
import { desktopEffects } from '@/composables/useElectron'
import IconSymbol from '@/components/common/IconSymbol.vue'
import InkButton from '@/components/common/InkButton.vue'
defineProps<{ collapsed: boolean }>()
const workspace = useWorkspaceStore(),
  router = useRouter()
const open = ref(false),
  dialog = ref<HTMLDialogElement | null>(null)
const root = ref(''),
  name = ref(''),
  error = ref(''),
  busy = ref(false),
  choosing = ref(false)
useDialog(dialog, () => open.value)
onMounted(() => {
  void workspace.load()
})
async function select(id: string) {
  workspace.select(id)
  open.value = false
  await router.push('/chat')
}
async function add() {
  if (busy.value || !root.value.trim()) return
  busy.value = true
  error.value = ''
  try {
    const folder = await workspace.add(root.value.trim(), name.value.trim())
    await select(folder.id)
    root.value = name.value = ''
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : String(reason)
  } finally {
    busy.value = false
  }
}
async function choose() {
  if (choosing.value || busy.value) return
  open.value = true
  error.value = ''
  if (!desktopEffects) return
  choosing.value = true
  try {
    const selected = await desktopEffects.chooseWorkspaceFolder()
    if (selected) {
      root.value = selected
      await add()
    }
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : String(reason)
  } finally { choosing.value = false }
}
</script>
<template>
  <div class="workspace-selector">
    <select
      v-if="!collapsed"
      :value="workspace.selectedId"
      :disabled="workspace.loading"
      aria-label="当前工作区"
      :title="workspace.current?.root_path"
      @change="select(($event.target as HTMLSelectElement).value)"
    >
      <option v-if="!workspace.folders.length" value="">
        {{ workspace.loading ? '读取工作区…' : '默认工作区' }}
      </option>
      <option v-for="folder in workspace.folders" :key="folder.id" :value="folder.id">
        {{ folder.name }}
      </option>
    </select>
    <button
      class="icon-button"
      :aria-label="collapsed ? '选择工作区' : '添加文件夹工作区'"
      :disabled="choosing || busy"
      :aria-busy="choosing || busy || undefined"
      @click="choose"
    >
      <IconSymbol :name="collapsed ? 'folder' : 'plus'" :size="16" />
    </button>
    <p v-if="workspace.error && !collapsed" class="empty-copy" role="alert">
      {{ workspace.error }}
    </p>
    <Teleport to="body">
      <dialog
        ref="dialog"
        class="workspace-dialog"
        aria-label="选择工作区"
        @cancel.prevent="open = false"
        @click.self="open = false"
      >
        <section>
          <header>
            <strong>工作区</strong
            ><button class="icon-button" aria-label="关闭" @click="open = false">×</button>
          </header>
          <label
            >切换已有工作区<select
              :value="workspace.selectedId"
              @change="select(($event.target as HTMLSelectElement).value)"
            >
              <option v-for="folder in workspace.folders" :key="folder.id" :value="folder.id">
                {{ folder.name }}
              </option>
            </select></label
          >
          <form @submit.prevent="add">
            <label
              >文件夹路径<input
                v-model="root"
                maxlength="4096"
                placeholder="服务所在设备上的绝对路径"
                required
                :disabled="busy"
            /></label>
            <label
              >工作区名称<input
                v-model="name"
                maxlength="120"
                placeholder="默认使用文件夹名称"
                :disabled="busy"
            /></label>
            <p class="empty-copy">新对话和文件操作会使用所选文件夹；已有对话不会自动移动。</p>
            <p v-if="error" role="alert" class="error-banner">{{ error }}</p>
            <footer>
              <InkButton :disabled="busy" @click="open = false">取消</InkButton>
              <button
                class="primary-button"
                :disabled="busy || !root.trim()"
                :aria-busy="busy || undefined"
              >
                {{ busy ? '正在添加…' : '添加工作区' }}
              </button>
            </footer>
          </form>
        </section>
      </dialog>
    </Teleport>
  </div>
</template>
<style scoped lang="scss">
.workspace-selector {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
  margin-bottom: 12px;
}
.workspace-selector > select {
  flex: 1;
  min-width: 0;
  width: 0;
  font-size: var(--text-sm);
  padding: 6px;
  background: var(--paper);
}
.workspace-selector > p {
  width: 100%;
  overflow-wrap: anywhere;
}
.workspace-dialog {
  width: min(420px, calc(100vw - 32px));
  padding: 20px;
  border: 1px solid var(--rule);
  border-radius: var(--radius-md);
  color: var(--ink);
  background: var(--paper);
  box-shadow: var(--shadow-float);
}
.workspace-dialog::backdrop {
  background: var(--backdrop);
}
header,
footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}
header {
  margin-bottom: 18px;
}
label {
  display: grid;
  gap: 8px;
  margin: 14px 0;
  font-size: var(--text-sm);
}
input,
select {
  width: 100%;
}
footer {
  justify-content: flex-end;
  margin-top: 20px;
}
</style>
