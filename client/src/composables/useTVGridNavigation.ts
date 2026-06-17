import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useDeviceStore } from '@/stores/device'

// 响应式计算每行显示的卡片数量
function calculateColumns(): number {
  const width = window.innerWidth
  if (width >= 1920) return 8
  if (width >= 1600) return 7
  if (width >= 1366) return 6
  if (width >= 1200) return 5
  if (width >= 992) return 4
  if (width >= 768) return 3
  return 2
}

export function useTVGridNavigation(containerSelector: string, itemSelector: string) {
  const deviceStore = useDeviceStore()
  const columns = ref(calculateColumns())
  const currentIndex = ref(0)
  const items = ref<HTMLElement[]>([])

  // 更新项目列表
  function updateItems() {
    const container = document.querySelector(containerSelector)
    if (container) {
      items.value = Array.from(container.querySelectorAll(itemSelector)) as HTMLElement[]
      columns.value = calculateColumns()
    }
  }

  // 清除焦点
  function clearFocus() {
    items.value.forEach(item => {
      item.classList.remove('tv-focus')
    })
  }

  // 设置焦点
  function setFocus(index: number) {
    if (index < 0 || index >= items.value.length) return

    clearFocus()
    currentIndex.value = index
    const item = items.value[index]
    item.classList.add('tv-focus')
    item.focus()

    // 确保焦点元素可见
    item.scrollIntoView({ block: 'nearest', inline: 'nearest' })
  }

  // 获取当前行的起始和结束索引
  function getRowBounds(index: number): { start: number; end: number } {
    const row = Math.floor(index / columns.value)
    const start = row * columns.value
    const end = Math.min(start + columns.value - 1, items.value.length - 1)
    return { start, end }
  }

  // 移动焦点
  function moveFocus(direction: 'up' | 'down' | 'left' | 'right') {
    if (items.value.length === 0) return

    const { start, end } = getRowBounds(currentIndex.value)
    let targetIndex = currentIndex.value

    switch (direction) {
      case 'up':
        // 尝试向上移动到上一行同列
        const upTarget = currentIndex.value - columns.value
        if (upTarget >= 0) {
          targetIndex = upTarget
        }
        break

      case 'down':
        // 尝试向下移动到下一行同列
        const downTarget = currentIndex.value + columns.value
        if (downTarget < items.value.length) {
          targetIndex = downTarget
        }
        break

      case 'left':
        // 向左移动到同行的前一个
        if (currentIndex.value > start) {
          targetIndex = currentIndex.value - 1
        }
        break

      case 'right':
        // 向右移动到同行的后一个
        if (currentIndex.value < end) {
          targetIndex = currentIndex.value + 1
        }
        break
    }

    setFocus(targetIndex)
  }

  // 键盘事件处理
  function handleKeyDown(e: KeyboardEvent) {
    if (!deviceStore.isTV) return

    const focused = document.activeElement as HTMLElement
    const isInGrid = focused?.closest(containerSelector)

    if (!isInGrid) return

    switch (e.key) {
      case 'ArrowUp':
        e.preventDefault()
        moveFocus('up')
        break
      case 'ArrowDown':
        e.preventDefault()
        moveFocus('down')
        break
      case 'ArrowLeft':
        e.preventDefault()
        moveFocus('left')
        break
      case 'ArrowRight':
        e.preventDefault()
        moveFocus('right')
        break
      case 'Enter':
      case ' ':
        // 触发点击事件
        if (focused) {
          focused.click()
        }
        break
    }
  }

  // 点击时设置焦点
  function handleItemClick(e: Event) {
    const target = e.target as HTMLElement
    const item = target.closest(itemSelector) as HTMLElement
    if (item) {
      const index = items.value.indexOf(item)
      if (index >= 0) {
        setFocus(index)
      }
    }
  }

  // 初始化
  function init() {
    if (!deviceStore.isTV) return

    // 等待 DOM 渲染完成
    nextTick(() => {
      updateItems()
      // 设置初始焦点到第一个项目
      if (items.value.length > 0) {
        setFocus(0)
      }
    })

    document.addEventListener('keydown', handleKeyDown)

    // 监听窗口大小变化，重新计算列数
    window.addEventListener('resize', () => {
      columns.value = calculateColumns()
    })
  }

  // 清理
  function cleanup() {
    document.removeEventListener('keydown', handleKeyDown)
    clearFocus()
  }

  onMounted(init)
  onUnmounted(cleanup)

  return {
    items,
    columns,
    currentIndex,
    setFocus,
    moveFocus,
    updateItems,
    clearFocus,
    init,
    cleanup
  }
}
