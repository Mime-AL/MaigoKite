<script setup lang="ts">
import IconSymbol from '@/components/common/IconSymbol.vue'
</script>

<template>
  <main class="page-shell index-page">
    <header>
      <h1 class="page-title">{{ $t('知识库') }}</h1>
    </header>

    <section class="state-card glass-card">
      <span class="state-icon"><IconSymbol name="activity" :size="23" /></span>
      <div>
        <strong>{{ $t('此页面不可用') }}</strong>
      </div>
    </section>
  </main>
</template>

<style scoped lang="scss">
.index-page {
  display: flex;
  flex-direction: column;
  gap: 21px;
}
.state-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 19px;
}
.state-icon {
  display: grid;
  width: 46px;
  height: 46px;
  flex: none;
  place-items: center;
  border-radius: var(--radius-lg);
  color: var(--warning);
  background: var(--warning-soft);
}
.state-card div {
  min-width: 0;
  flex: 1;
}
.state-card strong {
  font-size: var(--text-sm);
}
</style>
