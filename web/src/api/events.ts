export type PulseState = 'idle' | 'thinking' | 'acting' | 'waiting' | 'error' | 'offline'
export type Verdict = 'allow' | 'allow_session' | 'deny'
export interface ToolHintAction {
  to: string
  label: string
}
export interface TurnSummary {
  files: number
  added: number
  removed: number
  commands: number
  failed: number
  awaits: number
  contextPct: number | null
  durationMs: number
}
export interface PlanItem {
  content: string
  status: 'pending' | 'in_progress' | 'completed'
}
export type GatewayEvent = {
  seq: number
  eventId?: string
  sessionId: string
  turnId: string
  time?: string
} & (
  | { type: 'text_delta' | 'thinking_delta' | 'thinking_completed'; text: string }
  | {
      type: 'step_start'
      stepId: string
      tool: string
      kind: 'read' | 'act'
      title: string
      input: unknown
      pending?: boolean
    }
  | {
      type: 'step_end'
      stepId: string
      ok: boolean
      output: string
      exitCode?: number
      durationMs: number
      hint?: string
      errorCode?: string
      action?: ToolHintAction
    }
  | {
      type: 'await'
      awaitId: string
      mode: 'approval' | 'question'
      title: string
      detail: string
      risk?: string
      options?: { label: string; recommended?: boolean }[]
      version?: number
    }
  | { type: 'await_resolved'; awaitId: string; verdict: Verdict; note?: string }
  | { type: 'file_change'; path: string; diff: string }
  | { type: 'plan_update'; items: PlanItem[] }
  | { type: 'memory_added'; memoryId: string; text: string }
  | { type: 'job_update'; jobId: string; status: string; logTail: string }
  | { type: 'turn_end'; summary?: TurnSummary; status?: 'completed' | 'failed' | 'cancelled' }
  | { type: 'error'; message: string }
)
export interface Step {
  id: string
  tool: string
  kind: 'read' | 'act'
  title: string
  input: unknown
  output: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  durationMs: number
  startedAt?: number
  exitCode?: number
  hint?: string
  errorCode?: string
  action?: ToolHintAction
}
export interface AwaitItem {
  id: string
  sessionId: string
  turnId: string
  mode: 'approval' | 'question'
  title: string
  detail: string
  risk?: string
  options?: { label: string; recommended?: boolean }[]
  version: number
  verdict?: Verdict
  note?: string
  closed?: boolean
}
export interface RailNode {
  id: string
  kind: 'read' | 'act' | 'await' | 'end' | 'failed' | 'memory'
  title: string
  steps: Step[]
  await?: AwaitItem
  memoryId?: string
  running?: boolean
}
export interface Turn {
  id: string
  sessionId: string
  status: 'running' | 'waiting' | 'completed' | 'failed' | 'cancelled'
  startedAt: number
  endedAt?: number
  text: string
  thinking: string
  userText?: string
  messageId?: string
  steps: Step[]
  awaits: AwaitItem[]
  memories: { id: string; text: string }[]
  timeline: { id: string; kind: 'step' | 'await' | 'memory' | 'error' }[]
  changes: { path: string; diff: string }[]
  plan: PlanItem[]
  jobs: { id: string; status: string; logTail: string }[]
  error?: string
  summary?: TurnSummary
}
