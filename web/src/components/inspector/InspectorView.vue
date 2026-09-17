<script setup lang="ts">
import { ref } from 'vue'
import { useInspector } from '@/composables/useInspector'
import IconSymbol from '@/components/common/IconSymbol.vue'
import DimensionSelector from './DimensionSelector.vue'
import InspectorCard from './InspectorCard.vue'

const { activeCards, completedCards, failedCards } = useInspector()
const expandedSessions = ref<string[]>([])

function toggle(sessionId: string) {
  expandedSessions.value = expandedSessions.value.includes(sessionId)
    ? expandedSessions.value.filter(id => id !== sessionId)
    : [...expandedSessions.value, sessionId]
}
</script>

<template>
  <main class="page-shell inspector-view">
    <header class="page-header">
      <div>
        <p class="page-eyebrow">Observability</p>
        <h1 class="page-title">Inspector</h1>
        <p class="page-subtitle">实时查看 Agent 如何规划、调用工具并完成任务。</p>
      </div>
      <DimensionSelector />
    </header>

    <template
      v-for="section in [
        { title: '运行中', cards: activeCards, tone: 'live' },
        { title: '已完成', cards: completedCards, tone: 'done' },
        { title: '失败', cards: failedCards, tone: 'failed' },
      ]"
      :key="section.title"
    >
      <section v-if="section.cards.length" class="card-section">
        <header><span :class="section.tone" />{{ section.title }}<small>{{ section.cards.length }}</small></header>
        <InspectorCard
          v-for="card in section.cards"
          :key="card.session_id"
          :card="card"
          :expanded="expandedSessions.includes(card.session_id)"
          @expand="toggle"
          @collapse="toggle"
        />
      </section>
    </template>

    <div v-if="!activeCards.length && !completedCards.length && !failedCards.length" class="empty-state glass-card">
      <span><IconSymbol name="activity" :size="25" /></span>
      <strong>没有正在执行的任务</strong>
      <p>开始一段对话后，任务时间线会实时显示在这里。</p>
    </div>
  </main>
</template>

<style scoped lang="scss">
.inspector-view { display: flex; flex-direction: column; gap: 25px; }
.page-header { display: flex; align-items: flex-end; justify-content: space-between; gap: 20px; }
.card-section > header { display: flex; align-items: center; gap: 7px; margin-bottom: 8px; color: var(--text-secondary); font-size: 10px; font-weight: 680; }
.card-section > header > span { width: 6px; height: 6px; border-radius: 50%; background: var(--text-tertiary); }
.card-section > header .live { background: var(--primary-color); box-shadow: 0 0 0 3px var(--primary-soft); }
.card-section > header .done { background: var(--success); }
.card-section > header .failed { background: var(--danger); }
.card-section > header small { color: var(--text-tertiary); font-size: 9px; font-weight: 500; }
.empty-state { display: flex; min-height: 260px; align-items: center; justify-content: center; flex-direction: column; text-align: center; }
.empty-state > span { display: grid; width: 54px; height: 54px; margin-bottom: 14px; place-items: center; border-radius: 17px; color: var(--primary-color); background: var(--primary-soft); }
.empty-state strong { font-size: 12px; }
.empty-state p { margin: 6px 0 0; color: var(--text-tertiary); font-size: 10px; }
</style>
