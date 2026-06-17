// API_BASE
// 优先使用环境变量中定义的 API 地址，打包时通过 .env.production 配置
// 格式: VITE_API_BASE=http://192.168.1.100:8000/api
// 如果未配置，默认使用相对路径（同域部署场景）
export const API_BASE = (import.meta.env.VITE_API_BASE as string) || '/api'

// 调试日志：输出API地址
console.log('API_BASE:', API_BASE)
console.log('VITE_PLATFORM:', import.meta.env.VITE_PLATFORM)

export function getProxyImageUrl(url: string): string {
  if (!url) return ''
  return `${API_BASE}/proxy/image?url=${encodeURIComponent(url)}`
}

export interface Series {
  id: number
  cid: string
  title: string
  category_key: string
  platform: string
  thumbnail: string
  cover_url: string
  year: string
  area: string
  score: number | string
  tags: string[] | string
  actors: string[] | string
  total_episodes: number
  updated_episodes: number
  is_vip: number // 0-免费，1-会员，2-点播
  is_hot: number // 0-否，1-是
  is_new: number // 0-否，1-是
  is_finished: number // -1 未完结/连载中，0 未知，1 已完结
  description: string
  episodes?: Episode[]
  first_vid?: string
  created_at?: string
  updated_at?: string
}

export interface Episode {
  id: number
  episode_num: string
  vid: string
  play_title: string
  play_url: string
  episode_type: number // 0:正片, 1:预告, 2:花絮
  is_vip: number // 0-免费，1-会员，2-点播
}

export interface Platform {
  key: string
  name: string
}

export interface Stats {
  total_series: number
  total_episodes: number
}

export interface ParseSource {
  key: string
  name: string
  url: string
}

export const PLATFORM_MAP: Record<string, { name: string; icon: string; badge: string }> = {
  iqiyi: { name: 'QYI.V', icon: '🎬', badge: 'badge-iqiyi' },
  tencent: { name: 'QQ.V', icon: '🎭', badge: 'badge-tencent' },
  youku: { name: 'UKU.V', icon: '📺', badge: 'badge-youku' },
  mgtv: { name: 'MGO.V', icon: '🥭', badge: 'badge-mgtv' },
  sohu: { name: 'SOHO.V', icon: '🦊', badge: 'badge-sohu' },
  bilibili: { name: 'BBLL.V', icon: '📱', badge: 'badge-bilibili' },
}

export const TYPE_MAP: Record<string, { name: string; icon: string }> = {
  tv: { name: '电视剧', icon: '📡' },
  movie: { name: '电影', icon: '🎞️' },
  variety: { name: '综艺', icon: '🎭' },
  cartoon: { name: '动漫', icon: '🎨' },
  child: { name: '少儿', icon: '🧸' },
}

export async function fetchPlatforms(): Promise<Platform[]> {
  const res = await fetch(`${API_BASE}/platforms`);
  const data = await res.json();
  return data.code === 0 ? data.data : [];
}

export async function fetchCategories(): Promise<Category[]> {
  try {
    console.log('Fetching categories from:', `${API_BASE}/categories`)
    const res = await fetch(`${API_BASE}/categories`);
    console.log('Response status:', res.status)
    if (!res.ok) {
      console.error('API request failed with status:', res.status)
      return []
    }
    const data = await res.json();
    console.log('Categories data:', data)
    return data.code === 0 ? data.data : [];
  } catch (error) {
    console.error('Error fetching categories:', error)
    return []
  }
}

export interface Category {
  key: string;
  name: string;
  icon?: string;
}

export async function fetchStats(): Promise<Stats> {
  const res = await fetch(`${API_BASE}/stats`)
  const data = await res.json()
  return data.code === 0 ? data.data : { total_series: 0, total_episodes: 0 }
}

export async function fetchSeries(params: {
  page?: number
  limit?: number
  platform?: string
  category?: string
  year?: string
  area?: string
  tag?: string
  director?: string
  actor?: string
  sort?: string
  min_score?: number
}): Promise<{ items: Series[]; total: number }> {
  const query = new URLSearchParams()
  query.set('page', String(params.page || 1))
  query.set('limit', String(params.limit || 20))
  if (params.platform && params.platform !== 'all') {
    query.set('platform', params.platform)
  }
  if (params.category) {
    query.set('category', params.category)
  }
  if (params.year && params.year !== 'all') {
    query.set('year', params.year)
  }
  if (params.area && params.area !== 'all') {
    query.set('area', params.area)
  }
  if (params.tag && params.tag !== 'all') {
    query.set('tag', params.tag)
  }
  if (params.director && params.director !== 'all') {
    query.set('director', params.director)
  }
  if (params.actor && params.actor !== 'all') {
    query.set('actor', params.actor)
  }
  if (params.sort) {
    query.set('sort', params.sort)
  }
  if (params.min_score) {
    query.set('min_score', String(params.min_score))
  }

  const res = await fetch(`${API_BASE}/series?${query}`)
  const data = await res.json()
  return data.code === 0 ? data.data : { items: [], total: 0 }
}

export interface FilterOptions {
  years: string[]
  areas: string[]
  tags: string[]
  directors: string[]
  actors: string[]
}

export async function fetchFilterOptions(category: string, platform?: string): Promise<FilterOptions> {
  const query = new URLSearchParams()
  query.set('category', category)
  if (platform && platform !== 'all') {
    query.set('platform', platform)
  }
  const res = await fetch(`${API_BASE}/filter-options?${query}`)
  const data = await res.json()
  return data.code === 0 ? data.data : { years: [], areas: [], tags: [], directors: [], actors: [] }
}

export async function fetchSeriesDetail(cid: string, category?: string): Promise<Series | null> {
  const query = new URLSearchParams()
  if (category) {
    query.set('category', category)
  }
  const res = await fetch(`${API_BASE}/series/${cid}?${query}`)
  const data = await res.json()
  return data.code === 0 ? data.data : null
}

export async function searchSeries(keyword: string, params?: {
  platform?: string
  category?: string
}): Promise<{ items: Series[]; total: number }> {
  const query = new URLSearchParams()
  query.set('keyword', keyword)
  query.set('page', '1')
  query.set('limit', '50')
  if (params?.platform && params.platform !== 'all') {
    query.set('platform', params.platform)
  }
  if (params?.category) {
    query.set('category', params.category)
  }

  const res = await fetch(`${API_BASE}/search?${query}`)
  const data = await res.json()
  return data.code === 0 ? data.data : { items: [], total: 0 }
}

export async function fetchParseSources(platform?: string): Promise<ParseSource[]> {
  const url = platform ? `${API_BASE}/parse_sources?platform=${encodeURIComponent(platform)}` : `${API_BASE}/parse_sources`
  const res = await fetch(url)
  const data = await res.json()
  return data.code === 0 ? data.data : []
}

export function parseTags(tags: string[] | string): string[] {
  if (!tags) return []
  try {
    return Array.isArray(tags) ? tags : JSON.parse(tags)
  } catch {
    return typeof tags === 'string' ? tags.split(',').map(t => t.trim()).filter(Boolean) : []
  }
}

export function parseActors(actors: string[] | string): string[] {
  if (!actors) return []
  try {
    return Array.isArray(actors) ? actors : JSON.parse(actors)
  } catch {
    return typeof actors === 'string' ? actors.split(',').map(a => a.trim()).filter(Boolean) : []
  }
}

export interface User {
  id: number
  username: string
  phone: string
  email?: string
  nickname?: string
  avatar?: string
  status: string
  created_at?: string
  vip_level?: number
  vip_expire_at?: string
}

export interface LoginResult {
  access_token: string
  refresh_token: string
  token_type: string
  user: User
}

export async function sendSmsCode(phone: string, codeType: 'login' | 'register' = 'login'): Promise<{ code?: string; expire_seconds: number; tip?: string }> {
  const res = await fetch(`${API_BASE}/sms/send`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone, code_type: codeType })
  })
  const data = await res.json()
  if (data.code !== 0) {
    throw new Error(data.message || '发送验证码失败')
  }
  return data.data
}

export async function smsLogin(phone: string, code: string): Promise<LoginResult> {
  const res = await fetch(`${API_BASE}/auth/sms_login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone, code })
  })
  const data = await res.json()
  if (data.code !== 0) {
    throw new Error(data.message || '登录失败')
  }
  return data.data
}

export async function passwordLogin(username: string, password: string): Promise<LoginResult> {
  const res = await fetch(`${API_BASE}/auth/password_login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  })
  const data = await res.json()
  if (data.code !== 0) {
    throw new Error(data.message || '登录失败')
  }
  return data.data
}

export async function register(phone: string, code: string, username?: string, email?: string, password?: string, inviteCode?: string): Promise<LoginResult> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ phone, code, username, email, password, invite_code: inviteCode })
  })
  const data = await res.json()
  if (data.code !== 0) {
    throw new Error(data.message || '注册失败')
  }
  return data.data
}

export async function refreshToken(refreshToken: string): Promise<{ access_token: string; refresh_token: string }> {
  const res = await fetch(`${API_BASE}/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken })
  })
  const data = await res.json()
  if (data.code !== 0) {
    throw new Error(data.message || '刷新失败')
  }
  return data.data
}

export async function logout(): Promise<void> {
  await fetch(`${API_BASE}/auth/logout`, {
    method: 'POST'
  })
}

export async function getUserInfo(): Promise<User> {
    const token = localStorage.getItem('access_token') || localStorage.getItem('token')
    const res = await fetch(`${API_BASE}/user/info`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
    })
    const data = await res.json()
    if (data.code !== 0) {
        throw new Error(data.message || '获取用户信息失败')
    }
    return data.data
}

export interface InviteListData {
    invite_code: string
    points: number
    invited_count: number
    vip_count: number
    invited_list: Array<{
        id: number
        username: string
        nickname: string
        phone: string
        avatar: string | null
        is_vip: boolean
        created_at: string
    }>
}

export async function getInviteList(userId: number): Promise<InviteListData> {
    const query = new URLSearchParams()
    query.set('user_id', String(userId))
    const token = localStorage.getItem('access_token') || localStorage.getItem('token')
    const headers: Record<string, string> = {}
    if (token) {
        headers['Authorization'] = `Bearer ${token}`
    }
    const res = await fetch(`${API_BASE}/user/invite-list?${query}`, { headers })
    const data = await res.json()
    if (data.code !== 0) {
        throw new Error(data.message || '获取邀请列表失败')
    }
    return data.data
}

export async function withdrawPoints(): Promise<{ remaining_points: number }> {
    const token = localStorage.getItem('access_token') || localStorage.getItem('token')
    const res = await fetch(`${API_BASE}/user/withdraw`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    })
    const data = await res.json()
    if (data.code !== 0) {
        throw new Error(data.message || '提现失败')
    }
    return data.data
}

export async function resetPassword(phone: string, code: string, newPassword: string): Promise<void> {
    const res = await fetch(`${API_BASE}/auth/reset_password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, code, new_password: newPassword })
    })
    const data = await res.json()
    if (data.code !== 0) {
        throw new Error(data.message || '重置密码失败')
    }
}

export async function changePassword(oldPassword: string, newPassword: string): Promise<void> {
  const token = localStorage.getItem('access_token') || localStorage.getItem('token')
  const res = await fetch(`${API_BASE}/user/change-password`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    },
    body: JSON.stringify({ old_password: oldPassword, new_password: newPassword })
  })
  const data = await res.json()
  if (data.code !== 0) {
    throw new Error(data.message || '修改密码失败')
  }
}

export async function updateProfile(data: {
  username?: string
  nickname?: string
  email?: string
  avatar?: string
}): Promise<User> {
  const token = localStorage.getItem('access_token') || localStorage.getItem('token')
  const res = await fetch(`${API_BASE}/user/profile`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    },
    body: JSON.stringify(data)
  })
  const result = await res.json()
  if (result.code !== 0) {
    throw new Error(result.message || '更新失败')
  }
  return result.data
}

// Token 相关工具函数
interface TokenPayload {
    sub?: number
    exp?: number
    type?: string
}

/**
 * 解析 token 并返回 payload
 */
export function parseToken(token: string): TokenPayload | null {
    try {
        const parts = token.split('.')
        // 标准 JWT 有三个部分：header.payload.signature
        // 也支持只有两个部分的简化格式
        if (parts.length !== 2 && parts.length !== 3) {
            return null
        }
        // 标准 JWT 的 payload 在第二部分（索引为 1）
        const payloadIndex = parts.length === 3 ? 1 : 0
        const payloadJson = atob(parts[payloadIndex])
        return JSON.parse(payloadJson)
    } catch (e) {
        return null
    }
}

/**
 * 检查 token 是否即将过期（默认 5 分钟内）
 */
export function isTokenExpiringSoon(token: string, thresholdMinutes: number = 5): boolean {
    const payload = parseToken(token)
    if (!payload || !payload.exp) {
        // 如果无法解析 token，不认为即将过期，避免误判
        return false
    }
    const now = Math.floor(Date.now() / 1000)
    const expirationTime = payload.exp
    const threshold = thresholdMinutes * 60
    return (expirationTime - now) < threshold
}

/**
 * 检查 token 是否已经过期
 */
export function isTokenExpired(token: string): boolean {
    const payload = parseToken(token)
    if (!payload || !payload.exp) {
        // 如果无法解析 token，不认为已过期，避免误判
        return false
    }
    const now = Math.floor(Date.now() / 1000)
    return now >= payload.exp
}

export interface WatchHistoryItem {
  id: number
  user_id: number
  series_id: number
  episode_id?: number
  play_title?: string
  progress: number
  watch_time: number
  last_watched: string
  episode_num: string
  series: Series
  episode?: Episode
}

/** 聚合观看历史中的单集信息 */
export interface WatchedEpisode {
  history_id: number
  episode_id: number
  play_title: string
  episode_num: string
  last_watched: string | null
}

/** 按剧集聚合后的观看历史 */
export interface WatchHistoryGroup {
  series: Series
  episodes: WatchedEpisode[]
  watched_count: number
  total_episodes: number
}

/** 剧集观看进度映射：series_id → 已看集数 */
export type WatchProgressMap = Record<number, number>

export interface FollowItem {
  id: number
  user_id: number
  series_id: number
  follow_time: string
  last_check_time: string
  last_episode_id?: number
  last_episode_num?: string
  series: Series
  last_episode?: Episode
}

export async function getWatchHistory(userId: number): Promise<{
  code: number
  message: string
  data: { items: WatchHistoryGroup[]; page: number; limit: number; total: number }
}> {
  const query = new URLSearchParams()
  query.set('user_id', String(userId))
  query.set('group_by', 'true')
  query.set('page', '1')
  query.set('limit', '50')

  const res = await fetch(`${API_BASE}/user/watch-history?${query}`)
  return res.json()
}

export async function getWatchProgress(userId: number): Promise<{
  code: number
  message: string
  data: WatchProgressMap
}> {
  const query = new URLSearchParams()
  query.set('user_id', String(userId))

  const res = await fetch(`${API_BASE}/user/watch-progress?${query}`)
  return res.json()
}

export async function updateWatchHistory(data: {
  user_id: number
  series_id: number
  episode_id?: number
  progress?: number
}): Promise<{ code: number; message: string; data: { updated: boolean } }> {
  const res = await fetch(`${API_BASE}/user/watch-history`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data)
  })
  return res.json()
}

export async function deleteWatchHistory(historyId: number): Promise<{ code: number; message: string; data: null }> {
  const res = await fetch(`${API_BASE}/user/watch-history/${historyId}`, {
    method: 'DELETE'
  })
  return res.json()
}

export async function clearWatchHistory(userId: number): Promise<{ code: number; message: string; data: null }> {
  const query = new URLSearchParams()
  query.set('user_id', String(userId))

  const res = await fetch(`${API_BASE}/user/watch-history?${query}`, {
    method: 'DELETE'
  })
  return res.json()
}

export async function getFollowList(userId: number): Promise<{
  code: number
  message: string
  data: { items: FollowItem[]; page: number; limit: number; total: number }
}> {
  const query = new URLSearchParams()
  query.set('user_id', String(userId))
  query.set('page', '1')
  query.set('limit', '50')

  const res = await fetch(`${API_BASE}/user/follow?${query}`)
  return res.json()
}

export async function addFollow(userId: number, seriesId: number): Promise<{ code: number; message: string; data: null }> {
  const query = new URLSearchParams()
  query.set('user_id', String(userId))

  const res = await fetch(`${API_BASE}/user/follow/${seriesId}?${query}`, {
    method: 'POST'
  })
  return res.json()
}

export async function removeFollow(userId: number, seriesId: number): Promise<{ code: number; message: string; data: null }> {
  const query = new URLSearchParams()
  query.set('user_id', String(userId))

  const res = await fetch(`${API_BASE}/user/follow/${seriesId}?${query}`, {
    method: 'DELETE'
  })
  return res.json()
}

export async function checkFollow(userId: number, seriesId: number): Promise<{ code: number; message: string; data: { followed: boolean } }> {
  const query = new URLSearchParams()
  query.set('user_id', String(userId))
  query.set('series_id', String(seriesId))

  const res = await fetch(`${API_BASE}/user/follow/check?${query}`)
  return res.json()
}

export async function checkFollowUpdates(userId: number): Promise<{ code: number; message: string; data: Array<{ series: Series; latest_episode: Episode; unread: boolean }> }> {
  const query = new URLSearchParams()
  query.set('user_id', String(userId))

  const res = await fetch(`${API_BASE}/user/follow/updates?${query}`)
  return res.json()
}

// ==================== 收藏 API ====================

export interface BookmarkItem {
  id: number
  user_id: number
  series_id: number
  created_at: string
  series: Series
}

export async function getBookmarks(userId: number): Promise<{
  code: number
  message: string
  data: { items: BookmarkItem[]; page: number; limit: number; total: number }
}> {
  const query = new URLSearchParams()
  query.set('user_id', String(userId))
  query.set('page', '1')
  query.set('limit', '50')

  const res = await fetch(`${API_BASE}/user/bookmarks?${query}`)
  return res.json()
}

export async function addBookmark(userId: number, seriesId: number): Promise<{ code: number; message: string; data: null }> {
  const query = new URLSearchParams()
  query.set('user_id', String(userId))

  const res = await fetch(`${API_BASE}/user/bookmarks/${seriesId}?${query}`, {
    method: 'POST'
  })
  return res.json()
}

export async function removeBookmark(userId: number, seriesId: number): Promise<{ code: number; message: string; data: null }> {
  const query = new URLSearchParams()
  query.set('user_id', String(userId))

  const res = await fetch(`${API_BASE}/user/bookmarks/${seriesId}?${query}`, {
    method: 'DELETE'
  })
  return res.json()
}

export async function checkBookmark(userId: number, seriesId: number): Promise<{ code: number; message: string; data: { bookmarked: boolean } }> {
  const query = new URLSearchParams()
  query.set('user_id', String(userId))
  query.set('series_id', String(seriesId))

  const res = await fetch(`${API_BASE}/user/bookmarks/check?${query}`)
  return res.json()
}

// ==================== VIP相关API ====================

export interface VipStatus {
  is_vip: boolean
  vip_expire_at?: string
  remaining_days: number
  is_expired: boolean
  vip_plans?: Array<{
    id: number
    plan_id: number
    name: string
    terminal: string
    activated_at: string
    expire_at: string
  }>
}

export interface VipPlan {
  id: number
  name: string
  price: number
  original_price?: number
  duration_days: number
  unit?: string
  save_amount?: number
  is_recommend?: boolean
  is_enabled?: boolean
  sort_order?: number
  devices?: string[]
  plan_type?: 'monthly' | 'quarterly' | 'yearly' | 'permanent'
  duration_type?: 'monthly' | 'quarterly' | 'yearly' | 'permanent'
}

export interface VipOrder {
  id: number
  user_id: number
  order_no: string
  plan_id: number
  plan_name?: string
  amount: number
  pay_type: string
  pay_status: string
  pay_time?: string
  remark?: string
  created_at: string
  updated_at: string
}

export interface CdkeyRedeemResult {
  duration_days: number
  expire_at: string
}

// 获取VIP状态
export async function getVipStatus(): Promise<{ code: number; message: string; data: VipStatus }> {
  const token = localStorage.getItem('access_token') || localStorage.getItem('token')
  const res = await fetch(`${API_BASE}/vip/status`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {}
  })
  return res.json()
}

// 卡密兑换
export async function redeemCdkey(code: string): Promise<{ code: number; message: string; data: CdkeyRedeemResult }> {
  const token = localStorage.getItem('access_token') || localStorage.getItem('token')
  const res = await fetch(`${API_BASE}/vip/redeem`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    },
    body: JSON.stringify({ code })
  })
  return res.json()
}

// 创建VIP订单
export async function createVipOrder(planId: number): Promise<{ code: number; message: string; data: VipOrder }> {
  const token = localStorage.getItem('access_token') || localStorage.getItem('token')
  const res = await fetch(`${API_BASE}/vip/order`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'Authorization': `Bearer ${token}` } : {})
    },
    body: JSON.stringify({ plan_id: planId })
  })
  return res.json()
}

// 获取我的VIP订单列表
export async function getMyVipOrders(page: number = 1, limit: number = 20): Promise<{ code: number; message: string; data: { items: VipOrder[]; total: number; page: number; limit: number } }> {
  const token = localStorage.getItem('access_token') || localStorage.getItem('token')
  const query = new URLSearchParams()
  query.set('page', String(page))
  query.set('limit', String(limit))

  const res = await fetch(`${API_BASE}/vip/orders?${query}`, {
    headers: token ? { 'Authorization': `Bearer ${token}` } : {}
  })
  return res.json()
}

export interface VipPlanConfig {
  id: number
  plan_type: string
  tip_text?: string
  created_at: string
  updated_at: string
}

// 获取VIP套餐列表
export async function getVipPlans(): Promise<{ code: number; message: string; data: { plans: VipPlan[]; configs: Record<string, VipPlanConfig> } }> {
  const res = await fetch(`${API_BASE}/vip/plans`)
  return res.json()
}
