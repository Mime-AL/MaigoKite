<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'
import { api, type WorkspaceChange } from '@/api/client'
import { useWorkspaceStore } from '@/stores/workspace'
import IconSymbol from '@/components/common/IconSymbol.vue'
import CodeBlock from '@/components/common/CodeBlock.vue'
import InkLoader from '@/components/common/InkLoader.vue'
import ResizeHandle from '@/components/common/ResizeHandle.vue'
import { layoutPixels } from '@/utils/layout-media'
import { usePreviewSplit } from './usePreviewSplit'

const changes = ref<WorkspaceChange[]>([])
const workspace = useWorkspaceStore()
const selectedPath = ref('')
const loading = ref(false)
const error = ref('')
const gitAvailable = ref(true)
const changesTruncated = ref(false)
const diffLoading = ref(false)
const diffError = ref('')
let listRequest = 0,
  diffRequest = 0
const selected = computed(() => changes.value.find((item) => item.path === selectedPath.value))
const {
  root: splitRoot, dragging: splitDragging, size: listHeight, minimum: listMinimum,
  maximum: listMaximum, defaultSize: defaultListHeight, resize: resizeList, remember: rememberSplit,
} = usePreviewSplit('file_explorer_changes_ratio', () =>
  changes.value.length * layoutPixels('--size-30') + 2 * layoutPixels('--size-6'),
)

async function load() {
  const request = ++listRequest
  diffRequest++
  diffLoading.value = false
  diffError.value = ''
  loading.value = true
  error.value = ''
  try {
    const result = await api.listWorkspaceChanges(workspace.selectedId)
    if (request !== listRequest) return
    changes.value = result.changes
    gitAvailable.value = result.git
    changesTruncated.value = result.truncated
    if (!changes.value.some((item) => item.path === selectedPath.value)) {
      selectedPath.value = changes.value[0]?.path || ''
    }
    if (selectedPath.value) await selectChange(selectedPath.value)
  } catch (reason) {
    if (request === listRequest)
      error.value = reason instanceof Error ? reason.message : String(reason)
  } finally {
    if (request === listRequest) loading.value = false
  }
}

async function selectChange(path: string) {
  const request = ++diffRequest
  selectedPath.value = path
  diffLoading.value = true
  diffError.value = ''
  try {
    const detail = await api.getWorkspaceDiff(path, workspace.selectedId)
    if (request !== diffRequest) return
    const index = changes.value.findIndex((item) => item.path === path)
    if (index >= 0) changes.value[index] = detail
  } catch (reason) {
    if (request === diffRequest)
      diffError.value = reason instanceof Error ? reason.message : String(reason)
  } finally {
    if (request === diffRequest) diffLoading.value = false
  }
}

watch(
  () => workspace.selectedId,
  () => {
    changes.value = []
    selectedPath.value = ''
    gitAvailable.value = true
    changesTruncated.value = false
    void load()
  },
  { immediate: true, flush: 'sync' },
)
onUnmounted(() => {
  listRequest++
  diffRequest++
})
defineExpose({ load })
</script>

<template>
  <section class="workspace-diff">
    <header>
      <span>{{ changes.length }}<template v-if="changesTruncated">+</template>{{ $t('个变更') }}</span><button
        class="icon-button"
        type="button"
        :disabled="loading"
        :aria-busy="loading || undefined"
        :aria-label="$t('刷新变更')"
        :title="$t('刷新变更')"
        @click="load"
      >
        <IconSymbol
          name="refresh"
          :size="14"
        />
      </button>
    </header>
    <p
      v-if="loading && !changes.length"
      class="state"
    >
      <InkLoader />{{ $t('正在读取 Git 变更…') }}
    </p>
    <p
      v-else-if="error"
      class="state error"
      role="alert"
    >
      {{ error }}
      <button
        class="secondary-button"
        @click="load"
      >
        {{ $t('重试') }}
      </button>
    </p>
    <p
      v-else-if="!gitAvailable"
      class="state"
    >
      {{ $t('当前工作区不是 Git 仓库。') }}
    </p>
    <p
      v-else-if="!changes.length"
      class="state"
    >
      {{ $t('工作区没有未提交变更。') }}
    </p>
    <div
      v-else
      ref="splitRoot"
      class="changes-split"
      :class="{ dragging: splitDragging }"
    >
      <div
        class="change-list"
        :class="{ 'with-preview': selected }"
        :style="selected ? { flexBasis: `${listHeight}px` } : undefined"
      >
        <button
          v-for="item in changes"
          :key="item.path"
          type="button"
          :class="{ active: item.path === selectedPath }"
          @click="selectChange(item.path)"
        >
          <i :class="item.status">{{ item.status.slice(0, 1).toUpperCase() }}</i><span>{{ item.path }}</span><b v-if="item.additions">+{{ item.additions }}</b><em v-if="item.deletions">−{{ item.deletions }}</em>
        </button>
      </div>
      <ResizeHandle
        v-if="selected"
        orientation="horizontal"
        :model-value="listHeight"
        :minimum="listMinimum"
        :maximum="listMaximum"
        :default-value="defaultListHeight"
        :label="$t('调整变更列表与预览的高度')"
        :hint="$t('拖动调整变更列表和预览；双击还原')"
        @update:model-value="resizeList"
        @change="rememberSplit"
        @dragging="splitDragging = $event"
      />
      <article
        v-if="selected"
        class="diff-preview"
      >
        <header>
          <strong>{{ selected.path }}</strong><small>{{ selected.status
          }}<template v-if="selected.diff_truncated">{{ $t('· 预览已截断') }}</template></small>
        </header>
        <p v-if="diffLoading">
          <InkLoader />{{ $t('正在生成差异…') }}
        </p>
        <p
          v-else-if="diffError"
          role="alert"
        >
          {{ diffError }}
          <button
            class="secondary-button"
            @click="selectChange(selectedPath)"
          >
            {{ $t('重试') }}
          </button>
        </p>
        <CodeBlock
          v-else-if="selected.diff"
          :key="selected.path"
          :content="selected.diff"
          kind="diff"
          :title="selected.path"
          layout="document"
        />
        <p v-else>
          {{ $t('该变更没有可显示的文本差异。') }}
        </p>
      </article>
    </div>
  </section>
</template>

<style scoped lang="scss">
@use '@/styles/workspace-diff';
</style>
