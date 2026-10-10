import type { AgentEvent } from './client'

export interface Playback {
  emit: (type: string, payload: Record<string, unknown>) => void
  wait: (delay: number, action: () => void) => void
  approval: (resume: () => void) => void
  remember: () => void
  finish: (content: string) => void
}
export function playTask(playback: Playback) {
  const { emit, wait } = playback
  wait(200, () => emit('reasoning.delta', { content: '先看看现有资料，再把下一步写下来。' }))
  const files = ['README.md', 'notes/ideas.md', 'notes/preferences.md']
  files.forEach((path, index) => {
    wait(700 + index * 700, () =>
      emit('tool.started', { tool_call_id: `read-${index}`, tool_name: 'file_read', arguments: { path } }),
    )
    wait(1000 + index * 700, () =>
      emit('tool.completed', {
        tool_call_id: `read-${index}`,
        tool_name: 'file_read',
        data: { content: `# ${path}\n已经读取，与当前任务相关的内容保留在上下文里。`, duration_ms: 300 },
      }),
    )
  })
  wait(2900, () =>
    emit('tool.started', { tool_call_id: 'command', tool_name: 'bash', arguments: { command: 'git status --short' } }),
  )
  wait(3300, () =>
    emit('tool.completed', {
      tool_call_id: 'command',
      tool_name: 'bash',
      data: { stdout: '工作区没有未提交变更。', return_code: 0, duration_ms: 400 },
    }),
  )
  wait(3700, () =>
    playback.approval(() => {
      emit('tool.started', {
        tool_call_id: 'write',
        tool_name: 'file_write',
        arguments: { path: 'notes/next-step.md', content: '# 下一步\n把想法整理成一个可执行的小目标。' },
      })
      wait(400, () => {
        emit('tool.completed', {
          tool_call_id: 'write',
          tool_name: 'file_write',
          data: { content: '已写入 notes/next-step.md', duration_ms: 400 },
        })
        emit('file.changed', {
          path: 'notes/next-step.md',
          diff: '+++ b/notes/next-step.md\n@@ -0,0 +1,2 @@\n+# 下一步\n+把想法整理成一个可执行的小目标。',
        })
      })
      wait(850, () => playback.remember())
      const answer = '已经整理好资料，并把下一步写进 `notes/next-step.md`。\n\n从一个小目标开始，完成后再继续。'
      answer
        .match(/.{1,8}|\n/g)
        ?.forEach((text, index) => wait(1200 + index * 75, () => emit('message.delta', { content: text })))
      wait(3000, () => playback.finish(answer))
    }),
  )
}
export function mockEnvelope(
  sessionId: string,
  turnId: string,
  sequence: number,
  type: string,
  payload: Record<string, unknown>,
): AgentEvent {
  return {
    schema_version: 1,
    event_id: `${sessionId}-${sequence}`,
    sequence,
    type,
    conversation_id: sessionId,
    task_id: turnId,
    occurred_at: new Date().toISOString(),
    payload,
  }
}
