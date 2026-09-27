<script setup lang="ts">
import IconSymbol from '@/components/common/IconSymbol.vue'
</script>

<template>
  <main class="page-shell index-page">
    <header>
      <h1 class="page-title">知识库</h1>
      <p class="page-subtitle">使用资料帮助助手理解你的工作内容。</p>
    </header>

    <section class="state-card glass-card">
      <span class="state-icon"><IconSymbol name="activity" :size="23" /></span>
      <div><strong>知识库暂未开放</strong><p>此功能准备好后会在这里提供。</p></div>
      <span class="badge">敬请期待</span>
    </section>
  </main>
</template>

<style scoped lang="scss">
.index-page { display: flex; flex-direction: column; gap: 21px; }
.state-card { display: flex; align-items: center; gap: 14px; padding: 19px; }
.state-icon { display: grid; width: 46px; height: 46px; flex: none; place-items: center; border-radius: 14px; color: var(--warning); background: var(--warning-soft); }
.state-card div { min-width: 0; flex: 1; }
.state-card strong { font-size: 13px; }
.state-card p { margin: 5px 0 0; color: var(--text-secondary); font-size: 10.5px; }
.badge { padding: 5px 8px; border-radius: 8px; color: var(--warning); background: var(--warning-soft); font-size: 9px; font-weight: 700; }
</style>
