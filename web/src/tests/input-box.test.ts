import { mount, flushPromises } from '@vue/test-utils'
import { beforeEach, describe, expect, it } from 'vitest'
import { mockDialogs, testRouter } from './ui-harness'

import InputBox from '@/components/chat-area/InputBox.vue'

describe('InputBox', () => {
  const configuredModel = [{ id: 'model-1', name: 'Local', model: 'qwen' }]
  let global: { plugins: Awaited<ReturnType<typeof testRouter>>[] }
  beforeEach(async () => {
    global = { plugins: [await testRouter('/chat/conv-1')] }
    mockDialogs()
  })

  it('trims and emits non-empty messages', async () => {
    const wrapper = mount(InputBox, {
      global,
      props: { sessionId: 'conv-1', modelId: 'model-1', modelOptions: configuredModel },
    })
    await wrapper.get('textarea').setValue('  hello  ')
    await wrapper.get('button[aria-label="发送消息"]').trigger('click')
    expect(wrapper.emitted('send')?.[0]).toEqual(['hello'])
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe('')
  })

  it('sends with Enter but keeps Shift+Enter for a new line', async () => {
    const wrapper = mount(InputBox, {
      global,
      props: { sessionId: 'conv-1', modelId: 'model-1', modelOptions: configuredModel },
    })
    const textarea = wrapper.get('textarea')

    await textarea.setValue('first line')
    await textarea.trigger('keydown', { key: 'Enter', shiftKey: true })
    expect(wrapper.emitted('send')).toBeUndefined()

    await textarea.trigger('keydown', { key: 'Enter' })
    expect(wrapper.emitted('send')?.[0]).toEqual(['first line'])
  })

  it('uses the configured assistant name in its placeholder', () => {
    const wrapper = mount(InputBox, {
      global,
      props: {
        sessionId: 'conv-1',
        assistantName: '小七',
        modelId: 'model-1',
        modelOptions: configuredModel,
      },
    })
    expect(wrapper.get('textarea').attributes('placeholder')).toBe('问问 小七…')
  })

  it('does not put execution progress in the composer while sending', () => {
    const wrapper = mount(InputBox, {
      global,
      props: {
        sessionId: 'conv-1',
        assistantName: '小七',
        isSending: true,
        modelId: 'model-1',
        modelOptions: configuredModel,
      },
    })
    expect(wrapper.get('textarea').attributes('placeholder')).toBe('问问 小七…')
    expect(wrapper.get('.composer').attributes('aria-busy')).toBe('true')
    expect(wrapper.get('.composer').text()).not.toContain('思考')
  })

  it('turns the send control into an explicit stop action while running', async () => {
    const wrapper = mount(InputBox, {
      global,
      props: {
        sessionId: 'conv-1',
        isSending: true,
        modelId: 'model-1',
        modelOptions: configuredModel,
      },
    })
    const button = wrapper.get('button[aria-label="停止任务"]')
    expect(button.attributes('aria-label')).toBe('停止任务')
    await button.trigger('click')
    expect(wrapper.emitted('cancel')).toHaveLength(1)
  })

  it('emits model, speed and approval-mode choices', async () => {
    const wrapper = mount(InputBox, {
      global,
      props: { sessionId: 'conv-1', modelId: 'model-1', modelOptions: [...configuredModel, { id: 'model-2', name: 'Cloud', model: 'other' }] },
    })
    await wrapper.get('[aria-haspopup="dialog"]').trigger('click')
    await flushPromises()
    const dialog = document.querySelector('dialog[aria-label="选择对话模型"]') as HTMLDialogElement
    expect(dialog.open).toBe(true)
    const option = [...dialog.querySelectorAll<HTMLButtonElement>('[role="option"]')].find(item => item.textContent?.includes('other'))!
    expect(option).toBeDefined()
    option.click()
    await flushPromises()
    expect(dialog.open).toBe(false)
    await wrapper.get('select[aria-label="响应速度"]').setValue('fast')
    await wrapper.get('select[aria-label="执行权限"]').setValue('workspace')
    expect(wrapper.emitted('model-change')?.[0]).toEqual(['model-2'])
    expect(wrapper.emitted('response-mode-change')?.[0]).toEqual(['fast'])
    expect(wrapper.emitted('permission-mode-change')?.[0]).toEqual(['workspace'])
  })
})
