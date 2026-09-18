import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import MessageList from '@/components/chat-area/MessageList.vue'
import { useSessionStore } from '@/stores/session'

describe('agent activity timeline', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.stubGlobal('requestAnimationFrame', (callback: FrameRequestCallback) => {
      callback(0)
      return 1
    })
    vi.stubGlobal('cancelAnimationFrame', vi.fn())
  })

  it('renders execution activity before the final assistant message', () => {
    const store = useSessionStore()
    store.activeSessionId = 'conv-1'
    store.messages['conv-1'] = [
      {
        id: 'user-1',
        conversation_id: 'conv-1',
        role: 'user',
        content: '检查代码',
        created_at: '2026-09-18T00:00:00Z',
      },
      {
        id: 'stream-task-1',
        conversation_id: 'conv-1',
        role: 'assistant',
        content: '最终结论',
        created_at: '2026-09-18T00:00:03Z',
        streaming: false,
      },
    ]
    store.activities['conv-1'] = [
      {
        id: 'reasoning-1',
        task_id: 'task-1',
        kind: 'reasoning',
        status: 'completed',
        title: '过程说明',
        summary: '先分析结构',
        sequence: 1,
        created_at: '2026-09-18T00:00:01Z',
      },
      {
        id: 'tool-call-1',
        task_id: 'task-1',
        kind: 'tool',
        status: 'completed',
        title: 'file_read',
        summary: '读取完成',
        sequence: 2,
        created_at: '2026-09-18T00:00:02Z',
      },
      {
        id: 'subagent-reviewer',
        task_id: 'task-1',
        kind: 'subagent',
        status: 'completed',
        title: '子 Agent · Reviewer',
        summary: '审查完成',
        sequence: 3,
        created_at: '2026-09-18T00:00:02Z',
      },
    ]
    store.taskActivityStatuses['conv-1'] = { 'task-1': 'completed' }

    const wrapper = mount(MessageList, {
      props: { sessionId: 'conv-1' },
      global: { stubs: { RouterLink: true } },
    })
    const reply = wrapper.get('.agent-message .message-content')
    const activity = wrapper.get('[data-testid="agent-activity"]')
    const timeline = wrapper.findAll('[data-testid="agent-activity"], .agent-message')

    expect(reply.text()).toBe('最终结论')
    expect(reply.text()).not.toContain('先分析结构')
    expect(activity.text()).toContain('过程说明')
    expect(activity.text()).toContain('file_read')
    expect(activity.text()).toContain('子 Agent · Reviewer')
    expect(timeline[0].attributes('data-testid')).toBe('agent-activity')
  })

  it('surfaces an actionable hint instead of only raw failure JSON', () => {
    const store = useSessionStore()
    store.activeSessionId = 'conv-1'
    store.messages['conv-1'] = [{
      id: 'user-search',
      conversation_id: 'conv-1',
      role: 'user',
      content: '搜索资料',
      created_at: '2026-09-18T00:00:00Z',
    }]
    store.activities['conv-1'] = [{
      id: 'tool-search',
      task_id: 'task-search',
      kind: 'tool',
      status: 'failed',
      title: 'web_search',
      summary: 'Web search provider request failed.',
      hint: '联网搜索暂不可用，请配置其他搜索服务。',
      action: { label: '配置联网工具', to: '/settings?tab=tools' },
      detail: { result: { results: [], error: 'search provider request failed' } },
      sequence: 1,
      created_at: '2026-09-18T00:00:01Z',
    }]
    store.taskActivityStatuses['conv-1'] = { 'task-search': 'completed' }

    const wrapper = mount(MessageList, {
      props: { sessionId: 'conv-1' },
      global: { stubs: { RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' } } },
    })

    expect(wrapper.text()).toContain('1 项需要处理')
    expect(wrapper.text()).toContain('联网搜索暂不可用')
    expect(wrapper.get('.item-hint a').text()).toBe('配置联网工具')
    expect(wrapper.get('.item-hint a').attributes('href')).toBe('/settings?tab=tools')
    expect(wrapper.get('.activity-heading').attributes('aria-expanded')).toBe('true')
  })
})
