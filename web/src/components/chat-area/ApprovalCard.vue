<script setup lang="ts">
import { computed, ref } from 'vue'
import type { Approval } from '@/api/client'
import IconSymbol from '@/components/common/IconSymbol.vue'
import { useSessionStore } from '@/stores/session'

const props = defineProps<{ approval: Approval }>()
const sessionStore = useSessionStore()
const submitting = ref(false)
const argumentsText = computed(() => JSON.stringify(props.approval.arguments, null, 2))

async function decide(decision: 'allow' | 'deny') {
  if (submitting.value) return
  submitting.value = true
  try { await sessionStore.decideApproval(props.approval, decision) }
  finally { submitting.value = false }
}
</script>

<template>
  <article class="approval-card" role="alert">
    <header>
      <span class="approval-icon"><IconSymbol name="shield" :size="18" /></span>
      <div><strong>需要你的确认</strong><small>{{ approval.tool_name }} · {{ approval.risk_level }}</small></div>
      <span class="risk">{{ approval.risk_level }}</span>
    </header>
    <dl>
      <div><dt>访问范围</dt><dd>{{ approval.resource_scope }}</dd></div>
      <div><dt>有效期</dt><dd>{{ new Date(approval.expires_at).toLocaleString() }}</dd></div>
    </dl>
    <details>
      <summary>查看规范化参数</summary>
      <pre>{{ argumentsText }}</pre>
    </details>
    <footer>
      <button type="button" class="deny" :disabled="submitting" @click="decide('deny')">拒绝</button>
      <button type="button" class="allow" :disabled="submitting" @click="decide('allow')">
        {{ submitting ? '正在提交…' : '仅允许本次' }}
      </button>
    </footer>
  </article>
</template>

<style scoped lang="scss">
.approval-card { margin: 12px 0; overflow: hidden; border: 1px solid rgba(218, 142, 34, .32); border-radius: 16px; background: var(--surface-solid); box-shadow: var(--shadow-card); }
header { display: flex; align-items: center; gap: 10px; padding: 14px 15px; background: var(--warning-soft); }
.approval-icon { display: grid; width: 34px; height: 34px; place-items: center; border-radius: 10px; color: var(--warning); background: var(--surface-solid); }
header div { display: flex; min-width: 0; flex: 1; flex-direction: column; }
header strong { font-size: 12px; } header small { margin-top: 3px; color: var(--text-secondary); font-size: 10px; }
.risk { padding: 4px 8px; border-radius: 999px; color: var(--warning); background: var(--surface-solid); font-size: 10px; font-weight: 750; }
dl { margin: 0; padding: 10px 15px; } dl div { display: grid; grid-template-columns: 76px 1fr; gap: 10px; padding: 5px 0; font-size: 10px; }
dt { color: var(--text-tertiary); } dd { margin: 0; overflow-wrap: anywhere; color: var(--text-secondary); }
details { margin: 0 15px 12px; border-radius: 10px; background: var(--surface-muted); }
summary { padding: 9px 10px; cursor: pointer; color: var(--text-secondary); font-size: 10px; }
pre { max-height: 180px; margin: 0; padding: 0 10px 10px; overflow: auto; white-space: pre-wrap; font-size: 9.5px; }
footer { display: flex; justify-content: flex-end; gap: 8px; padding: 11px 14px; border-top: 1px solid var(--border-color); }
button { min-height: 32px; padding: 0 13px; border-radius: 9px; cursor: pointer; font-size: 10.5px; font-weight: 650; }
.deny { border: 1px solid var(--border-color); color: var(--text-secondary); background: var(--surface-solid); }
.allow { border: 0; color: white; background: var(--primary-color); }
button:disabled { cursor: default; opacity: .55; }
</style>
