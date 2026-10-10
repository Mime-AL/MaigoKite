<script setup lang="ts">
import { t } from '@/i18n'
import { computed, ref } from 'vue'
import type { AwaitItem } from '@/api/events'
import type { Approval } from '@/api/client'
import { useInboxStore } from '@/stores/inbox'
import InkButton from '@/components/common/InkButton.vue'
const props = defineProps<{ item?: AwaitItem; approval?: Approval }>()
const item = computed<AwaitItem | undefined>(
  () =>
    props.item ||
    (props.approval
      ? {
          id: props.approval.id,
          sessionId: props.approval.conversation_id,
          turnId: props.approval.task_id,
          mode: 'approval',
          title: t("批准 {0}", [props.approval.tool_name]),
          detail: JSON.stringify(props.approval.arguments, null, 2),
          risk: props.approval.risk_level,
          version: props.approval.version,
        }
      : undefined),
)
const inbox = useInboxStore(),
  rejecting = ref(false),
  note = ref(''),
  failure = ref('')
const pendingDecision = ref<'allow' | 'deny' | null>(null)
async function decide(decision: 'allow' | 'deny') {
  if (!item.value || pendingDecision.value || inbox.busy.includes(item.value.id)) return
  pendingDecision.value = decision
  failure.value = ''
  try {
    await inbox.decide(item.value, decision, note.value.trim() || undefined)
  } catch (reason) {
    failure.value = reason instanceof Error ? reason.message : String(reason)
  } finally {
    pendingDecision.value = null
  }
}
</script>
<template>
  <article v-if="item" class="approval-card" :data-await="item.id">
    <header>
      <strong>{{ item.title }}</strong
      ><span>{{ item.risk }}</span>
    </header>
    <pre>{{ item.detail }}</pre>
    <div v-if="rejecting">
      <label>{{ $t('驳回理由（可选）') }}<textarea v-model="note" rows="2" maxlength="2000" /></label>
    </div>
    <p v-if="failure" role="alert">{{ failure }}</p>
    <footer>
      <InkButton
        tone="primary"
        data-verdict="allow"
        :disabled="inbox.busy.includes(item.id) || pendingDecision !== null"
        :loading="pendingDecision === 'allow'"
        @click="decide('allow')"
        >{{ pendingDecision === 'allow' ? $t('正在提交…') : $t('允许') }} <small>Y</small></InkButton
      >
      <InkButton
        tone="danger"
        data-verdict="deny"
        :disabled="inbox.busy.includes(item.id) || pendingDecision !== null"
        :loading="pendingDecision === 'deny'"
        @click="rejecting ? decide('deny') : (rejecting = true)"
        >{{ pendingDecision === 'deny' ? $t('正在提交…') : rejecting ? $t('确认驳回') : $t('驳回') }} <small>N</small></InkButton
      >
      <button v-if="rejecting" class="cancel-note secondary-button" :disabled="pendingDecision !== null" @click="rejecting = false">{{ $t('取消') }}</button>
    </footer>
  </article>
</template>
<style scoped lang="scss">
.approval-card {
  margin: 8px 0 16px;
  padding: 16px;
  border: 1px solid var(--rule);
  border-left: 2px solid var(--wait);
  border-radius: var(--radius-md);
  background: var(--paper-2);
}
header {
  display: flex;
  justify-content: space-between;
  font-size: var(--text-sm);
}
header span {
  color: var(--ink-2);
}
pre {
  max-height: 180px;
  overflow: auto;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: var(--leading-small);
}
footer {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
small {
  margin-left: 6px;
  opacity: 0.6;
}
label {
  display: grid;
  gap: 6px;
  font-size: var(--text-xs);
  color: var(--ink-2);
}
textarea {
  width: 100%;
  margin-bottom: 12px;
}
.cancel-note {
  border: 0;
  background: var(--transparent);
  color: var(--ink-2);
}
p {
  color: var(--ink-2);
  font-size: var(--text-xs);
}
</style>
