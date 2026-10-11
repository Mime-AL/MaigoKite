<script setup lang="ts">
import { nextTick, onMounted, reactive, ref } from 'vue'
import type { MemoryCategory } from '@/api/client'
import IconSymbol from '@/components/common/IconSymbol.vue'
export interface MemoryDraft {
  id?: string
  category: MemoryCategory
  content: string
  confidence: number
  persona: boolean
}
const props = defineProps<{ draft: MemoryDraft; busy: boolean }>()
const emit = defineEmits<{ (event: 'save', draft: MemoryDraft): void; (event: 'cancel'): void }>()
const local = reactive({ ...props.draft }),
  textarea = ref<HTMLTextAreaElement | null>(null)
onMounted(() => {
  void nextTick(() => textarea.value?.focus())
})
</script>
<template>
  <form
    class="memory-editor"
    @submit.prevent="emit('save', { ...local })"
    @keydown.esc.stop.prevent="!busy && emit('cancel')"
  >
    <label>{{ $t('内容')
    }}<textarea
      ref="textarea"
      v-model="local.content"
      rows="4"
      maxlength="4000"
      required
      :disabled="busy"
    />
    </label>
    <label
      v-if="!local.persona"
      class="memory-category"
    >{{ $t('类型')
    }}<select
      v-model="local.category"
      :disabled="busy"
    >
      <option value="preference">{{ $t('偏好') }}</option>
      <option value="constraint">{{ $t('约束') }}</option>
      <option value="fact">{{ $t('事实') }}</option>
      <option value="project">{{ $t('项目') }}</option>
      <option value="other">{{ $t('其他') }}</option>
    </select></label>
    <footer>
      <button
        class="secondary-button"
        type="button"
        :disabled="busy"
        @click="emit('cancel')"
      >
        {{ $t('取消') }}
      </button>
      <button
        class="primary-button"
        :disabled="busy || !local.content.trim()"
        :aria-busy="busy || undefined"
      >
        <IconSymbol
          name="check"
          :size="14"
        />{{ busy ? $t('正在保存…') : $t('记下') }}
      </button>
    </footer>
  </form>
</template>
<style scoped lang="scss">
.memory-editor {
  display: grid;
  gap: var(--space-5);
  padding: var(--space-5);
  margin-block: var(--space-4);
  background: var(--paper-2);
  border-inline-start: var(--pending-line) solid var(--accent);
  box-shadow: var(--elevation-inset);
}
label {
  display: grid;
  gap: var(--space-3);
  font-size: var(--type-small);
  color: var(--ink-2);
}
textarea {
  width: 100%;
  min-height: var(--memory-editor-height);
  resize: vertical;
}
.memory-category {
  grid-template-columns: auto minmax(0, 1fr);
  align-items: center;
}
footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  flex-wrap: wrap;
}
footer button {
  display: inline-flex;
  align-items: center;
  gap: var(--space-3);
}
</style>
