// Short dialogue excerpts from BanG Dream! It's MyGO!!!!!, not song lyrics.
// Chinese subtitle wording varies; keep the existing opening line.
export const MYGO_QUOTES = [
  // Episode 12; retained from the existing welcome screen.
  '迷失方向也无所谓，在迷茫中前进吧！',
  // https://zh.wikiquote.org/zh-cn/BanG_Dream!_It%27s_MyGO!!!!!
  '那……能陪我组一辈子的乐队吗？',
  '有趣的女人。',
  '我不会放弃的。',
  // https://zh.wikipedia.org/wiki/BanG_Dream!_It%27s_MyGO!!!!!#反響
  '是又怎样？',
  '我爱慕虚荣啦！',
  '为什么要演奏春日影！',
  '那家伙竟敢无视灯！',
  // Episodes 12–13 / dialogue and audio excerpts:
  // https://moegirl.icu/zh-sg/BanG_Dream!_It%27s_MyGO!!!!!/轶事
  '谢谢你，没有放开我的手。',
  '要是心灵也可以贴创可贴就好了。',
  '祝你幸福。',
  // Episode 5 dialogue, also used by this card:
  // https://bestdori.com/info/cards/1824/Anon-Chihaya-While-We-re-Lost
  '一起在迷失之中前进！',
] as const

const storageKey = 'maigokite.mygo.lastQuote'
let lastQuote = ''

export function pickMygoQuote(): string {
  try { lastQuote = localStorage.getItem(storageKey) || lastQuote } catch { /* Storage may be unavailable. */ }
  const choices = MYGO_QUOTES.filter((quote) => quote !== lastQuote)
  const quote = choices[Math.floor(Math.random() * choices.length)] ?? MYGO_QUOTES[0]
  lastQuote = quote
  try { localStorage.setItem(storageKey, quote) } catch { /* Still avoid repeats in this window. */ }
  return quote
}
