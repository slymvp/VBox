/**
 * TV 播放器焦点导航系统
 *
 * 将播放器界面分为多个"焦点区域"(zones)：
 *   - top-bar:     顶部栏按钮（返回、选集、详情、收藏、追剧）
 *   - bottom-bar:  底部栏按钮（上一集、播放/暂停、下一集、自动播、倍速、音量、全屏）
 *   - episodes:    选集面板按钮列表
 *   - detail-tabs: 详情面板 Tab（简介、演员、标签、关闭）
 *
 * 方向键行为：
 *   - 区域内 Left/Right:  在同区域按钮间水平移动
 *   - 区域内 Up/Down:     在同区域按钮间垂直移动（选集面板多行时）
 *   - 跨区域 Up/Down:     到达区域边界时跳转到相邻区域
 *   - Enter/Space:        触发当前焦点按钮的 click
 *
 * 特殊跳转规则：
 *   - top-bar Down  → bottom-bar
 *   - bottom-bar Up → top-bar
 *   - top-bar Down（选集面板打开时）→ episodes
 *   - top-bar Down（详情面板打开时）→ detail-tabs
 *   - episodes Up（第一行）→ top-bar（选集按钮）
 *   - detail-tabs Up → top-bar（详情按钮）
 */

import { ref, type Ref } from 'vue'

export type FocusZone = 'top-bar' | 'bottom-bar' | 'episodes' | 'detail-tabs' | 'video-overlay' | 'video'

interface ZoneInfo {
  /** 当前焦点索引 */
  currentIndex: number
  /** 可聚焦元素列表 */
  items: HTMLElement[]
  /** 区域内每行列数（用于上下导航），默认 1 */
  columns?: number
}

/** 全局焦点状态 */
const currentZone = ref<FocusZone>('video')
const currentZoneIndex = ref(0)

/** 各区域的可聚焦元素缓存 */
const zoneItems: Record<FocusZone, Ref<HTMLElement[]>> = {
  'top-bar': ref([]),
  'bottom-bar': ref([]),
  'episodes': ref([]),
  'detail-tabs': ref([]),
  'video-overlay': ref([]),
  'video': ref([]),
}

/** 各区域当前索引 */
const zoneIndex: Record<FocusZone, number> = {
  'top-bar': 0,
  'bottom-bar': 0,
  'episodes': 0,
  'detail-tabs': 0,
  'video-overlay': 0,
  'video': 0,
}

/** 选集面板 / 详情面板是否打开（由外部控制） */
const episodesOpen = ref(false)
const detailOpen = ref(false)

/** 5秒无操作自动回到视频区 */
let idleTimer: ReturnType<typeof setTimeout> | null = null
const IDLE_TIMEOUT = 5000

function resetIdleTimer() {
  if (idleTimer) { clearTimeout(idleTimer); idleTimer = null }
  if (currentZone.value === 'video') return
  idleTimer = setTimeout(() => {
    clearAllFocus()
    currentZone.value = 'video'
  }, IDLE_TIMEOUT)
}

/** 清除空闲计时器 */
function clearIdleTimer() {
  if (idleTimer) { clearTimeout(idleTimer); idleTimer = null }
}

/** 清除所有 TV 焦点样式 */
function clearAllFocus() {
  document.querySelectorAll('.tv-player-focus').forEach(el => {
    el.classList.remove('tv-player-focus')
  })
}

/** 设置某个元素的焦点样式 */
function applyFocus(zone: FocusZone, index: number) {
  const items = zoneItems[zone].value
  if (!items || items.length === 0) return false
  if (index < 0) index = 0
  if (index >= items.length) index = items.length - 1

  clearAllFocus()
  const el = items[index]
  if (!el) return false

  el.classList.add('tv-player-focus')
  el.focus({ preventScroll: false })

  // 滚动到可视区域
  el.scrollIntoView({ block: 'nearest', inline: 'nearest' })

  currentZone.value = zone
  currentZoneIndex.value = index
  zoneIndex[zone] = index

  // 焦点移动后重置空闲计时器
  resetIdleTimer()
  return true
}

/** 刷新某个区域的可聚焦元素列表 */
function refreshZone(zone: FocusZone, selector: string, container?: string) {
  let root: Document | HTMLElement = document
  if (container) {
    const el = document.querySelector(container)
    if (!el) {
      zoneItems[zone].value = []
      return
    }
    root = el as HTMLElement
  }
  const items = Array.from(root.querySelectorAll<HTMLElement>(selector))
  // 过滤掉不可见的元素
  const visibleItems = items.filter(el => {
    if (el.style.display === 'none') return false
    if (el.offsetParent === null && el.getClientRects().length === 0) return false
    return true
  })
  zoneItems[zone].value = visibleItems
}

/** 刷新所有区域（根据当前打开状态决定哪些区域可聚焦） */
function refreshAllZones() {
  // 顶部栏：只聚焦有 data-tv-focus 标记的按钮
  refreshZone('top-bar', '.top-bar [data-tv-focus]')
  // 底部栏
  refreshZone('bottom-bar', '.bottom-bar [data-tv-focus]')

  // 视频覆盖层（加载中/失败/缓冲中的"切换线路"按钮）
  refreshZone('video-overlay', '.load-overlay [data-tv-focus], .video-buffering-overlay [data-tv-focus]')

  if (episodesOpen.value) {
    refreshZone('episodes', '.ep-panel-item', '.episodes-panel')
  } else {
    zoneItems['episodes'].value = []
  }

  if (detailOpen.value) {
    refreshZone('detail-tabs', '.detail-tabs [data-tv-focus], .detail-close-btn', '.detail-panel')
  } else {
    zoneItems['detail-tabs'].value = []
  }
}

/** 获取当前应活跃的区域（优先级：选集面板 > 详情面板 > 视频覆盖层 > 顶部栏/底部栏） */
function getActiveZone(): FocusZone {
  if (episodesOpen.value && zoneItems['episodes'].value.length > 0) return 'episodes'
  if (detailOpen.value && zoneItems['detail-tabs'].value.length > 0) return 'detail-tabs'
  if (zoneItems['video-overlay'].value.length > 0) return 'video-overlay'
  return currentZone.value === 'video' ? 'top-bar' : currentZone.value
}

/**
 * 在指定区域内移动焦点
 * @returns true 如果成功移动，false 如果到达区域边界
 */
function moveInZone(zone: FocusZone, direction: 'up' | 'down' | 'left' | 'right'): boolean {
  const items = zoneItems[zone].value
  if (!items || items.length === 0) return false

  const currentIdx = zoneIndex[zone]
  let targetIdx = currentIdx

  // 计算选集面板的列数（基于实际渲染位置）
  if (zone === 'episodes' && (direction === 'up' || direction === 'down')) {
    const cols = calculateEpisodeColumns(currentIdx, items)
    if (direction === 'up') {
      targetIdx = currentIdx - cols
    } else {
      targetIdx = currentIdx + cols
    }
    if (targetIdx < 0 || targetIdx >= items.length) return false
    applyFocus(zone, targetIdx)
    return true
  }

  // 水平导航
  if (direction === 'left') {
    if (currentIdx <= 0) return false
    targetIdx = currentIdx - 1
  } else if (direction === 'right') {
    if (currentIdx >= items.length - 1) return false
    targetIdx = currentIdx + 1
  } else if (direction === 'up' || direction === 'down') {
    // 顶部栏 / 底部栏 / 详情 Tab 都是单行水平排列，上下是跨区域跳转
    return false
  }

  applyFocus(zone, targetIdx)
  return true
}

/** 计算选集面板中当前索引所在行的列数 */
function calculateEpisodeColumns(index: number, items: HTMLElement[]): number {
  if (index < 0 || index >= items.length) return 1
  const currentTop = Math.round(items[index].getBoundingClientRect().top)
  // 计算同行有多少个元素
  let count = 0
  for (let i = 0; i < items.length; i++) {
    if (Math.round(items[i].getBoundingClientRect().top) === currentTop) {
      count++
    }
  }
  return Math.max(1, count)
}

/** 跨区域跳转 */
function moveAcrossZones(direction: 'up' | 'down'): boolean {
  const zone = currentZone.value

  if (direction === 'down') {
    switch (zone) {
      case 'top-bar':
        // 选集面板打开 → 进入选集
        if (episodesOpen.value && zoneItems['episodes'].value.length > 0) {
          return applyFocus('episodes', 0)
        }
        // 详情面板打开 → 进入详情 Tab
        if (detailOpen.value && zoneItems['detail-tabs'].value.length > 0) {
          return applyFocus('detail-tabs', 0)
        }
        // 视频覆盖层（切换线路按钮）→ 进入覆盖层
        if (zoneItems['video-overlay'].value.length > 0) {
          return applyFocus('video-overlay', 0)
        }
        // 默认 → 底部栏
        if (zoneItems['bottom-bar'].value.length > 0) {
          return applyFocus('bottom-bar', 0)
        }
        return false
      case 'video-overlay':
        // 覆盖层向下 → 底部栏
        if (zoneItems['bottom-bar'].value.length > 0) {
          return applyFocus('bottom-bar', 0)
        }
        return false
      case 'episodes':
        // 选集面板最后一行向下 → 底部栏
        return applyFocus('bottom-bar', 0)
      case 'detail-tabs':
        // 详情 Tab 向下不动（面板内容是只读的）
        return false
      case 'bottom-bar':
        return false
    }
  } else if (direction === 'up') {
    switch (zone) {
      case 'bottom-bar':
        // 选集面板打开 → 回到选集面板
        if (episodesOpen.value && zoneItems['episodes'].value.length > 0) {
          const epItems = zoneItems['episodes'].value
          const lastIdx = epItems.length - 1
          return applyFocus('episodes', lastIdx)
        }
        // 详情面板打开 → 回到详情 Tab
        if (detailOpen.value && zoneItems['detail-tabs'].value.length > 0) {
          return applyFocus('detail-tabs', zoneIndex['detail-tabs'])
        }
        // 视频覆盖层 → 回到覆盖层
        if (zoneItems['video-overlay'].value.length > 0) {
          return applyFocus('video-overlay', 0)
        }
        // 默认 → 顶部栏
        if (zoneItems['top-bar'].value.length > 0) {
          return applyFocus('top-bar', zoneIndex['top-bar'])
        }
        return false
      case 'video-overlay':
        // 覆盖层向上 → 顶部栏
        if (zoneItems['top-bar'].value.length > 0) {
          return applyFocus('top-bar', zoneIndex['top-bar'])
        }
        return false
      case 'episodes':
        // 选集面板第一行向上 → 顶部栏（聚焦选集按钮）
        const epItems = zoneItems['episodes'].value
        const currentEpIdx = zoneIndex['episodes']
        const cols = calculateEpisodeColumns(currentEpIdx, epItems)
        if (currentEpIdx < cols) {
          // 回到顶部栏，尝试聚焦选集按钮
          return focusTopBarButton('episodes-btn') || applyFocus('top-bar', 0)
        }
        return false
      case 'detail-tabs':
        // 详情 Tab 向上 → 顶部栏（聚焦详情按钮）
        return focusTopBarButton('detail-btn') || applyFocus('top-bar', 0)
      case 'top-bar':
        return false
    }
  }
  return false
}

/** 尝试聚焦顶部栏中指定 data-tv-zone 的按钮 */
function focusTopBarButton(tvZone: string): boolean {
  const items = zoneItems['top-bar'].value
  const idx = items.findIndex(el => el.dataset.tvZone === tvZone)
  if (idx >= 0) return applyFocus('top-bar', idx)
  return false
}

/** 主键盘处理：由播放页在 TV 模式下调用 */
function handleKeyDown(e: KeyboardEvent): boolean {
  const key = e.key
  const zone = currentZone.value

  // 选集/详情面板打开时的特殊处理
  const activeZone = getActiveZone()
  if (activeZone !== zone) {
    currentZone.value = activeZone
  }

  // 每次有效按键重置空闲计时器
  resetIdleTimer()

  switch (key) {
    case 'ArrowUp': {
      e.preventDefault()
      refreshAllZones()
      const moved = moveInZone(currentZone.value, 'up')
      if (!moved) moveAcrossZones('up')
      return true
    }
    case 'ArrowDown': {
      e.preventDefault()
      refreshAllZones()
      const moved = moveInZone(currentZone.value, 'down')
      if (!moved) moveAcrossZones('down')
      return true
    }
    case 'ArrowLeft': {
      e.preventDefault()
      const moved = moveInZone(currentZone.value, 'left')
      if (!moved) {
        // 选集面板向左到边界时不跳转
        // 底部栏向左到边界 → 不跳转
      }
      return true
    }
    case 'ArrowRight': {
      e.preventDefault()
      const moved = moveInZone(currentZone.value, 'right')
      if (!moved) {
        // 向右到边界不跳转
      }
      return true
    }
    case 'Enter':
    case ' ': {
      e.preventDefault()
      const items = zoneItems[currentZone.value].value
      const el = items[zoneIndex[currentZone.value]]
      if (el) {
        el.click()
      }
      return true
    }
  }
  return false
}

/** 进入某个区域（打开面板后调用） */
function enterZone(zone: FocusZone, index = 0) {
  nextTickRefresh(() => {
    applyFocus(zone, index)
  })
}

/** 进入某个区域并通过 data-tv-zone 指定默认聚焦的按钮 */
function enterZoneByDataZone(zone: FocusZone, tvZone: string) {
  nextTickRefresh(() => {
    const items = zoneItems[zone].value
    const idx = items.findIndex(el => el.dataset.tvZone === tvZone)
    if (idx >= 0) {
      applyFocus(zone, idx)
    } else {
      applyFocus(zone, 0)
    }
  })
}

/** 延迟刷新并聚焦（等待 DOM 更新） */
function nextTickRefresh(cb: () => void) {
  requestAnimationFrame(() => {
    refreshAllZones()
    cb()
  })
}

/** 设置选集/详情面板打开状态，并自动刷新 */
function setEpisodesOpen(open: boolean) {
  episodesOpen.value = open
  if (open) {
    nextTickRefresh(() => {
      // 默认聚焦当前播放集
      const items = zoneItems['episodes'].value
      if (items.length > 0) {
        const activeIdx = items.findIndex(el => el.classList.contains('active'))
        applyFocus('episodes', activeIdx >= 0 ? activeIdx : 0)
      }
    })
  } else {
    // 关闭面板：同步清空 + 刷新 + 恢复焦点（避免异步间隙导致 currentZone 不一致无法走焦）
    zoneItems['episodes'].value = []
    refreshAllZones()
    focusTopBarButton('episodes-btn')
  }
}

function setDetailOpen(open: boolean) {
  detailOpen.value = open
  if (open) {
    nextTickRefresh(() => {
      applyFocus('detail-tabs', 0)
    })
  } else {
    // 关闭面板：同步清空 + 刷新 + 恢复焦点到详情按钮
    zoneItems['detail-tabs'].value = []
    refreshAllZones()
    focusTopBarButton('detail-btn')
  }
}

/** 初始化：聚焦顶部栏第一个元素 */
function initFocus() {
  nextTickRefresh(() => {
    const activeZone = getActiveZone()
    applyFocus(activeZone, 0)
  })
}

/** 清除焦点 */
function clearFocus() {
  clearAllFocus()
  clearIdleTimer()
  currentZone.value = 'video'
}

export function useTVPlayerFocus() {
  return {
    currentZone,
    currentZoneIndex,
    episodesOpen,
    detailOpen,
    refreshAllZones,
    handleKeyDown,
    enterZone,
    enterZoneByDataZone,
    setEpisodesOpen,
    setDetailOpen,
    initFocus,
    clearFocus,
    applyFocus,
    zoneItems,
    resetIdleTimer,
    clearIdleTimer,
  }
}
