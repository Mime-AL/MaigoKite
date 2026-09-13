/**
 * Skill 状态 Store
 *
 * 管理已注册的 Skill 列表及其启用状态。
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { SkillInfo } from '@/types'

export const useSkillStore = defineStore('skill', () => {
  const skills = ref<SkillInfo[]>([])
  const isLoading = ref(false)

  /** 加载 Skill 列表 */
  async function loadSkills() {
    isLoading.value = true
    try {
      const result = await window.electronAPI.listSkills()
      skills.value = result.skills ?? []
    } finally {
      isLoading.value = false
    }
  }

  /** 切换 Skill 启用状态 */
  function toggleSkill(skillId: string) {
    const skill = skills.value.find((s) => s.id === skillId)
    if (skill) {
      skill.enabled = !skill.enabled
    }
  }

  return {
    skills,
    isLoading,
    loadSkills,
    toggleSkill
  }
})
