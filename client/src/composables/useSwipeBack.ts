/**
 * 移动端手势返回组件
 * 监听从屏幕左侧边缘向右滑动的手势，触发返回上一页
 */

import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

export function useSwipeBack() {
  const router = useRouter()

  let startX = 0
  let startY = 0
  let isSwiping = false

  // 配置参数
  const edgeThreshold = 20 // 左侧边缘阈值（px）
  const swipeThreshold = 100 // 滑动距离阈值（px）
  const verticalThreshold = 50 // 纵向偏移阈值（px）

  // 显示/隐藏滑动提示条
  const showIndicator = (show: boolean) => {
    let indicator = document.querySelector('.swipe-back-indicator')
    if (!indicator) {
      indicator = document.createElement('div')
      indicator.className = 'swipe-back-indicator'
      document.body.appendChild(indicator)
    }
    indicator.classList.toggle('active', show)
  }

  // 触摸开始
  const handleTouchStart = (e: TouchEvent) => {
    const touch = e.touches[0]
    // 只有从左侧边缘开始的触摸才触发
    if (touch.clientX <= edgeThreshold) {
      startX = touch.clientX
      startY = touch.clientY
      isSwiping = true
      showIndicator(true)
    }
  }

  // 触摸移动
  const handleTouchMove = (e: TouchEvent) => {
    if (!isSwiping) return

    const touch = e.touches[0]
    const deltaY = Math.abs(touch.clientY - startY)

    // 纵向偏移过大，取消手势（避免与滚动冲突）
    if (deltaY > verticalThreshold) {
      isSwiping = false
      showIndicator(false)
    }
  }

  // 触摸结束
  const handleTouchEnd = (e: TouchEvent) => {
    if (!isSwiping) return

    const touch = e.changedTouches[0]
    const deltaX = touch.clientX - startX

    // 滑动距离超过阈值，且有上一页时触发返回
    if (deltaX > swipeThreshold) {
      if (router.options.history.state.back) {
        router.back()
      }
    }

    isSwiping = false
    showIndicator(false)
  }

  onMounted(() => {
    document.addEventListener('touchstart', handleTouchStart, { passive: true })
    document.addEventListener('touchmove', handleTouchMove, { passive: true })
    document.addEventListener('touchend', handleTouchEnd, { passive: true })
  })

  onUnmounted(() => {
    document.removeEventListener('touchstart', handleTouchStart)
    document.removeEventListener('touchmove', handleTouchMove)
    document.removeEventListener('touchend', handleTouchEnd)
  })
}
