import { readonly, shallowRef } from 'vue'

interface Confirmation { message: string; danger: boolean }
const pending = shallowRef<Confirmation | null>(null)
export const confirmation = readonly(pending)
let resolve: ((accepted: boolean) => void) | undefined

/** Presentation-only replacement for window.confirm; no business action runs here. */
export function confirmAction(message: string, danger = true): Promise<boolean> {
  resolve?.(false)
  return new Promise<boolean>(settle => {
    resolve = settle
    pending.value = { message, danger }
  })
}
export function settleConfirmation(accepted: boolean) {
  const settle = resolve
  resolve = undefined
  pending.value = null
  settle?.(accepted)
}
