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
  await router.push('/chat')
  workspace.select(id)
  open.value = false
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
  } finally {
    choosing.value = false
  }
}
function openSelector() {
  error.value = ''
  open.value = true
}
function close() {
  if (!busy.value && !choosing.value) open.value = false
}
</script>
<template>
  <div class="workspace-selector">
    <span v-if="!collapsed" class="workspace-label"
      >{{ $t('工作区') }}<small>{{ workspace.folders.length }}</small></span
    >
    <button
      class="icon-button"
      :aria-label="collapsed ? $t('选择工作区') : $t('添加文件夹工作区')"
      :title="collapsed ? workspace.current?.name || $t('选择工作区') : $t('添加文件夹工作区')"
      :disabled="choosing || busy"
      :aria-busy="choosing || busy || undefined"
      @click="collapsed ? openSelector() : choose()"
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
        :aria-label="$t('选择工作区')"
        @cancel.prevent="close"
        @click.self="close"
      >
        <section>
          <header>
            <strong>{{ $t('工作区') }}</strong
            ><button
              class="icon-button"
              :disabled="busy || choosing"
              :aria-label="$t('关闭')"
              @click="close"
            >
              ×
            </button>
          </header>
          <label
            >{{ $t('切换已有工作区')
            }}<select
              :value="workspace.selectedId"
              :disabled="busy || choosing || workspace.loading"
              @change="select(($event.target as HTMLSelectElement).value)"
            >
              <option v-for="folder in workspace.folders" :key="folder.id" :value="folder.id">
                {{ folder.id ? folder.name : $t('默认工作区') }}
              </option>
            </select></label
          >
          <form @submit.prevent="add">
            <button
              v-if="desktopEffects"
              type="button"
              class="secondary-button folder-picker"
              :disabled="choosing || busy"
              :aria-busy="choosing || undefined"
              @click="choose"
            >
              <IconSymbol name="folder" :size="16" />{{
                choosing ? $t('正在选择…') : $t('选择文件夹')
              }}
            </button>
            <label
              >{{ $t('文件夹路径')
              }}<input
                v-model="root"
                maxlength="4096"
                :placeholder="$t('服务所在设备上的绝对路径')"
                required
                :disabled="busy || choosing"
            /></label>
            <label
              >{{ $t('工作区名称')
              }}<input
                v-model="name"
                maxlength="120"
                :placeholder="$t('默认使用文件夹名称')"
                :disabled="busy || choosing"
            /></label>
            <p class="empty-copy">
              {{ $t('新对话和文件操作会使用所选文件夹；已有对话不会自动移动。') }}
            </p>
            <p v-if="error" role="alert" class="error-banner">{{ error }}</p>
            <footer>
              <InkButton :disabled="busy || choosing" @click="close">{{ $t('取消') }}</InkButton>
              <button
                class="primary-button"
                :disabled="busy || choosing || !root.trim()"
                :aria-busy="busy || undefined"
              >
                {{ busy ? $t('正在添加…') : $t('添加工作区') }}
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
  flex: 1;
  min-width: 0;
}
.workspace-label {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  min-width: 0;
  padding-left: 8px;
  font-size: var(--text-xs);
}
.workspace-label small {
  color: var(--ink-2);
  font-size: var(--text-xs);
}
.workspace-selector > .icon-button {
  width: 32px;
  min-height: 36px;
}
.folder-picker {
  display: flex;
  align-items: center;
  gap: 8px;
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
