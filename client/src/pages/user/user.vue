<template>
  <div class="page">
    <component v-if="!deviceStore.isMobile" :is="headerComponent" />

    <!-- 移动端返回栏 -->
    <div v-if="deviceStore.isMobile" class="mobile-back-bar">
      <button class="mobile-back-btn" @click="goBack" title="返回">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5"/><path d="M12 19l-7-7 7-7"/></svg>
      </button>
      <span class="mobile-back-title">用户中心</span>
      <!-- 右上角菜单按钮 -->
      <button v-if="userStore.isLoggedIn" class="mobile-menu-btn" @click="showMobileMenu = !showMobileMenu">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="3" y1="12" x2="21" y2="12"/>
          <line x1="3" y1="6" x2="21" y2="6"/>
          <line x1="3" y1="18" x2="21" y2="18"/>
        </svg>
      </button>
    </div>

    <!-- 移动端菜单下拉 -->
    <Transition name="menu-fade">
      <div v-if="showMobileMenu" class="mobile-menu-overlay" @click="showMobileMenu = false">
        <div class="mobile-menu-panel" @click.stop>
          <div class="mobile-menu-list">
            <button
              v-for="tab in tabs"
              :key="tab.key"
              :class="['mobile-menu-item', { active: activeTab === tab.key }]"
              @click="handleMenuTabClick(tab.key)"
            >
              <span class="menu-icon">{{ tab.icon }}</span>
              <span class="menu-label">{{ tab.label }}</span>
            </button>
            <div class="mobile-menu-divider"></div>
            <button class="mobile-menu-item logout" @click="handleLogout">
              <span class="menu-icon">🚪</span>
              <span class="menu-label">退出登录</span>
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <div :class="['container', { 'page-content': deviceStore.isMobile }]">
      <!-- 主题选择弹窗 -->
    <ThemePicker :visible="showThemePicker" @close="showThemePicker = false" />

    <main class="main-content">
      <!-- 未登录状态 -->
      <div v-if="isReady && (!userStore.isLoggedIn || !userStore.user)" class="login-prompt">
        <div class="prompt-card">
          <span class="prompt-icon">👤</span>
          <h2>登录后可查看用户中心</h2>
          <p>登录后可以追更剧集、查看观看历史</p>
          <router-link to="/login" class="login-btn">立即登录</router-link>
          <div class="register-link">
            没有账号？<router-link to="/register" class="link">立即注册</router-link>
          </div>
        </div>
      </div>

      <!-- 已登录状态 -->
      <div v-else class="user-center">
        <!-- PC端左侧导航 -->
        <aside v-if="!deviceStore.isMobile" class="sidebar-nav">
          <div class="sidebar-profile">
            <div class="profile-avatar">
              <img v-if="userStore.user?.avatar" :src="userStore.user?.avatar" alt="头像" />
              <span v-else class="avatar-text">{{ userStore.user?.username?.charAt(0).toUpperCase() }}</span>
            </div>
            <div class="profile-info">
              <h2 class="profile-name">{{ userStore.user?.username }}</h2>
              <div class="profile-meta">
                <span v-if="userStore.user?.email" class="meta-item">
                  <span class="meta-icon">✉</span>
                  {{ userStore.user?.email }}
                </span>
                <span v-if="userStore.user?.phone" class="meta-item">
                  <span class="meta-icon">📱</span>
                  {{ formatPhone(userStore.user?.phone) }}
                </span>
              </div>
            </div>
          </div>

          <nav class="sidebar-menu">
            <button
              v-for="tab in tabs"
              :key="tab.key"
              :class="['sidebar-menu-item', { active: activeTab === tab.key }]"
              @click="handleSidebarTabClick(tab.key)"
            >
              <span class="menu-icon">{{ tab.icon }}</span>
              <span class="menu-label">{{ tab.label }}</span>
              <span v-if="tab.key === 'follow' && followCount > 0" class="menu-badge">{{ followCount }}</span>
            </button>
          </nav>

          <div class="sidebar-footer">
            <button class="logout-btn" @click="handleLogout">
              <span>🚪</span> 退出登录
            </button>
          </div>
        </aside>

        <!-- 移动端用户信息栏 - 现代化设计 -->
        <div v-if="deviceStore.isMobile && userStore.user" class="mobile-user-header">
          <div class="mobile-avatar-large">
            <img v-if="userStore.user?.avatar" :src="userStore.user?.avatar" alt="头像" />
            <span v-else class="avatar-text">{{ userStore.user?.username?.charAt(0).toUpperCase() }}</span>
          </div>
          <div class="mobile-user-info-content">
            <div class="mobile-name-row">
              <span class="mobile-username">{{ userStore.user?.username }}</span>
              <span :class="['mobile-vip-tag', { vip: isVip, normal: !isVip }]">
                {{ isVip ? 'VIP' : '普通用户' }}
              </span>
            </div>
            <span class="mobile-user-email">
              {{ userStore.user?.email || userStore.user?.phone }}
            </span>
          </div>
        </div>

        <!-- 右侧内容区 -->
        <div class="content-area">
          <div class="tab-content">
          <!-- 移动端Tab导航（仅历史/收藏/追剧页显示） -->
          <nav v-if="deviceStore.isMobile && ['history','favorites','follow'].includes(activeTab)" class="mobile-bottom-tabs">
            <button
              v-for="tab in quickTabs"
              :key="tab.key"
              :class="['bottom-tab-item', { active: activeTab === tab.key }]"
              @click="handleMenuTabClick(tab.key)"
            >
              <span class="tab-icon">{{ tab.icon }}</span>
              <span class="tab-label">{{ tab.label }}</span>
              <span v-if="tab.key === 'follow' && followCount > 0" class="tab-count">{{ followCount }}</span>
            </button>
          </nav>

          <!-- 我的追剧 -->
          <div v-if="activeTab === 'follow'" class="tab-panel">
            <div class="panel-header">
              <h3 class="panel-title">我的追剧</h3>
              <button class="panel-action" @click="checkFollowUpdates">
                <span>🔄</span> 检查更新
              </button>
            </div>
            <template v-if="followList.length > 0">
              <div class="card-grid">
                <div
                  v-for="item in followList"
                  :key="item.series.id"
                  class="series-card"
                  @click="goToDetail(item.series.cid)"
                >
                  <div
                    class="card-poster"
                    @touchstart.prevent="startLongPress('follow-' + item.series.id)"
                    @touchend.prevent="endLongPress"
                    @touchmove.prevent="cancelLongPress"
                    @mousedown.prevent="startLongPress('follow-' + item.series.id)"
                    @mouseup="endLongPress"
                    @mouseleave="cancelLongPress"
                  >
                    <img :src="getProxyImageUrl(item.series.thumbnail)" :alt="item.series.title" />
                    <div class="poster-overlay" :class="{ visible: pressedCardId === 'follow-' + item.series.id }">
                      <button
                        v-if="pressedCardId === 'follow-' + item.series.id"
                        class="overlay-cancel-btn"
                        @click.stop="handleUnfollow(item.series.id)"
                      >✕</button>
                      <span v-else class="play-icon">▶</span>
                    </div>
                    <div v-if="item.series.total_episodes" class="poster-ep-badge">
                      {{ item.series.updated_episodes && item.series.updated_episodes < item.series.total_episodes ? `更新${item.series.updated_episodes}/共${item.series.total_episodes}集` : `共${item.series.total_episodes}集` }}
                    </div>
                  </div>
                  <div class="card-info">
                    <div class="card-title-row">
                      <span class="card-title">{{ item.series.title }}</span>
                      <span v-if="item.series.year" class="card-year">{{ item.series.year }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </template>
            <div v-else class="empty-state">
              <span class="empty-icon">📺</span>
              <p class="empty-title">暂无追剧内容</p>
              <p class="empty-desc">去剧集详情页点击"追更"按钮添加</p>
            </div>
          </div>

          <!-- 观看历史 -->
          <div v-if="activeTab === 'history'" class="tab-panel">
            <div class="panel-header">
              <h3 class="panel-title">观看历史</h3>
              <button v-if="historyList.length > 0" class="panel-action danger" @click="clearAllHistory">
                <span>🗑</span> 清空
              </button>
            </div>
            <template v-if="historyList.length > 0">
              <div class="card-grid history-grid">
                <div
                  v-for="group in historyList"
                  :key="group.series.id"
                  class="series-card history-card"
                >
                  <!-- 封面点击进入详情页 -->
                  <div class="card-poster" @click="goToDetail(group.series.cid)">
                    <img :src="getProxyImageUrl(group.series.thumbnail)" :alt="group.series.title" />
                    <div class="poster-overlay">
                      <span class="play-icon">▶</span>
                    </div>
                  </div>
                  <div class="card-info">
                    <div class="card-title-row">
                      <span class="card-title" :title="group.series.title">{{ group.series.title }}</span>
                    </div>
                    <!-- 移动端直接显示分集列表（按观看时间倒序） -->
                    <div class="card-tooltip">
                      <div class="tooltip-ep-list">
                        <div
                          v-for="ep in sortedEpisodes(group.episodes)"
                          :key="ep.history_id"
                          class="tooltip-ep-item"
                          @click="goToPlay(group.series.cid, ep.episode_id)"
                        >
                          <span class="tooltip-ep-title">{{ ep.play_title || `第${ep.episode_num}集` }}</span>
                          <span class="tooltip-ep-time">{{ formatTime(ep.last_watched || '') }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </template>
            <div v-else class="empty-state">
              <span class="empty-icon">📜</span>
              <p class="empty-title">暂无观看记录</p>
              <p class="empty-desc">开始观看剧集，记录你的追剧足迹</p>
            </div>
          </div>

          <!-- 我的收藏 -->
          <div v-if="activeTab === 'favorites'" class="tab-panel">
            <div class="panel-header">
              <h3 class="panel-title">我的收藏</h3>
            </div>
            <template v-if="favorites.length > 0">
              <div class="card-grid">
                <div
                  v-for="item in favorites"
                  :key="item.cid"
                  class="series-card"
                  @click="goToDetail(item.cid)"
                >
                  <div
                    class="card-poster"
                    @touchstart.prevent="startLongPress('fav-' + item.cid)"
                    @touchend.prevent="endLongPress"
                    @touchmove.prevent="cancelLongPress"
                    @mousedown.prevent="startLongPress('fav-' + item.cid)"
                    @mouseup="endLongPress"
                    @mouseleave="cancelLongPress"
                  >
                    <img :src="getProxyImageUrl(item.thumbnail)" :alt="item.title" />
                    <div class="poster-overlay" :class="{ visible: pressedCardId === 'fav-' + item.cid }">
                      <button
                        v-if="pressedCardId === 'fav-' + item.cid"
                        class="overlay-cancel-btn"
                        @click.stop="handleRemoveBookmark(item.cid)"
                      >✕</button>
                      <span v-else class="play-icon">▶</span>
                    </div>
                    <div v-if="item.total_episodes" class="poster-ep-badge">
                      {{ item.updated_episodes && item.updated_episodes < item.total_episodes ? `更新${item.updated_episodes}/共${item.total_episodes}集` : `共${item.total_episodes}集` }}
                    </div>
                  </div>
                  <div class="card-info">
                    <div class="card-title-row">
                      <span class="card-title">{{ item.title }}</span>
                      <span v-if="item.year" class="card-year">{{ item.year }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </template>
            <div v-else class="empty-state">
              <span class="empty-icon">❤️</span>
              <p class="empty-title">暂无收藏内容</p>
              <p class="empty-desc">收藏喜欢的剧集，方便随时回看</p>
            </div>
          </div>

          <!-- 我的邀请 -->
          <div v-if="activeTab === 'invite'" class="tab-panel">
            <div class="panel-header">
              <h3 class="panel-title">我的邀请</h3>
            </div>

            <div v-if="loadingInvite" class="loading-state">
              <span class="loading-text">加载中...</span>
            </div>

            <div v-else-if="inviteLoadError" class="error-state">
              <span class="error-icon">⚠️</span>
              <p class="error-text">加载失败</p>
              <button class="retry-btn" @click="loadInviteData">重试</button>
            </div>

            <template v-else-if="inviteData">
              <!-- 积分和邀请码卡片 -->
              <div class="invite-card">
                <div class="invite-stats">
                  <div class="stat-box">
                    <div class="stat-number">{{ inviteData.points }}</div>
                    <div class="stat-label">我的积分</div>
                  </div>
                  <div class="stat-box">
                    <div class="stat-number">{{ inviteData.invited_count }}</div>
                    <div class="stat-label">已邀请</div>
                  </div>
                  <div class="stat-box">
                    <div class="stat-number">{{ inviteData.vip_count }}</div>
                    <div class="stat-label">成为会员</div>
                  </div>
                </div>

                <div class="invite-code-box">
                  <div class="invite-code-label">我的邀请码</div>
                  <div class="invite-code-value">
                    <span class="code-text">{{ inviteData.invite_code }}</span>
                    <button class="copy-code-btn" @click="copyInviteCode">复制</button>
                  </div>
                  <div class="invite-hint">邀请好友注册，双方都可获得积分奖励</div>
                </div>

                <!-- 提现区域 -->
                <div class="withdraw-section">
                  <div class="withdraw-title">积分提现</div>
                  <div class="withdraw-info">
                    <div class="withdraw-desc">
                      <span class="desc-text">{{ withdrawAmount }}</span>
                      <span v-if="inviteData.points < WITHDRAW_MIN_POINTS" class="withdraw-tip">
                        （还差{{ WITHDRAW_MIN_POINTS - inviteData.points }}积分）
                      </span>
                    </div>
                    <button
                      class="withdraw-btn"
                      :disabled="!canWithdraw() || isWithdrawing"
                      @click="handleWithdraw"
                    >
                      <span v-if="isWithdrawing">提现中...</span>
                      <span v-else>立即提现</span>
                    </button>
                  </div>
                </div>

                <!-- 积分规则说明 -->
                <div class="rules-section">
                  <div class="rules-title">积分规则</div>
                  <ul class="rules-list">
                    <li>邀请用户注册成功：+10积分</li>
                    <li>被邀请用户成为会员：+20积分</li>
                    <li>积分满100可提现10元</li>
                  </ul>
                </div>
              </div>

              <!-- 邀请列表 -->
              <div class="invited-list-section" v-if="inviteData.invited_list.length > 0">
                <div class="section-title">邀请记录</div>
                <div class="invited-users">
                  <div
                    v-for="user in inviteData.invited_list"
                    :key="user.id"
                    class="invited-user-item"
                  >
                    <div class="user-avatar">
                      <img v-if="user.avatar" :src="user.avatar" alt="头像" />
                      <span v-else class="avatar-default">{{ user.username?.charAt(0).toUpperCase() }}</span>
                    </div>
                    <div class="user-info">
                      <div class="user-name">{{ user.nickname || user.username }}<span v-if="user.phone" class="user-phone">({{ maskPhone(user.phone) }})</span></div>
                      <div class="user-date">注册于 {{ formatDate(user.created_at) }}</div>
                    </div>
                    <div class="user-vip-badge" :class="{ 'is-vip': user.is_vip }">
                      {{ user.is_vip ? 'VIP会员' : '普通用户' }}
                    </div>
                  </div>
                </div>
              </div>
              <div v-else class="empty-invite">
                <span class="empty-icon">🎁</span>
                <p class="empty-title">暂无邀请记录</p>
                <p class="empty-desc">分享邀请码给好友，好友注册后你可获得积分奖励</p>
              </div>
            </template>
          </div>

          <!-- 账号设置 -->
          <div v-if="activeTab === 'settings'" class="tab-panel">
            <div class="panel-header">
              <h3 class="panel-title">账号设置</h3>
            </div>

            <div class="settings-section">
              <h4 class="section-title">基本信息</h4>
              <div class="settings-form">
                <div class="form-group">
                  <label>用户名</label>
                  <input type="text" v-model="editForm.username" placeholder="请输入用户名" />
                </div>
                <div class="form-group">
                  <label>昵称</label>
                  <input type="text" v-model="editForm.nickname" placeholder="请输入昵称" />
                </div>
                <div class="form-group">
                  <label>邮箱</label>
                  <input type="email" v-model="editForm.email" placeholder="请输入邮箱" />
                </div>
                <div class="form-group">
                  <label>手机号</label>
                  <input type="tel" v-model="editForm.phone" placeholder="请输入手机号" disabled />
                </div>
                <button class="save-btn" @click="saveSettings" :disabled="isSavingProfile">
                  <span v-if="isSavingProfile">保存中...</span>
                  <span v-else>保存修改</span>
                </button>
              </div>
            </div>

            <div class="settings-section">
              <h4 class="section-title">修改密码</h4>
              <div class="settings-form">
                <div class="form-group">
                  <label>当前密码（首次设置留空即可）</label>
                  <input
                    type="password"
                    v-model="passwordForm.oldPassword"
                    placeholder="请输入当前密码"
                  />
                </div>
                <div class="form-group">
                  <label>新密码</label>
                  <input
                    type="password"
                    v-model="passwordForm.newPassword"
                    placeholder="请输入新密码（至少6位）"
                  />
                </div>
                <div class="form-group">
                  <label>确认新密码</label>
                  <input
                    type="password"
                    v-model="passwordForm.confirmPassword"
                    placeholder="请再次输入新密码"
                  />
                </div>
                <button
                  class="save-btn"
                  @click="handleChangePassword"
                  :disabled="isSavingPassword"
                >
                  <span v-if="isSavingPassword">修改中...</span>
                  <span v-else>修改密码</span>
                </button>
              </div>
            </div>
          </div>
          </div>
        </div>
      </div>
    </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import {
  getProxyImageUrl,
  getWatchHistory,
  deleteWatchHistory,
  clearWatchHistory,
  getFollowList,
  removeFollow,
  getBookmarks,
  removeBookmark,
  checkFollowUpdates as fetchFollowUpdates,
  changePassword,
  updateProfile,
  getInviteList,
  withdrawPoints,
  type WatchHistoryGroup,
  type WatchedEpisode,
  type InviteListData
} from '@/utils/api'
import { useUserStore } from '@/stores/user'
import { useDeviceStore } from '@/stores/device'
import { useToast } from '@/composables/useToast'
import { useThemeStore } from '@/stores/theme'
import PcHeader from '@/components/pc/Header.vue'
import MobileHeader from '@/components/mobile/Header.vue'
import ThemePicker from '@/components/ThemePicker.vue'

const router = useRouter()
const userStore = useUserStore()
const deviceStore = useDeviceStore()
const toast = useToast()
const themeStore = useThemeStore()

const showThemePicker = ref(false)

// 页面是否已初始化完成（避免闪烁未登录提示）
const isReady = ref(false)

function goBack() {
  const lastCategory = sessionStorage.getItem('lastCategory') || '/tv'
  router.push(lastCategory)
}

// 根据设备类型选择 Header
const headerComponent = computed(() => {
  return deviceStore.isMobile ? MobileHeader : PcHeader
})

// ===== Tab 配置 =====
// 完整tabs（包含会员中心）
const tabs = [
  { key: 'follow', label: '我的追剧', icon: '📺' },
  { key: 'history', label: '观看历史', icon: '📜' },
  { key: 'favorites', label: '我的收藏', icon: '❤️' },
  { key: 'invite', label: '我的邀请', icon: '🎁' },
  { key: 'vip', label: '会员中心', icon: '👑' },
  { key: 'settings', label: '账号设置', icon: '⚙️' },
  { key: 'theme', label: '外观设置', icon: '🎨' },
]

// 移动端快速Tab（历史、收藏、追剧）
const quickTabs = [
  { key: 'history', label: '历史', icon: '📜' },
  { key: 'favorites', label: '收藏', icon: '❤️' },
  { key: 'follow', label: '追剧', icon: '📺' },
]

// VIP标识
const isVip = computed(() => {
  // 暂时根据是否有vip相关字段判断，后续根据实际数据结构调整
  const user = userStore.user as any
  return user?.is_vip === 1 || user?.vip === true || user?.vip_level > 0
})

const activeTab = ref('history')
const showMobileMenu = ref(false)
const favorites = ref<any[]>([])
const historyList = ref<WatchHistoryGroup[]>([])
const followList = ref<any[]>([])
const followCount = computed(() => followList.value.length)

// 长按显示遮罩层状态
const pressedCardId = ref<string | null>(null)
const isLongPressed = ref(false) // 是否已完成长按（遮罩正在显示）
let longPressTimer: ReturnType<typeof setTimeout> | null = null

function startLongPress(cardId: string) {
  isLongPressed.value = false
  longPressTimer = setTimeout(() => {
    pressedCardId.value = cardId
    isLongPressed.value = true
  }, 500)
}

function cancelLongPress() {
  if (longPressTimer) {
    clearTimeout(longPressTimer)
    longPressTimer = null
  }
}

function endLongPress() {
  cancelLongPress()
  // 如果正在显示遮罩，不清除，由点击遮罩或按钮处理
  if (!isLongPressed.value) {
    pressedCardId.value = null
  }
  isLongPressed.value = false
}

// 点击空白处关闭遮罩
function handleGlobalClick(e: MouseEvent) {
  if (!pressedCardId.value) return
  const target = e.target as HTMLElement
  // 点击卡片内（card-poster 或 card-info）不关闭
  if (target.closest('.card-poster') || target.closest('.card-info')) return
  pressedCardId.value = null
}

// 移动端菜单点击处理
const handleMenuTabClick = (key: string) => {
  showMobileMenu.value = false
  if (key === 'theme') {
    showThemePicker.value = true
  } else if (key === 'vip') {
    router.push('/vip')
  } else {
    activeTab.value = key
  }
}

// PC端侧边栏点击处理
const handleSidebarTabClick = (key: string) => {
  if (key === 'theme') {
    showThemePicker.value = true
  } else if (key === 'vip') {
    router.push('/vip')
  } else {
    activeTab.value = key
  }
}

// 加载状态
const loadingFollow = ref(false)
const loadingHistory = ref(false)
const loadingFavorites = ref(false)
const loadingInvite = ref(false)
const inviteLoadError = ref(false)
const isWithdrawing = ref(false)
const editForm = ref({
  username: '',
  nickname: '',
  email: '',
  phone: ''
})

// 邀请相关数据
const inviteData = ref<InviteListData | null>(null)
const withdrawAmount = ref('')  // 提现金额文本框（只读显示）

const passwordForm = ref({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const isSavingPassword = ref(false)
const isSavingProfile = ref(false)

// 提现规则
const WITHDRAW_MIN_POINTS = 100  // 最低提现积分
const WITHDRAW_AMOUNT = 10  // 提现金额（元）

// ===== 导航 =====
function goToDetail(cid: string) {
  // 长按遮罩显示时不跳转
  if (pressedCardId.value) return
  router.push(`/detail/${cid}`)
}

function goToPlay(cid: string, episodeId: number) {
  router.push(`/play/${cid}?ep=${episodeId}`)
}

// 按观看时间倒序排序分集
function sortedEpisodes(episodes: WatchedEpisode[]): WatchedEpisode[] {
  return [...episodes].sort((a, b) => {
    const timeA = a.last_watched ? new Date(a.last_watched).getTime() : 0
    const timeB = b.last_watched ? new Date(b.last_watched).getTime() : 0
    return timeB - timeA
  })
}

// ===== 格式化 =====
function formatPhone(phone?: string): string {
  if (!phone) return ''
  return phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')
}

function formatScore(score: number | string): string {
  const s = Number(score)
  if (isNaN(s)) return String(score)
  return s.toFixed(1)
}

function maskPhone(phone: string): string {
  if (!phone) return ''
  return phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2')
}

function copyInviteCode() {
  const code = inviteData.value?.invite_code || (userStore.user as any)?.invite_code
  if (!code) return
  navigator.clipboard.writeText(code).then(() => {
    toast.success('邀请码已复制')
  }).catch(() => {
    toast.error('复制失败')
  })
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN')
}

async function loadInviteData() {
  if (!userStore.user?.id) return
  loadingInvite.value = true
  inviteLoadError.value = false
  try {
    const data = await getInviteList(userStore.user.id)
    inviteData.value = data
    withdrawAmount.value = `${WITHDRAW_MIN_POINTS}积分 = ${WITHDRAW_AMOUNT}元`
  } catch (error: any) {
    console.error('Failed to load invite data:', error)
    inviteLoadError.value = true
    toast.error(error.message || '加载邀请数据失败')
  } finally {
    loadingInvite.value = false
  }
}

async function handleWithdraw() {
  if (!inviteData.value || inviteData.value.points < WITHDRAW_MIN_POINTS) {
    toast.warning(`积分不足${WITHDRAW_MIN_POINTS}，无法提现`)
    return
  }

  toast.confirm(
    `确定提现吗？将扣除${WITHDRAW_MIN_POINTS}积分，获得${WITHDRAW_AMOUNT}元`,
    async () => {
      isWithdrawing.value = true
      try {
        const result = await withdrawPoints()
        // 更新本地积分
        if (inviteData.value) {
          inviteData.value.points = result.remaining_points
        }
        // 更新用户store中的积分
        if (userStore.user) {
          (userStore.user as any).points = result.remaining_points
        }
        toast.success(`提现成功！${WITHDRAW_AMOUNT}元将很快到账`)
      } catch (error: any) {
        toast.error(error.message || '提现失败')
      } finally {
        isWithdrawing.value = false
      }
    }
  )
}

function canWithdraw(): boolean {
  return inviteData.value ? inviteData.value.points >= WITHDRAW_MIN_POINTS : false
}

function formatTime(timestamp: string): string {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))

  if (days === 0) return '今天'
  if (days === 1) return '昨天'
  if (days < 7) return `${days}天前`
  return date.toLocaleDateString('zh-CN')
}

function progressPercent(group: WatchHistoryGroup): number {
  if (!group.total_episodes || group.total_episodes === 0) return 0
  return Math.min(100, Math.round((group.watched_count / group.total_episodes) * 100))
}


// ===== 退出登录 =====
function handleLogout() {
  toast.confirm('确定要退出登录吗？', () => {
    userStore.logout()
    router.push('/')
  })
}

// ===== 数据加载 =====
async function loadWatchHistory() {
    if (!userStore.user?.id) {
      console.log('📊 用户未登录，跳过加载')
      return
    }
    loadingHistory.value = true
    try {
      console.log('📊 开始加载观看历史，用户ID:', userStore.user.id)
      const result = await getWatchHistory(userStore.user.id)
      console.log('📊 API返回完整数据:', result)
      console.log('📊 data字段:', result.data)
      console.log('📊 data.items:', result.data?.items)
      console.log('📊 data.items类型:', typeof result.data?.items)
      console.log('📊 data.items长度:', result.data?.items?.length)

      if (result.code === 0) {
        historyList.value = result.data.items || []
        console.log('📊 历史数据赋值后条数:', historyList.value.length)
        if (historyList.value.length > 0) {
          console.log('📊 第一条数据:', historyList.value[0])
        } else {
          console.log('📊 历史数据为空数组')
        }
      } else {
        console.log('📊 API返回错误码:', result.code, result.message)
      }
    } catch (error) {
      console.error('📊 加载观看历史失败:', error)
    } finally {
      loadingHistory.value = false
    }
  }

  async function loadFollowList() {
    if (!userStore.user?.id) return
    loadingFollow.value = true
    try {
      const result = await getFollowList(userStore.user.id)
      if (result.code === 0) {
        followList.value = result.data.items || []
      }
    } catch (error) {
      console.error('Failed to load follow list:', error)
    } finally {
      loadingFollow.value = false
    }
  }

  async function deleteHistory(historyId: number) {
  try {
    const result = await deleteWatchHistory(historyId)
    if (result.code === 0) {
      // 从聚合数据中移除该分集
      historyList.value = historyList.value
        .map(group => ({
          ...group,
          episodes: group.episodes.filter(ep => ep.history_id !== historyId),
          watched_count: group.watched_count - (group.episodes.some(ep => ep.history_id === historyId) ? 1 : 0)
        }))
        .filter(group => group.episodes.length > 0)
      toast.success('已删除')
    }
  } catch (error) {
    console.error('Failed to delete history:', error)
  }
}

async function clearAllHistory() {
  if (!userStore.user?.id) return
  toast.confirm('确定要清空所有观看历史吗？', async () => {
    try {
      const result = await clearWatchHistory(userStore.user.id)
      if (result.code === 0) {
        historyList.value = []
        toast.success('已清空观看历史')
      }
    } catch (error) {
      console.error('Failed to clear history:', error)
    }
  })
}

async function handleUnfollow(seriesId: number) {
  if (!userStore.user?.id) return
  try {
    const result = await removeFollow(userStore.user.id, seriesId)
    if (result.code === 0) {
      followList.value = followList.value.filter(f => f.series.id !== seriesId)
      toast.success('已取消追更')
      pressedCardId.value = null
    }
  } catch (error) {
    console.error('Failed to unfollow:', error)
  }
}

async function handleRemoveBookmark(seriesId: number) {
  if (!userStore.user?.id) return
  try {
    const result = await removeBookmark(userStore.user.id, seriesId)
    if (result.code === 0) {
      favorites.value = favorites.value.filter(f => f.cid !== seriesId)
      toast.success('已取消收藏')
      pressedCardId.value = null
    }
  } catch (error) {
    console.error('Failed to remove bookmark:', error)
  }
}

async function loadBookmarks() {
    if (!userStore.user?.id) return
    loadingFavorites.value = true
    try {
      const result = await getBookmarks(userStore.user.id)
      if (result.code === 0) {
        favorites.value = (result.data.items || []).map(item => ({
          cid: item.series.cid,
          title: item.series.title,
          thumbnail: item.series.thumbnail,
          platform: item.series.platform,
          category_key: item.series.category_key,
          area: item.series.area,
          year: item.series.year,
          score: item.series.score,
          total_episodes: item.series.total_episodes,
          updated_episodes: item.series.updated_episodes,
        }))
      }
    } catch (error) {
      console.error('Failed to load bookmarks:', error)
    } finally {
      loadingFavorites.value = false
    }
  }

async function checkFollowUpdates() {
  if (!userStore.user?.id) return
  try {
    const result = await fetchFollowUpdates(userStore.user.id)
    if (result.code === 0 && result.data.length > 0) {
      await loadFollowList()
      toast.success(`有 ${result.data.length} 部剧集更新了`)
    } else {
      toast.success('所有剧集都是最新的')
    }
  } catch (error) {
    console.error('Failed to check updates:', error)
  }
}

async function saveSettings() {
  isSavingProfile.value = true
  try {
    const updatedUser = await updateProfile({
      username: editForm.value.username,
      nickname: editForm.value.nickname,
      email: editForm.value.email,
    })
    userStore.setLogin(
      userStore.accessToken || localStorage.getItem('access_token') || '',
      userStore.refreshToken || localStorage.getItem('refresh_token') || '',
      updatedUser
    )
    toast.success('保存成功')
  } catch (error: any) {
    toast.error(error.message || '保存失败')
  } finally {
    isSavingProfile.value = false
  }
}

async function handleChangePassword() {
  if (!passwordForm.value.newPassword) {
    toast.warning('请输入新密码')
    return
  }
  if (passwordForm.value.newPassword.length < 6) {
    toast.warning('密码长度不能少于6位')
    return
  }
  if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
    toast.warning('两次输入的密码不一致')
    return
  }

  isSavingPassword.value = true
  try {
    await changePassword(passwordForm.value.oldPassword, passwordForm.value.newPassword)
    toast.success('密码修改成功')
    // 清空表单
    passwordForm.value = {
      oldPassword: '',
      newPassword: '',
      confirmPassword: ''
    }
  } catch (error: any) {
    toast.error(error.message || '密码修改失败')
  } finally {
    isSavingPassword.value = false
  }
}

onMounted(async () => {
  // 全局点击监听：点击卡片外空白处关闭遮罩
  document.addEventListener('click', handleGlobalClick, true)

  // 只有在没有用户信息的情况下才从 localStorage 初始化
  // 避免覆盖已有的登录状态
  if (!userStore.user) {
    userStore.initFromStorage()
  }

  // 移动端：隐藏 ChannelBar
  setTimeout(() => {
    const ml = document.querySelector('.mobile-layout')
    if (ml) {
      ml.classList.add('no-channelbar')
    }
  }, 100)

  // 初始化完成，允许渲染
  isReady.value = true

  // 如果已登录，加载数据
  if (userStore.user) {
    editForm.value = {
      username: userStore.user.username || '',
      nickname: (userStore.user as any).nickname || userStore.user.username || '',
      email: userStore.user.email || '',
      phone: userStore.user.phone || ''
    }
    await Promise.all([loadWatchHistory(), loadFollowList(), loadBookmarks()])
  }
})

onBeforeUnmount(() => {
  cancelLongPress()
  document.removeEventListener('click', handleGlobalClick, true)
  if (deviceStore.isMobile) {
    const ml = document.querySelector('.mobile-layout')
    if (ml) {
      ml.classList.remove('no-channelbar')
    }
  }
})

// 监听登录状态变化
watch(() => userStore.isLoggedIn, async (isLogged) => {
  if (isLogged && userStore.user) {
    editForm.value = {
      username: userStore.user.username || '',
      nickname: (userStore.user as any).nickname || userStore.user.username || '',
      email: userStore.user.email || '',
      phone: userStore.user.phone || ''
    }
    await Promise.all([loadWatchHistory(), loadFollowList(), loadBookmarks()])
  }
})

// Tab切换时按需刷新数据
watch(activeTab, (tab) => {
  if (tab === 'favorites') {
    loadBookmarks()
  } else if (tab === 'follow') {
    loadFollowList()
  } else if (tab === 'history') {
    loadWatchHistory()
  } else if (tab === 'invite') {
    loadInviteData()
  }
})
</script>

<style lang="scss" scoped>
/* ========== 移动端返回栏 ========== */
.mobile-back-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 6px 12px 4px;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1001;
  background: var(--surface);
}

.page-content {
  padding-top: 52px !important;
}

.mobile-back-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: var(--text-primary);
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.2s ease;

  &:hover {
    background: var(--surface-hover);
  }
}

.mobile-back-title {
  font-size: 16px;
  color: var(--text-primary);
  flex: 1;
  text-align: center;
}

.mobile-menu-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  margin: 0;
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;

  &:active {
    color: var(--text-primary);
  }
}

/* ========== 移动端菜单 ========== */
.mobile-menu-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
}

.mobile-menu-panel {
  position: absolute;
  top: 54px;
  right: 12px;
  width: 160px;
  background: var(--surface);
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  overflow: hidden;
}

.mobile-menu-list {
  padding: 8px 0;
}

.mobile-menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 12px 16px;
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-size: 14px;
  text-align: left;
  cursor: pointer;

  &:active {
    background: var(--surface-hover);
  }

  &.active {
    color: var(--primary);
    background: var(--primary-light);
  }

  &.logout {
    color: var(--danger);
  }

  .menu-icon {
    font-size: 16px;
  }
}

.mobile-menu-divider {
  height: 1px;
  background: var(--border-light);
  margin: 8px 0;
}

/* ========== 移动端用户信息栏 - 现代化设计 ========== */
.mobile-user-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 16px;
  background: var(--surface);
  border-radius: 0;
  margin-bottom: 0;
  border-bottom: 1px solid var(--border-light);
  width: 100%;
  max-width: none;
  box-sizing: border-box;
}

.mobile-avatar-large {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--primary);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  flex-shrink: 0;
  border: 2px solid var(--primary-light);

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .avatar-text {
    font-size: 24px;
    font-weight: 700;
    color: white;
  }
}

.mobile-user-info-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.mobile-name-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.mobile-username {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.mobile-vip-tag {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;

  &.vip {
    background: linear-gradient(135deg, #ffd700, #ff8c00);
    color: #4a2800;
    box-shadow: 0 2px 8px rgba(255, 183, 0, 0.3);
  }

  &.normal {
    background: var(--surface-hover);
    color: var(--text-secondary);
  }
}

.mobile-user-email {
  font-size: 13px;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ========== 移动端底部Tab导航 ========== */
.mobile-bottom-tabs {
  display: flex;
  background: var(--surface);
  border-radius: 0;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-light);
}

.bottom-tab-item {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 12px;
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: 12px;
  position: relative;
  transition: all 0.3s ease;

  &:active {
    background: var(--surface-hover);
  }

  &.active {
    color: var(--primary);
    background: var(--primary-light);
    font-weight: 600;
    box-shadow: 0 4px 12px rgba(var(--primary-rgb, 59, 130, 246), 0.3);
    transform: scale(1.02);

    .tab-icon {
      transform: scale(1.1);
    }
  }

  .tab-icon {
    font-size: 20px;
    transition: transform 0.3s ease;
  }

  .tab-label {
    font-size: 14px;
    font-weight: 500;
  }

  .tab-count {
    min-width: 20px;
    height: 20px;
    padding: 0 6px;
    background: var(--danger);
    color: white;
    font-size: 11px;
    font-weight: 600;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
}

/* ========== Page ========== */
.page {
  min-height: 100vh;
  background: var(--background);
  padding-bottom: 20px;
}

/* ========== Container ========== */
.container {
  padding-top: 0;
  min-height: calc(100vh - 44px);
  display: flex;
  flex-direction: column;
}

/* ========== Main Content ========== */
.main-content {
  padding-bottom: 40px;
  min-height: calc(100vh - 44px);
  display: block;
}

/* ========== Login Prompt ========== */
.login-prompt {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: calc(100vh - 100px);
  padding: 24px;
  width: 100%;
}

.prompt-card {
  text-align: center;
  padding: 40px 32px;
  background: var(--surface);
  border-radius: 16px;
  max-width: 360px;
  width: 100%;

  .prompt-icon {
    font-size: 64px;
    display: block;
    margin-bottom: 16px;
  }

  h2 {
    font-size: 20px;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0 0 6px 0;
  }

  p {
    font-size: 14px;
    color: var(--text-secondary);
    margin: 0 0 24px 0;
  }
}

.login-btn {
  display: block;
  width: 100%;
  padding: 14px 0;
  background: var(--primary-solid);
  color: #ffffff;
  font-size: 16px;
  font-weight: 600;
  border-radius: 22px;
  text-decoration: none;
  text-align: center;
  margin-bottom: 16px;
  transition: all 0.2s;

  &:active {
    opacity: 0.85;
  }
}

.register-link {
  font-size: 13px;
  color: var(--text-muted);

  .link {
    color: var(--primary-solid);
    font-weight: 500;
    text-decoration: none;
    padding: 0;
    background: none;

    &:active {
      opacity: 0.7;
    }
  }
}

/* ========== User Center ========== */
.user-center {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 24px;
  display: flex;
  gap: 24px;
  align-items: flex-start;
}

/* ========== Sidebar Nav ========== */
.sidebar-nav {
  width: 260px;
  flex-shrink: 0;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: fixed;
  top: 88px;
  height: calc(100vh - 104px);
}

.sidebar-profile {
  padding: 24px 20px;
  text-align: center;
  border-bottom: 1px solid var(--border);
  background: linear-gradient(180deg, color-mix(in srgb, var(--gold) 6%, transparent), transparent);
}

.profile-avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  overflow: hidden;
  background: linear-gradient(135deg, var(--gold-light), var(--gold-dark));
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 12px;
  box-shadow: 0 0 20px var(--gold-glow);

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .avatar-text {
    font-size: 26px;
    font-weight: 700;
    color: #0a0a0f;
  }
}

.profile-info {
  min-width: 0;
}

.profile-name {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 6px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.profile-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.meta-item {
  font-size: 12px;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.meta-icon {
  opacity: 0.5;
}

.profile-stats {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.stat-label {
  font-size: 11px;
  color: var(--text-muted);
}

.stat-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--gold);
}

.invite-section {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--border);
}

.invite-label {
  font-size: 11px;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.invite-code-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.invite-code {
  font-size: 14px;
  font-weight: 600;
  color: var(--gold);
  letter-spacing: 1px;
  background: color-mix(in srgb, var(--gold) 10%, transparent);
  padding: 4px 10px;
  border-radius: 4px;
}

.copy-btn {
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 14px;
  opacity: 0.6;
  transition: opacity 0.2s;
  padding: 4px;
}

.sidebar-menu {
  padding: 8px;
  flex: 1;
}

.sidebar-menu-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
  text-align: left;

  &.active {
    background: var(--primary);
    color: #fff;
    font-weight: 600;
    box-shadow: 0 2px 10px color-mix(in srgb, var(--primary-solid) 30%, transparent);
  }
}

.menu-icon {
  font-size: 18px;
  flex-shrink: 0;
}

.menu-label {
  flex: 1;
}

.menu-badge {
  background: rgba(10, 10, 15, 0.3);
  color: inherit;
  font-size: 11px;
  font-weight: 700;
  padding: 1px 7px;
  border-radius: 10px;
  min-width: 20px;
  text-align: center;
}

.sidebar-footer {
  padding: 12px;
  border-top: 1px solid var(--border);
}

/* ========== Content Area ========== */
.content-area {
  flex: 1;
  min-width: 0;
  margin-left: 284px;
  padding-bottom: 20px;
}

/* ========== Tab Content ========== */
.tab-content {
  background: var(--surface);
  border: 1px solid var(--border-light);
  border-radius: 16px;
  overflow: hidden;
  margin-bottom: 20px;
  box-shadow: 0 2px 16px rgba(0,0,0,0.04);
}

.tab-panel {
  padding: 24px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.panel-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.panel-action {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 14px;
  background: var(--surface-hover);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

/* ========== 统一卡片网格（对齐频道页 series-grid 断点体系） ========== */
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 24px;
}

/* ========== 统一剧集卡片 ========== */
.series-card {
  background: var(--surface);
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid var(--border-light);
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  }
}

.card-poster {
  position: relative;
  width: 100%;
  aspect-ratio: 3/4;
  overflow: hidden;
  background: var(--surface-light);

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: transform 0.3s ease;
  }
}

.series-card:hover .card-poster img {
  transform: scale(1.05);
}

.poster-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.25s;

  &.visible {
    opacity: 1;
  }
}

.play-icon {
  font-size: 36px;
  color: white;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.5));
}

.overlay-cancel-btn {
  width: 56px;
  height: 56px;
  padding: 0;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.7);
  background: rgba(220, 38, 38, 0.7);
  color: #fff;
  font-size: 24px;
  line-height: 52px;
  text-align: center;
  cursor: pointer;
  backdrop-filter: blur(4px);
  transition: all 0.2s;

  &:hover {
    background: rgba(220, 38, 38, 0.95);
    border-color: #fff;
    transform: scale(1.05);
  }
}

.poster-ep-badge {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 6px 8px;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.75));
  color: #fff;
  font-size: 13px;
  text-align: right;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-title-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 6px;
  min-width: 0;
}

.card-year {
  color: var(--text-muted);
  font-size: 12px;
  flex-shrink: 0;
}



.card-info {
  padding: 10px 12px;
}

.card-title {
  font-size: 14px;
  font-weight: 400;
  color: var(--text-primary);
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.card-episodes {
  font-size: 12px;
  color: var(--text-secondary);
}

.card-tag {
  font-size: 11px;
  font-weight: 600;
  padding: 1px 7px;
  border-radius: 4px;

  &.finished {
    background: rgba(34, 197, 94, 0.15);
    color: var(--success);
  }

  &.updating {
    background: rgba(59, 130, 246, 0.15);
    color: var(--info);
  }

  &.platform {
    background: rgba(245, 158, 11, 0.15);
    color: var(--gold);
    font-weight: 500;
  }
}

/* ========== 历史卡片扩展 ========== */
.history-card {
  position: relative;
}

.card-progress-bar {
  width: 100%;
  height: 3px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  overflow: hidden;
}

.card-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--gold-dark), var(--gold-light));
  border-radius: 2px;
  transition: width 0.5s ease;
}

.card-progress-text {
  font-size: 14px;
  color: var(--text-muted);
  margin-top: 4px;
}

.history-card .card-meta {
  flex-direction: column;
  align-items: stretch;
}

/* ========== 历史卡片 Tooltip ========== */
.card-tooltip {
  position: absolute;
  inset: 0;
  background: rgba(14, 14, 22, 0.95);
  border-radius: 12px;
  padding: 14px;
  z-index: 10;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.25s ease;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.tooltip-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex-shrink: 0;
}

.tooltip-ep-list {
  flex: 1;
  overflow-y: auto;
  min-height: 0;

  &::-webkit-scrollbar {
    width: 4px;
  }

  &::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.15);
    border-radius: 2px;
  }
}

.tooltip-ep-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 5px 0;
  font-size: 14px;
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.15s ease;
}

.tooltip-ep-item + .tooltip-ep-item {
  border-top: 1px solid rgba(255, 255, 255, 0.04);
}

.tooltip-ep-title {
  flex: 1;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tooltip-ep-time {
  font-size: 13px;
  color: var(--text-muted);
  flex-shrink: 0;
}

/* ========== Settings ========== */
.settings-section {
  margin-bottom: 32px;

  &:last-child {
    margin-bottom: 0;
  }
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 16px 0;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
}

.settings-form {
  max-width: 480px;

  .form-group {
    margin-bottom: 20px;

    label {
      display: block;
      font-size: 13px;
      font-weight: 500;
      color: var(--text-secondary);
      margin-bottom: 6px;
    }

    input {
      width: 100%;
      padding: 12px 16px;
      background: var(--surface-hover);
      border: 1px solid var(--border);
      border-radius: 8px;
      color: var(--text-primary);
      font-size: 14px;
      transition: border-color 0.2s;

      &:focus {
        outline: none;
        border-color: var(--gold);
      }

      &::placeholder {
        color: var(--text-muted);
      }
    }
  }
}

.save-btn {
  width: 100%;
  padding: 13px 24px;
  background: var(--primary);
  border: none;
  border-radius: 8px;
  color: #ffffff;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;

  &:active {
    transform: translateY(0);
  }
}

/* ========== Empty State ========== */
.empty-state {
  text-align: center;
  padding: 64px 24px;

  .empty-animation {
    margin-bottom: 20px;

    .empty-icon {
      font-size: 56px;
      display: block;
      opacity: 0.4;
      animation: float 3s ease-in-out infinite;
    }
  }

  .empty-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 8px 0;
  }

  .empty-desc {
    font-size: 13px;
    color: var(--text-muted);
    margin: 0 0 20px 0;
  }

  .empty-action {
    display: inline-block;
    padding: 10px 24px;
    background: var(--primary);
    color: #ffffff;
    text-decoration: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    transition: all 0.2s;
  }
}

@keyframes float {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-6px);
  }
}

/* ========== Skeleton Loading ========== */
.skeleton-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
  pointer-events: none;
}

.skeleton-poster {
  width: 100%;
  aspect-ratio: 3/4;
  background: linear-gradient(90deg, var(--surface-hover) 25%, rgba(255, 255, 255, 0.05) 50%, var(--surface-hover) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}

.skeleton-info {
  padding: 12px;
}

.skeleton-title {
  height: 16px;
  width: 100%;
  margin-bottom: 10px;
  background: linear-gradient(90deg, var(--surface-hover) 25%, rgba(255, 255, 255, 0.05) 50%, var(--surface-hover) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 4px;
}

.skeleton-meta {
  height: 12px;
  width: 60%;
  background: linear-gradient(90deg, var(--surface-hover) 25%, rgba(255, 255, 255, 0.05) 50%, var(--surface-hover) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: 4px;
}

@keyframes shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

/* ========== Button Loading ========== */
.btn-loading {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid transparent;
  border-top-color: var(--text-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* ========== Logout ========== */
.logout-btn {
  width: 100%;
  padding: 10px 16px;
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 10px;
  color: var(--text-muted);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

/* ========== 卡片网格响应式（对齐频道页 series-grid 断点） ========== */

/* 宽屏优化 */
@media screen and (min-width: 1600px) {
  .card-grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 28px;
  }
}

@media screen and (min-width: 1920px) {
  .card-grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 32px;
  }
}

@media screen and (min-width: 2560px) {
  .card-grid {
    grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
    gap: 36px;
  }
}

/* 中等及小屏幕 */
@media screen and (max-width: 1400px) {
  .card-grid {
    grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
    gap: 20px;
  }
}

@media screen and (max-width: 1200px) {
  .card-grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 18px;
  }
}

@media screen and (max-width: 992px) {
  .card-grid {
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 16px;
  }

  .series-card .card-info {
    padding: 8px 10px;
  }

  .series-card .card-title {
    font-size: 13px;
  }
}

@media screen and (max-width: 768px) {
  .card-grid {
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 14px;
  }

  .history-grid {
    grid-template-columns: 1fr;
  }

  .series-card .card-info {
    padding: 6px;
  }

  .series-card .card-title {
    font-size: 14px;
  }

  .series-card:hover {
    transform: none;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  }

  .container {
    padding-top: 0;
  }

  .main-content {
    padding-top: 16px;
    padding-bottom: 60px;
  }

  .user-center {
    padding: 0;
    flex-direction: column;
    gap: 0;
    max-width: none;
    width: 100%;
  }

  .sidebar-nav {
    width: 100%;
    position: static;
    height: auto;
    top: auto;
  }

  .sidebar-profile {
    display: flex;
    align-items: center;
    gap: 16px;
    text-align: left;
    padding: 16px 20px;
  }

  .profile-avatar {
    width: 48px;
    height: 48px;
    margin: 0;

    .avatar-text {
      font-size: 20px;
    }
  }

  .profile-name {
    font-size: 15px;
  }

  .profile-meta {
    flex-direction: row;
    gap: 8px;
  }

  .meta-item {
    font-size: 11px;
  }

  .sidebar-menu {
    display: flex;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
    padding: 6px;
    gap: 4px;

    &::-webkit-scrollbar {
      display: none;
    }
  }

  .sidebar-menu-item {
    flex: none;
    padding: 8px 14px;
    font-size: 13px;
    border-radius: 8px;
  }

  .sidebar-footer {
    display: none;
  }

  .content-area {
    margin-left: 0;
    width: 100%;
    max-width: none;
  }

  .tab-content {
    border-radius: 0;
    border: none;
    border-top: 1px solid var(--border-light);
    margin-bottom: 0;
    width: 100%;
    max-width: none;
  }

  .tab-panel {
    padding: 16px;
    width: 100%;
    box-sizing: border-box;
  }

  /* 移动端观看历史卡片 - 横向布局 */
  .series-card.history-card {
    display: flex;
    flex-direction: row;
    align-items: stretch;
    height: auto;
    padding: 12px;
    gap: 12px;

    .card-poster {
      width: 120px;
      height: auto;
      aspect-ratio: 3 / 4;
      flex-shrink: 0;
      border-radius: 8px;
    }

    .card-info {
      flex: 1;
      display: flex;
      flex-direction: column;
      justify-content: flex-start;
      align-items: flex-start;
      min-width: 0;
      padding: 0;
      gap: 6px;
    }

    .card-title-row {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 8px;
      margin-bottom: 4px;
    }

    .card-title {
      font-size: 14px;
      font-weight: 500;
      line-height: 1.4;
      max-height: 1.4em;
      -webkit-line-clamp: 1;
      display: -webkit-box;
      -webkit-box-orient: vertical;
      overflow: hidden;
      text-overflow: ellipsis;
      flex: 1;
      min-width: 0;
    }

    .card-meta {
      flex-direction: column;
      align-items: flex-start;
      gap: 8px;
    }

    .card-tooltip {
      position: static;
      opacity: 1;
      pointer-events: auto;
      background: transparent;
      border-radius: 0;
      padding: 0;
      margin-top: 4px;
      max-height: 140px;
      overflow-y: auto;

      &::-webkit-scrollbar {
        width: 3px;
      }

      &::-webkit-scrollbar-thumb {
        background: var(--border);
        border-radius: 2px;
      }
    }

    .tooltip-ep-list {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .tooltip-ep-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 6px 8px;
      background: var(--surface-light);
      border-radius: 6px;
      font-size: 12px;
    }

    .tooltip-ep-title {
      flex: 1;
      overflow: hidden;
      white-space: nowrap;
      text-overflow: ellipsis;
      margin-right: 8px;
    }

    .tooltip-ep-time {
      color: var(--text-muted);
      font-size: 11px;
      flex-shrink: 0;
    }

    .tooltip-title {
      display: none;
    }
  }

  .prompt-buttons {
    flex-direction: column;
  }

  .login-prompt {
    min-height: calc(100vh - 80px);
    padding: 16px;
  }

  .prompt-card {
    padding: 32px 24px;
  }

  .settings-form {
    max-width: none;
  }
}

@media screen and (max-width: 576px) {
  .card-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }

  .history-grid {
    grid-template-columns: 1fr;
  }
}

@media screen and (max-width: 400px) {
  .card-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }
}

@media screen and (max-width: 480px) {
  .sidebar-profile {
    flex-direction: column;
    text-align: center;
  }

  .profile-meta {
    align-items: center;
    flex-direction: column;
  }

  .menu-icon {
    display: none;
  }

  .sidebar-menu-item {
    padding: 8px 12px;
    font-size: 12px;
  }
}

/* ========== 邀请页面样式 ========== */
.invite-card {
  background: linear-gradient(135deg, color-mix(in srgb, var(--gold) 10%, transparent), color-mix(in srgb, var(--gold) 2%, transparent));
  border: 1px solid var(--gold);
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;
}

.invite-stats {
  display: flex;
  justify-content: space-around;
  margin-bottom: 24px;
}

.stat-box {
  text-align: center;
  padding: 16px 24px;
  background: var(--surface);
  border-radius: 12px;
  min-width: 100px;
}

.stat-number {
  font-size: 32px;
  font-weight: 800;
  color: var(--gold);
  line-height: 1.2;
}

.stat-label {
  font-size: 13px;
  color: var(--text-muted);
  margin-top: 4px;
}

.invite-code-box {
  text-align: center;
  padding: 20px;
  background: var(--surface);
  border-radius: 12px;
  margin-bottom: 20px;
}

.invite-code-label {
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.invite-code-value {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-bottom: 8px;
}

.code-text {
  font-size: 28px;
  font-weight: 800;
  color: var(--gold);
  letter-spacing: 3px;
}

.copy-code-btn {
  padding: 8px 16px;
  background: var(--gold);
  border: none;
  border-radius: 8px;
  color: #1a1a1a;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.invite-hint {
  font-size: 12px;
  color: var(--text-muted);
}

.withdraw-section {
  padding: 16px;
  background: var(--surface);
  border-radius: 12px;
  margin-bottom: 20px;
}

.withdraw-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.withdraw-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.withdraw-desc {
  flex: 1;
}

.desc-text {
  font-size: 15px;
  color: var(--text-primary);
  font-weight: 500;
}

.withdraw-tip {
  font-size: 12px;
  color: var(--text-muted);
  margin-left: 8px;
}

.withdraw-btn {
  padding: 10px 24px;
  background: var(--gold);
  border: none;
  border-radius: 8px;
  color: #1a1a1a;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;

  &:disabled {
    background: var(--border);
    color: var(--text-muted);
    cursor: not-allowed;
  }
}

.rules-section {
  padding: 16px;
  background: var(--surface);
  border-radius: 12px;
}

.rules-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.rules-list {
  margin: 0;
  padding-left: 20px;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.8;

  li {
    margin-bottom: 4px;
  }
}

.invited-list-section {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
}

.invited-users {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.invited-user-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--surface-hover);
  border-radius: 10px;
  transition: background 0.2s;
}

.user-avatar {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  overflow: hidden;
  background: linear-gradient(135deg, var(--gold-light), var(--gold-dark));
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .avatar-default {
    font-size: 18px;
    font-weight: 700;
    color: #000;
  }
}

.user-info {
  flex: 1;
  min-width: 0;
}

.user-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-phone {
  font-size: 12px;
  font-weight: 400;
  color: var(--text-muted);
  margin-left: 4px;
}

.user-date {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}

.user-vip-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-muted);

  &.is-vip {
    background: linear-gradient(135deg, var(--gold-light), var(--gold-dark));
    color: #000;
  }
}

.empty-invite {
  text-align: center;
  padding: 48px 24px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;

  .empty-icon {
    font-size: 48px;
    display: block;
    margin-bottom: 16px;
    opacity: 0.5;
  }

  .empty-title {
    font-size: 16px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 8px 0;
  }

  .empty-desc {
    font-size: 13px;
    color: var(--text-muted);
    margin: 0;
  }
}

.loading-state {
  text-align: center;
  padding: 48px 24px;
  color: var(--text-muted);
}

.error-state {
  text-align: center;
  padding: 48px 24px;
  color: var(--text-muted);

  .error-icon {
    font-size: 48px;
    display: block;
    margin-bottom: 12px;
  }

  .error-text {
    font-size: 15px;
    margin-bottom: 16px;
  }

  .retry-btn {
    padding: 8px 24px;
    border-radius: 20px;
    background: var(--primary);
    color: #fff;
    border: none;
    cursor: pointer;
    font-size: 14px;

    &:hover {
      opacity: 0.85;
    }
  }
}

/* ========== 菜单动画 ========== */
.menu-fade-enter-active,
.menu-fade-leave-active {
  transition: opacity 0.2s ease;
}

.menu-fade-enter-from,
.menu-fade-leave-to {
  opacity: 0;
}

.menu-fade-enter-active .mobile-menu-panel,
.menu-fade-leave-active .mobile-menu-panel {
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.menu-fade-enter-from .mobile-menu-panel,
.menu-fade-leave-to .mobile-menu-panel {
  transform: translateY(-10px);
  opacity: 0;
}
</style>

<!-- 移动端用户页：隐藏 Header 和 ChannelBar -->
<style lang="scss">
.mobile-layout.no-channelbar {
  .sticky-header {
    display: none !important;
  }
}
</style>
