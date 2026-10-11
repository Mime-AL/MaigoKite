export type PaperLight = 'morning' | 'noon' | 'evening' | 'night'

export function paperLight(hour: number): PaperLight {
  if (hour < 6) return 'night'
  if (hour < 11) return 'morning'
  if (hour < 18) return 'noon'
  return 'evening'
}

// One introduction per main renderer lifetime, not a persistent user preference.
let introduced = false
export function takeWelcomeIntroduction(): boolean {
  const first = !introduced
  introduced = true
  return first
}

export const welcomeStarters = [
  {
    icon: 'file',
    title: '读读工作区',
    hint: '文件与资料',
    workspace: true,
    prompt: '阅读当前工作区的资料，概括主要内容和目录结构。不要修改文件。',
  },
  {
    icon: 'review',
    title: '规划一个任务',
    hint: '思路与步骤',
    workspace: false,
    prompt: '我想规划一个任务。请和我一起明确目标、限制和执行步骤，有不清楚的地方请问我。',
  },
  {
    icon: 'activity',
    title: '看看最近变更',
    hint: '变更与检查',
    workspace: true,
    prompt: '检查当前工作区的 Git 变更，概括改了什么和需要留意的问题。不要修改文件。',
  },
  {
    icon: 'compose',
    title: '分析一个问题',
    hint: '不需要文件夹',
    workspace: false,
    prompt: '我有一个问题想和你一起分析。请帮我梳理事实、假设和可选方向。',
  },
] as const

export function starterShortcut(event: KeyboardEvent): number | undefined {
  if (
    event.defaultPrevented ||
    event.isComposing ||
    event.altKey ||
    event.ctrlKey ||
    event.metaKey ||
    event.shiftKey
  )
    return
  if (
    event.target instanceof Element &&
    event.target.closest(
      'input, textarea, select, [contenteditable]:not([contenteditable="false"]), [role="textbox"]',
    )
  )
    return
  if (document.querySelector('dialog[open], [role="dialog"][aria-modal="true"]')) return
  return /^[1-4]$/.test(event.key) ? Number(event.key) - 1 : undefined
}
