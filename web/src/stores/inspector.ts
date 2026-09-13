/**
 * Inspector 状态 Store
 *
 * 管理 Inspector 监控页面的卡片、时间线和维度选择。
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { InspectorCard, TimelineNode, Dimension } from '@/types'

export const useInspectorStore = defineStore('inspector', () => {
  const cards = ref<InspectorCard[]>([])
  const timelineNodes = ref<TimelineNode[]>([])
  const selectedDimensions = ref<string[]>(['task', 'tool', 'model'])
  const saveHistory = ref(false)

  const activeCards = computed(() => cards.value.filter((c) => c.status === 'running'))
  const completedCards = computed(() => cards.value.filter((c) => c.status === 'completed'))
  const failedCards = computed(() => cards.value.filter((c) => c.status === 'failed'))

  /** 更新卡片状态 */
  function updateCard(card: InspectorCard) {
    const idx = cards.value.findIndex((c) => c.session_id === card.session_id)
    if (idx >= 0) {
      cards.value[idx] = card
    } else {
      cards.value.push(card)
    }
  }

  /** 添加时间线节点 */
  function addTimelineNode(node: TimelineNode) {
    timelineNodes.value.push(node)
  }

  /** 切换维度选择 */
  function toggleDimension(dim: string) {
    if (selectedDimensions.value.includes(dim)) {
      selectedDimensions.value = selectedDimensions.value.filter((d) => d !== dim)
    } else {
      selectedDimensions.value.push(dim)
    }
  }

  return {
    cards,
    timelineNodes,
    selectedDimensions,
    saveHistory,
    activeCards,
    completedCards,
    failedCards,
    updateCard,
    addTimelineNode,
    toggleDimension
  }
})
