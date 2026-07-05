/**
 * TV 端遥控器返回键监听 + 智能返回路由
 *
 * 监听 Backspace / Escape 键（遥控器返回键），根据当前页面路由
 * 跳转到正确的上级页面，保证 TV 端导航体验一致。
 *
 * 返回路由映射：
 *   /                    → 弹出退出应用确认弹窗
 *   /tv, /movie, ...     → /
 *   /search              → /
 *   /filter              → /
 *   /play/:cid           → router.back() → fallback /
 *   /login, /register    → router.back() → fallback /
 *   /user, /vip          → router.back() → fallback /
 */

import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

/** 页面返回路由映射表 */
const BACK_ROUTE_MAP: Record<string, string | null> = {
  '/tv': '/',
  '/movie': '/',
  '/variety': '/',
  '/cartoon': '/',
  '/child': '/',
  '/free': '/',
  '/search': '/',
  '/filter': '/',
}

/** 根路由列表 */
const ROOT_PATHS = ['/']

/** 播放页弹窗检测：返回 true 表示有弹窗打开，应阻止路由返回
 *  注意：只检测不关闭，关闭动作由播放页的 handleTVKeyDown 统一处理（避免双重关闭导致焦点丢失）
 *  这些弹窗都是 v-if 控制，元素存在即表示显示（不能用 offsetParent，因为 fixed 元素的 offsetParent 为 null） */
function hasPlayOverlays(): boolean {
  // 1. 权限弹窗（登录/VIP）
  if (document.querySelector('.permission-modal')) return true
  // 2. 详情面板
  if (document.querySelector('.detail-panel')) return true
  // 3. 选集面板
  if (document.querySelector('.episodes-panel')) return true
  return false
}

/** 执行退出应用 */
function exitApp() {
  // Capacitor 原生环境
  if (typeof (window as any).Capacitor !== 'undefined') {
    try {
      const { App: CapacitorApp } = require('@capacitor/app')
      CapacitorApp.exitApp()
      return
    } catch { /* fallthrough */ }
  }
  // Web 环境：尝试关闭窗口
  window.close()
}

export function useTVBackNavigation() {
  const router = useRouter()

  /** 是否显示退出确认弹窗 */
  const showExitDialog = ref(false)

  function handleBack(): boolean {
    const route = router.currentRoute.value
    const path = route.path

    // 已在根路由 → 弹出退出确认
    if (ROOT_PATHS.includes(path)) {
      showExitDialog.value = true
      return true
    }

    // 播放页特殊处理：任何弹窗打开时不路由返回，由播放页 handleTVKeyDown 关闭弹窗
    if (route.name === 'Play') {
      if (hasPlayOverlays()) return true
    }

    // 1. 查找映射表中的固定返回路由
    const mappedBack = BACK_ROUTE_MAP[path]
    if (mappedBack !== undefined) {
      if (mappedBack === null) {
        router.back()
        return true
      }
      router.push(mappedBack)
      return true
    }

    // 2. 播放页、登录、用户等 → 读取上一页路径直接跳转（用 push 而不用 back，避免 trap state 干扰）
    //    播放页特殊处理：若上一页是登录/注册等认证页，直接回首页，避免返回到登录页
    if (['Play', 'Login', 'Register', 'ForgotPassword', 'User', 'Vip'].includes(route.name as string)) {
      const back = (router.options.history.state as any)?.back
      const isAuthBack = back && typeof back === 'string' && (back.includes('/login') || back.includes('/register') || back.includes('/forgot-password'))
      if (isAuthBack || window.history.length <= 1) {
        router.push('/')
      } else if (back && typeof back === 'string') {
        router.push(back)
      } else {
        router.push('/')
      }
      return true
    }

    // 4. 兜底：router.back()
    router.back()
    return true
  }

  /** 确认退出 */
  function confirmExit() {
    showExitDialog.value = false
    exitApp()
  }

  /** 取消退出 */
  function cancelExit() {
    showExitDialog.value = false
  }

  function onKeyDown(e: KeyboardEvent) {
    if (e.key === 'Backspace' || e.key === 'Escape') {
      e.preventDefault()
      e.stopPropagation()
      handleBack()
    }
  }

  onMounted(() => {
    document.addEventListener('keydown', onKeyDown)
  })

  onUnmounted(() => {
    document.removeEventListener('keydown', onKeyDown)
  })

  return { handleBack, showExitDialog, confirmExit, cancelExit }
}
