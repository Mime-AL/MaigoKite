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

    const wrapper = mount(MessageList, { props: { sessionId: 'conv-1' } })
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
})
