/**
 * Skill 管理页
 *
 * 查看、安装和配置 Agent Skills。
 */

<script setup lang="ts">
import { useSkillStore } from '@/stores/skill'
import { onMounted } from 'vue'

const skillStore = useSkillStore()

onMounted(() => {
  skillStore.loadSkills()
})
</script>

<template>
  <div class="skill-manager-page">
    <h1>Skill 管理</h1>
    <ul>
      <li v-for="skill in skillStore.skills" :key="skill.id">
        {{ skill.name }} v{{ skill.version }}
      </li>
    </ul>
  </div>
</template>

<style scoped lang="scss">
.skill-manager-page {
  padding: 24px;
}
</style>
