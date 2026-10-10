import { realpathSync } from 'node:fs'
import path from 'node:path'

/** Resolve an ID through the local Gateway; never trust a renderer-supplied root. */
export async function registeredWorkspaceRoot(folderId: string): Promise<string> {
  const base = new URL(process.env.MAIGOKITE_GATEWAY_URL || 'http://127.0.0.1:8080')
  if (
    !['http:', 'https:'].includes(base.protocol) ||
    !['127.0.0.1', 'localhost', '[::1]'].includes(base.hostname) ||
    base.username ||
    base.password
  )
    throw new Error('本机文件打开功能只支持本地 Gateway。')
  const response = await fetch(new URL('/api/v1/workspaces/personal/folders', base), {
    signal: AbortSignal.timeout(5000),
    redirect: 'error',
  })
  if (!response.ok) throw new Error('无法确认工作区，请检查本地服务。')
  const data: unknown = await response.json()
  const folders =
    data && typeof data === 'object' ? (data as Record<string, unknown>).folders : undefined
  if (!Array.isArray(folders)) throw new Error('工作区信息不正确。')
  for (const value of folders as unknown[]) {
    if (!value || typeof value !== 'object') continue
    const item = value as Record<string, unknown>
    if (
      (item.id === undefined ? '' : item.id) !== folderId ||
      typeof item.root_path !== 'string' ||
      !path.isAbsolute(item.root_path)
    )
      continue
    const root = realpathSync(item.root_path)
    if (root !== item.root_path) throw new Error('工作区路径已变更，请重新选择文件夹。')
    return root
  }
  throw new Error('工作区不存在，请重新选择文件夹。')
}
