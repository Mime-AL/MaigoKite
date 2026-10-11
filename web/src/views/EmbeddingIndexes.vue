<script setup lang="ts">
import RailGlyph from '@/components/rail/RailGlyph.vue'
import { useUIStore } from '@/stores/ui'
const ui = useUIStore()
</script>
<template>
  <main class="page-shell index-page">
    <header>
      <h1 class="page-title">
        {{ $t('知识库') }}
      </h1>
    </header>
    <section class="page-state">
      <RailGlyph kind="read" /><strong>{{ $t('此页面不可用') }}</strong>
      <p>{{ $t('文件可以在对话中直接读取，也可以从工作区预览。') }}</p>
      <div class="page-actions">
        <RouterLink
          class="secondary-button"
          to="/chat"
        >
          {{ $t('返回对话') }}
        </RouterLink><button
          class="secondary-button"
          @click="ui.openDrawer('files')"
        >
          {{ $t('查看工作区文件') }}
        </button>
      </div>
    </section>
  </main>
</template>
<style scoped lang="scss">
.index-page {
  display: grid;
  gap: var(--space-7);
}
</style>
