/**
 * 移动端系统返回按钮 / 手势拦截
 *
 * 拦截安卓系统返回键和 iOS 左滑返回手势，改为应用内路由返回。
 * 在首页时不做拦截，保留系统默认行为（退出/最小化）。
 *
 * 实现原理：
 * - 在每个非首页路由的 history 栈中插入虚拟 state，
 *   当用户触发系统返回（Android 返回键 / iOS 左滑手势）时，
 *   popstate 事件触发，我们拦截到后执行 router.back()
 * - 同时监听 touchstart/touchend 实现应用内左滑手势兜底
 */

import { useRouter } from 'vue-router'

export function useSystemBack() {
  const router = useRouter()

  // 首页路径
  const ROOT_PATHS = ['/', '/tv', '/movie', '/variety', '/cartoon', '/child', '/free']

  function isAtRoot(): boolean {
    return ROOT_PATHS.includes(router.currentRoute.value.path)
  }

  function handleBack(): boolean {
    if (isAtRoot()) return false

    // 播放页特殊处理：分集面板打开时先关闭面板
    if (router.currentRoute.value.name === 'Play') {
      const panel = document.querySelector('.episodes-panel') as HTMLElement | null
      if (panel && panel.style.display !== 'none' && panel.offsetParent !== null) {
        const closeBtn = panel.querySelector('.episodes-close-btn') as HTMLElement | null
        closeBtn?.click()
        return true
      }
    }

    router.back()
    return true
  }

  // ==================== 方案 1：Capacitor App ====================
  if (typeof (window as any).Capacitor !== 'undefined') {
    try {
      // eslint-disable-next-line @typescript-eslint/no-var-requires
      const { App: CapacitorApp } = require('@capacitor/app')
      CapacitorApp.addListener('backButton', () => {
        if (!handleBack()) {
          CapacitorApp.exitApp()
        }
      })
    } catch {
      setupWebIntercept()
    }
  } else {
    setupWebIntercept()
  }

  // ==================== 方案 2：Web 端拦截 ====================
  function setupWebIntercept() {
    let interceptActive = false

    // 在 history 栈中推一个虚拟条目作为"陷阱"
    function pushTrap() {
      if (!interceptActive) return
      // 先确保当前位置没有 trap state，避免重复 push
      if (history.state?.__vbox_trap) return
      history.pushState({ __vbox_trap: true, __vbox_path: window.location.hash }, '', window.location.hash)
    }

    // 清掉当前位置之后的所有 trap，避免栈污染
    function cleanTraps() {
      // 如果当前位置已经是 trap，先回退一步到真实页面
      while (history.state?.__vbox_trap) {
        history.back()
      }
    }

    // 路由变化时重新设置陷阱
    router.afterEach((to, from) => {
      if (ROOT_PATHS.includes(to.path)) {
        interceptActive = false
        cleanTraps()
      } else {
        interceptActive = true
        // 延迟 push，等 router 内部的 history 操作完成
        setTimeout(pushTrap, 100)
      }
    })

    // 初始状态
    if (!isAtRoot()) {
      interceptActive = true
      setTimeout(pushTrap, 150)
    }

    // 监听 popstate
    window.addEventListener('popstate', (e) => {
      if (e.state?.__vbox_trap) {
        // 命中陷阱 → 执行应用内返回
        if (handleBack()) {
          // 如果返回后还在非首页，重新设陷阱
          if (!isAtRoot()) {
            interceptActive = true
            setTimeout(pushTrap, 150)
          }
        }
        // 阻止浏览器默认行为：push 一个新状态来抵消 pop
        history.pushState({ __vbox_trap: true, __vbox_path: window.location.hash }, '', window.location.hash)
      }
    })

    // ==================== 应用内左滑手势兜底 ====================
    // 部分 WebView 环境 popstate 拦截不可靠，增加 touch 手势兜底
    let touchStartX = 0
    let touchStartY = 0
    let touchStarted = false

    document.addEventListener('touchstart', (e: TouchEvent) => {
      if (e.touches.length !== 1) return
      const t = e.touches[0]
      touchStartX = t.clientX
      touchStartY = t.clientY
      touchStarted = t.clientX <= 30 // 只在左侧边缘 30px 内触发
    }, { passive: true })

    document.addEventListener('touchend', (e: TouchEvent) => {
      if (!touchStarted) return
      touchStarted = false
      const t = e.changedTouches[0]
      const dx = t.clientX - touchStartX
      const dy = Math.abs(t.clientY - touchStartY)
      // 右滑超过 80px 且不是纵向滚动
      if (dx > 80 && dy < dx * 0.6) {
        handleBack()
      }
    }, { passive: true })
  }
}
