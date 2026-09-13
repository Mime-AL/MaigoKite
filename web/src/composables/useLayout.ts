/**
 * 布局拖拽组合式函数
 *
 * 处理三栏布局中分隔线的拖拽调整宽度。
 */

import { ref, onMounted, onUnmounted } from 'vue'
import { useLayoutStore } from '@/stores/layout'

export function useLayout() {
  const layoutStore = useLayoutStore()
  const isDragging = ref(false)
  const dragStartX = ref(0)
  const dragStartWidth = ref(0)

  let onMouseMove: ((e: MouseEvent) => void) | null = null
  let onMouseUp: (() => void) | null = null

  /** 开始拖拽 */
  function startDrag(side: 'left' | 'right', startX: number, startWidth: number) {
    isDragging.value = true
    dragStartX.value = startX
    dragStartWidth.value = startWidth

    onMouseMove = (e: MouseEvent) => {
      if (!isDragging.value) return
      const delta = side === 'left' ? e.clientX - dragStartX.value : dragStartX.value - e.clientX
      const newWidth = dragStartWidth.value + delta
      if (side === 'left') {
        layoutStore.setSidebarWidth(newWidth)
      } else {
        layoutStore.setFileExplorerWidth(newWidth)
      }
    }

    onMouseUp = () => {
      isDragging.value = false
    }

    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('mouseup', onMouseUp)
  }

  /** 停止拖拽 */
  function stopDrag() {
    isDragging.value = false
    if (onMouseMove) document.removeEventListener('mousemove', onMouseMove)
    if (onMouseUp) document.removeEventListener('mouseup', onMouseUp)
    onMouseMove = null
    onMouseUp = null
  }

  onUnmounted(() => {
    stopDrag()
  })

  return {
    isDragging,
    startDrag,
    stopDrag
  }
}
