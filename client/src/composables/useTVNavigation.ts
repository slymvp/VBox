import { ref, onMounted, onUnmounted, computed } from 'vue'

export interface FocusableElement {
  el: HTMLElement
  row: number
  col: number
  onEnter?: () => void
  onLeft?: () => void
  onRight?: () => void
  onUp?: () => void
  onDown?: () => void
}

export interface GridConfig {
  columns: number
  rowGap?: number
  colGap?: number
}

// 全局焦点状态
const currentFocus = ref<{ row: number; col: number } | null>(null)
const isTVMode = ref(false)

// 当前页面的焦点元素网格
const focusGrid = ref<FocusableElement[]>([])
const gridConfig = ref<GridConfig>({ columns: 6 })

export function useTVNavigation() {
  // 获取第一个可聚焦元素
  const firstFocusable = computed(() => {
    if (focusGrid.value.length === 0) return null
    return focusGrid.value[0]
  })

  // 获取最后一个可聚焦元素
  const lastFocusable = computed(() => {
    if (focusGrid.value.length === 0) return null
    return focusGrid.value[focusGrid.value.length - 1]
  })

  // 设置焦点网格
  function setFocusGrid(elements: HTMLElement[], config: GridConfig = { columns: 6 }) {
    gridConfig.value = config
    focusGrid.value = elements.map((el, index) => {
      const row = Math.floor(index / config.columns)
      const col = index % config.columns
      return { el, row, col }
    })
  }

  // 更新某个元素的焦点处理器
  function updateElementHandlers(row: number, col: number, handlers: Partial<FocusableElement>) {
    const element = focusGrid.value.find(e => e.row === row && e.col === col)
    if (element) {
      Object.assign(element, handlers)
    }
  }

  // 清除所有焦点样式
  function clearFocus() {
    document.querySelectorAll('.tv-focus').forEach(el => {
      el.classList.remove('tv-focus')
    })
    currentFocus.value = null
  }

  // 设置焦点到指定元素
  function setFocus(row: number, col: number) {
    const element = focusGrid.value.find(e => e.row === row && e.col === col)
    if (!element) return false

    // 清除旧的焦点
    clearFocus()

    // 设置新的焦点
    element.el.classList.add('tv-focus')
    element.el.focus()
    currentFocus.value = { row, col }

    // 滚动到可视区域
    element.el.scrollIntoView({ block: 'nearest', inline: 'nearest' })

    return true
  }

  // 移动焦点
  function moveFocus(direction: 'up' | 'down' | 'left' | 'right') {
    if (!currentFocus.value) {
      // 如果没有焦点，设置到第一个
      if (firstFocusable.value) {
        setFocus(firstFocusable.value.row, firstFocusable.value.col)
      }
      return
    }

    const { row, col } = currentFocus.value
    const cols = gridConfig.value.columns

    let targetRow = row
    let targetCol = col

    switch (direction) {
      case 'up':
        targetRow = row - 1
        break
      case 'down':
        targetRow = row + 1
        break
      case 'left':
        targetCol = col - 1
        break
      case 'right':
        targetCol = col + 1
        break
    }

    // 查找目标位置的元素
    let target = focusGrid.value.find(e => e.row === targetRow && e.col === targetCol)

    // 如果没找到同一行的，尝试在同一列找最近的元素
    if (!target) {
      if (direction === 'up') {
        target = [...focusGrid.value].reverse().find(e => e.row < row && e.col === col)
      } else if (direction === 'down') {
        target = focusGrid.value.find(e => e.row > row && e.col === col)
      } else if (direction === 'left') {
        target = focusGrid.value.filter(e => e.row === row).reverse().find(e => e.col < col)
      } else if (direction === 'right') {
        target = focusGrid.value.find(e => e.row === row && e.col > col)
      }
    }

    if (target) {
      setFocus(target.row, target.col)
    }
  }

  // 按下确认键
  function handleEnter() {
    if (!currentFocus.value) return
    const element = focusGrid.value.find(
      e => e.row === currentFocus.value!.row && e.col === currentFocus.value!.col
    )
    if (element?.onEnter) {
      element.onEnter()
    } else {
      // 默认行为：触发 click 事件
      element?.el.click()
    }
  }

  // 键盘事件处理
  function handleKeyDown(e: KeyboardEvent) {
    if (!isTVMode.value) return

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
        e.preventDefault()
        handleEnter()
        break
      case 'Backspace':
      case 'Escape':
        e.preventDefault()
        // 返回上一页
        window.history.back()
        break
    }
  }

  // 初始化 TV 模式
  function initTVMode() {
    isTVMode.value = true
    document.addEventListener('keydown', handleKeyDown)

    // 延迟设置初始焦点
    setTimeout(() => {
      if (firstFocusable.value) {
        setFocus(firstFocusable.value.row, firstFocusable.value.col)
      }
    }, 100)
  }

  // 退出 TV 模式
  function exitTVMode() {
    isTVMode.value = false
    clearFocus()
    document.removeEventListener('keydown', handleKeyDown)
  }

  onUnmounted(() => {
    document.removeEventListener('keydown', handleKeyDown)
  })

  return {
    currentFocus,
    isTVMode,
    focusGrid,
    gridConfig,
    setFocusGrid,
    updateElementHandlers,
    clearFocus,
    setFocus,
    moveFocus,
    handleEnter,
    initTVMode,
    exitTVMode,
    firstFocusable,
    lastFocusable
  }
}

// 快捷方式：直接在元素上启用 TV 焦点
export function setupTVElement(el: HTMLElement, options?: {
  onEnter?: () => void
  onLeft?: () => void
  onRight?: () => void
  onUp?: () => void
  onDown?: () => void
}) {
  if (!el) return

  // 标记为可聚焦
  el.setAttribute('tabindex', '0')
  el.dataset.tvFocusable = 'true'

  // 点击时获取焦点
  el.addEventListener('click', () => {
    el.classList.add('tv-focus')
  })

  return {
    update(newOptions?: {
      onEnter?: () => void
      onLeft?: () => void
      onRight?: () => void
      onUp?: () => void
      onDown?: () => void
    }) {
      if (newOptions) {
        Object.assign(options, newOptions)
      }
    },
    cleanup() {
      el.classList.remove('tv-focus')
      el.removeAttribute('data-tv-focusable')
    }
  }
}
