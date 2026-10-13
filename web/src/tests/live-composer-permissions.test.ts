import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { api } from '@/api/client'
import { chooseOption, mockDialogs } from './ui-harness'
import ComposerToolbar from '@/components/inkwell/ComposerToolbar.vue'
import QueuedMessages from '@/components/chat-area/QueuedMessages.vue'

const props = {
  sessionId: 'c', mode: 'auto' as const, busy: false, hasDraft: true,
  guideDisabled: false, isSending: true, permissionMode: 'workspace' as const,
  modelId: 'm', modelOptions: [{ id: 'm', name: 'Local', model: 'local' }],
}
describe('live composer controls', () => {
  beforeEach(() => {
    mockDialogs()
    vi.spyOn(api, 'getModelThinking').mockResolvedValue({
      kind: 'effort', options: ['low', 'high'], default: 'low', source: 'fixture', reason: '',
    })
  })
  it('allows permission changes while running without unlocking model changes', async () => {
    const wrapper = mount(ComposerToolbar, { props })
    await flushPromises()
    const permission = wrapper.get('button[role="combobox"][aria-label="执行权限"]')
    expect(permission.attributes('disabled')).toBeUndefined()
    await chooseOption(wrapper, '执行权限', '只读')
    expect(wrapper.emitted('permission-mode-change')).toEqual([['read_only']])
    expect(wrapper.get('[aria-haspopup="dialog"]').attributes('disabled')).toBeDefined()
    expect(wrapper.get('input[aria-label="思考强度"]').attributes('disabled')).toBeDefined()
    await wrapper.setProps({ isSubmitting: true })
    expect(permission.attributes('disabled')).toBeDefined()
    await permission.trigger('click')
    expect(wrapper.emitted('permission-mode-change')).toEqual([['read_only']])
  })
  it('keeps send now, queue, and stop as independent existing events', async () => {
    const wrapper = mount(ComposerToolbar, { props })
    await wrapper.get('[aria-label="发送选项"]').trigger('click')
    const choices = wrapper.findAll('.send-options-menu button')
    expect(choices[0].text()).toContain('立即发送')
    expect(choices[1].text()).toContain('加入队列')
    await choices[1].trigger('click')
    expect(wrapper.emitted('send')?.[0]).toEqual([true])
    expect(wrapper.emitted('cancel')).toBeUndefined()
    await wrapper.get('[aria-label="停止任务"]').trigger('click')
    expect(wrapper.emitted('cancel')).toHaveLength(1)
  })
  it('exposes queued messages without auto-sending or hiding failed sends', async () => {
    const guide = vi.fn().mockRejectedValue(new Error('waiting approval'))
    const wrapper = mount(QueuedMessages, { props: {
      items: [{ id: 'q', content: 'keep this' }], paused: false,
      guideReason: '', canContinue: false, guide,
    } })
    expect(guide).not.toHaveBeenCalled()
    await wrapper.get('.queue-actions .text-button').trigger('click')
    await vi.waitFor(() => expect(wrapper.get('[role="alert"]').text()).toBe('waiting approval'))
    expect(wrapper.text()).toContain('keep this')
    expect(wrapper.emitted('remove')).toBeUndefined()
  })
})
