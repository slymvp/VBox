/**
 * 设备状态管理
 * 管理设备类型和平台信息（支持 Phone / Pad / PC / TV 四种设备类型）
 *
 * 移动端（Mobile）包含手机和平板，统一使用 MobileLayout。
 * 通过 deviceType 可以区分手机和 Pad，用于布局微调。
 */

import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { DeviceType, detectDevice } from '@/utils/device'

export const useDeviceStore = defineStore('device', () => {
  const deviceInfo = ref(detectDevice())
  // 强制TV模式：URL参数 ?tv=1 或 localStorage.forceTV=true
  const forceTV = ref(
    new URLSearchParams(window.location.search).get('tv') === '1' ||
    localStorage.getItem('forceTV') === 'true'
  )
  const platform = ref(import.meta.env.VITE_PLATFORM || 'mobile')

  // 计算属性
  const isTV = computed(() => forceTV.value || platform.value === 'tv' || deviceInfo.value.isTV)
  // PC：不是 TV，且检测结果是 PC
  const isPC = computed(() => !isTV.value && deviceInfo.value.isPC)
  // 移动端（含手机 + Pad）：不是 TV 也不是 PC
  const isMobile = computed(() => !isTV.value && !isPC.value)
  // 细粒度：是否 Pad
  const isPad = computed(() => !isTV.value && deviceInfo.value.isPad)

  const deviceType = computed(() => {
    if (isTV.value) return DeviceType.TV
    if (isPC.value) return DeviceType.PC
    // 移动端细分
    return deviceInfo.value.type
  })

  // 监听 isTV 变化，自动更新 body 类
  watch(isTV, (tvMode) => {
    if (tvMode) {
      document.body.classList.add('tv-mode')
    } else {
      document.body.classList.remove('tv-mode')
    }
  }, { immediate: true })

  // 更新设备信息
  function updateDeviceInfo() {
    deviceInfo.value = detectDevice()
  }

  // 节流后的设备信息更新
  let resizeTimer: ReturnType<typeof setTimeout> | null = null
  const throttledUpdate = () => {
    if (resizeTimer) clearTimeout(resizeTimer)
    resizeTimer = setTimeout(updateDeviceInfo, 200)
  }

  // 监听窗口大小变化（节流处理）
  if (typeof window !== 'undefined') {
    window.addEventListener('resize', throttledUpdate)
    // 页面卸载时移除监听
    window.addEventListener('beforeunload', () => {
      window.removeEventListener('resize', throttledUpdate)
      if (resizeTimer) clearTimeout(resizeTimer)
    })
  }

  return {
    deviceInfo,
    platform,
    forceTV,
    isTV,
    isPC,
    isPad,
    isMobile,
    deviceType,
    updateDeviceInfo,
  }
})
