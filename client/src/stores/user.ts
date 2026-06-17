import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User } from '@/utils/api'
import { refreshToken as refreshTokenApi, isTokenExpiringSoon, isTokenExpired } from '@/utils/api'

let refreshTimer: number | null = null

export const useUserStore = defineStore('user', () => {
  const accessToken = ref<string>('')
  const refreshToken = ref<string>('')
  const userInfo = ref<User | null>(null)
  const isRefreshing = ref<boolean>(false)

  const isLoggedIn = computed(() => !!accessToken.value && !!userInfo.value)
  const user = computed(() => userInfo.value)

  // 启动 token 自动刷新检查
  function startAutoRefresh() {
    // 清除之前的定时器
    stopAutoRefresh()

    // 启动新的定时器，每分钟检查一次
    // 不立即检查，刚登录的 token 肯定是有效的
    refreshTimer = window.setInterval(async () => {
      await checkAndRefreshToken()
    }, 60000)
  }

  // 停止自动刷新
  function stopAutoRefresh() {
    if (refreshTimer !== null) {
      clearInterval(refreshTimer)
      refreshTimer = null
    }
  }

  // 检查并刷新 token
  async function checkAndRefreshToken(): Promise<void> {
    // 如果已经在刷新中，或者没有登录，就跳过
    if (isRefreshing.value || !isLoggedIn.value || !refreshToken.value) {
      return
    }

    try {
      // 检查是否过期或即将过期
      const token = accessToken.value || localStorage.getItem('access_token') || ''
      if (isTokenExpired(token)) {
        // token 已经过期，需要立即刷新
        await performTokenRefresh()
      } else if (isTokenExpiringSoon(token, 5)) {
        // token 5 分钟内即将过期，进行刷新
        await performTokenRefresh()
      }
    } catch (e) {
      console.error('Token refresh check failed:', e)
      // 刷新失败，退出登录
      logout()
    }
  }

  // 执行 token 刷新
  async function performTokenRefresh(): Promise<void> {
    if (!refreshToken.value || isRefreshing.value) {
      return
    }

    isRefreshing.value = true
    try {
      const newTokens = await refreshTokenApi(refreshToken.value)
      setTokens(newTokens.access_token, newTokens.refresh_token)
    } catch (e) {
      console.error('Failed to refresh token:', e)
      // 刷新失败，退出登录
      logout()
    } finally {
      isRefreshing.value = false
    }
  }

  function setLogin(access: string, refresh: string, newUser: User) {
    accessToken.value = access
    refreshToken.value = refresh
    userInfo.value = newUser
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
    localStorage.setItem('user', JSON.stringify(newUser))
    // 登录成功后启动自动刷新
    startAutoRefresh()
  }

  function setTokens(access: string, refresh: string) {
    accessToken.value = access
    refreshToken.value = refresh
    localStorage.setItem('access_token', access)
    localStorage.setItem('refresh_token', refresh)
  }

  function logout() {
    accessToken.value = ''
    refreshToken.value = ''
    userInfo.value = null
    isRefreshing.value = false
    // 登出时停止自动刷新
    stopAutoRefresh()
    // 清除存储
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user')
  }

  function updateUser(updates: Partial<User>) {
    if (userInfo.value) {
      userInfo.value = { ...userInfo.value, ...updates }
      localStorage.setItem('user', JSON.stringify(userInfo.value))
    }
  }

  function initFromStorage() {
    const savedAccessToken = localStorage.getItem('access_token')
    const savedRefreshToken = localStorage.getItem('refresh_token')
    const savedUser = localStorage.getItem('user')
    if (savedAccessToken && savedRefreshToken && savedUser) {
      try {
        accessToken.value = savedAccessToken
        refreshToken.value = savedRefreshToken
        userInfo.value = JSON.parse(savedUser)
        // 初始化时也启动自动刷新
        startAutoRefresh()
      } catch {
        logout()
      }
    } else if (localStorage.getItem('token')) {
      // 兼容旧的 token 格式
      const oldToken = localStorage.getItem('token')
      const oldUser = localStorage.getItem('user')
      if (oldToken && oldUser) {
        try {
          accessToken.value = oldToken
          userInfo.value = JSON.parse(oldUser)
          // 旧格式没有 refresh token，不启动自动刷新
        } catch {
          logout()
        }
      }
    }
  }

  return {
    accessToken,
    refreshToken,
    userInfo,
    isRefreshing,
    isLoggedIn,
    user,
    setLogin,
    setTokens,
    logout,
    updateUser,
    initFromStorage,
    startAutoRefresh,
    stopAutoRefresh
  }
})
