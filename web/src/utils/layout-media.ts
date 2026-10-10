/** Values originate in _breakpoints.scss, exported by tokens.scss. */
export function layoutBreakpoint(panel: 'drawer' | 'sidebar'): number {
  return Number.parseFloat(getComputedStyle(document.documentElement)
    .getPropertyValue(`--breakpoint-${panel}`))
}
export function overlayPanel(panel: 'drawer' | 'sidebar', width = window.innerWidth): boolean {
  const boundary = layoutBreakpoint(panel)
  return panel === 'drawer' ? width <= boundary : width < boundary
}
export function layoutPixels(token: string): number {
  return Number.parseFloat(getComputedStyle(document.documentElement).getPropertyValue(token)) || 0
}
