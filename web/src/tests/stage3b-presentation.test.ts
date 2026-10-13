import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { Turn } from '@/api/events'
import { presentationNodes } from '@/utils/rail-presentation'
import { codeLines, visibleCodeLines } from '@/utils/code-presentation'
import { inkBuckets } from '@/utils/rail-minimap'
import { assistantMarkdownBlocks } from '@/utils/markdown'
import CodeBlock from '@/components/common/CodeBlock.vue'
import RailNode from '@/components/rail/RailNode.vue'
import RailMinimap from '@/components/rail/RailMinimap.vue'
import Receipt from '@/components/rail/Receipt.vue'
import MarkdownContent from '@/components/chat-area/MarkdownContent.vue'
import ComposerDraft from '@/components/inkwell/ComposerDraft.vue'
import ModePill from '@/components/inkwell/ModePill.vue'
import { menuSelectionIndex } from '@/utils/composer-presentation'
const originalClipboard = Object.getOwnPropertyDescriptor(navigator, 'clipboard')

function turn(): Turn {
  return { id: 't', sessionId: 'c', status: 'completed', startedAt: 0, text: '', thinking: '', steps: [], awaits: [], memories: [], timeline: [], changes: [], plan: [], jobs: [], inputs: [], summary: { files: 0, added: 0, removed: 0, commands: 0, failed: 0, awaits: 0, contextPct: null, durationMs: 800 } }
}
afterEach(() => {
  vi.useRealTimers(); vi.unstubAllGlobals()
  if (originalClipboard) Object.defineProperty(navigator, 'clipboard', originalClipboard)
  else Reflect.deleteProperty(navigator, 'clipboard')
})
describe('3b read-only Rail presentation', () => {
  it('merges consecutive reads without mutating the product projection', () => {
    const value = turn()
    for (const id of ['a', 'b', 'c']) {
      value.steps.push({ id, title: id, tool: 'file_read', kind: 'read', input: {}, output: '', status: 'completed', durationMs: 1 })
      value.timeline.push({ id, kind: 'step' })
    }
    const original = JSON.stringify(value)
    const nodes = presentationNodes(value)
    expect(nodes).toHaveLength(1); expect(nodes[0].title).toBe('翻了 3 个文件')
    expect(JSON.stringify(value)).toBe(original)
  })
  it('inserts input by creation time even when consumed with a later seq, breaking read grouping', () => {
    const value = turn()
    for (const [id, seq, second] of [['a', 1, '00'], ['b', 2, '02']] as const) {
      value.steps.push({ id, title: id, tool: 'file_read', kind: 'read', input: {}, output: '', status: 'completed', durationMs: 1 })
      value.timeline.push({ id, kind: 'step', seq, time: `2026-10-11T08:00:${second}Z` })
    }
    value.inputs = [{ id: 'i', task_id: 't', content: 'steer', status: 'consumed', seq: 99, created_at: '2026-10-11T08:00:01Z' }]
    const nodes = presentationNodes(value)
    expect(nodes.map(node => node.kind)).toEqual(['read', 'input', 'read'])
    expect(nodes[1].input?.status).toBe('consumed')
  })
  it('keeps exact approval ownership after inserting supplemental input', () => {
    const value = turn()
    value.steps = [{ id: 'write', title: 'write', tool: 'file_write', kind: 'act', input: {}, output: '', status: 'completed', durationMs: 1 }]
    value.awaits = [{ id: 'a', sessionId: 'c', turnId: 't', mode: 'approval', title: 'approve', detail: '{}', version: 7, toolCallId: 'write', verdict: 'allow' }]
    value.timeline = [{ id: 'write', kind: 'step', seq: 1 }, { id: 'a', kind: 'await', seq: 2 }]
    value.inputs = [{ id: 'i', task_id: 't', content: 'later', status: 'queued', created_at: '', seq: 3 }]
    expect(presentationNodes(value)[0].await?.version).toBe(7)
    expect(presentationNodes(value).filter(node => node.await)).toHaveLength(1)
  })
  it('renders failure as SVG and automatically opens its detail', () => {
    const wrapper = mount(RailNode, { props: { node: { id: 'f', kind: 'failed', title: 'Failed', steps: [] }, turnId: 't' } })
    expect(wrapper.get('.node-button').attributes('aria-expanded')).toBe('true')
    expect(wrapper.find('.node-glyph svg .cross').exists()).toBe(true)
    expect(wrapper.get('.node-glyph').text()).toBe('')
    wrapper.unmount()
  })
  it('shows unused supplemental input and preserves the explicit resend action', async () => {
    const resend = vi.fn().mockResolvedValue(undefined)
    const wrapper = mount(RailNode, { props: { node: { id: 'input-i', kind: 'input', title: '补充指令', steps: [], input: { id: 'i', task_id: 't', content: 'Keep me', status: 'not_consumed', created_at: '' } }, turnId: 't', canResend: true, resendInput: resend } })
    expect(wrapper.text()).toContain('本轮未采用')
    await wrapper.get('.supplement-message button').trigger('click'); await flushPromises()
    expect(resend).toHaveBeenCalledWith('i')
    wrapper.unmount()
  })
  it('uses compact completion for pure chat and keeps operation details behind category toggles', async () => {
    const value = turn(), wrapper = mount(Receipt, { props: { turn: value } })
    expect(wrapper.classes()).toContain('compact')
    expect(wrapper.find('.receipt-facts').exists()).toBe(false)
    await wrapper.setProps({ turn: { ...value, summary: { ...value.summary!, files: 1 } } })
    expect(wrapper.classes()).not.toContain('compact')
    expect(wrapper.find('.receipt-facts').exists()).toBe(true)
    expect(wrapper.find('.receipt-details').exists()).toBe(false)
    const files = wrapper.get('.receipt-facts button')
    await files.trigger('click')
    expect(files.attributes('aria-expanded')).toBe('true')
    expect(wrapper.find('.receipt-details').exists()).toBe(true)
    await files.trigger('click')
    expect(files.attributes('aria-expanded')).toBe('false')
    expect(wrapper.find('.receipt-details').exists()).toBe(false)
    wrapper.unmount()
  })
})
describe('3b bounded code and safe Markdown', () => {
  it('calculates both diff gutters and ignores file headers', () => {
    const result = codeLines('--- a/x\n+++ b/x\n@@ -7,2 +8,2 @@\n-old\n+new\n keep', true)
    expect(result[0].kind).toBe('header')
    expect(result[3].before).toBe(7); expect(result[3].after).toBeUndefined()
    expect(result[4].after).toBe(8); expect(result[4].before).toBeUndefined()
    expect([result[5].before, result[5].after]).toEqual([8, 9])
  })
  it('renders 20 preview lines and at most the last 200 when expanded', async () => {
    const content = Array.from({ length: 300 }, (_, n) => 'line ' + (n + 1)).join('\n')
    expect(visibleCodeLines(codeLines(content), true)[0].index).toBe(101)
    const wrapper = mount(CodeBlock, { props: { content } })
    expect(wrapper.findAll('.code-line')).toHaveLength(20)
    await wrapper.get('.code-footer button').trigger('click')
    expect(wrapper.findAll('.code-line')).toHaveLength(200)
    expect(wrapper.text()).toContain('显示最后 200 行')
    wrapper.unmount()
  })
  it('copies the complete original output, reports success, and releases the feedback timer', async () => {
    vi.useFakeTimers()
    const copy = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: copy } })
    const content = 'exact\n<untrusted>\n', wrapper = mount(CodeBlock, { props: { content } })
    await wrapper.get('.copy-button').trigger('click'); await flushPromises()
    expect(copy).toHaveBeenCalledWith(content); expect(wrapper.get('[role="status"]').text()).toBe('已复制')
    wrapper.unmount(); expect(vi.getTimerCount()).toBe(0)
  })
  it('does not claim copy success when clipboard access fails', async () => {
    Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: vi.fn().mockRejectedValue(new Error('denied')) } })
    const wrapper = mount(CodeBlock, { props: { content: 'x' } })
    await wrapper.get('.copy-button').trigger('click'); await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('无法复制')
    expect(wrapper.find('[role="status"]').exists()).toBe(false); wrapper.unmount()
  })
  it('keeps fenced code literal and preserves safe link attributes', () => {
    const wrapper = mount(MarkdownContent, { props: { content: '[Docs](https://example.com)\n\n```html\n<img src=x onerror=alert(1)>\n```' } })
    expect(wrapper.get('a').attributes('rel')).toBe('noopener noreferrer')
    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.get('.code-text').text()).toContain('<img')
    wrapper.unmount()
  })
  it('preserves nested list/quote fences instead of breaking their HTML structure', () => {
    const blocks = assistantMarkdownBlocks('> note\n>\n> ```ts\n> const n = 1\n> ```')
    expect(blocks).toHaveLength(1)
    expect(blocks[0].kind === 'html' && blocks[0].html).toContain('<blockquote>')
    expect(blocks[0].kind === 'html' && blocks[0].html).toContain('<pre>')
  })
  it('throttles streaming Markdown and immediately flushes the final content', async () => {
    vi.useFakeTimers()
    const wrapper = mount(MarkdownContent, { props: { content: 'start', isStreaming: true } })
    await wrapper.setProps({ content: 'stream' }); expect(wrapper.text()).toBe('start')
    await vi.advanceTimersByTimeAsync(100); expect(wrapper.text()).toBe('stream')
    await wrapper.setProps({ content: 'final', isStreaming: false }); expect(wrapper.text()).toBe('final')
    wrapper.unmount(); expect(vi.getTimerCount()).toBe(0)
  })
})
describe('3b real-position minimap and menu navigation', () => {
  it('supports model Home/End/page navigation and wraps directional selection', () => {
    expect(menuSelectionIndex('Home', 8, 20)).toBe(0)
    expect(menuSelectionIndex('End', 8, 20)).toBe(19)
    expect(menuSelectionIndex('PageDown', 18, 20)).toBe(19)
    expect(menuSelectionIndex('PageUp', 2, 20)).toBe(0)
    expect(menuSelectionIndex('ArrowUp', 0, 20)).toBe(19)
    expect(menuSelectionIndex('ArrowDown', 19, 20)).toBe(0)
    expect(menuSelectionIndex('ArrowDown', 0, 0)).toBe(-1)
    expect(menuSelectionIndex('a', 0, 20)).toBeNull()
  })
  it('maps measured position rather than index and makes dense positions darker', () => {
    const nodes = [{ node: { id: 'a', turnId: 't' }, position: .1 }, { node: { id: 'b', turnId: 't' }, position: .11 }, { node: { id: 'c', turnId: 't' }, position: .8 }]
    const result = inkBuckets(nodes, 10)
    expect(result.map(item => item.top)).toEqual([10, 80])
    expect(result[0].density).toBeGreaterThan(result[1].density)
  })
  it('measures DOM height, jumps to the corresponding node, and disconnects observers', async () => {
    const disconnected = vi.fn()
    vi.stubGlobal('ResizeObserver', class { observe() {} disconnect = disconnected })
    const root = document.createElement('div'), button = document.createElement('button')
    button.dataset.railNode = 't:a'; root.append(button); document.body.append(root)
    Object.defineProperty(root, 'scrollHeight', { value: 1000 })
    vi.spyOn(root, 'getBoundingClientRect').mockReturnValue(new DOMRect(0, 0, 800, 400))
    vi.spyOn(button, 'getBoundingClientRect').mockReturnValue(new DOMRect(0, 800, 50, 40))
    const wrapper = mount(RailMinimap, { props: { nodes: [{ id: 'a', turnId: 't' }], scrollRoot: root } })
    await flushPromises(); await new Promise(requestAnimationFrame); await flushPromises()
    expect(wrapper.get('button').attributes('style')).toContain('top: 81.25%')
    await wrapper.get('button').trigger('click'); expect(wrapper.emitted('jump')?.[0]).toEqual([{ id: 'a', turnId: 't' }])
    wrapper.unmount(); expect(disconnected).toHaveBeenCalled(); root.remove()
  })
  it('tracks menu highlight, selects with Tab/Alt-number, and closes before Esc reaches cancel', async () => {
    const commands = [{ id: 'files', label: '文件' }, { id: 'plan', label: '计划' }]
    const wrapper = mount(ComposerDraft, { props: { modelValue: '/', menuId: 'test', mentions: [], commands, placeholder: '', disabled: false } })
    await wrapper.get('textarea').trigger('keydown', { key: 'ArrowDown' })
    expect(wrapper.get('textarea').attributes('aria-activedescendant')).toBe('test-commands-option-1')
    await wrapper.get('textarea').trigger('keydown', { key: 'Tab' })
    expect(wrapper.emitted('command')?.[0]).toEqual([commands[1]])
    await wrapper.get('textarea').trigger('keydown', { key: '1', altKey: true })
    expect(wrapper.emitted('command')?.[1]).toEqual([commands[0]])
    await wrapper.get('textarea').trigger('keydown', { key: 'Escape' })
    expect(wrapper.find('.slash-menu').exists()).toBe(false); expect(wrapper.emitted('keydown')).toBeUndefined()
    wrapper.unmount()
  })
  it('does not select or submit while the IME is composing', async () => {
    const wrapper = mount(ComposerDraft, { props: { modelValue: '/', menuId: 'ime', mentions: [], commands: [{ id: 'files', label: '文件' }], placeholder: '', disabled: false } })
    await wrapper.get('textarea').trigger('keydown', { key: 'Enter', isComposing: true })
    expect(wrapper.emitted('command')).toBeUndefined(); expect(wrapper.emitted('keydown')).toBeUndefined()
    wrapper.unmount()
  })
  it('supports directional mode navigation without changing permission semantics', async () => {
    const wrapper = mount(ModePill, { props: { modelValue: 'ask' } })
    await wrapper.get('.mode-pill').trigger('keydown', { key: 'ArrowRight' })
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['plan'])
    await wrapper.setProps({ disabled: true }); await wrapper.get('.mode-pill').trigger('keydown', { key: 'End' })
    expect(wrapper.emitted('update:modelValue')).toHaveLength(1)
    wrapper.unmount()
  })
})
