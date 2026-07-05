/**
 * 平台统一入口 composable
 * 替代散落在各页面的 deviceStore.isX 判断
 *
 * 使用方式：
 *   const { platform, isTV, isPC, isMobile, focus, gesture } = usePlatform()
 *
 * 平台特定能力（focus/gesture）只在对应平台激活，其他平台为 no-op
 */

import { computed } from 'vue'
import { useDeviceStore } from '@/stores/device'

export type PlatformType = 'pc' | 'tv' | 'mobile'

export function usePlatform() {
  const deviceStore = useDeviceStore()

  const platform = computed<PlatformType>(() => {
    if (deviceStore.isTV) return 'tv'
    if (deviceStore.isPC) return 'pc'
    return 'mobile'
  })

  const isTV = computed(() => platform.value === 'tv')
  const isPC = computed(() => platform.value === 'pc')
  const isMobile = computed(() => platform.value === 'mobile')

  return {
    /** 当前平台类型 */
    platform,
    /** 是否 TV */
    isTV,
    /** 是否 PC */
    isPC,
    /** 是否移动端（含手机 + Pad） */
    isMobile,
    /** 是否 Pad */
    isPad: computed(() => deviceStore.isPad),
    /** 设备类型（细粒度） */
    deviceType: computed(() => deviceStore.deviceType),
  }
}
