import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api } from '@/api/client'
import DataManagement from '@/views/DataManagement.vue'
import EmbeddingIndexes from '@/views/EmbeddingIndexes.vue'
import Integrations from '@/views/Integrations.vue'
import Memory from '@/views/Memory.vue'
import NavMenu from '@/components/sidebar/NavMenu.vue'

describe('data and extension pages', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.restoreAllMocks()
  })

  it('loads persisted user memories', async () => {
    vi.spyOn(api, 'listMemories').mockResolvedValue([{
      id: 'memory_1', workspace_id: 'personal', subject_user_id: 'local-user',
      category: 'preference', content: '回答时使用中文', source_type: 'user',
      source_id: 'local-user', confidence: 1, created_at: 'now', updated_at: 'now',
    }])
    const wrapper = mount(Memory)
    await flushPromises()

    expect(wrapper.text()).toContain('回答时使用中文')
    expect(wrapper.text()).not.toContain('Phase 2')
    expect(wrapper.text()).not.toContain('自动抽取、语义检索')
    expect(wrapper.find('input[type="range"]').exists()).toBe(false)
  })

  it('shows actual MCP runtime inventory', async () => {
    vi.spyOn(api, 'listMCPServers').mockResolvedValue([{
      namespace: 'local_tools', status: 'running', transport: 'stdio', tool_names: ['local_tools__echo'],
    }])
    vi.spyOn(api, 'listSkills').mockResolvedValue([{
      name: 'research', version: '1.0.0', description: '整理研究资料',
      kind: 'instruction', source_path: '/workspace/skills/research/SKILL.md', parameters_schema: {},
    }])
    const wrapper = mount(Integrations)
    await flushPromises()

    expect(wrapper.text()).toContain('local_tools')
    expect(wrapper.text()).toContain('local_tools__echo')
    expect(wrapper.text()).toContain('运行中')
    expect(wrapper.text()).toContain('整理研究资料')
    expect(wrapper.text()).not.toContain('stdio')
    expect(wrapper.text()).not.toContain('/workspace/skills')
  })

  it('shows real workspace data counts', async () => {
    vi.spyOn(api, 'getWorkspaceDataSummary').mockResolvedValue({
      storage_backend: 'sqlite', conversation_count: 2, message_count: 8,
      memory_count: 3, task_count: 5, audit_event_count: 13,
    })
    const wrapper = mount(DataManagement)
    await flushPromises()

    expect(wrapper.text()).toContain('13')
    expect(wrapper.text()).toContain('操作记录')
    expect(wrapper.text()).not.toContain('sqlite')
  })

  it('registers the index page without fake configuration controls', () => {
    const wrapper = mount(EmbeddingIndexes)
    expect(wrapper.text()).toContain('知识库暂未开放')
    expect(wrapper.text()).not.toContain('Phase 2')
    expect(wrapper.text()).not.toContain('待实现')
    expect(wrapper.find('input').exists()).toBe(false)
    expect(wrapper.find('select').exists()).toBe(false)
  })

  it('keeps release phases and unavailable features out of the main navigation', () => {
    const wrapper = mount(NavMenu, { global: { stubs: { RouterLink: RouterLinkStub } } })

    expect(wrapper.text()).toContain('数据')
    expect(wrapper.text()).not.toContain('Phase 2')
    expect(wrapper.text()).not.toContain('Embedding')
    expect(wrapper.text()).not.toContain('知识库')
  })
})
