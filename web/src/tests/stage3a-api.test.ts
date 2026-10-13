import { afterEach, describe, expect, it, vi } from 'vitest'
import { api } from '@/api/client'
import { mapGatewayEvent } from '@/api/event-adapter'

afterEach(() => { vi.unstubAllGlobals() })
describe('3a API and event contracts', () => {
  it('POSTs an input with its idempotency key and reads the same resource', async () => {
    const input = { id: 'input_1', task_id: 'task/1', content: 'keep it', status: 'queued', created_at: 'now' }
    const fetch = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify(input), { status: 202 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ inputs: [input] })))
    vi.stubGlobal('fetch', fetch)
    expect(await api.submitTaskInput('task/1', 'keep it', 'logical-key')).toEqual(input)
    expect(fetch.mock.calls[0][0]).toContain('/tasks/task%2F1/inputs')
    expect(new Headers(fetch.mock.calls[0][1].headers).get('Idempotency-Key')).toBe('logical-key')
    expect(fetch.mock.calls[0][1].body).toBe(JSON.stringify({ content: 'keep it' }))
    expect(await api.listTaskInputs('task/1')).toEqual([input])
  })
  it('preserves definitive 4xx failures rather than accepting an input', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: { code: 'CONFLICT', message: 'too many pending messages' } }), { status: 409 })))
    await expect(api.submitTaskInput('task', 'text', 'key')).rejects.toMatchObject({ status: 409, code: 'CONFLICT' })
  })
  it('reads real inspection and process records', async () => {
    const fetch = vi.fn().mockResolvedValueOnce(new Response(JSON.stringify({ task: { id: 't' }, projection: { plan: [], truncated: false }, last_sequence: 9 })))
      .mockResolvedValueOnce(new Response(JSON.stringify({ jobs: [{ id: 'j', live: true }] })))
    vi.stubGlobal('fetch', fetch)
    expect((await api.getTaskInspection('t')).last_sequence).toBe(9)
    expect(await api.listJobs('c/1')).toEqual([{ id: 'j', live: true }])
    expect(fetch.mock.calls[1][0]).toContain('/jobs?conversation_id=c%2F1')
  })
  it('maps input receipts with their task, input ID, sequence and time', () => {
    const event = { schema_version: 1, event_id: 'e', sequence: 7, conversation_id: 'c', task_id: 't', occurred_at: '2026-10-11T00:00:00Z', type: 'task.input.consumed', payload: { input_id: 'i', content: 'read only' } }
    expect(mapGatewayEvent(event)).toEqual([expect.objectContaining({ type: 'input_update', seq: 7, turnId: 't', input: { id: 'i', task_id: 't', content: 'read only', status: 'consumed', created_at: event.occurred_at } })])
    expect(mapGatewayEvent({ ...event, type: 'task.input.queued' })[0]).toMatchObject({ input: { status: 'queued' } })
  })
  it('maps valid plans, including explicit clearing, but rejects malformed ones', () => {
    const base = { schema_version: 1, event_id: 'p', sequence: 8, conversation_id: 'c', task_id: 't', type: 'plan.updated' }
    expect(mapGatewayEvent({ ...base, payload: { items: [{ content: 'read', status: 'pending' }] } })[0]).toMatchObject({ type: 'plan_update', items: [{ content: 'read', status: 'pending' }] })
    expect(mapGatewayEvent({ ...base, payload: { items: [] } })[0]).toMatchObject({ items: [] })
    expect(mapGatewayEvent({ ...base, payload: { items: [{ content: 'bad', status: 'invented' }] } })).toEqual([])
  })
})
