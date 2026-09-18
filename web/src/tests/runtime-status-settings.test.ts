import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api } from '@/api/client'
import RuntimeStatusPanel from '@/components/settings/RuntimeStatusPanel.vue'

describe('workspace runtime settings', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    setActivePinia(createPinia())
  })

  it('shows values returned by the runtime status API', async () => {
    vi.spyOn(api, 'getWorkspaceRuntimeStatus').mockResolvedValue({
      workspaceId: 'personal',
      workspaceRoot: '/workspaces/current-project',
      workspaceSource: 'environment',
      environment: 'development',
      gateway: { status: 'serving', version: '0.1.0' },
      agentCore: { status: 'serving', version: '0.1.0' },
      restart: {
        pending: false,
        requiredFor: ['Workspace 根目录', 'MCP Server 启动配置'],
        hotApplied: ['Chat 模型与默认模型', '权限模式'],
        note: '当前设置页没有待重启更改。',
      },
    })

    const wrapper = mount(RuntimeStatusPanel)
    await flushPromises()

    expect(wrapper.text()).toContain('/workspaces/current-project')
    expect(wrapper.text()).toContain('环境变量')
    expect(wrapper.text()).toContain('Gateway')
    expect(wrapper.text()).toContain('Agent Core')
    expect(wrapper.text()).toContain('Workspace 根目录')
    expect(wrapper.text()).toContain('Chat 模型与默认模型')
    expect(wrapper.find('input').exists()).toBe(false)
  })

  it('shows an unavailable Agent Core without hiding Gateway state', async () => {
    vi.spyOn(api, 'getWorkspaceRuntimeStatus').mockResolvedValue({
      workspaceId: 'personal',
      workspaceRoot: '/workspaces/current-project',
      workspaceSource: 'configuration',
      environment: 'production',
      gateway: { status: 'serving', version: '0.1.0' },
      agentCore: { status: 'unavailable' },
      restart: { pending: false, requiredFor: [], hotApplied: [], note: '没有待重启更改。' },
    })

    const wrapper = mount(RuntimeStatusPanel)
    await flushPromises()

    expect(wrapper.text()).toContain('Agent Core')
    expect(wrapper.text()).toContain('不可用')
    expect(wrapper.text()).toContain('Gateway')
  })
})
