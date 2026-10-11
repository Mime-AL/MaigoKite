<script setup lang="ts">
import { ref } from 'vue'
import type { SupplementInput } from '@/api/events'
const props = defineProps<{
  input: SupplementInput
  canResend: boolean
  resend: () => Promise<void>
  inline?: boolean
}>()
const busy = ref(false),
  error = ref('')
async function send() {
  if (busy.value) return
  busy.value = true
  error.value = ''
  try {
    await props.resend()
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : String(reason)
  } finally {
    busy.value = false
  }
}
</script>
<template>
  <article
    class="supplement-message"
    :class="{ inline }"
    :data-input-id="input.id"
  >
    <span
      v-if="!inline"
      class="supplement-label"
    >{{ $t('补充指令') }}</span>
    <p>{{ input.content }}</p>
    <div
      class="supplement-status"
      role="status"
      :class="{ unused: input.status === 'not_consumed' }"
    >
      <span>{{
        $t(
          input.status === 'consumed'
            ? '已纳入'
            : input.status === 'not_consumed'
              ? '本轮未采用'
              : '等待纳入',
        )
      }}</span>
      <span v-if="input.sentAsTaskId">{{ $t('已作为新回合发送') }}</span>
      <button
        v-else-if="input.status === 'not_consumed'"
        class="text-button"
        :disabled="busy || !canResend"
        @click="send"
      >
        {{ $t(busy ? '正在发送…' : '作为新回合发送') }}
      </button>
    </div>
    <p
      v-if="input.status === 'not_consumed' && !canResend && !input.sentAsTaskId"
      class="supplement-label"
    >
      {{ $t('当前任务结束后可作为新回合发送。') }}
    </p>
    <p
      v-if="error"
      role="alert"
    >
      {{ error }}
    </p>
  </article>
</template>
<style scoped lang="scss">
@use '@/styles/mixins' as mixins;
.text-button {
  @include mixins.text-action;
}
.supplement-message {
  margin: var(--space-4) 0 var(--space-6) var(--rail-width);
  padding: var(--space-4) var(--space-5);
  border-inline-start: var(--hairline) solid var(--accent);
  background: var(--paper-2);
}
.supplement-message.inline {
  margin: var(--space-2) 0 var(--space-5);
}
p {
  margin: var(--space-3) 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font-size: var(--type-body);
  line-height: var(--leading-message);
}
.supplement-label,
.supplement-status {
  font-size: var(--text-xs);
  color: var(--ink-2);
}
.supplement-status {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-4);
  align-items: center;
}
.unused {
  border-inline-start: var(--hairline) solid var(--wait);
  padding-inline-start: var(--space-3);
}
</style>
