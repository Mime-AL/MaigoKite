<script setup lang="ts">
import { ref } from 'vue'
import IconSymbol from '@/components/common/IconSymbol.vue'
const props = defineProps<{
  items: { id: string; content: string }[]
  paused: boolean
  guideReason: string
  canContinue: boolean
  guide: (id: string) => Promise<void>
}>()
const emit = defineEmits<{
  (event: 'edit', id: string, content: string): void
  (event: 'remove', index: number): void
  (event: 'continue'): void
}>()
const editing = ref(''),
  draft = ref(''),
  busy = ref(''),
  error = ref('')
function edit(item: { id: string; content: string }) {
  editing.value = item.id
  draft.value = item.content
}
function save() {
  if (draft.value.trim()) {
    emit('edit', editing.value, draft.value)
    editing.value = ''
  }
}
async function guideNow(id: string) {
  busy.value = id
  error.value = ''
  try {
    await props.guide(id)
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : String(reason)
  } finally {
    busy.value = ''
  }
}
</script>
<template>
  <section
    v-if="items.length"
    class="queued-messages"
    :aria-label="$t('消息队列')"
  >
    <header>
      {{ $t('队列（{0}）', [items.length])
      }}<span v-if="paused">{{ $t('已暂停自动发送') }}</span>
    </header>
    <article
      v-for="(item, index) in items"
      :key="item.id"
    >
      <template v-if="editing === item.id">
        <textarea
          v-model="draft"
          :aria-label="$t('编辑待发消息')"
          rows="2"
          @keydown.ctrl.enter.prevent="save"
          @keydown.esc.stop="editing = ''"
        />
        <button
          class="text-button"
          :disabled="!draft.trim()"
          @click="save"
        >
          {{ $t('保存') }}
        </button>
        <button
          class="text-button"
          @click="editing = ''"
        >
          {{ $t('取消') }}
        </button>
      </template>
      <template v-else>
        <p>{{ item.content }}</p>
        <div class="queue-actions">
          <button
            class="text-button"
            :disabled="Boolean(guideReason) || Boolean(busy)"
            :title="guideReason || undefined"
            @click="guideNow(item.id)"
          >
            <IconSymbol
              name="arrow-up"
              :size="14"
            />{{ $t('立即发送') }}
          </button>
          <button
            class="icon-button"
            :disabled="Boolean(busy)"
            :title="$t('编辑')"
            @click="edit(item)"
          >
            <IconSymbol
              name="edit"
              :size="14"
            /><span class="sr-only">{{ $t('编辑') }}</span>
          </button>
          <button
            class="icon-button"
            :disabled="Boolean(busy)"
            :title="$t('移除')"
            @click="emit('remove', index)"
          >
            <IconSymbol
              name="close"
              :size="14"
            /><span class="sr-only">{{ $t('移除') }}</span>
          </button>
        </div>
      </template>
    </article>
    <p
      v-if="error"
      role="alert"
    >
      {{ error }}
    </p>
    <button
      v-if="paused"
      class="text-button"
      :disabled="!canContinue"
      @click="emit('continue')"
    >
      {{ $t('确认继续发送') }}
    </button>
  </section>
</template>
<style scoped lang="scss">
@use '@/styles/mixins' as mixins;
@use '@/styles/breakpoints' as breakpoints;
.text-button {
  @include mixins.text-action;
}
.queued-messages {
  flex: none;
  width: min(var(--content-width), 100%);
  max-height: calc(var(--space-10) * 3);
  overflow: auto;
  padding: var(--space-3) var(--space-7);
}
header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  font-size: var(--text-xs);
  color: var(--ink-2);
}
article {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--space-3);
  margin-top: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border: var(--hairline) solid var(--rule);
  border-radius: var(--radius-sm);
  background: var(--paper-2);
}
article div {
  display: flex;
  gap: var(--space-2);
  align-items: center;
}
p {
  display: block;
  margin: var(--space-3) 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font-size: var(--text-sm);
}
textarea {
  grid-column: 1 / -1;
  width: 100%;
  padding: var(--space-3);
  background: var(--paper-2);
  color: var(--ink);
  font: inherit;
  border: var(--hairline) solid var(--rule);
  border-radius: var(--radius-sm);
  resize: vertical;
}
.text-button { display: inline-flex; align-items: center; gap: var(--space-2); }
.queue-actions .icon-button { min-height: var(--titlebar-button-size); padding: var(--space-2); border: 0; background: var(--transparent); }
@include breakpoints.sidebar-overlay {
  article { grid-template-columns: minmax(0, 1fr); }
  .queue-actions { justify-content: flex-end; }
}
</style>
