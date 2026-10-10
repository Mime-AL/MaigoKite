import { t } from '@/i18n'
import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  api,
  type InstalledSkill,
  type MCPServerStatus,
  type WorkspaceDataSummary,
} from '@/api/client'

export const usePhase2Store = defineStore('phase2', () => {
  const mcpServers = ref<MCPServerStatus[]>([])
  const skills = ref<InstalledSkill[]>([])
  const dataSummary = ref<WorkspaceDataSummary | null>(null)
  const mcpLoading = ref(false)
  const dataLoading = ref(false)
  const mcpError = ref<string | null>(null)
  const dataError = ref<string | null>(null)

  async function loadMCPServers() {
    if (mcpLoading.value) return
    mcpLoading.value = true
    mcpError.value = null
    try {
      const [servers, installedSkills] = await Promise.allSettled([
        api.listMCPServers(),
        api.listSkills(),
      ])
      if (servers.status === 'rejected') throw servers.reason
      mcpServers.value = servers.value
      skills.value = installedSkills.status === 'fulfilled' ? installedSkills.value : []
      if (installedSkills.status === 'rejected') {
        mcpError.value = t("无法读取技能列表：{0}", [installedSkills.reason instanceof Error ? installedSkills.reason.message : String(installedSkills.reason)])
      }
    }
    catch (reason) { mcpError.value = reason instanceof Error ? reason.message : String(reason) }
    finally { mcpLoading.value = false }
  }

  async function loadDataSummary() {
    if (dataLoading.value) return
    dataLoading.value = true
    dataError.value = null
    try { dataSummary.value = await api.getWorkspaceDataSummary() }
    catch (reason) { dataError.value = reason instanceof Error ? reason.message : String(reason) }
    finally { dataLoading.value = false }
  }

  return {
    mcpServers, skills, dataSummary, mcpLoading, dataLoading, mcpError, dataError,
    loadMCPServers, loadDataSummary,
  }
})
