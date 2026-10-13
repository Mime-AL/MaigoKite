import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { h } from 'vue'
import RailTrack from '@/components/rail/RailTrack.vue'
import AgentMessage from '@/components/chat-area/AgentMessage.vue'
import { useRunStore } from '@/stores/run'
import { mapGatewayEvent } from '@/api/event-adapter'
import type { AgentEvent } from '@/api/client'
import { testRouter } from './ui-harness'

// The production Chat view renders RailTrack + AgentMessage. Do not seed the
// read-only legacy activities facade or test a disconnected MessageList.
function receipt(type: string, sequence: number, payload: AgentEvent['payload']) {
  for (const event of mapGatewayEvent({ schema_version: 1, event_id: 'event-' + sequence,
    sequence, type, conversation_id: 'conv-1', task_id: 'task-1',
    occurred_at: '2026-09-18T00:00:01Z', payload })) useRunStore().apply(event)
}
async function render() {
  await vi.advanceTimersByTimeAsync(20)
  const turn = useRunStore().getTurn('conv-1', 'task-1')
  return mount(RailTrack, {
    props: { turn },
    slots: { default: () => h(AgentMessage, { content: '最终结论' }) },
    global: { plugins: [await testRouter('/chat/conv-1')] },
  })
}
describe('agent activity timeline', () => {
  beforeEach(() => { vi.useFakeTimers() })

  it('renders execution activity before the final assistant message', async () => {
    receipt('reasoning.completed', 1, { summary: '先分析结构' })
    receipt('tool.started', 2, { tool_call_id: 'read-1', tool_name: 'file_read', arguments: { path: 'README.md' } })
    receipt('tool.completed', 3, { tool_call_id: 'read-1', tool_name: 'file_read', summary: '读取完成' })
    receipt('subagent.started', 4, { subagent_id: 'reviewer', name: 'Reviewer', task: '审查实现' })
    receipt('subagent.completed', 5, { subagent_id: 'reviewer', summary: '审查完成' })
    receipt('task.succeeded', 6, {})
    const wrapper = await render()
    const reply = wrapper.get('.agent-message .markdown-content')
    expect(reply.text()).toBe('最终结论')
    expect(reply.text()).not.toContain('先分析结构')
    expect(reply.text()).not.toContain('审查完成')
    expect(wrapper.get('.thinking-panel').attributes('open')).toBeUndefined()
    expect(wrapper.find('.thinking-content').exists()).toBe(false)
    await wrapper.get('.thinking-heading').trigger('click')
    expect(wrapper.get('.thinking-panel').attributes('open')).toBeDefined()
    expect(wrapper.get('.thinking-content').text()).toContain('先分析结构')
    await wrapper.get('.process').trigger('toggle')
    await wrapper.get('.node-button').trigger('click')
    await flushPromises()
    expect(wrapper.get('.process').text()).toContain('读取 README.md')
    expect(useRunStore().getTurn('conv-1', 'task-1').steps[0].tool).toBe('file_read')
    expect(wrapper.get('.process').text()).toContain('Reviewer')
    expect(wrapper.get('.process').text()).toContain('审查完成')
    const ordered = wrapper.findAll('.thinking-panel, .process, .answer')
    expect(ordered.map(node => node.classes()[0])).toEqual(['thinking-panel', 'process', 'answer'])
    await wrapper.get('.thinking-heading').trigger('click')
    expect(wrapper.find('.thinking-content').exists()).toBe(false)
    expect(reply.text()).toBe('最终结论')
  })

  it('surfaces an actionable hint instead of only raw failure JSON', async () => {
    receipt('tool.started', 1, { tool_call_id: 'search', tool_name: 'web_search', arguments: { query: 'math' } })
    receipt('tool.failed', 2, { tool_call_id: 'search', tool_name: 'web_search',
      user_hint: '联网搜索暂不可用，请配置其他搜索服务。',
      action: { label: '配置联网工具', to: '/settings?tab=tools' },
      data: { results: [], error: 'search provider request failed' } })
    receipt('task.succeeded', 3, {})
    const wrapper = await render()
    // Failures stay expanded even after the overall task succeeds.
    expect(wrapper.get('.rail-node.failed .node-button').attributes('aria-expanded')).toBe('true')
    expect(wrapper.get('.hint').text()).toContain('联网搜索暂不可用')
    expect(wrapper.get('.hint a').text()).toBe('设置工具')
    expect(wrapper.get('.hint a').attributes('href')).toBe('/settings?tab=tools')
    expect(wrapper.get('.rail-node.failed').isVisible()).toBe(true)
    expect(useRunStore().getTurn('conv-1', 'task-1').summary?.failed).toBe(1)
  })
})
