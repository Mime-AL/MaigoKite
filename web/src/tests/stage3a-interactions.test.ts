import { mount, flushPromises } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import InputBox from '@/components/chat-area/InputBox.vue'
import SupplementMessage from '@/components/chat-area/SupplementMessage.vue'
import QueuedMessages from '@/components/chat-area/QueuedMessages.vue'
import JobsTab from '@/components/drawer/JobsTab.vue'
import PlanTab from '@/components/drawer/PlanTab.vue'
import { useUIStore } from '@/stores/ui'
import { useSessionStore } from '@/stores/session'
import { useRunStore } from '@/stores/run'
import { api } from '@/api/client'
const models = [{ id: 'm', name: 'Local', model: 'local' }]
const global = { plugins: [createRouter({ history: createMemoryHistory(), routes: [{ path: '/', component: { template: '<div />' } }] })], stubs: { ModelPicker: true, ComposerStats: true, ModePill: true, SubagentSettings: true, MentionMenu: true, SlashMenu: true } }
describe('3a composer and drawer interactions', () => {
  it('guides with Enter, queues with Alt+Enter, and cancels only with Esc', async () => {
    const submit = vi.fn().mockResolvedValue(undefined)
    const wrapper = mount(InputBox, { props: { sessionId: 'c', isSending: true, modelOptions: models, submit }, global })
    await wrapper.get('textarea').setValue('read only')
    await wrapper.get('textarea').trigger('keydown', { key: 'Enter' })
    await flushPromises()
    expect(submit).toHaveBeenLastCalledWith('read only', 'guide')
    expect(wrapper.emitted('cancel')).toBeUndefined()
    await wrapper.get('textarea').setValue('later')
    await wrapper.get('textarea').trigger('keydown', { key: 'Enter', altKey: true })
    await flushPromises()
    expect(submit).toHaveBeenLastCalledWith('later', 'later')
    await wrapper.get('textarea').trigger('keydown', { key: 'Escape' })
    expect(wrapper.emitted('cancel')).toHaveLength(1)
  })
  it('retains the draft until acknowledgement and on 4xx refusal', async () => {
    let reject: (reason: Error) => void = () => {}
    const submit = vi.fn().mockImplementation(() => new Promise<void>((_resolve, fail) => { reject = fail }))
    const wrapper = mount(InputBox, { props: { sessionId: 'c', isSending: true, modelOptions: models, submit }, global })
    await wrapper.get('textarea').setValue('do not lose me')
    await wrapper.get('textarea').trigger('keydown', { key: 'Enter' })
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe('do not lose me')
    reject(new Error('too many pending messages'))
    await flushPromises()
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe('do not lose me')
    expect(wrapper.get('[role="alert"]').text()).toContain('too many')
  })
  it('does not erase a newer draft when an older submission succeeds', async () => {
    let resolve: () => void = () => {}
    const submit = vi.fn().mockImplementation(() => new Promise<void>(done => { resolve = done }))
    const wrapper = mount(InputBox, { props: { sessionId: 'c', isSending: true, modelOptions: models, submit }, global })
    await wrapper.get('textarea').setValue('original')
    await wrapper.get('textarea').trigger('keydown', { key: 'Enter' })
    await wrapper.get('textarea').setValue('new draft')
    resolve(); await flushPromises()
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe('new draft')
  })
  it('disables steering while waiting but leaves send later available', async () => {
    const submit = vi.fn().mockResolvedValue(undefined)
    const wrapper = mount(InputBox, { props: { sessionId: 'c', isSending: true, waiting: true, guideReason: '请先处理审批', modelOptions: models, submit }, global })
    await wrapper.get('textarea').setValue('later')
    await wrapper.get('textarea').trigger('keydown', { key: 'Enter' })
    expect(submit).not.toHaveBeenCalled()
    expect((wrapper.get('textarea').element as HTMLTextAreaElement).value).toBe('later')
    await wrapper.get('textarea').trigger('keydown', { key: 'Enter', altKey: true })
    await flushPromises()
    expect(submit).toHaveBeenCalledWith('later', 'later')
  })
  it('explicitly shows unused input with a new-message action and no automatic resend', async () => {
    const resend = vi.fn().mockResolvedValue(undefined)
    const wrapper = mount(SupplementMessage, { props: { input: { id: 'i', task_id: 't', content: 'late', status: 'not_consumed', created_at: 'now' }, canResend: true, resend } })
    expect(wrapper.text()).toContain('本轮未采用')
    expect(wrapper.get('button').text()).toBe('作为新回合发送')
    expect(resend).not.toHaveBeenCalled()
    await wrapper.get('button').trigger('click'); await flushPromises()
    expect(resend).toHaveBeenCalledTimes(1)
  })
  it('keeps queued edits cancellable and exposes remove and guide actions', async () => {
    const wrapper = mount(QueuedMessages, { props: { items: [{ id: 'q', content: 'original' }], paused: false, guideReason: '', canContinue: false, guide: vi.fn().mockResolvedValue(undefined) } })
    await wrapper.findAll('button').find(button => button.text() === '编辑')!.trigger('click')
    await wrapper.get('textarea').setValue('edited')
    await wrapper.findAll('button').find(button => button.text() === '保存')!.trigger('click')
    expect(wrapper.emitted('edit')?.[0]).toEqual(['q', 'edited'])
    await wrapper.findAll('button').find(button => button.text() === '移除')!.trigger('click')
    expect(wrapper.emitted('remove')?.[0]).toEqual([0])
  })
  it('uses real jobs and collapses historical runs without exposing the full input', async () => {
    const ui = useUIStore(), session = useSessionStore()
    ui.drawerOpen = true; ui.drawerTab = 'jobs'; session.activeSessionId = 'c'; session.capabilities.process_list = true
    vi.spyOn(api, 'listTasks').mockResolvedValue([{ id: 't', workspace_id: 'personal', conversation_id: 'c', title: 'Finished', input_text: 'full historical text must stay in chat', status: 'succeeded', version: 1, last_error: '', created_at: '2026-10-11T00:00:00Z', updated_at: '2026-10-11T00:00:01Z' }])
    vi.spyOn(api, 'listJobs').mockResolvedValue([{ id: 'j', task_id: 't', conversation_id: 'c', command: 'echo actual', status: 'completed', log_tail: 'actual output', live: false, live_logs_available: false, stdin_available: false }])
    const wrapper = mount(JobsTab)
    await flushPromises()
    expect(wrapper.get('details').attributes('open')).toBeUndefined()
    expect(wrapper.text()).not.toContain('full historical text')
    expect(wrapper.text()).toContain('echo actual')
    wrapper.unmount()
  })
  it('renders a genuine plan empty state instead of invented steps', () => {
    useSessionStore().activeSessionId = 'c'
    useRunStore().markStarted('c', 't')
    const wrapper = mount(PlanTab)
    expect(wrapper.text()).toContain('还没有执行计划')
    expect(wrapper.findAll('li')).toHaveLength(0)
  })
  it('closes the send menu with Esc without stopping the task', async () => {
    const wrapper = mount(InputBox, { props: { sessionId: 'c', isSending: true, modelOptions: models, submit: vi.fn() }, global })
    await wrapper.get('[aria-label="发送选项"]').trigger('click')
    expect(wrapper.find('.send-options-menu').exists()).toBe(true)
    await wrapper.get('.send-options button').trigger('keydown', { key: 'Escape' })
    expect(wrapper.find('.send-options-menu').exists()).toBe(false)
    expect(wrapper.emitted('cancel')).toBeUndefined()
  })
})
