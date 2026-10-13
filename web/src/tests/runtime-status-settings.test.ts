import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia, type Pinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api } from '@/api/client'
import RuntimeStatusPanel from '@/components/settings/RuntimeStatusPanel.vue'

describe('workspace runtime settings', () => {
  let pinia: Pinia

  beforeEach(() => {
    vi.restoreAllMocks()
    pinia = createPinia()
    setActivePinia(pinia)
  })

  function mountPanel() {
    return mount(RuntimeStatusPanel, { global: { plugins: [pinia] } })
  }

  it('shows values returned by the runtime status API', async () => {
    vi.spyOn(api, 'getWorkspaceRuntimeStatus').mockResolvedValue({
      workspaceId: 'personal',
      workspaceRoot: '/workspaces/current-project',
      workspaceSource: 'environment',
      environment: 'development',
      backend: { status: 'serving', version: '0.1.0' },
      restart: {
        pending: false,
        requiredFor: ['Workspace 根目录', 'MCP Server 启动配置'],
        hotApplied: ['Chat 模型与默认模型', '权限模式'],
        note: '当前设置页没有待重启更改。',
      },
    })

    const wrapper = mountPanel()
    await flushPromises()

    expect(wrapper.text()).toContain('/workspaces/current-project')
    expect(wrapper.text()).toContain('应用服务')
    expect(wrapper.text()).toContain('运行中')
    expect(wrapper.text()).toContain('0.1.0')
    expect(wrapper.text()).not.toContain('环境变量')
    expect(wrapper.text()).not.toContain('Gateway')
    expect(wrapper.text()).not.toContain('Agent Core')
    expect(wrapper.text()).not.toContain('待重启')
    expect(wrapper.find('input').exists()).toBe(false)
  })

  it('shows an unavailable application service without exposing internal component names', async () => {
    vi.spyOn(api, 'getWorkspaceRuntimeStatus').mockResolvedValue({
      workspaceId: 'personal',
      workspaceRoot: '/workspaces/current-project',
      workspaceSource: 'configuration',
      environment: 'production',
      backend: { status: 'unavailable' },
      restart: { pending: false, requiredFor: [], hotApplied: [], note: '没有待重启更改。' },
    })

    const wrapper = mountPanel()
    await flushPromises()

    expect(wrapper.text()).toContain('不可用')
    expect(wrapper.text()).toContain('应用服务')
    expect(wrapper.text()).not.toContain('Gateway')
    expect(wrapper.text()).not.toContain('Agent Core')
  })

  it('only shows a restart hint when a restart is actually pending', async () => {
    vi.spyOn(api, 'getWorkspaceRuntimeStatus').mockResolvedValue({
      workspaceId: 'personal',
      workspaceRoot: '/workspaces/current-project',
      workspaceSource: 'configuration',
      environment: 'production',
      backend: { status: 'serving', version: '0.1.0' },
      restart: {
        pending: true,
        requiredFor: ['internal.setting'],
        hotApplied: [],
        note: 'internal implementation detail',
      },
    })

    const wrapper = mountPanel()
    await flushPromises()

    expect(wrapper.get('.pending').text()).toBe('重启应用后生效。')
    expect(wrapper.text()).not.toContain('internal.setting')
    expect(wrapper.text()).not.toContain('implementation detail')
  })
})
