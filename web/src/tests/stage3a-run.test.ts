import { describe, expect, it } from 'vitest'
import { useRunStore } from '@/stores/run'
import { remainingMessages } from '@/stores/session-projection'
import type { AgentTask, TaskInput } from '@/api/client'
const task: AgentTask = { id: 't', conversation_id: 'c', workspace_id: 'personal', title: 'Read', input_text: 'same', status: 'running', version: 1, last_error: '', created_at: '2026-10-11T00:00:00Z', updated_at: '2026-10-11T00:00:00Z' }
const input: TaskInput = { id: 'i', task_id: 't', content: 'same', status: 'queued', created_at: task.created_at }
describe('3a run projections', () => {
  it('never regresses consumed when queued events or POST receipts arrive late', () => {
    const run = useRunStore()
    run.apply({ seq: 10, sessionId: 'c', turnId: 't', type: 'input_update', input: { ...input, status: 'consumed' } })
    run.apply({ seq: 9, sessionId: 'c', turnId: 't', type: 'input_update', input })
    run.mergeInput('c', input)
    expect(run.getTurn('c', 't').inputs).toHaveLength(1)
    expect(run.getTurn('c', 't').inputs?.[0].status).toBe('consumed')
  })
  it('keeps same-text inputs separate and removes only their persisted IDs', () => {
    const run = useRunStore()
    run.markStarted('c', 't', 'original')
    run.mergeInput('c', { ...input, status: 'consumed' })
    run.mergeInput('c', { ...input, id: 'i2', status: 'consumed' })
    const messages = ['i', 'i2', 'unrelated'].map(id => ({ id, conversation_id: 'c', role: 'user' as const, content: 'same', created_at: task.created_at }))
    expect(remainingMessages(messages, [run.getTurn('c', 't')]).map(m => m.id)).toEqual(['unrelated'])
  })
  it('does not let a GET started earlier overwrite a newer event', () => {
    const run = useRunStore()
    run.mergeInput('c', input, 3)
    const cursor = run.inputReadSequence('c', 't')
    run.mergeInput('c', { ...input, status: 'consumed' }, 7)
    run.hydrateInputs('c', 't', [{ ...input, status: 'not_consumed' }], cursor)
    expect(run.getTurn('c', 't').inputs?.[0].status).toBe('consumed')
  })
  it('restores not_consumed and never fabricates it from a task terminal event', () => {
    const run = useRunStore()
    run.mergeInput('c', input)
    run.apply({ seq: 9, sessionId: 'c', turnId: 't', type: 'turn_end', status: 'completed' })
    expect(run.getTurn('c', 't').inputs?.[0].status).toBe('queued')
    run.hydrateInputs('c', 't', [{ ...input, status: 'not_consumed' }], 0)
    expect(run.getTurn('c', 't').inputs?.[0].status).toBe('not_consumed')
    run.markInputSent('c', 't', 'i', 'new-task')
    expect(run.getTurn('c', 't').inputs?.[0].sentAsTaskId).toBe('new-task')
  })
  it('whole-replaces the latest plan, rejects stale history and keeps tasks isolated', () => {
    const run = useRunStore()
    const base = { sessionId: 'c', turnId: 't', type: 'plan_update' as const }
    run.apply({ ...base, seq: 4, items: [{ content: 'old', status: 'pending' }] })
    run.apply({ ...base, seq: 8, items: [{ content: 'new', status: 'completed' }] })
    run.apply({ ...base, seq: 6, items: [{ content: 'stale', status: 'pending' }] })
    expect(run.getTurn('c', 't').plan).toEqual([{ content: 'new', status: 'completed' }])
    expect(run.getTurn('c', 'next').plan).toEqual([])
    run.apply({ ...base, seq: 9, items: [] })
    expect(run.getTurn('c', 't').plan).toEqual([])
  })
  it('restores inspection plans without letting an older inspection erase live state', () => {
    const run = useRunStore()
    run.hydrateTask('c', task, undefined, 20)
    run.hydratePlan('c', { task, projection: { plan: [{ content: 'restored', status: 'in_progress' }], truncated: false }, last_sequence: 20 })
    run.apply({ seq: 21, sessionId: 'c', turnId: 't', type: 'plan_update', items: [{ content: 'live', status: 'completed' }] })
    run.hydratePlan('c', { task, projection: { plan: null, truncated: false }, last_sequence: 20 })
    expect(run.getTurn('c', 't').plan[0].content).toBe('live')
    run.hydratePlan('c', { task, projection: { plan: null, truncated: true }, last_sequence: 22 })
    expect(run.getTurn('c', 't').plan[0].content).toBe('live')
  })
})
