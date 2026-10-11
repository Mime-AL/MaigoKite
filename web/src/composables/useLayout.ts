/**
 * 布局拖拽组合式函数
 *
 * 处理三栏布局中分隔线的拖拽调整宽度。
 */

import { nextTick, ref, onUnmounted } from 'vue'
import { panelWidths, useLayoutStore } from '@/stores/layout'
import { layoutPixels } from '@/utils/layout-media'

export function useLayout() {
  const layoutStore = useLayoutStore()
  const isDragging = ref(false)

  let detach: (() => void) | null = null
  let commit: (() => void) | null = null
  function visibilityChanged() {
    if (document.hidden) stopDrag()
  }

  /** 开始拖拽 */
  function startDrag(
    side: 'left' | 'right',
    startX: number,
    startWidth: number,
    maximum = Infinity,
    pointerId?: number,
    panel?: HTMLElement,
  ) {
    stopDrag()
    let width = startWidth
    const originalWidth = panel?.style.width ?? ''
    const handle = panel?.querySelector<HTMLElement>(':scope > .resize-handle')
    const drawer = side === 'left'
      ? panel?.parentElement?.querySelector<HTMLElement>('#work-drawer')
      : null
    const peer = drawer && drawer.getClientRects().length && getComputedStyle(drawer).position !== 'fixed'
      ? drawer : null
    const peerWidth = peer?.getBoundingClientRect().width ?? 0
    const originalPeerWidth = peer?.style.width ?? ''
    const available = window.innerWidth - layoutPixels('--chat-min-width')
    function apply(x: number) {
      const delta = side === 'left' ? x - startX : startX - x
      width = Math.max(panelWidths[side].min, Math.min(maximum, startWidth + delta))
      // Local DOM writes keep the gesture off the app-wide reactive render path.
      if (panel) panel.style.width = `${width}px`
      handle?.setAttribute('aria-valuenow', String(Math.round(width)))
      if (peer) {
        const limit = Math.max(panelWidths.right.min, available - width)
        peer.style.width = `${peer.classList.contains('wide') ? limit : Math.min(peerWidth, limit)}px`
      }
    }
    function move(e: MouseEvent | PointerEvent) {
      if (!isDragging.value || (pointerId !== undefined &&
        (!(e instanceof PointerEvent) || e.pointerId !== pointerId))) return
      if (!(e.buttons & 1)) return stopDrag()
      apply(e.clientX)
    }
    function end(e: MouseEvent | PointerEvent) {
      if (pointerId !== undefined && (!(e instanceof PointerEvent) || e.pointerId !== pointerId)) return
      if (pointerId === undefined && e instanceof PointerEvent && e.pointerType !== 'mouse') return
      if (e.type === 'pointerup' || e.type === 'mouseup') apply(e.clientX)
      stopDrag()
    }
    const moveEvent = pointerId === undefined ? 'mousemove' : 'pointermove'
    const endEvent = pointerId === undefined ? 'mouseup' : 'pointerup'
    document.addEventListener(moveEvent, move, true)
    document.addEventListener(endEvent, end, true)
    document.addEventListener('pointercancel', end, true)
    document.addEventListener('visibilitychange', visibilityChanged)
    window.addEventListener('blur', stopDrag)
    window.addEventListener('resize', stopDrag)
    detach = () => {
      document.removeEventListener(moveEvent, move, true)
      document.removeEventListener(endEvent, end, true)
      document.removeEventListener('pointercancel', end, true)
      document.removeEventListener('visibilitychange', visibilityChanged)
      window.removeEventListener('blur', stopDrag)
      window.removeEventListener('resize', stopDrag)
    }
    commit = () => {
      if (side === 'left') layoutStore.setSidebarWidth(width)
      else layoutStore.setFileExplorerWidth(width)
      layoutStore.persistLayout()
      // Restore CSS ownership only after the committed layout reaches the DOM.
      void nextTick(() => {
        if (panel) panel.style.width = originalWidth
        if (peer) peer.style.width = originalPeerWidth
      })
    }
    isDragging.value = true
  }

  /** 停止拖拽 */
  function stopDrag() {
    detach?.()
    detach = null
    const finish = commit
    commit = null
    finish?.()
    isDragging.value = false
  }

  onUnmounted(() => {
    stopDrag()
  })

  return {
    isDragging,
    startDrag,
    stopDrag,
  }
}
