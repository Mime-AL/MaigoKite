import DOMPurify from 'dompurify'
import MarkdownIt from 'markdown-it'

const markdown = new MarkdownIt({ html: false, breaks: true, linkify: true }).disable('image')
markdown.renderer.rules.link_open = (tokens, index, options, _env, renderer) => {
  tokens[index].attrSet('rel', 'noopener noreferrer')
  tokens[index].attrSet('target', '_blank')
  return renderer.renderToken(tokens, index, options)
}
const cache = new Map<string, string>()

const codeSegmentPattern = /(```[\s\S]*?(?:```|$)|~~~[\s\S]*?(?:~~~|$)|`[^`\n]*`)/g
const serializedStringEscapePattern = /\\(?:["\\/bfnrt]|u[0-9a-fA-F]{4})/

function decodeSerializedString(value: string): string {
  let result = value
  for (let attempt = 0; attempt < 2; attempt += 1) {
    const trimmed = result.trim()
    if (!trimmed.startsWith('"') || !trimmed.endsWith('"') || !serializedStringEscapePattern.test(trimmed)) {
      break
    }
    try {
      const parsed: unknown = JSON.parse(trimmed)
      if (typeof parsed !== 'string') break
      result = parsed
    } catch {
      break
    }
  }
  return result
}

function normalizeProseSegment(value: string): string {
  return value
    .replace(/\\([*_~])/g, '$1')
    .replace(/^(\s*)\\([#>+-])(?=\s)/gm, '$1$2')
    .replace(/^(\s*\d+)\\\.(?=\s)/gm, '$1.')
}

export function normalizeAssistantMarkdown(value: string): string {
  const decoded = decodeSerializedString(value)
  return decoded
    .split(codeSegmentPattern)
    .map((segment, index) => (index % 2 === 0 ? normalizeProseSegment(segment) : segment))
    .join('')
}

export function renderAssistantMarkdown(value: string): string {
  const source = normalizeAssistantMarkdown(value)
  const cached = cache.get(source)
  if (cached) return cached
  const rendered = markdown.render(source)
  const sanitized = DOMPurify.sanitize(rendered, {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ['form', 'iframe', 'img', 'input', 'button', 'style', 'video', 'audio'],
    FORBID_ATTR: ['style'],
    ADD_ATTR: ['target'],
  })
  if (source.length < 50000) {
    if (cache.size >= 64) cache.delete(cache.keys().next().value || '')
    cache.set(source, sanitized)
  }
  return sanitized
}
