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
  private handshake: ReturnType<typeof setTimeout> | null = null
  private stopped = true
  private attempts = 0
  private recovering = false
  private subscribed = false
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
    this.subscribed = false
    this.recovering = true
    const socket = this.options.connect((event) => {
      if (this.stopped || generation !== this.generation) return
      if (event.type === 'stream.ready') {
        this.subscribed = true
        if (this.handshake) clearTimeout(this.handshake)
        this.handshake = null
        // Replay starts only AFTER registration. Live events remain buffered
        // until history catches up; a snapshot cannot advance this cursor.
        void this.recover(generation)
        return
      }
      if (this.recovering) this.queued.push(event)
      else this.deliver(event, false)
    })
    this.socket = socket
    socket.onopen = () => {
      if (this.stopped || generation !== this.generation) return
      this.handshake = setTimeout(() => {
        if (!this.subscribed && generation === this.generation) socket.close()
      }, 10_000)
      // Gateway has no application pong. HTTP replay checks liveness too.
      this.heartbeat = setInterval(() => {
        void this.recover(generation)
      }, 25_000)
    }
    socket.onerror = () => socket.close()
    socket.onclose = () => {
      if (this.stopped || generation !== this.generation) return
      if (this.heartbeat) clearInterval(this.heartbeat)
      if (this.handshake) clearTimeout(this.handshake)
      this.handshake = null
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
    // Snapshot loading may request replay before the WS subscription is ready.
    // stream.ready will start it; never treat browser onopen as registration.
    if (!this.subscribed) return Promise.resolve()
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
    let completed = false
    try {
      for (;;) {
        const before = this.lastSeq
        const events = await this.options.history(before, signal)
        if (this.stopped || generation !== this.generation) return
        for (const event of events.slice().sort((a, b) => a.sequence - b.sequence)) this.deliver(event, true)
        if (events.length < 1000 || this.lastSeq === before) break
      }
      completed = true
      if (this.subscribed && this.socket?.readyState === 1) {
        this.attempts = 0
        this.options.connection(true)
      }
    } catch {
      if (!this.stopped && generation === this.generation) {
        this.subscribed = false
        this.options.connection(false)
        // Don't release newer live deltas over a missing history segment.
        // Reconnect and replay from the last confirmed durable cursor.
        this.socket?.close()
      }
    } finally {
      if (!this.stopped && generation === this.generation) {
        // close() is asynchronous; messages already queued by the browser must
        // still be buffered until the replacement connection replays the gap.
        this.recovering = !completed
        const pending = this.queued.splice(0)
        if (completed)
          for (const event of pending.sort((a, b) => a.sequence - b.sequence)) this.deliver(event, false)
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
    if (this.handshake) clearTimeout(this.handshake)
    this.handshake = null
    this.reconnect = this.heartbeat = null
    this.socket?.close()
    this.socket = null
    this.queued = []
  }
}
