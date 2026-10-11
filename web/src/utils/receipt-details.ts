import type { Step, Turn } from '@/api/events'

export function stepArguments(step: Step): Record<string, unknown> {
  return step.input && typeof step.input === 'object' && !Array.isArray(step.input)
    ? (step.input as Record<string, unknown>)
    : {}
}

export function commandSteps(turn: Turn): Step[] {
  return turn.steps.filter((step) =>
    ['bash', 'exec_command', 'shell', 'powershell'].includes(step.tool),
  )
}

export function commandText(step: Step): string {
  const input = stepArguments(step)
  const command = input.command ?? input.cmd
  if (typeof command === 'string') return command
  if (Array.isArray(input.argv) && input.argv.every((value) => typeof value === 'string'))
    return JSON.stringify(input.argv)
  return ''
}

/** Normalize only against the recorded workspace; never strip an arbitrary absolute prefix. */
export function workspaceRelativePath(path: string, root = ''): string | null {
  let relative = path.replaceAll('\\', '/')
  const base = root.replaceAll('\\', '/').replace(/\/+$/, '')
  const absolute = relative.startsWith('/') || /^[a-z]:\//i.test(relative)
  if (absolute) {
    if (!base && root !== '/') return null
    const prefix = base + '/'
    const matches = /^[a-z]:/i.test(base)
      ? relative.toLowerCase().startsWith(prefix.toLowerCase())
      : relative.startsWith(prefix)
    if (!matches) return null
    relative = relative.slice(prefix.length)
  }
  const parts = relative.split('/').filter((part) => part && part !== '.')
  if (!parts.length || parts.includes('..') || parts.some((part) => part.toLowerCase() === '.git'))
    return null
  return parts.join('/')
}

export function changedFiles(turn: Turn, root = ''): { path: string; relative: string | null }[] {
  const paths = turn.changes.map((change) => change.path)
  for (const step of turn.steps) {
    if (
      step.status !== 'completed' ||
      !['file_write', 'file_edit', 'write', 'edit'].includes(step.tool)
    )
      continue
    const path = stepArguments(step).path
    if (typeof path === 'string' && path) paths.push(path)
  }
  const seen = new Set<string>()
  return paths.flatMap((path) => {
    const relative = workspaceRelativePath(path, root)
    const key = relative ?? path
    if (seen.has(key)) return []
    seen.add(key)
    return [{ path: relative ?? path, relative }]
  })
}
