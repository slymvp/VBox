/**
 * 处理刘海屏安全区域
 * 确保在竖屏模式下内容区域不占用状态栏区域
 *
 * 策略：
 * 1. 在 :root 上设置 --safe-area-inset-top 和 --safe-area-inset-bottom CSS 变量
 * 2. 各组件通过 var(--safe-area-inset-top, 0px) 自行处理偏移
 * 3. 不在 body 上设置全局 padding（避免影响全屏页面）
 */

let initialized = false

export const handleSafeArea = () => {
  // 防止重复初始化
  if (initialized) return
  initialized = true

  // 在 :root 上定义 CSS 变量，使用 env() 作为默认值
  // 这样支持安全区域的浏览器会自动获取正确的值
  const styleEl = document.createElement('style')
  styleEl.setAttribute('data-safe-area', '')
  styleEl.innerHTML = `
    :root {
      --safe-area-inset-top: env(safe-area-inset-top, 0px);
      --safe-area-inset-bottom: env(safe-area-inset-bottom, 0px);
      --safe-area-inset-left: env(safe-area-inset-left, 0px);
      --safe-area-inset-right: env(safe-area-inset-right, 0px);
    }
  `
  document.head.appendChild(styleEl)

  // 移动端竖屏时，额外确保 body 不溢出到状态栏
  const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)

  if (!isMobile) return

  // 在移动端竖屏下，监听横竖屏切换以更新布局
  let wasPortrait = window.innerHeight > window.innerWidth

  const updateLayout = () => {
    const isPortrait = window.innerHeight > window.innerWidth

    if (isPortrait) {
      // 竖屏：设置顶部安全区域（body 不使用 padding，交给各组件处理）
      // 通过 CSS 变量已经传递了 safe-area-inset-top，各组件自行使用
    } else {
      // 横屏：清除顶部安全区域
      document.documentElement.style.setProperty('--safe-area-inset-top', '0px')
    }

    wasPortrait = isPortrait
  }

  // 监听窗口变化和屏幕旋转
  window.addEventListener('resize', updateLayout)
  window.addEventListener('orientationchange', () => {
    // orientationchange 后 resize 也会触发，这里做一次立即更新
    setTimeout(updateLayout, 100)
  })
}
