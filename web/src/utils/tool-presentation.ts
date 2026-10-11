import { t } from '@/i18n'
import type { AwaitItem } from '@/api/events'
import type { Approval } from '@/api/client'
/** Display the server's exact scope; never infer or broaden an authorization. */
export function approvalScopeDescription(scope: Record<string, unknown> = {}) {
  const lines: string[] = []
  if (typeof scope.tool === 'string') lines.push(t('工具：{0}', [scope.tool]))
  if (typeof scope.directory === 'string')
    lines.push(t(scope.recursive === false ? '目录：{0}（不含子目录）' : '目录：{0}', [scope.directory]))
  if (typeof scope.origin === 'string') lines.push(t('目标站点：{0}', [scope.origin]))
  if (typeof scope.engine === 'string') lines.push(t('搜索服务：{0}', [scope.engine]))
  if (Array.isArray(scope.argv)) lines.push(t('固定命令参数：{0}', [JSON.stringify(scope.argv)]))
  if (typeof scope.workdir === 'string') lines.push(t('执行目录：{0}', [scope.workdir]))
  if (typeof scope.workspace_root === 'string') lines.push(t('工作区：{0}', [scope.workspace_root]))
  return lines
}
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
