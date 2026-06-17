<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useDeviceStore } from '@/stores/device'
import { useThemeStore } from '@/stores/theme'
import { useSwipeBack } from './composables/useSwipeBack'
import { useSystemBack } from './composables/useSystemBack'
import Toast from './components/Toast.vue'
import MobileLayout from './layouts/MobileLayout.vue'
import PCLayout from './layouts/PCLayout.vue'
import TVLayout from './layouts/TVLayout.vue'
import { handleSafeArea } from './utils/handleSafeArea'

const deviceStore = useDeviceStore()
const themeStore = useThemeStore()
const route = useRoute()

// 播放页、搜索页、用户中心页不需要布局，直接铺满全屏
const isFullScreen = computed(() => ['Play', 'ForgotPassword', 'Search', 'User'].includes(route.name as string))

// 根据设备类型选择布局：TV → TVLayout, Mobile → MobileLayout, PC → PCLayout
const layoutComponent = computed(() => {
  if (deviceStore.isTV) return TVLayout
  if (deviceStore.isPC) return PCLayout
  return MobileLayout
})

// 路由到频道的映射（前缀匹配）
const ROUTE_CHANNEL_PREFIXES: [string, string][] = [
  ['/tv', 'tv'],
  ['/movie', 'movie'],
  ['/variety', 'variety'],
  ['/cartoon', 'cartoon'],
  ['/child', 'child'],
  ['/free', 'free'],
]
function getChannelFromPath(path: string): string {
  for (const [prefix, ch] of ROUTE_CHANNEL_PREFIXES) {
    if (path.startsWith(prefix)) return ch
  }
  return 'default'
}

// 监听路由变化，彩色模式下切换频道颜色
watch(() => route.path, (path) => {
  const channel = getChannelFromPath(path)
  themeStore.setChannel(channel)
}, { immediate: true })

// 初始化主题
onMounted(() => {
  themeStore.init()
  if (deviceStore.isMobile) {
    useSwipeBack()
    useSystemBack()
    // 处理刘海屏安全区域
    handleSafeArea()
  }
})
</script>

<style lang="scss">
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  min-height: 100%;
}

#app {
  min-height: 100vh;
  background-color: var(--background);
  color: var(--text-primary);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  transition: background-color 0.3s ease, color 0.3s ease;
}

:root {
  /* VIP尊贵主题色 - 橙色系 */
  --primary: linear-gradient(135deg, #f97316 0%, #ea580c 50%, #c2410c 100%);
  --primary-solid: #f97316;
  --primary-dark: #ea580c;

  /* 科技渐变 */
  --secondary: linear-gradient(135deg, #8b5cf6 0%, #6366f1 50%, #4f46e5 100%);
  --secondary-solid: #8b5cf6;

  /* 背景色系 - 纯白 */
  --background: #ffffff;
  --background-deep: #f3f1ed;
  --surface: #ffffff;
  --surface-hover: #f9f8f5;
  --surface-light: #fcfcfb;

  /* 文字色系 - 黑色/深灰 */
  --text-primary: #1a1a1a;
  --text-secondary: #666666;
  --text-muted: #999999;

  /* VIP金色系 */
  --gold: #e8c547;
  --gold-light: #f0d76a;
  --gold-dark: #c9a830;
  --gold-glow: rgba(232, 197, 71, 0.3);

  /* 边框 */
  --border: #e5e5e5;
  --border-light: #f0f0f0;

  /* 功能色 */
  --success: #22c55e;
  --warning: #f97316;
  --error: #ef4444;
  --info: #3b82f6;
}

/* 全局滚动条 */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: var(--background);
}

::-webkit-scrollbar-thumb {
  background: var(--surface-light);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--gold);
}

/* 隐藏移动端滚动条 */
@media screen and (max-width: 768px) {
  ::-webkit-scrollbar {
    display: none;
    width: 0;
    height: 0;
  }

  * {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }

  html, body {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }

  html, body, #app {
    overflow-x: hidden;
  }
}

/* 全局选中样式 */
::selection {
  background: var(--gold);
  color: var(--background);
}

/* 全局过渡动画 */
* {
  transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}

/* 确保所有图片透明背景 */
img {
  background-color: transparent !important;
  background: transparent !important;
  background-image: none !important;
  border: none;
  outline: none;
  box-shadow: none !important;
  filter: none !important;
  mix-blend-mode: normal;
  -webkit-backdrop-filter: none;
  backdrop-filter: none;
}

/* =============== 最强Header透明背景样式 =============== */
/* 使用最高优先级的选择器，确保任何情况下都不会被覆盖 */
/* 使用 body 作为父选择器，优先级更高 */
/* 注意：TV端使用 .tv-layout .header，移动端使用带透明度的样式 */

/* TV端Header（.tv-layout内的header）强制不透明 */
body.tv-mode header.header,
body.tv-mode .header,
.tv-layout header.header,
.tv-layout .header {
  background: #0a0a0f !important;
  background-color: #0a0a0f !important;
  background-image: none !important;
}

/* 非TV端：header 背景随主题变化（使用 CSS 变量） */
body:not(.tv-mode) #app header.header,
body:not(.tv-mode) #app .header {
  background: var(--header-bg-override, var(--surface)) !important;
  background-color: var(--header-bg-override, var(--surface)) !important;
}

body:not(.tv-mode) header[class*="header"] {
  background: var(--header-bg-override, var(--surface)) !important;
  background-color: var(--header-bg-override, var(--surface)) !important;
}

/* =============== TV适配样式 =============== */
/* TV界面样式适配 */
body {
  font-size: 24px; /* 增大字体以适应TV距离 */
  line-height: 1.5;
}

/* TV遥控器焦点样式 */
.focusable {
  outline: none;
}

.focusable:focus {
  outline: 3px solid var(--gold) !important; /* 使用主题色作为焦点边框 */
  outline-offset: 2px;
}

/* 按钮样式优化 */
button {
  padding: 15px 25px;
  margin: 10px;
  font-size: 24px;
  border-radius: 8px;
  background-color: var(--primary-solid);
  color: #ffffff;
  border: none;
  cursor: pointer;
  transition: all 0.3s ease;
}

button:hover, button:focus {
  background-color: var(--primary-dark);
  transform: scale(1.05);
}

/* 链接样式优化 */
a {
  color: var(--primary-solid);
  text-decoration: none;
  padding: 8px 16px;
  border-radius: 4px;
  transition: all 0.3s ease;
}

a:hover, a:focus {
  background-color: rgba(245, 158, 11, 0.1);
  color: var(--primary-dark);
}

/* 卡片样式优化 */
.card {
  background-color: var(--surface);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.card:hover, .card:focus-within {
  transform: translateY(-5px);
  box-shadow: 0 10px 15px rgba(0, 0, 0, 0.2);
}

/* 列表项样式优化 */
.list-item {
  padding: 15px 20px;
  margin-bottom: 10px;
  border-radius: 8px;
  background-color: var(--surface);
  transition: all 0.3s ease;
}

.list-item:hover, .list-item:focus {
  background-color: var(--surface-hover);
}

/* TV网格布局优化 */
.grid-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 20px;
  padding: 20px;
}

/* 响应式布局 - 适配不同尺寸的TV屏幕 */
@media (min-width: 1920px) {
  body {
    font-size: 28px;
  }

  .grid-container {
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 30px;
  }
}

@media (max-width: 1366px) {
  body {
    font-size: 20px;
  }

  .grid-container {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 15px;
  }
}

/* =============== 移动端手势返回提示条 =============== */
.swipe-back-indicator {
  position: fixed;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 60px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 0 2px 2px 0;
  z-index: 9999;
  transition: all 0.2s ease;
  opacity: 0;
  pointer-events: none;

  &.active {
    opacity: 1;
    background: rgba(232, 197, 71, 0.6);
  }
}

/* 仅在移动端显示手势提示 */
@media screen and (min-width: 769px) {
  .swipe-back-indicator {
    display: none;
  }
}
</style>

<template>
  <component v-if="!isFullScreen" :is="layoutComponent">
    <RouterView />
  </component>
  <RouterView v-else />
  <Toast />
</template>
