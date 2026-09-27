/**
 * 校验工具函数
 *
 * 提供表单和输入值的通用校验方法。
 */

/** 校验邮箱格式 */
export function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

/** 校验 URL 格式 */
export function isValidUrl(url: string): boolean {
  try {
    new URL(url)
    return true
  } catch {
    return false
  }
}

/** 校验非空 */
export function isNotEmpty(value: string | null | undefined): boolean {
  return value !== null && value !== undefined && value.trim().length > 0
}

/** 校验整数范围 */
export function isInRange(value: number, min: number, max: number): boolean {
  return Number.isInteger(value) && value >= min && value <= max
}

/** 校验文件名合法性 */
export function isValidFileName(name: string): boolean {
  return /^[a-zA-Z0-9._/\\-]+$/.test(name)
}
