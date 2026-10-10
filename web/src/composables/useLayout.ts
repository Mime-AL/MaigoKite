/**
 * 布局拖拽组合式函数
 *
 * 处理三栏布局中分隔线的拖拽调整宽度。
 */

import { ref, onUnmounted } from 'vue'
import { useLayoutStore } from '@/stores/layout'

export function useLayout() {
  const layoutStore = useLayoutStore()
  const isDragging = ref(false)
  const dragStartX = ref(0)
  const dragStartWidth = ref(0)

  let onPointerMove: ((e: PointerEvent) => void) | null = null
  let onPointerEnd: ((e: PointerEvent) => void) | null = null
  let dragFrame = 0
  let pendingX: number | null = null
  let applyPendingDrag: (() => void) | null = null

  /** 开始拖拽 */
  function startDrag(
    side: 'left' | 'right',
    startX: number,
    startWidth: number,
    maximum = Infinity,
    pointerId?: number,
  ) {
    stopDrag()
    isDragging.value = true
    dragStartX.value = startX
    dragStartWidth.value = startWidth

    applyPendingDrag = () => {
      if (pendingX === null) return
      const delta = side === 'left' ? pendingX - dragStartX.value : dragStartX.value - pendingX
      const newWidth = Math.min(maximum, dragStartWidth.value + delta)
      if (side === 'left') layoutStore.setSidebarWidth(newWidth)
      else layoutStore.setFileExplorerWidth(newWidth)
      pendingX = null
    }

    onPointerMove = (e: PointerEvent) => {
      if (!isDragging.value || (pointerId !== undefined && e.pointerId !== pointerId)) return
      pendingX = e.clientX
      if (dragFrame) return
      dragFrame = requestAnimationFrame(() => {
        applyPendingDrag?.()
        dragFrame = 0
      })
    }

    document.addEventListener('pointermove', onPointerMove)
    onPointerEnd = (e: PointerEvent) => {
      if (pointerId === undefined || e.pointerId === pointerId) stopDrag()
    }
    document.addEventListener('pointerup', onPointerEnd)
    document.addEventListener('pointercancel', onPointerEnd)
    window.addEventListener('blur', stopDrag)
  }

  /** 停止拖拽 */
  function stopDrag() {
    if (dragFrame) cancelAnimationFrame(dragFrame)
    dragFrame = 0
    applyPendingDrag?.()
    applyPendingDrag = null
    if (isDragging.value) layoutStore.persistLayout()
    isDragging.value = false
    if (onPointerMove) document.removeEventListener('pointermove', onPointerMove)
    if (onPointerEnd) {
      document.removeEventListener('pointerup', onPointerEnd)
      document.removeEventListener('pointercancel', onPointerEnd)
    }
    window.removeEventListener('blur', stopDrag)
    onPointerMove = null
    onPointerEnd = null
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
