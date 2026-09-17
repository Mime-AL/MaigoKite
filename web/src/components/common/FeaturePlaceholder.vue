<script setup lang="ts">
import IconSymbol from './IconSymbol.vue'

withDefaults(defineProps<{
  eyebrow?: string
  title: string
  description: string
  icon: string
  status?: string
}>(), {
  eyebrow: 'Workspace',
  status: '即将推出',
})
</script>

<template>
  <main class="page-shell feature-page">
    <header>
      <p class="page-eyebrow">{{ eyebrow }}</p>
      <h1 class="page-title">{{ title }}</h1>
      <p class="page-subtitle">{{ description }}</p>
    </header>

    <section class="feature-card glass-card">
      <div class="feature-icon"><IconSymbol :name="icon" :size="34" :stroke-width="1.5" /></div>
      <div>
        <span class="status-pill">{{ status }}</span>
        <h2>正在准备更完整的体验</h2>
        <p>该能力已经纳入产品路线，当前界面先保持清晰的功能边界，不展示无法使用的模拟操作。</p>
      </div>
    </section>
  </main>
</template>

<style scoped lang="scss">
.feature-page { display: flex; flex-direction: column; gap: 38px; }
.feature-card {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 22px;
  padding: 28px;
}
.feature-icon {
  display: grid;
  width: 64px;
  height: 64px;
  place-items: center;
  border-radius: 18px;
  color: var(--primary-color);
  background: var(--primary-soft);
}
.status-pill {
  display: inline-flex;
  margin-bottom: 12px;
  padding: 5px 10px;
  border-radius: 999px;
  color: var(--warning);
  background: var(--warning-soft);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
}
h2 { margin: 0; font-size: 20px; letter-spacing: -0.02em; }
p { max-width: 620px; margin: 8px 0 0; color: var(--text-secondary); line-height: 1.6; }
</style>
