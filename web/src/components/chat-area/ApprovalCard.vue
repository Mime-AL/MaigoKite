<script setup lang="ts">
import { t } from '@/i18n'
import { computed, nextTick, ref } from 'vue'
import type { AwaitItem } from '@/api/events'
import type { Approval } from '@/api/client'
import { useInboxStore } from '@/stores/inbox'
import InkButton from '@/components/common/InkButton.vue'
import { useSessionStore } from '@/stores/session'
import { approvalDescription } from '@/utils/tool-presentation'
import { awaitFocus } from '@/utils/await-focus'
const card = ref<HTMLElement | null>(null)
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
          title: t('批准 {0}', [props.approval.tool_name]),
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
const session = useSessionStore()
const description = computed(() =>
  item.value
    ? approvalDescription(
        item.value,
        props.approval ||
          session.approvals[item.value.sessionId]?.find((record) => record.id === item.value?.id),
      )
    : undefined,
)
async function decide(decision: 'allow' | 'deny') {
  if (!item.value || pendingDecision.value || inbox.busy.includes(item.value.id)) return
  pendingDecision.value = decision
  failure.value = ''
  const restoreFocus = awaitFocus(card.value)
  try {
    await inbox.decide(item.value, decision, note.value.trim() || undefined)
  } catch (reason) {
    failure.value = reason instanceof Error ? reason.message : String(reason)
  } finally {
    pendingDecision.value = null
    await nextTick()
    restoreFocus()
  }
}
</script>
<template>
  <article
    v-if="item"
    ref="card"
    class="approval-card"
    :data-await="item.id"
  >
    <header>
      <strong>{{ description?.action }}</strong><span class="await-label">{{ $t('等你处理') }}</span>
    </header>
    <p class="approval-target">
      {{ description?.target }}
    </p>
    <p
      v-if="description?.command"
      class="approval-command"
    >
      {{ description.command }}
    </p>
    <p class="approval-impact">
      {{ description?.impact }}
    </p>
    <details class="approval-details">
      <summary>{{ $t('操作详情') }}</summary>
      <dl>
        <dt>{{ $t('工具') }}</dt>
        <dd>{{ description?.tool }}</dd>
        <dt>{{ $t('风险等级') }}</dt>
        <dd>{{ item.risk }}</dd>
      </dl>
      <pre>{{ item.detail }}</pre>
    </details>
    <div v-if="rejecting">
      <label>{{ $t('驳回理由（可选）') }}<textarea
        v-model="note"
        rows="2"
        maxlength="2000"
      />
      </label>
    </div>
    <p
      v-if="failure"
      role="alert"
    >
      {{ failure }}
    </p>
    <footer>
      <InkButton
        tone="primary"
        data-verdict="allow"
        data-await-action
        :disabled="inbox.busy.includes(item.id) || pendingDecision !== null"
        :loading="pendingDecision === 'allow'"
        @click="decide('allow')"
      >
        {{ pendingDecision === 'allow' ? $t('正在提交…') : $t('允许') }}
        <small>Y</small>
      </InkButton>
      <InkButton
        tone="danger"
        data-verdict="deny"
        data-await-action
        :disabled="inbox.busy.includes(item.id) || pendingDecision !== null"
        :loading="pendingDecision === 'deny'"
        @click="rejecting ? decide('deny') : (rejecting = true)"
      >
        {{
          pendingDecision === 'deny' ? $t('正在提交…') : rejecting ? $t('确认驳回') : $t('驳回')
        }}
        <small>N</small>
      </InkButton>
      <button
        v-if="rejecting"
        class="cancel-note secondary-button"
        :disabled="pendingDecision !== null"
        @click="rejecting = false"
      >
        {{ $t('取消') }}
      </button>
    </footer>
  </article>
</template>
<style scoped lang="scss">
.approval-card {
  margin: var(--space-3) 0 var(--space-5);
  padding: var(--space-5);
  border: var(--hairline) solid var(--rule);
  border-left: var(--space-1) solid var(--wait);
  border-radius: var(--radius-md);
  background: var(--paper-2);
}
.approval-target {
  color: var(--ink);
  font: var(--text-sm) var(--font-mono);
  overflow-wrap: anywhere;
}
.approval-command {
  color: var(--ink);
  white-space: pre-wrap;
  font: var(--text-sm) var(--font-mono);
}
.approval-impact {
  color: var(--ink-2);
  line-height: var(--leading-normal);
}
.await-label {
  color: var(--wait-ink);
  font-size: var(--text-xs);
}
.approval-details {
  margin-block: var(--space-4);
  font-size: var(--text-xs);
}
.approval-details summary {
  cursor: pointer;
  color: var(--ink-2);
}
dl {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: var(--space-2) var(--space-4);
}
dd {
  margin: 0;
  overflow-wrap: anywhere;
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
  max-height: var(--detail-max-height);
  overflow: auto;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font-family: var(--font-mono);
  font-size: var(--text-sm);
  line-height: var(--leading-small);
}
footer {
  display: flex;
  gap: var(--space-3);
  flex-wrap: wrap;
}
small {
  margin-left: var(--size-6);
}
label {
  display: grid;
  gap: var(--size-6);
  font-size: var(--text-xs);
  color: var(--ink-2);
}
textarea {
  width: 100%;
  margin-bottom: var(--space-4);
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
