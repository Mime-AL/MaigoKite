import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises } from '@vue/test-utils'
import { api, type AgentEvent, type AgentTask, type Conversation } from '@/api/client'
import { GatewayError } from '@/api/http'
import { useSessionStore } from '@/stores/session'
import { useRunStore } from '@/stores/run'
const task: AgentTask = { id: 't', conversation_id: 'c', workspace_id: 'personal', title: 'Read', input_text: 'read files', status: 'running', version: 1, last_error: '', created_at: '2026-10-11T00:00:00Z', updated_at: '2026-10-11T00:00:00Z' }
const conversation: Conversation = { id: 'c', workspace_id: 'personal', title: 'Chat', model_id: 'm', permission_mode: 'workspace', response_mode: 'balanced', created_at: task.created_at, updated_at: task.updated_at, message_count: 0 }
const input = { id: 'i', task_id: 't', content: 'read only', status: 'queued' as const, created_at: task.created_at }
let receive: (event: AgentEvent) => void
beforeEach(() => {
  vi.spyOn(api, 'getConversation').mockResolvedValue(conversation)
  vi.spyOn(api, 'getConversationSnapshot').mockResolvedValue({ messages: [], tasks: [task], approvals: [], questions: [], last_sequence: 0, truncated: false })
  vi.spyOn(api, 'getCapabilities').mockResolvedValue({ task_input: true, structured_plan: true, task_inspection: true })
  vi.spyOn(api, 'listTaskInputs').mockResolvedValue([])
  vi.spyOn(api, 'getTaskInspection').mockResolvedValue({ task, projection: { plan: null, truncated: false }, last_sequence: 0 })
  vi.spyOn(api, 'listTaskEvents').mockResolvedValue([])
  vi.spyOn(api, 'connectEvents').mockImplementation((_id, callback) => { receive = callback; return { close: vi.fn(), readyState: 1 } as unknown as WebSocket })
  vi.spyOn(api, 'submitTaskInput').mockResolvedValue(input)
})
afterEach(() => { useSessionStore().disconnect() })
async function ready() {
  const session = useSessionStore()
  await session.switchSession('c')
  session.runningTaskIds.c = ['t']
  useRunStore().setConnection('c', true)
  return session
}
describe('3a session inputs and restoration', () => {
  it('submits immediately, not to the next-turn queue', async () => {
    const session = await ready()
    await session.guideTask('c', 'read only')
    expect(api.submitTaskInput).toHaveBeenCalledWith('t', 'read only', expect.any(String))
    expect(session.queuedMessages.c || []).toEqual([])
    expect(useRunStore().getTurn('c', 't').inputs?.[0]).toMatchObject(input)
  })
  it('blocks waiting approvals while still accepting an explicit later message', async () => {
    const session = await ready(), run = useRunStore()
    run.hydrateTask('c', { ...task, status: 'waiting_approval' }, undefined, 1)
    await expect(session.guideTask('c', 'change course')).rejects.toThrow('请先处理审批')
    expect(api.submitTaskInput).not.toHaveBeenCalled()
    session.queueMessage('c', 'later')
    expect(session.queuedMessages.c[0].content).toBe('later')
  })
  it('rejects queued tasks until a real task.started event arrives', async () => {
    vi.mocked(api.getConversationSnapshot).mockResolvedValue({ messages: [], tasks: [{ ...task, status: 'queued' }], approvals: [], questions: [], last_sequence: 0, truncated: false })
    const session = await ready()
    await expect(session.guideTask('c', 'guide')).rejects.toThrow('任务运行后')
    expect(api.submitTaskInput).not.toHaveBeenCalled()
    receive({ schema_version: 1, event_id: 'ready', sequence: 0, conversation_id: 'c', type: 'stream.ready', payload: {} })
    await flushPromises()
    receive({ schema_version: 1, event_id: 'started', sequence: 1, conversation_id: 'c', task_id: 't', type: 'task.started', payload: {} })
    await session.guideTask('c', 'guide')
    expect(api.submitTaskInput).toHaveBeenCalledTimes(1)
  })
  it('merges live queued and consumed receipts before a delayed POST acknowledgement', async () => {
    const session = await ready(), run = useRunStore()
    receive({ schema_version: 1, event_id: 'ready', sequence: 0, conversation_id: 'c', type: 'stream.ready', payload: {} })
    await flushPromises()
    const base = { schema_version: 1, conversation_id: 'c', task_id: 't', occurred_at: task.created_at, payload: { input_id: 'i', content: input.content } }
    receive({ ...base, type: 'task.input.queued', event_id: 'queued', sequence: 1 })
    receive({ ...base, type: 'task.input.consumed', event_id: 'consumed', sequence: 2 })
    await session.guideTask('c', input.content)
    expect(run.getTurn('c', 't').inputs).toHaveLength(1)
    expect(run.getTurn('c', 't').inputs?.[0].status).toBe('consumed')
    expect(session.runningTaskIds.c).toEqual(['t'])
  })
  it('counts only queued inputs towards 20 and leaves server refusal visible', async () => {
    const session = await ready(), run = useRunStore()
    for (let i = 0; i < 20; i++) run.mergeInput('c', { ...input, id: `i${i}` })
    await expect(session.guideTask('c', 'extra')).rejects.toThrow('20 条')
    expect(api.submitTaskInput).not.toHaveBeenCalled()
    run.mergeInput('c', { ...input, id: 'i0', status: 'consumed' })
    vi.mocked(api.submitTaskInput).mockRejectedValueOnce(new GatewayError('too many pending messages', 409, 'CONFLICT'))
    await expect(session.guideTask('c', 'extra')).rejects.toThrow('too many')
    expect(session.inputErrors.c).toContain('too many')
    expect(session.inputSubmissions.t).toBeUndefined()
  })
  it('retains the same idempotency key after an ambiguous transport failure', async () => {
    const session = await ready()
    vi.mocked(api.submitTaskInput).mockRejectedValueOnce(new GatewayError('timeout'))
    await expect(session.guideTask('c', 'read only')).rejects.toThrow('timeout')
    const key = session.inputSubmissions.t.key
    expect(session.inputSubmissions.t.uncertain).toBe(true)
    await session.confirmInputSubmission('c', 't')
    expect(vi.mocked(api.submitTaskInput).mock.calls.map(call => call[2])).toEqual([key, key])
    expect(session.inputSubmissions.t).toBeUndefined()
  })
  it('edits and removes later messages and removes guided ones only on acceptance', async () => {
    const session = await ready()
    session.queueMessage('c', 'old')
    const id = session.queuedMessages.c[0].id
    session.editQueued('c', id, 'edited')
    vi.mocked(api.submitTaskInput).mockRejectedValueOnce(new GatewayError('refused', 409))
    await expect(session.guideQueued('c', id)).rejects.toThrow('refused')
    expect(session.queuedMessages.c[0].content).toBe('edited')
    await session.guideQueued('c', id)
    expect(session.queuedMessages.c).toEqual([])
    session.queueMessage('c', 'remove'); session.removeQueued('c', 0)
    expect(session.queuedMessages.c).toEqual([])
  })
  it('restores plans and not_consumed input through refreshSnapshot supplementary reads', async () => {
    const session = await ready()
    vi.mocked(api.getConversationSnapshot).mockResolvedValue({ messages: [{ id: 'i', conversation_id: 'c', role: 'user', content: 'read only', created_at: task.created_at }], tasks: [{ ...task, status: 'succeeded' }], approvals: [], questions: [], last_sequence: 20, truncated: false })
    vi.mocked(api.listTaskInputs).mockResolvedValue([{ ...input, status: 'not_consumed' }])
    vi.mocked(api.getTaskInspection).mockResolvedValue({ task, projection: { plan: [{ content: 'restored', status: 'completed' }], truncated: false }, last_sequence: 20 })
    await session.refreshSnapshot('c')
    const turn = useRunStore().getTurn('c', 't')
    expect(turn.plan).toEqual([{ content: 'restored', status: 'completed' }])
    expect(turn.inputs?.[0].status).toBe('not_consumed')
    expect(session.isSending).toBe(false)
  })
  it('keeps a failed reconciliation unknown and exposes retry', async () => {
    const session = await ready()
    vi.mocked(api.listTaskInputs).mockRejectedValueOnce(new GatewayError('offline'))
    await session.refreshTaskDetails('c', 't')
    expect(useRunStore().getTurn('c', 't').inputsError).toContain('未确认')
    await session.refreshTaskDetails('c', 't')
    expect(useRunStore().getTurn('c', 't').inputsError).toBe('')
  })
  it('uses the normal message endpoint only after explicit resend and refuses a running task', async () => {
    const session = await ready(), run = useRunStore()
    run.mergeInput('c', { ...input, status: 'not_consumed' })
    const send = vi.spyOn(api, 'sendMessage').mockResolvedValue({ task_id: 'new-t', status: 'succeeded' })
    await expect(session.resendInput('c', 't', 'i')).rejects.toThrow('当前任务结束后')
    expect(send).not.toHaveBeenCalled()
    session.runningTaskIds.c = []
    await session.resendInput('c', 't', 'i')
    await session.resendInput('c', 't', 'i')
    expect(send).toHaveBeenCalledTimes(1)
    expect(run.getTurn('c', 't').inputs?.[0].sentAsTaskId).toBe('new-t')
  })
  it('never interprets a supplement as cancellation', async () => {
    const session = await ready()
    const cancel = vi.spyOn(api, 'cancelTask')
    await session.guideTask('c', 'stop modifying files; explain instead')
    expect(cancel).not.toHaveBeenCalled()
  })
  it('confirms an ambiguous resend with the same key and closes the original action', async () => {
    const session = await ready(), run = useRunStore()
    session.runningTaskIds.c = []
    run.mergeInput('c', { ...input, status: 'not_consumed' })
    const send = vi.spyOn(api, 'sendMessage').mockRejectedValueOnce(new GatewayError('timeout'))
      .mockResolvedValueOnce({ task_id: 'new-t', status: 'succeeded', replayed: true })
    await expect(session.resendInput('c', 't', 'i')).rejects.toThrow('timeout')
    const key = session.submissions.c.key
    await session.confirmSubmission('c')
    expect(send.mock.calls.map(call => call[2])).toEqual([key, key])
    expect(run.getTurn('c', 't').inputs?.[0].sentAsTaskId).toBe('new-t')
    session.runningTaskIds.c = []
    await session.resendInput('c', 't', 'i')
    expect(send).toHaveBeenCalledTimes(2)
  })
  it('bounds snapshot detail reads to recent input-bearing turns', async () => {
    const session = await ready(), run = useRunStore()
    for (let n = 0; n < 35; n++) {
      const historic = { ...task, id: `old-${n}`, status: 'succeeded' as const, created_at: new Date(1700000000000 + n * 1000).toISOString() }
      run.hydrateTask('c', historic)
      run.mergeInput('c', { ...input, id: `input-${n}`, task_id: historic.id, status: 'not_consumed' })
    }
    vi.mocked(api.listTaskInputs).mockClear()
    await session.refreshSnapshot('c')
    expect(api.listTaskInputs).toHaveBeenCalledTimes(20)
    expect(vi.mocked(api.listTaskInputs).mock.calls.map(call => call[0])).not.toContain('old-0')
  })
})
