/**
 * Inspector 主页面组件
 *
 * 展示活跃/已完成/失败的对话卡片列表和维度选择器。
 */

<script setup lang="ts">
import InspectorCard from './InspectorCard.vue'
import TimelineNode from './TimelineNode.vue'
import DimensionSelector from './DimensionSelector.vue'
import { useInspector } from '@/composables/useInspector'
import { ref } from 'vue'

const { activeCards, completedCards, failedCards, connect, loadCards } = useInspector()

const expandedSessions = ref<string[]>([])
const currentTimeline = ref<any[]>([])

function toggleExpand(sessionId: string) {
  if (expandedSessions.value.includes(sessionId)) {
    expandedSessions.value = expandedSessions.value.filter((id) => id !== sessionId)
    currentTimeline.value = []
  } else {
    expandedSessions.value.push(sessionId)
    // TODO: 加载时间线数据
  }
}
</script>

<template>
  <div class="inspector-view">
    <div class="inspector-header">
      <h2>Inspector</h2>
      <DimensionSelector />
    </div>

    <section class="card-section">
      <h3>运行中 ({{ activeCards.length }})</h3>
      <InspectorCard
        v-for="card in activeCards"
        :key="card.session_id"
        :card="card"
        :expanded="expandedSessions.includes(card.session_id)"
        @expand="toggleExpand"
        @collapse="toggleExpand"
      />
    </section>

    <section class="card-section">
      <h3>已完成 ({{ completedCards.length }})</h3>
      <InspectorCard
        v-for="card in completedCards"
        :key="card.id"
        :card="card"
        :expanded="expandedSessions.includes(card.session_id)"
        @expand="toggleExpand"
        @collapse="toggleExpand"
      />
    </section>

    <section class="card-section">
      <h3>失败 ({{ failedCards.length }})</h3>
      <InspectorCard
        v-for="card in failedCards"
        :key="card.id"
        :card="card"
        :expanded="expandedSessions.includes(card.session_id)"
        @expand="toggleExpand"
        @collapse="toggleExpand"
      />
    </section>

    <div v-if="activeCards.length === 0 && completedCards.length === 0 && failedCards.length === 0">
      <p class="empty-state">暂无执行的对话</p>
    </div>
  </div>
</template>

<style scoped lang="scss">
.inspector-view {
  padding: 16px;
  height: 100%;
  overflow-y: auto;
}

.inspector-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.card-section {
  margin-bottom: 24px;

  h3 {
    font-size: 14px;
    color: #666;
    margin-bottom: 8px;
  }
}

.empty-state {
  text-align: center;
  color: #999;
  padding: 48px 0;
}
</style>
