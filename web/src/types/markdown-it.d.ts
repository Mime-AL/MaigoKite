declare module 'markdown-it' {
  interface Token {
    attrSet(name: string, value: string): void
  }
  interface Options {
    html?: boolean
    breaks?: boolean
    linkify?: boolean
  }
  interface Renderer {
    renderToken(tokens: Token[], index: number, options: Options): string
    rules: Record<
      string,
      ((tokens: Token[], index: number, options: Options, env: unknown, renderer: Renderer) => string) | undefined
    >
  }
  export default class MarkdownIt {
    constructor(options?: Options)
    renderer: Renderer
    disable(rules: string | string[]): this
    render(source: string): string
  }
}
