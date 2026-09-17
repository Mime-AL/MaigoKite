import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import MarkdownContent from '@/components/chat-area/MarkdownContent.vue'

describe('MarkdownContent', () => {
  it('renders model-escaped markdown without showing escape slashes', () => {
    const wrapper = mount(MarkdownContent, {
      props: { content: '## 标题\n\n\\*\\*重要内容\\*\\*' },
    })

    expect(wrapper.get('h2').text()).toBe('标题')
    expect(wrapper.get('strong').text()).toBe('重要内容')
    expect(wrapper.text()).not.toContain('\\*')
  })

  it('decodes a response that was serialized as a JSON string', () => {
    const wrapper = mount(MarkdownContent, {
      props: { content: JSON.stringify('第一行\n第二行') },
    })

    expect(wrapper.text()).toContain('第一行')
    expect(wrapper.text()).toContain('第二行')
    expect(wrapper.html()).toContain('<br>')
  })

  it('does not alter escape characters inside code', () => {
    const wrapper = mount(MarkdownContent, {
      props: { content: '正文：\\*\\*强调\\*\\*\n\n`/\\*\\*/`' },
    })

    expect(wrapper.get('strong').text()).toBe('强调')
    expect(wrapper.get('code').text()).toBe('/\\*\\*/')
  })

  it('preserves backslashes used by math expressions', () => {
    const wrapper = mount(MarkdownContent, {
      props: { content: '$\\text{A} \\Rightarrow \\text{B}$' },
    })

    expect(wrapper.text()).toContain('\\text{A} \\Rightarrow \\text{B}')
  })

  it('sanitizes active HTML from model output', () => {
    const wrapper = mount(MarkdownContent, {
      props: {
        content:
          '<script>window.pwned = true</script><img src=x onerror="window.pwned=true"><a href="javascript:alert(1)">link</a>',
      },
    })

    expect(wrapper.find('script').exists()).toBe(false)
    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.get('a').attributes('href')).toBeUndefined()
  })
})
