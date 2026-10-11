export interface CodeLine {
  index: number
  text: string
  kind: 'plain' | 'addition' | 'deletion' | 'header' | 'hunk'
  before?: number
  after?: number
}
/** Unified-diff gutters are presentation only; no patch application here. */
export function codeLines(content: string, diff = false): CodeLine[] {
  let before = 0,
    after = 0,
    inHunk = false
  const source = content.replace(/\n$/, '').split('\n')
  return source.map((text, index) => {
    const line: CodeLine = { index: index + 1, text, kind: 'plain' }
    if (!diff) return line
    const hunk = /^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/.exec(text)
    if (hunk) {
      before = Number(hunk[1])
      after = Number(hunk[2])
      inHunk = true
      line.kind = 'hunk'
    } else if (
      text.startsWith('diff ') ||
      text.startsWith('index ') ||
      text.startsWith('--- ') ||
      text.startsWith('+++ ')
    ) {
      line.kind = 'header'
      inHunk = false
    } else if (inHunk && text.startsWith('+')) {
      line.kind = 'addition'
      line.after = after++
    } else if (inHunk && text.startsWith('-')) {
      line.kind = 'deletion'
      line.before = before++
    } else if (inHunk && text.startsWith(' ')) {
      line.before = before++
      line.after = after++
    }
    return line
  })
}
export function visibleCodeLines(lines: CodeLine[], expanded: boolean, preview = 20, limit = 200) {
  return expanded ? lines.slice(-limit) : lines.slice(0, preview)
}
