declare module 'markdown-it' {
  interface Token {
    type: string
    level: number
    content: string
    info: string
    attrSet(name: string, value: string): void
  }
  interface Options {
    html?: boolean
    breaks?: boolean
    linkify?: boolean
  }
  interface Renderer {
    render(tokens: Token[], options: Options, env: unknown): string
    renderToken(tokens: Token[], index: number, options: Options): string
    rules: Record<
      string,
      | ((
          tokens: Token[],
          index: number,
          options: Options,
          env: unknown,
          renderer: Renderer,
        ) => string)
      | undefined
    >
  }
  export default class MarkdownIt {
    constructor(options?: Options)
    renderer: Renderer
    options: Options
    parse(source: string, env: unknown): Token[]
    disable(rules: string | string[]): this
    render(source: string): string
  }
}
