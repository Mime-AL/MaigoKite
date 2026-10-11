<script setup lang="ts">
import { useSettingsStore } from '@/stores/settings'
import AgentMessage from '@/components/chat-area/AgentMessage.vue'
import Pulse from '@/components/shell/Pulse.vue'
import RailGlyph from '@/components/rail/RailGlyph.vue'
import ModePill from '@/components/inkwell/ModePill.vue'
const settings = useSettingsStore()
</script>
<template>
  <section
    class="appearance-preview"
    :aria-label="$t('外观预览')"
  >
    <header>
      <span>{{ $t('外观预览') }}</span><Pulse state="idle" />
    </header>
    <div class="preview-step">
      <RailGlyph kind="read" /><span>{{ $t('读取工作区中的文本文件。') }}</span>
    </div>
    <AgentMessage
      :assistant-name="settings.profile.assistantName"
      :content="$t('资料已经整理好了。可以继续讨论，也可以打开文件查看。')"
      :show-actions="false"
    />
    <div class="preview-inkwell">
      <span>{{ $t('输入消息…') }}</span><ModePill
        model-value="ask"
        disabled
      />
    </div>
  </section>
</template>
<style scoped lang="scss">
.appearance-preview {
  padding: var(--space-6);
  border: var(--hairline) solid var(--rule);
  border-radius: var(--radius-sm);
  background: var(--paper-raised, var(--paper));
  box-shadow: var(--elevation-sheet);
}
header,
.preview-step {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  color: var(--ink-2);
  font-size: var(--text-xs);
}
header {
  justify-content: space-between;
  margin-bottom: var(--space-5);
}
.preview-step {
  border-inline-start: var(--hairline) solid var(--accent);
  padding-inline-start: var(--space-3);
}
.preview-inkwell {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-4);
  border: var(--hairline) solid var(--rule);
  background: var(--paper-2);
  border-radius: var(--radius-sm);
  color: var(--ink-3);
  font-size: var(--text-sm);
  box-shadow: var(--elevation-inset);
}
</style>
