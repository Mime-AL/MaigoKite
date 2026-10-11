import type { AgentEvent } from './client'

export interface Playback {
  emit: (type: string, payload: Record<string, unknown>) => void
  wait: (delay: number, action: () => void) => void
  approval: (resume: (allowed: boolean, note?: string) => void) => void
  remember: () => void
  finish: (content: string) => void
}
export function playTask(playback: Playback) {
  const { emit, wait } = playback
  wait(200, () => emit('reasoning.delta', { content: '正在阅读资料，确认计划。' }))
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
    playback.approval((allowed, note) => {
      if (!allowed) {
        emit('tool.failed', {
          tool_call_id: 'write', tool_name: 'file_write', error_code: 'APPROVAL_REJECTED',
          message: note ? `用户驳回本次写入：${note}` : '用户驳回本次写入，文件未修改。',
        })
        const answer = '未写入文件。你可以先在对话中查看下一步：整理资料，列出待办事项。'
        wait(400, () => emit('message.delta', { content: answer }))
        wait(800, () => playback.finish(answer))
        return
      }
      emit('tool.started', {
        tool_call_id: 'write',
        tool_name: 'file_write',
        arguments: { path: 'notes/next-step.md', content: '# 下一步\n整理资料，列出待办事项。' },
      })
      wait(400, () => {
        emit('tool.completed', {
          tool_call_id: 'write',
          tool_name: 'file_write',
          data: { content: '已写入 notes/next-step.md', duration_ms: 400 },
        })
        emit('file.changed', {
          path: 'notes/next-step.md',
          diff: '+++ b/notes/next-step.md\n@@ -0,0 +1,2 @@\n+# 下一步\n+整理资料，列出待办事项。',
        })
      })
      wait(850, () => playback.remember())
      const answer = '资料已整理，计划已保存到 `notes/next-step.md`。'
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
