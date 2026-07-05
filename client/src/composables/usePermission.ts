import { useUserStore } from '@/stores/user'
import type { Series, Episode } from '@/utils/api'

export const PermissionResult = {
  ALLOWED: 'allowed',
  NEED_LOGIN: 'need_login',
  NEED_VIP: 'need_vip'
}

export function usePermission() {
  const userStore = useUserStore()

  function isVipContent(vipLevel: number | undefined): boolean {
    return vipLevel !== undefined && vipLevel !== 0
  }

  function checkSeriesPermission(series: Series): string {
    if (!isVipContent(series.is_vip)) {
      return PermissionResult.ALLOWED
    }

    if (!userStore.isLoggedIn) {
      console.log('[Permission] 需要登录')
      return PermissionResult.NEED_LOGIN
    }

    const hasPerm = userStore.hasPermission()
    console.log('[Permission] checkSeriesPermission:', {
      isLoggedIn: userStore.isLoggedIn,
      isVip: userStore.isVip,
      vipStatus: userStore.vipStatus,
      hasPermission: hasPerm
    })
    if (!hasPerm) {
      return PermissionResult.NEED_VIP
    }

    return PermissionResult.ALLOWED
  }

  function checkEpisodePermission(series: Series, episode: Episode): string {
    const vipLevel = episode.is_vip !== undefined ? episode.is_vip : series.is_vip

    if (!isVipContent(vipLevel)) {
      return PermissionResult.ALLOWED
    }

    if (!userStore.isLoggedIn) {
      console.log('[Permission] 需要登录')
      return PermissionResult.NEED_LOGIN
    }

    const hasPerm = userStore.hasPermission()
    console.log('[Permission] checkEpisodePermission:', {
      isLoggedIn: userStore.isLoggedIn,
      isVip: userStore.isVip,
      vipStatus: userStore.vipStatus,
      hasPermission: hasPerm
    })
    if (!hasPerm) {
      return PermissionResult.NEED_VIP
    }

    return PermissionResult.ALLOWED
  }

  function canWatch(series: Series, episode?: Episode): boolean {
    if (episode) {
      return checkEpisodePermission(series, episode) === PermissionResult.ALLOWED
    }
    return checkSeriesPermission(series) === PermissionResult.ALLOWED
  }

  return {
    PermissionResult,
    checkSeriesPermission,
    checkEpisodePermission,
    canWatch
  }
}
