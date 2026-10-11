// Inline controls disappear after resolution; do not leave keyboard focus on body.
export function awaitFocus(card: HTMLElement | null): () => void {
  const focused = document.activeElement
  if (!(focused instanceof HTMLElement) || !card?.contains(focused)) return () => {}
  const node = card.closest('[data-await-anchor]')?.querySelector<HTMLElement>('.node-button')
  const pending = card.closest('.pending-tab')
  return () => {
    if (
      focused.isConnected ||
      (document.activeElement !== document.body && document.activeElement?.isConnected)
    )
      return
    const targets = [
      node,
      pending?.querySelector<HTMLElement>('[data-await-action]:not(:disabled)'),
      pending?.querySelector<HTMLElement>('.pending-heading button'),
      document.querySelector<HTMLElement>('.composer textarea'),
    ]
    targets
      .find(
        (target) =>
          target?.isConnected && !target.closest('[inert]') && target.getClientRects().length,
      )
      ?.focus({ preventScroll: true })
  }
}
