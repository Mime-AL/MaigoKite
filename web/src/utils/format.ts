import { i18n, t } from '@/i18n'
/**
 * 格式化工具函数
 *
 * 提供日期、数字、时长等通用格式化方法。
 */

/** 格式化日期时间 */
export function formatDateTime(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return d.toLocaleString(i18n.global.locale.value, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

/** 格式化相对时间（如 3 分钟前） */
export function formatRelativeTime(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffSec = Math.floor(diffMs / 1000)

  if (diffSec < 60) return t("刚刚")
  if (diffSec < 3600) return t("{0} 分钟前", [Math.floor(diffSec / 60)])
  if (diffSec < 86400) return t("{0} 小时前", [Math.floor(diffSec / 3600)])
  if (diffSec < 604800) return t("{0} 天前", [Math.floor(diffSec / 86400)])
  return formatDateTime(d)
}

/** 格式化持续时间（毫秒 -> 可读字符串） */
export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  const sec = Math.floor(ms / 1000)
  if (sec < 60) return `${sec}s`
  const min = Math.floor(sec / 60)
  const remainSec = sec % 60
  if (min < 60) return t("{0}分{1}秒", [min, remainSec])
  const hr = Math.floor(min / 60)
  const remainMin = min % 60
  return t("{0}时{1}分", [hr, remainMin])
}

/** 格式化文件大小 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return `${(bytes / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0)} ${units[i]}`
}

/** 截断字符串 */
export function truncate(str: string, maxLength: number): string {
  if (str.length <= maxLength) return str
  return str.slice(0, maxLength) + '...'
}
