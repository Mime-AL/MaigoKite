<script setup lang="ts">
import { composerDefaults, type ComposerProps } from '@/utils/composer-presentation'
import ComposerStats from './ComposerStats.vue'
import SubagentSettings from '@/components/chat-area/SubagentSettings.vue'
defineOptions({ inheritAttrs: false })
withDefaults(defineProps<ComposerProps & { busy: boolean }>(), composerDefaults)
const emit = defineEmits<{
  (
    event: 'subagents-change',
    value: { calls: number; concurrent: number; modelIds?: string[] },
  ): void
}>()
</script>
<template>
  <ComposerStats
    :session-id="sessionId"
    :model-name="modelOptions.find((item) => item.id === modelId)?.model || ''"
  />
  <SubagentSettings
    v-if="subagentsSupported"
    :key="sessionId"
    :calls="maxSubagentCalls"
    :concurrent="maxConcurrentSubagents"
    :model-options="modelOptions"
    :model-ids="subagentModelIds"
    :model-selection-supported="subagentModelsSupported"
    :saving="savingSubagents"
    :disabled="isSubmitting"
    @change="emit('subagents-change', $event)"
  />
  <p class="composer-help">
    {{
      isStopping
        ? $t('正在请求停止，等待服务确认…')
        : busy
          ? $t('正在发送，草稿会保留…')
          : isSending
            ? $t('Enter 引导 · Alt + Enter 稍后发送 · Esc 停止')
            : $t('Enter 发送 · Shift + Enter 换行')
    }}
  </p>
  <router-link
    v-if="!modelOptions.length"
    class="configure-link"
    to="/settings?tab=models"
  >
    {{
      $t('连接模型')
    }}
  </router-link>
</template>
<style scoped lang="scss">
.composer-help {
  margin: var(--space-3) 0 0;
  text-align: right;
  color: var(--ink-2);
  font-size: var(--text-xs);
}
.configure-link {
  display: block;
  margin-top: var(--space-3);
  text-align: center;
  font-size: var(--text-sm);
}
</style>
