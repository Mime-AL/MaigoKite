import type { AgentActivityGroup, AgentActivityItem, AgentEvent, ChatMessage } from '@/api/client'
import type { Turn } from '@/api/events'

export function remainingMessages(messages: ChatMessage[], turns: Turn[]) {
  const knownIds = new Set(turns.flatMap((t) => [t.messageId, `stream-${t.id}`]).filter(Boolean))
  const counts = new Map<string, number>()
  for (const turn of turns)
    for (const [role, content] of [
      ['user', turn.userText],
      ['assistant', turn.text],
    ]) {
      if (content) {
        const key = `${role}:${content}`
        counts.set(key, (counts.get(key) || 0) + 1)
      }
    }
  return messages.filter((message) => {
    if (!['user', 'assistant'].includes(message.role)) return false
    const key = `${message.role}:${message.content}`,
      count = counts.get(key) || 0
    if (count || knownIds.has(message.id)) {
      if (count) counts.set(key, count - 1)
      return false
    }
    return true
  })
}

export function projectMessage(list: ChatMessage[], event: AgentEvent, replay: boolean) {
  const streamId = `stream-${event.task_id || ''}`,
    content = String(event.payload.content || '')
  if (event.type === 'message.delta' && !replay && content) {
    const item = list.find((m) => m.id === streamId)
    if (item) item.content += content
    else
      list.push({
        id: streamId,
        conversation_id: event.conversation_id,
        role: 'assistant',
        content,
        created_at: event.occurred_at || new Date().toISOString(),
        streaming: true,
      })
  }
  if (event.type !== 'message.completed') return
  const streamed = list.find((m) => m.id === streamId)
  const messageId = String(event.payload.message_id || streamId)
  const persisted =
    list.find((m) => m.id === messageId) ||
    (replay && content ? list.find((m) => m.role === 'assistant' && m.content === content) : undefined)
  if (streamed && persisted && streamed !== persisted) list.splice(list.indexOf(streamed), 1)
  else if (streamed) {
    streamed.id = messageId
    streamed.streaming = false
    if (content) streamed.content = content
  } else if (!persisted && content)
    list.push({
      id: messageId,
      conversation_id: event.conversation_id,
      role: 'assistant',
      content,
      created_at: event.occurred_at || new Date().toISOString(),
    })
}
export function activityGroups(turns: Turn[]): AgentActivityGroup[] {
  return turns.map((turn) => {
    const items: AgentActivityItem[] = turn.steps.map((step, index) => ({
      id: step.id,
      task_id: turn.id,
      kind: 'tool',
      status: step.status,
      title: step.tool,
      summary: step.title,
      detail: { arguments: step.input, result: step.output },
      hint: step.hint,
      sequence: index,
      created_at: new Date(turn.startedAt).toISOString(),
    }))
    if (turn.thinking)
      items.unshift({
        id: `thinking-${turn.id}`,
        task_id: turn.id,
        kind: 'reasoning',
        status: turn.status === 'running' ? 'running' : 'completed',
        title: '过程说明',
        summary: turn.thinking,
        sequence: -1,
        created_at: new Date(turn.startedAt).toISOString(),
      })
    return { task_id: turn.id, status: turn.status === 'waiting' ? 'waiting_approval' : turn.status, items }
  })
}
