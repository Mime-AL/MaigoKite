<script setup lang="ts">
import { composerDefaults, type ComposerProps } from '@/utils/composer-presentation'
import ComposerStats from './ComposerStats.vue'
defineOptions({ inheritAttrs: false })
withDefaults(defineProps<ComposerProps & { busy: boolean }>(), composerDefaults)
</script>
<template>
  <ComposerStats
    :session-id="sessionId"
    :model="modelOptions.find((item) => item.id === modelId)"
  />
  <p
    v-if="isStopping || busy"
    class="composer-help"
    role="status"
  >
    {{
      isStopping
        ? $t('正在请求停止，等待服务确认…')
        : $t('正在发送，草稿会保留…')
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
