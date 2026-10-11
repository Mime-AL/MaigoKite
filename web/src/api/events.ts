import type { TaskInput } from './client'

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
export interface SupplementInput extends TaskInput {
  seq?: number
  sentAsTaskId?: string
}
export interface TokenUsage {
  input_tokens?: number
  output_tokens?: number
  total_tokens?: number
  cache_read_tokens?: number
  cache_creation_tokens?: number
  cache_miss_tokens?: number
  reasoning_tokens?: number
}
export interface ModelTiming {
  durationMs?: number
  firstTokenMs?: number
  decodeMs?: number
}
export interface ModelCall extends ModelTiming {
  id: string
  purpose: string
  seq: number
  usage?: TokenUsage
  failed?: boolean
}
export interface ContextUsage {
  seq: number
  callId: string
  modelName: string
  usedTokens: number | null
  windowTokens: number | null
  measurement: 'estimate' | 'provider'
}
export type GatewayEvent = {
  seq: number
  eventId?: string
  sessionId: string
  turnId: string
  time?: string
} & (
  | { type: 'model_start' | 'model_failed'; callId: string; purpose: string }
  | ({ type: 'model_end'; callId: string; purpose: string; usage?: TokenUsage } & ModelTiming)
  | { type: 'context_update'; context: ContextUsage }
  | { type: 'thinking_started' }
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
      toolCallId?: string
    }
  | { type: 'await_resolved'; awaitId: string; verdict: Verdict; note?: string }
  | { type: 'question_answered'; awaitId: string; answer: string }
  | { type: 'file_change'; path: string; diff: string }
  | { type: 'plan_update'; items: PlanItem[] }
  | { type: 'input_update'; input: TaskInput }
  | { type: 'memory_added'; memoryId: string; text: string }
  | { type: 'job_update'; jobId: string; status: string; logTail: string }
  | { type: 'turn_resumed' }
  | { type: 'turn_waiting' }
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
  answer?: string
  note?: string
  closed?: boolean
  // Presentation association/order only; never an approval authorization fact.
  toolCallId?: string
  seq?: number
  time?: string
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
  thinkingStatus?: 'running' | 'completed'
  userText?: string
  messageId?: string
  steps: Step[]
  awaits: AwaitItem[]
  memories: { id: string; text: string }[]
  timeline: {
    id: string
    kind: 'step' | 'await' | 'memory' | 'error'
    seq?: number
    time?: string
  }[]
  changes: { path: string; diff: string }[]
  plan: PlanItem[]
  planSeq?: number
  planLoading?: boolean
  planError?: string
  inputs?: SupplementInput[]
  inputsLoading?: boolean
  inputsError?: string
  jobs: { id: string; status: string; logTail: string }[]
  error?: string
  summary?: TurnSummary
  modelCalls?: Record<string, ModelCall>
  context?: ContextUsage
}
