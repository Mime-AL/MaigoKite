import type { AgentEvent } from './client'

export interface EventSocketOptions {
  connect: (receive: (event: AgentEvent) => void) => WebSocket
  history: (after: number, signal?: AbortSignal) => Promise<AgentEvent[]>
  receive: (event: AgentEvent, replay: boolean) => boolean | void
  connection: (online: boolean) => void
  failure?: (error: unknown) => void
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
  // Only live receipts ahead of the confirmed history cursor need identities.
  private seen = new Map<string, number>()
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
      if (!this.subscribed) return
      if (this.recovering) this.buffer(event, generation)
      else {
        try {
          if (!this.deliver(event, false)) {
            this.buffer(event, generation)
            this.recovering = true
          }
          if (this.seen.size >= 1000) void this.recover(generation)
        } catch (error) {
          this.replayFailed(generation, error)
        }
      }
    })
    this.socket = socket
    socket.onopen = () => {
      if (this.stopped || generation !== this.generation) return
      this.handshake = setTimeout(() => {
        if (!this.subscribed && generation === this.generation) socket.close()
      }, 10_000)
      // The API has no application pong. HTTP replay checks liveness too.
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
      this.subscribed = false
      this.recovering = true
      this.controller?.abort()
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
  /** Retry after the consumer has installed a snapshot, including an in-flight replay. */
  async retry() {
    await this.recovery?.promise
    if (!this.stopped) await this.recover()
  }
  private async replay(generation: number, signal: AbortSignal) {
    if (this.stopped || generation !== this.generation) return
    this.recovering = true
    let completed = false
    try {
      for (;;) {
        const before = this.lastSeq
        const events = await this.options.history(before, signal)
        if (this.stopped || generation !== this.generation || signal.aborted) return
        for (const event of events.slice().sort((a, b) => a.sequence - b.sequence))
          if (!this.deliver(event, true)) return
        if (events.length < 1000 || this.lastSeq === before) break
      }
      // Buffered projections are part of recovery too. Leave the failed item
      // queued and do not report online until every projection has succeeded.
      this.queued.sort((a, b) => a.sequence - b.sequence)
      while (this.queued.length) {
        if (!this.deliver(this.queued[0], false)) return
        this.queued.shift()
      }
      completed = true
      if (this.subscribed && this.socket?.readyState === 1) {
        this.attempts = 0
        this.options.connection(true)
      }
    } catch (error) {
      if (!signal.aborted) this.replayFailed(generation, error)
    } finally {
      if (!this.stopped && generation === this.generation) {
        // close() is asynchronous; messages already queued by the browser must
        // still be buffered until the replacement connection replays the gap.
        this.recovering = !completed
      }
    }
  }
  private replayFailed(generation: number, error: unknown) {
    if (this.stopped || generation !== this.generation) return
    this.subscribed = false
    this.recovering = true
    this.controller?.abort()
    // These events are durable. Reconnect re-reads them from the last
    // successfully applied cursor instead of retaining an unbounded buffer.
    this.queued = []
    this.options.connection(false)
    // Only successfully projected receipts are acknowledged; reconnect can
    // replay a failed item instead of leaving the chat permanently thinking.
    this.socket?.close()
    this.options.failure?.(error)
  }
  private buffer(event: AgentEvent, generation: number) {
    if (this.queued.length >= 2000) {
      this.replayFailed(generation, new Error('Conversation replay buffer full; reconnecting'))
      return
    }
    this.queued.push(event)
  }
  private deliver(event: AgentEvent, replay: boolean) {
    if (
      !event ||
      typeof event.type !== 'string' ||
      !Number.isSafeInteger(event.sequence) ||
      event.sequence <= 0 ||
      !event.payload ||
      typeof event.payload !== 'object' ||
      Array.isArray(event.payload)
    )
      throw new Error('Invalid conversation event')
    // Both live paths now preserve durable IDs. Keep the history cursor tied
    // to HTTP replay: a higher live sequence alone does not prove no gap exists.
    const key = event.event_id || `${event.task_id}:${event.sequence}:${event.type}`
    if (event.sequence <= this.lastSeq) return true
    if (!this.seen.has(key)) {
      if (this.options.receive(event, replay) === false) return false
      this.seen.set(key, event.sequence)
    }
    if (replay) {
      this.lastSeq = Math.max(this.lastSeq, event.sequence)
      for (const [id, sequence] of this.seen)
        if (sequence <= this.lastSeq) this.seen.delete(id)
    }
    return true
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
