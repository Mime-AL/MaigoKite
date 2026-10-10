import { t } from '@/i18n'
import type { AwaitItem } from '@/api/events'
import type { Approval } from '@/api/client'
/** Describes known effects, never authorizes a tool or predicts arbitrary code. */
export function approvalDescription(item: AwaitItem, record?: Approval) {
  let input: Record<string, unknown> = record?.arguments || {}
  if (!record) {
    try { const value: unknown = JSON.parse(item.detail); if (value && typeof value === 'object' && !Array.isArray(value)) input = value as Record<string, unknown> }
    catch { /* Plain resource scopes are kept as targets, not parsed as commands. */ }
  }
  const tool = record?.tool_name || item.title.split(' ').slice(-1)[0] || ''
  const descriptions: Record<string, [string, string]> = {
    file_write: ['写入文件', '将更改目标文件的内容。'],
    file_edit: ['修改文件', '将更改目标文件的内容。'],
    file_read: ['读取文件', '读取内容，不修改文件。'],
    bash: ['运行命令', '将在目标目录运行命令。'],
    exec_command: ['运行命令', '将在目标目录运行命令。'],
    browser: ['浏览器操作', '操作目标页面，可能改变页面状态。'],
  }
  const descriptor = descriptions[tool]
  const target = [input.path, input.cwd, input.url, record?.resource_scope]
    .find(value => typeof value === 'string' && value.trim())
  return { action: descriptor ? t(descriptor[0]) : t('执行操作'),
    target: typeof target === 'string' ? target : t('未指定目标'),
    impact: descriptor ? t(descriptor[1]) : t('请查看操作详情，确认后继续。'),
    tool, command: typeof input.command === 'string' ? input.command : '' }
}
