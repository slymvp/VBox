<template>
  <div class="mobile-layout">
    <header v-if="!isAuthPage" class="sticky-header">
      <MobileHeader />
      <ChannelBar ref="channelBarRef" />
    </header>
    <main ref="contentRef" class="content">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import MobileHeader from '@/components/mobile/Header.vue'
import ChannelBar from '@/components/mobile/ChannelBar.vue'
import { handleSafeArea } from '@/utils/handleSafeArea'

const route = useRoute()
const channelBarRef = ref<InstanceType<typeof ChannelBar> | null>(null)
const contentRef = ref<HTMLElement | null>(null)

// 登录/注册页面需要隐藏header
const isAuthPage = computed(() => {
  return ['Login', 'Register', 'ForgotPassword'].includes(route.name as string)
})

// 是否启用频道切换手势（只在分类页面启用）
const enableSwipe = computed(() => {
  const path = route.path
  return path === '/tv' || path === '/movie' || path === '/variety' ||
         path === '/cartoon' || path === '/child' || path === '/free'
})

// 触摸滑动切换频道
const startX = ref(0)
const startY = ref(0)
const isTracking = ref(false)
const swipeThreshold = 50 // 滑动阈值

const handleTouchStart = (e: TouchEvent) => {
  if (!enableSwipe.value) return
  const touch = e.touches[0]
  startX.value = touch.clientX
  startY.value = touch.clientY
  isTracking.value = true
}

const handleTouchEnd = (e: TouchEvent) => {
  if (!isTracking.value) return
  isTracking.value = false

  const touch = e.changedTouches[0]
  const deltaX = touch.clientX - startX.value
  const deltaY = touch.clientY - startY.value

  // 只有水平滑动幅度大于垂直滑动幅度才触发频道切换
  if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > swipeThreshold) {
    if (deltaX < 0) {
      // 左滑 -> 下一个频道
      channelBarRef.value?.switchToNextChannel()
    } else {
      // 右滑 -> 上一个频道
      channelBarRef.value?.switchToPrevChannel()
    }
  }
}

onMounted(() => {
  // 处理刘海屏安全区域
  handleSafeArea()

  if (contentRef.value) {
    contentRef.value.addEventListener('touchstart', handleTouchStart, { passive: true })
    contentRef.value.addEventListener('touchend', handleTouchEnd, { passive: true })
  }
})

onUnmounted(() => {
  if (contentRef.value) {
    contentRef.value.removeEventListener('touchstart', handleTouchStart)
    contentRef.value.removeEventListener('touchend', handleTouchEnd)
  }
})
</script>

<style lang="scss">
.mobile-layout {
  min-height: 100vh;
  background: var(--background);
}

.sticky-header {
  position: fixed;
  top: var(--safe-area-inset-top, 0px);
  left: 0;
  right: 0;
  z-index: 1000;
  background: var(--header-bg-override, var(--surface));
  transition: background 0.3s ease;

  // 用伪元素填充 safe-area 区域，避免露出 body 背景
  &::before {
    content: '';
    position: absolute;
    bottom: 100%;
    left: 0;
    right: 0;
    height: var(--safe-area-inset-top, 0px);
    background: var(--header-bg-override, var(--surface));
  }
}

.content {
  // header 48px + channelbar 32px - 8px 间距 + 安全区域
  padding-top: calc(72px + var(--safe-area-inset-top, 0px));
}

@media screen and (max-width: 480px) {
  .sticky-header {
    top: var(--safe-area-inset-top, 0px);
  }

  .content {
    // header 44px + channelbar 32px - 8px 间距 + 安全区域
    padding-top: calc(68px + var(--safe-area-inset-top, 0px));
  }
}
</style>
