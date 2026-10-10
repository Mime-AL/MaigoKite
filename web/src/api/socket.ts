import type { AgentEvent } from './client'

export interface EventSocketOptions {
  connect: (receive: (event: AgentEvent) => void) => WebSocket
  history: (after: number, signal?: AbortSignal) => Promise<AgentEvent[]>
  receive: (event: AgentEvent, replay: boolean) => void
  connection: (online: boolean) => void
}

/** Replay durable events before releasing buffered live events. */
export class EventSocket {
  private socket: WebSocket | null = null
  private reconnect: ReturnType<typeof setTimeout> | null = null
  private heartbeat: ReturnType<typeof setInterval> | null = null
  private stopped = true
  private attempts = 0
  private recovering = false
  private queued: AgentEvent[] = []
  private seen = new Set<string>()
  private generation = 0
  private recovery: { generation: number; promise: Promise<void> } | null = null
  private controller: AbortController | null = null
  lastSeq = 0
  constructor(private readonly options: EventSocketOptions) {}
  start() {
    if (!this.stopped) return
    this.stopped = false
    this.open()
  }
  private open() {
    if (this.stopped) return
    const generation = ++this.generation
    this.controller?.abort()
    this.options.connection(false)
    this.recovering = true
    const socket = this.options.connect((event) => {
      if (this.stopped || generation !== this.generation) return
      if (this.recovering) this.queued.push(event)
      else this.deliver(event, false)
    })
    this.socket = socket
    socket.onopen = () => {
      if (this.stopped || generation !== this.generation) return
      void this.recover(generation)
      // Gateway has no application pong. HTTP replay checks liveness too.
      this.heartbeat = setInterval(() => {
        void this.recover(generation)
      }, 25_000)
    }
    socket.onerror = () => socket.close()
    socket.onclose = () => {
      if (this.stopped || generation !== this.generation) return
      if (this.heartbeat) clearInterval(this.heartbeat)
      this.heartbeat = null
      this.options.connection(false)
      this.socket = null
      const delay = Math.min(30_000, 1000 * 2 ** this.attempts++)
      this.reconnect = setTimeout(() => {
        this.reconnect = null
        this.open()
      }, delay)
    }
  }
  recover(generation = this.generation): Promise<void> {
    if (this.recovery?.generation === generation) return this.recovery.promise
    const controller = new AbortController()
    this.controller = controller
    const promise = this.replay(generation, controller.signal).finally(() => {
      if (this.recovery?.generation === generation) this.recovery = null
    })
    this.recovery = { generation, promise }
    return promise
  }
  private async replay(generation: number, signal: AbortSignal) {
    if (this.stopped || generation !== this.generation) return
    this.recovering = true
    try {
      for (;;) {
        const before = this.lastSeq
        const events = await this.options.history(before, signal)
        if (this.stopped || generation !== this.generation) return
        for (const event of events.slice().sort((a, b) => a.sequence - b.sequence)) this.deliver(event, true)
        if (events.length < 1000 || this.lastSeq === before) break
      }
      if (this.socket?.readyState === 1) {
        this.attempts = 0
        this.options.connection(true)
      }
    } catch {
      if (!this.stopped && generation === this.generation) this.options.connection(false)
    } finally {
      if (!this.stopped && generation === this.generation) {
        this.recovering = false
        for (const event of this.queued.splice(0).sort((a, b) => a.sequence - b.sequence)) this.deliver(event, false)
      }
    }
  }
  private deliver(event: AgentEvent, replay: boolean) {
    if (!event || typeof event.type !== 'string' || !event.payload || typeof event.payload !== 'object') return
    // Both live paths now preserve durable IDs. Keep the history cursor tied
    // to HTTP replay: a higher live sequence alone does not prove no gap exists.
    if (replay) this.lastSeq = Math.max(this.lastSeq, event.sequence || 0)
    const key = event.event_id || `${event.task_id}:${event.sequence}:${event.type}`
    if (this.seen.has(key)) return
    this.seen.add(key)
    this.options.receive(event, replay)
  }
  stop() {
    this.stopped = true
    this.generation++
    this.controller?.abort()
    this.controller = null
    if (this.reconnect) clearTimeout(this.reconnect)
    if (this.heartbeat) clearInterval(this.heartbeat)
    this.reconnect = this.heartbeat = null
    this.socket?.close()
    this.socket = null
    this.queued = []
  }
}
