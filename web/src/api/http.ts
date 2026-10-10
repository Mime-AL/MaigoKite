export const apiBase =
  import.meta.env.VITE_API_BASE_URL || (location.protocol === 'file:' ? 'http://127.0.0.1:8080' : '')
export const workspacePath = '/api/v1/workspaces/personal'
export class GatewayError extends Error {
  constructor(
    message: string,
    public readonly status = 0,
    public readonly code = 'NETWORK',
  ) {
    super(message)
    this.name = 'GatewayError'
  }
}
let bearer = ''
export function setAuthToken(token: string) {
  bearer = token
}
export async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController()
  const abort = () => controller.abort()
  init?.signal?.addEventListener('abort', abort, { once: true })
  if (init?.signal?.aborted) abort()
  const timeout = setTimeout(abort, 30_000)
  try {
    if (import.meta.env.VITE_MOCK === '1') return (await import('./mock')).mockRequest<T>(url, init)
    const headers = new Headers(init?.headers)
    headers.set('Content-Type', 'application/json')
    if (bearer) headers.set('Authorization', `Bearer ${bearer}`)
    const response = await fetch(`${apiBase}${url}`, { ...init, headers, signal: controller.signal })
    if (!response.ok) {
      const body: unknown = await response.json().catch(() => null)
      const error = body && typeof body === 'object' ? (body as Record<string, unknown>).error : null
      const detail = error && typeof error === 'object' ? (error as Record<string, unknown>) : {}
      const message =
        typeof error === 'string'
          ? error
          : typeof detail.message === 'string'
            ? detail.message
            : response.status === 404
              ? '当前应用版本缺少所需功能，请重启应用；若问题仍然存在，请更新或重新安装。'
              : `请求失败（${response.status}）`
      throw new GatewayError(message, response.status, String(detail.code || 'HTTP'))
    }
    return response.status === 204 ? (undefined as T) : ((await response.json()) as T)
  } catch (reason) {
    if (reason instanceof GatewayError) throw reason
    throw new GatewayError(
      controller.signal.aborted
        ? '请求超时或已取消，请重试。'
        : reason instanceof Error
          ? reason.message
          : '无法连接服务',
    )
  } finally {
    clearTimeout(timeout)
    init?.signal?.removeEventListener('abort', abort)
  }
}
