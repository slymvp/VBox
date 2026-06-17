<template>
  <div class="page">
    <!-- PC端独立渲染 Header，移动端由 MobileLayout 提供，TV端由 TVLayout 提供 -->
    <component
      v-if="deviceStore.isPC"
      :is="headerComponent"
      :show-type-filters="true"
      :show-layout-toggle="true"
      :layout="cardLayout"
      @layout-change="cardLayout = $event"
      @home-click="resetFilters"
    />

    <div class="container">
      <main class="main-content">
        <!-- 轮播图只在首页显示，且有数据才渲染避免空方框闪烁 -->
        <div v-if="isHomePage && featuredSeries.length > 0" class="carousel-section">
          <div class="carousel-container">
            <!-- 图片区域 -->
            <div class="carousel-image-wrapper">
              <img
                v-for="(series, index) in featuredSeries"
                :key="series.cid"
                :class="['carousel-image-item', { active: index === (hoverIndex === -1 ? currentIndex : hoverIndex) }]"
                :src="getProxyImageUrl(series.cover_url || series.thumbnail)"
                :alt="series.title"
                @click="goToDetail(series.cid)"
              />
            </div>

            <!-- 文字区域 -->
            <div class="carousel-text-list" @mouseenter="pauseCarousel()" @mouseleave="resumeCarousel()">
              <div
                v-for="(series, index) in featuredSeries"
                :key="series.cid"
                :class="['carousel-text-item', { active: index === (hoverIndex === -1 ? currentIndex : hoverIndex) }]"
                @click="goToSlide(index)"
                @mouseenter="hoverIndex = index"
                @mouseleave="hoverIndex = -1"
              >
                <div class="carousel-text">
                  {{ series.title }}
                </div>
              </div>
            </div>
          </div>
        </div>



        <div v-if="showUserCenter && isLoggedIn && user" class="user-center-panel">
          <div class="user-profile-section">
            <div class="user-avatar-large">
              <span>{{ user.username?.charAt(0).toUpperCase() }}</span>
            </div>
            <div class="user-info">
              <h2 class="user-name">{{ user.username }}</h2>
              <p class="user-email">{{ user.email || '未填写邮箱' }}</p>
              <p class="user-phone">{{ user.phone ? user.phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2') : '' }}</p>
            </div>
            <button class="close-btn" @click="showUserCenter = false">✕</button>
          </div>

          <div class="user-tabs">
            <div
              :class="['user-tab', { active: activeUserTab === 'follow' }]"
              @click="activeUserTab = 'follow'"
            >
              📺 我的追剧
              <span v-if="userFollowList.length > 0" class="tab-badge">{{ userFollowList.length }}</span>
            </div>
            <div
              :class="['user-tab', { active: activeUserTab === 'bookmarks' }]"
              @click="activeUserTab = 'bookmarks'"
            >
              ⭐ 我的收藏
              <span v-if="bookmarkedSet.size > 0" class="tab-badge">{{ bookmarkedSet.size }}</span>
            </div>
            <div
              :class="['user-tab', { active: activeUserTab === 'history' }]"
              @click="activeUserTab = 'history'"
            >
              📜 观看历史
            </div>
          </div>

          <div v-if="activeUserTab === 'follow'" class="user-content">
            <div v-if="userFollowList.length > 0" class="follow-grid">
              <div
                v-for="item in userFollowList"
                :key="item.series.id"
                class="follow-item"
                @click="goToDetail(item.series.cid)"
              >
                <img :src="getProxyImageUrl(item.series.thumbnail)" :alt="item.series.title" class="follow-cover" />
                <div class="follow-info">
                  <h4 class="follow-title">{{ item.series.title }}</h4>
                  <p class="follow-status">更新至 {{ item.series.updated_episodes }}/{{ item.series.total_episodes }} 集</p>
                </div>
              </div>
            </div>
            <div v-else class="empty-content">
              <span class="empty-icon">📭</span>
              <p>暂无追剧内容</p>
              <p class="empty-hint">去剧集详情页点击"追更"按钮添加</p>
            </div>
          </div>

          <div v-if="activeUserTab === 'bookmarks'" class="user-content">
            <div v-if="userBookmarks.length > 0" class="follow-grid">
              <div
                v-for="item in userBookmarks"
                :key="item.series.id"
                class="follow-item"
                @click="goToDetail(item.series.cid)"
              >
                <img :src="getProxyImageUrl(item.series.thumbnail)" :alt="item.series.title" class="follow-cover" />
                <div class="follow-info">
                  <h4 class="follow-title">{{ item.series.title }}</h4>
                  <p class="follow-status">{{ item.series.area || '' }} {{ item.series.year || '' }}</p>
                </div>
              </div>
            </div>
            <div v-else class="empty-content">
              <span class="empty-icon">⭐</span>
              <p>暂无收藏内容</p>
              <p class="empty-hint">在剧集卡片右上角点击 ⭐ 收藏喜欢的剧集</p>
            </div>
          </div>

            <div v-if="activeUserTab === 'history'" class="user-content">
            <div v-if="userHistoryList.length > 0" class="history-list">
              <div
                v-for="group in userHistoryList"
                :key="group.series.id"
                class="history-item"
                @click="goToDetail(group.series.cid)"
              >
                <img :src="getProxyImageUrl(group.series.thumbnail)" :alt="group.series.title" class="history-cover" />
                <div class="history-info">
                  <h4 class="history-title">{{ group.series.title }}</h4>
                  <p class="history-episode">已看 {{ group.watched_count }} / 共 {{ group.total_episodes || '?' }} 集</p>
                </div>
              </div>
            </div>
            <div v-else class="empty-content">
              <span class="empty-icon">📭</span>
              <p>暂无观看记录</p>
            </div>
          </div>
        </div>

        <div v-else-if="isHomePage">
          <div class="category-sections">
            <div
              v-for="cat in displayCategories"
              :key="cat.key"
              class="category-section"
            >
              <div class="category-header">
                <div class="category-title-row">
                  <span class="category-icon">{{ getCategoryIcon(cat.key) }}</span>
                  <h3 class="category-title">{{ cat.name }}</h3>

                  <!-- 排序标签 -->
                  <div class="category-sort-tabs">
                    <button
                      :class="['sort-tab', { active: (homeSortMap[cat.key] || 'latest') === 'latest' }]"
                      @click="handleHomeSort(cat.key, 'latest')"
                    >
                      最新
                    </button>
                    <button
                      :class="['sort-tab', { active: (homeSortMap[cat.key] || 'latest') === 'hot' }]"
                      @click="handleHomeSort(cat.key, 'hot')"
                    >
                      最热
                    </button>
                  </div>

                  <button class="category-more" @click="goToCategory(cat.key)">
                    更多 →
                  </button>
                </div>
                <div class="category-divider">
                  <div class="divider-line"></div>
                </div>
              </div>

              <div v-if="homeLoading[cat.key]" class="category-loading">
                <div class="spinner small"></div>
                <span>加载中...</span>
              </div>

              <div v-else-if="!homeCategoryData[cat.key] || homeCategoryData[cat.key].length === 0" class="category-empty">
                暂无内容
              </div>

              <div v-else :class="['series-grid', cardLayout]">
                <SeriesCard
                  v-for="series in getDisplaySeries(cat.key)"
                  :key="series.cid"
                  :series="series"
                  :layout="cardLayout"
                  :watched-count="watchProgress[series.id] || 0"
                  :is-followed="followedSet.has(series.id)"
                  :is-bookmarked="bookmarkedSet.has(series.id)"
                  @toggle-follow="handleToggleFollow"
                  @toggle-bookmark="handleToggleBookmark"
                />
              </div>
            </div>
          </div>
        </div>

        <div v-else>
          <!-- 移动端排序栏 -->
          <SortBar v-if="deviceStore.isMobile" />

          <div v-if="isLoading && seriesList.length === 0" class="loading">
            <div class="spinner"></div>
            <span>加载中...</span>
          </div>

          <div v-else-if="seriesList.length === 0" class="empty-state">
            <span class="empty-icon">📭</span>
            <h2 class="empty-title">暂无内容</h2>
            <p class="empty-desc">当前频道还没有剧集，请稍后再来</p>
          </div>

          <div v-else :class="['content-section', 'series-grid', cardLayout]">
            <SeriesCard
              v-for="series in seriesList"
              :key="series.cid"
              :series="series"
              :layout="cardLayout"
              :watched-count="watchProgress[series.id] || 0"
              :is-followed="followedSet.has(series.id)"
              :is-bookmarked="bookmarkedSet.has(series.id)"
              @toggle-follow="handleToggleFollow"
              @toggle-bookmark="handleToggleBookmark"
            />
          </div>

          <div v-if="hasMore && isLoading && seriesList.length > 0" class="loading-more">
            <div class="spinner small"></div>
            <span>加载更多...</span>
          </div>
          <div v-if="!hasMore && seriesList.length > 0" class="no-more">
            <span>- 已加载全部 -</span>
          </div>
        </div>
      </main>
    </div>

    <!-- 一键到顶 -->
    <div
      v-show="showBackToTop"
      class="back-to-top"
      @click="backToTop"
    >↑</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useSeriesStore } from '@/stores/series'
import { useUserStore } from '@/stores/user'
import { useDeviceStore } from '@/stores/device'
import { getFollowList, getWatchHistory, getProxyImageUrl, getWatchProgress, addFollow, removeFollow, getBookmarks, addBookmark, removeBookmark, PLATFORM_MAP, TYPE_MAP, type WatchHistoryGroup, type WatchProgressMap, type BookmarkItem, type Series } from '@/utils/api'
import { useTVGridNavigation } from '@/composables/useTVGridNavigation'
import SeriesCard from '@/components/SeriesCard.vue'
import PcHeader from '@/components/pc/Header.vue'
import SortBar from '@/components/mobile/SortBar.vue'

const router = useRouter()
const route = useRoute()
const store = useSeriesStore()
const userStore = useUserStore()
const deviceStore = useDeviceStore()

// TV 模式网格导航 - 首页分类区域
const categoryGridNav = useTVGridNavigation('.category-section .series-grid', '.series-card')
// TV 模式网格导航 - 分类列表页
const listGridNav = useTVGridNavigation('.content-section .series-grid', '.series-card')

// 卡片布局模式：竖版/横版
// 移动端强制使用竖版，PC/TV端默认横版
const cardLayout = ref<'vertical' | 'horizontal'>(deviceStore.isMobile
  ? 'vertical'
  : ((localStorage.getItem('cardLayout') as 'vertical' | 'horizontal') || 'horizontal'))
watch(cardLayout, (val) => { localStorage.setItem('cardLayout', val) })

// PC端使用 PcHeader
const headerComponent = PcHeader

// 显示的分类列表（从 store 获取）
const displayCategories = computed(() => {
  return store.categories
})

// 获取分类图标
function getCategoryIcon(key: string) {
  return store.categoryMap[key]?.icon || '📁'
}

const platforms = computed(() => store.platforms)
const seriesList = computed(() => store.seriesList)
const currentPlatform = computed(() => store.currentPlatform)
const currentCategory = computed(() => store.currentCategory)
const hasMore = computed(() => store.hasMore)
const isLoading = computed(() => store.isLoading)
const isLoggedIn = computed(() => userStore.isLoggedIn)
const user = computed(() => userStore.user)
const currentYear = computed(() => store.currentYear)
const currentArea = computed(() => store.currentArea)
const currentTag = computed(() => store.currentTag)
const currentDirector = computed(() => store.currentDirector)
const currentActor = computed(() => store.currentActor)
const currentSort = computed(() => store.currentSort)
const currentMinScore = computed(() => store.currentMinScore)
const filterOptions = computed(() => store.filterOptions)

// 判断是否是首页
const isHomePage = computed(() => route.path === '/')

// 首页分类数据
const homeCategoryData = computed(() => store.homeCategoryData)
const homeSortMap = computed(() => store.homeSortMap)
const homeLoading = computed(() => store.homeLoading)

// 获取每个分类要显示的剧集（默认两行，按响应式布局计算数量）
function getDisplaySeries(categoryKey: string) {
  const series = homeCategoryData.value[categoryKey] || []
  // 假设一行显示 6 个，两行就是 12 个
  return series.slice(0, 12)
}

// 首页排序切换
function handleHomeSort(categoryKey: string, sort: string) {
  store.loadHomeCategoryData(categoryKey, sort)
}

// 分类key到路由路径的映射
const categoryToPathMap: Record<string, string> = {
  tv: '/tv',
  movie: '/movie',
  variety: '/variety',
  cartoon: '/cartoon',
  child: '/child',
  free: '/free'
}

// 路由路径到分类key的映射
const pathToCategoryMap: Record<string, string> = {
  '/tv': 'tv',
  '/movie': 'movie',
  '/variety': 'variety',
  '/cartoon': 'cartoon',
  '/child': 'child',
  '/free': 'free'
}

// 跳转到分类页
function goToCategory(key: string) {
  router.push(categoryToPathMap[key] || '/')
}

// 路径到type的映射（用于 syncTypeFromRoute）
const pathToTypeMap: Record<string, string> = pathToCategoryMap

// 轮播数据：只从腾讯、爱奇艺取，只取电视剧、电影，带横版大图，按最热最新联合排序
const featuredSeries = computed(() => {
  // 只从电视剧、电影频道获取剧集（去掉综艺）
  const allowedCategories = ['tv', 'movie']
  const allowedPlatforms = ['tencent', 'iqiyi']

  const allSeries: any[] = []

  // 遍历所有分类，只获取允许的分类
  Object.entries(homeCategoryData.value).forEach(([categoryKey, seriesList]) => {
    if (allowedCategories.includes(categoryKey)) {
      allSeries.push(...(seriesList || []))
    }
  })

  // 使用cid去重，并且满足条件：
  // 1. 必须有cover_url（横板大图）
  // 2. 平台必须是腾讯或爱奇艺
  const seenCids = new Set()
  const uniqueSeries = allSeries.filter(s => {
    if (seenCids.has(s.cid)) return false
    if (!s.cover_url) return false
    if (!allowedPlatforms.includes(s.platform)) return false
    seenCids.add(s.cid)
    return true
  })

  // 按最热、最新联合排序
  // 排序规则：
  // 1. is_hot 为 1 的优先
  // 2. is_new 为 1 的其次
  // 3. 接着按 updated_at 降序（更新时间越新越靠前）
  // 4. 最后按评分降序
  const sorted = [...uniqueSeries].sort((a, b) => {
    // 先按 is_hot 排序
    if (a.is_hot !== b.is_hot) {
      return (b.is_hot || 0) - (a.is_hot || 0)
    }
    // 再按 is_new 排序
    if (a.is_new !== b.is_new) {
      return (b.is_new || 0) - (a.is_new || 0)
    }
    // 再按 updated_at 排序
    if (a.updated_at && b.updated_at) {
      return new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
    }
    // 最后按评分排序
    const scoreA = a.score || 0
    const scoreB = b.score || 0
    return scoreB - scoreA
  })

  // 取前8条
  return sorted.slice(0, 8)
})

// 轮播图逻辑
const currentIndex = ref(0)
const hoverIndex = ref(-1)
let carouselTimer: ReturnType<typeof setInterval> | null = null

function nextSlide() {
  if (featuredSeries.value.length === 0) return
  currentIndex.value = (currentIndex.value + 1) % featuredSeries.value.length
}

function prevSlide() {
  if (featuredSeries.value.length === 0) return
  currentIndex.value = (currentIndex.value - 1 + featuredSeries.value.length) % featuredSeries.value.length
}

function goToSlide(index: number) {
  currentIndex.value = index
}

function startCarousel() {
  if (carouselTimer) clearInterval(carouselTimer)
  carouselTimer = setInterval(() => {
    nextSlide()
  }, 4000)
}

function pauseCarousel() {
  if (carouselTimer) {
    clearInterval(carouselTimer)
    carouselTimer = null
  }
}

function resumeCarousel() {
  startCarousel()
}

// 重置筛选条件
function resetFilters() {
  router.push('/')
}

const showUserCenter = ref(false)
const activeUserTab = ref('follow')
const userFollowList = ref<any[]>([])
const userHistoryList = ref<WatchHistoryGroup[]>([])
const userBookmarks = ref<BookmarkItem[]>([])
const watchProgress = ref<WatchProgressMap>({})
const followedSet = ref(new Set<number>())
const bookmarkedSet = ref(new Set<number>())

async function loadUserCenterData() {
  if (!userStore.user?.id) return
  try {
    const [followResult, historyResult, bookmarkResult] = await Promise.all([
      getFollowList(userStore.user.id),
      getWatchHistory(userStore.user.id),
      getBookmarks(userStore.user.id)
    ])
    if (followResult.code === 0) {
      userFollowList.value = followResult.data.items || []
    }
    if (historyResult.code === 0) {
      userHistoryList.value = historyResult.data.items || []
    }
    if (bookmarkResult.code === 0) {
      userBookmarks.value = bookmarkResult.data.items || []
      bookmarkedSet.value = new Set(
        (bookmarkResult.data.items || []).map(item => item.series_id)
      )
    }
  } catch (error) {
    console.error('Failed to load user center data:', error)
  }
}

async function loadWatchProgress() {
  if (!userStore.user?.id) return
  try {
    const result = await getWatchProgress(userStore.user.id)
    if (result.code === 0) {
      watchProgress.value = result.data || {}
    }
  } catch (error) {
    console.error('Failed to load watch progress:', error)
  }
}

async function loadFollowedSet() {
  if (!userStore.user?.id) return
  try {
    const result = await getFollowList(userStore.user.id)
    if (result.code === 0) {
      followedSet.value = new Set(
        (result.data.items || []).map(item => item.series_id)
      )
    }
  } catch (error) {
    console.error('Failed to load follow list:', error)
  }
}

async function handleToggleFollow(seriesId: number) {
  if (!userStore.user?.id) {
    router.push('/user')
    return
  }
  try {
    if (followedSet.value.has(seriesId)) {
      await removeFollow(userStore.user.id, seriesId)
      const next = new Set(followedSet.value)
      next.delete(seriesId)
      followedSet.value = next
    } else {
      await addFollow(userStore.user.id, seriesId)
      const next = new Set(followedSet.value)
      next.add(seriesId)
      followedSet.value = next
    }
  } catch (error) {
    console.error('Toggle follow failed:', error)
  }
}

async function loadBookmarkedSet() {
  if (!userStore.user?.id) return
  try {
    const result = await getBookmarks(userStore.user.id)
    if (result.code === 0) {
      bookmarkedSet.value = new Set(
        (result.data.items || []).map(item => item.series_id)
      )
      userBookmarks.value = result.data.items || []
    }
  } catch (error) {
    console.error('Failed to load bookmarks:', error)
  }
}

async function handleToggleBookmark(seriesId: number) {
  if (!userStore.user?.id) {
    router.push('/user')
    return
  }
  try {
    if (bookmarkedSet.value.has(seriesId)) {
      await removeBookmark(userStore.user.id, seriesId)
      bookmarkedSet.value = new Set([...bookmarkedSet.value].filter(id => id !== seriesId))
      userBookmarks.value = userBookmarks.value.filter(item => item.series_id !== seriesId)
    } else {
      await addBookmark(userStore.user.id, seriesId)
      // 同时刷新列表，获取完整 series 数据
      await loadBookmarkedSet()
    }
  } catch (error) {
    console.error('Toggle bookmark failed:', error)
  }
}

function goToDetail(cid: string) {
  showUserCenter.value = false
  router.push(`/detail/${cid}`)
}

const pageTitle = computed(() => {
  const typeName = currentCategory.value ? store.TYPE_MAP[currentCategory.value]?.name : null

  if (typeName) {
    return typeName
  } else if (currentPlatform.value !== 'all') {
    return store.PLATFORM_MAP[currentPlatform.value]?.name || currentPlatform.value
  } else {
    return '全部剧集'
  }
})

const pageSubtitle = computed(() => {
  const typeName = currentCategory.value ? store.TYPE_MAP[currentCategory.value]?.name : null

  if (typeName) {
    return `${typeName}内容`
  } else if (currentPlatform.value !== 'all') {
    return `${store.PLATFORM_MAP[currentPlatform.value]?.name}精选内容`
  } else {
    return '浏览精彩内容'
  }
})

function handleLogoClick() {
  store.resetFilters()
  loadData()
}

function loadData() {
  store.loadSeries(true)
}

function loadMore() {
  if (hasMore.value && !isLoading.value) {
    store.loadSeries()
  }
}

const showBackToTop = ref(false)

function backToTop() {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function handleScroll() {
  const scrollTop = window.scrollY || document.documentElement.scrollTop || document.body.scrollTop
  const scrollHeight = Math.max(
    document.documentElement.scrollHeight,
    document.body.scrollHeight
  )
  const clientHeight = window.innerHeight || document.documentElement.clientHeight

  if (scrollTop + clientHeight >= scrollHeight - 200 && !isLoading.value) {
    loadMore()
  }

  showBackToTop.value = scrollTop > 400
}

// 根据路由设置类型
function syncTypeFromRoute() {
  // 详情页路由不重置分类，由 detail.vue 自行设置
  if (route.path.startsWith('/detail/')) return

  // 根路径默认跳转到电视剧频道
  if (route.path === '/') {
    router.replace('/tv')
    return
  }

  const type = pathToTypeMap[route.path]
  const isSameType = type && currentCategory.value === type
  const isSameHome = !type && !currentCategory.value

  // 如果是同一类型且没有携带筛选条件，且有数据，跳过
  if ((isSameType || isSameHome) && !hasActiveFilter() && seriesList.value.length > 0) {
    return
  }

  if (type) {
    // 如果切换到不同的分类，重置所有筛选条件
    if (currentCategory.value !== type) {
      store.resetFilterOptions()
    }
    store.setCategory(type)
  } else {
    // 跳转到首页，重置所有筛选
    store.resetFilters()
  }
  loadData()
  store.loadFilterOptions()
}

// 检查是否有激活的筛选条件（用于从详情页点击标签/演员后触发重新加载）
function hasActiveFilter() {
  return currentTag.value !== 'all' || 
         currentActor.value !== 'all' || 
         currentDirector.value !== 'all'
}

// TV端键盘事件处理
function handleTVKeydown(e: KeyboardEvent) {
  // 获取当前聚焦的元素
  const activeEl = document.activeElement as HTMLElement
  if (!activeEl) return

  // 如果当前在输入框内，不处理方向键
  const tagName = activeEl.tagName.toLowerCase()
  if (tagName === 'input' || tagName === 'textarea') return

  const key = e.key

  // 左右方向键 - 在同一行内导航
  if (key === 'ArrowLeft' || key === 'ArrowRight') {
    e.preventDefault()
    const focusableEls = document.querySelectorAll('.focusable')
    if (focusableEls.length === 0) return

    const elsArray = Array.from(focusableEls) as HTMLElement[]
    const currentIndex = elsArray.indexOf(activeEl)

    if (currentIndex === -1) {
      // 如果当前元素不在列表中，聚焦第一个
      elsArray[0]?.focus()
      return
    }

    let nextIndex: number
    if (key === 'ArrowLeft') {
      nextIndex = currentIndex > 0 ? currentIndex - 1 : elsArray.length - 1
    } else {
      nextIndex = currentIndex < elsArray.length - 1 ? currentIndex + 1 : 0
    }

    elsArray[nextIndex]?.focus()
    return
  }

  // 上方向键 - 尝试移动到上一行
  if (key === 'ArrowUp') {
    e.preventDefault()
    const focusableEls = document.querySelectorAll('.focusable')
    if (focusableEls.length === 0) return

    const elsArray = Array.from(focusableEls) as HTMLElement[]
    const currentIndex = elsArray.indexOf(activeEl)

    if (currentIndex === -1) {
      elsArray[0]?.focus()
      return
    }

    // 简单实现：移动到上一个元素
    const prevIndex = currentIndex > 0 ? currentIndex - 1 : elsArray.length - 1
    elsArray[prevIndex]?.focus()
    return
  }

  // 下方向键 - 尝试移动到下一行
  if (key === 'ArrowDown') {
    e.preventDefault()
    const focusableEls = document.querySelectorAll('.focusable')
    if (focusableEls.length === 0) return

    const elsArray = Array.from(focusableEls) as HTMLElement[]
    const currentIndex = elsArray.indexOf(activeEl)

    if (currentIndex === -1) {
      elsArray[0]?.focus()
      return
    }

    // 简单实现：移动到下一个元素
    const nextIndex = currentIndex < elsArray.length - 1 ? currentIndex + 1 : 0
    elsArray[nextIndex]?.focus()
    return
  }
}

onMounted(async () => {
  try {
    userStore.initFromStorage()
    store.loadPlatforms()
    store.loadStats() // 加载统计数据
    await store.loadCategories() // 加载分类数据
    store.loadAllSeries()
  } catch (e) {
    console.error('Index page init error:', e)
  }

  // TV端默认直接跳转到电视剧频道
  if (deviceStore.isTV && isHomePage.value) {
    router.push('/tv')
    return
  }

  syncTypeFromRoute()

  // 兜底：频道页无数据时强制重新加载
  if (!isHomePage.value && seriesList.value.length === 0 && !isLoading.value) {
    loadData()
  }

  loadWatchProgress()
  loadFollowedSet()
  loadBookmarkedSet()
  window.addEventListener('scroll', handleScroll)

  // 检查是否需要滚动到顶部（从筛选页返回时）
  nextTick(() => {
    const scrollToTop = sessionStorage.getItem('scrollToTop')
    if (scrollToTop === 'true') {
      window.scrollTo({ top: 0, behavior: 'smooth' })
      sessionStorage.removeItem('scrollToTop')
    }
  })

  // TV端键盘事件监听
  if (deviceStore.isTV) {
    window.addEventListener('keydown', handleTVKeydown)
  }

  // 初始化首页数据
  if (isHomePage.value) {
    store.initHomeData()
  }

})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
  window.removeEventListener('keydown', handleTVKeydown)
  pauseCarousel()
})

// 监听路由变化
watch(() => route.path, (newPath, oldPath) => {
  // 记录频道路径，供登录/注册/用户页返回使用
  if (newPath.match(/^\/(tv|movie|variety|cartoon|child|free)$/)) {
    sessionStorage.setItem('lastCategory', newPath)
  }

  // 如果是从详情页返回，利用 syncTypeFromRoute 中的 isSameType 检查避免重复加载
  syncTypeFromRoute()
  // 初始化首页数据
  if (isHomePage.value) {
    store.initHomeData()
  } else {
    pauseCarousel()
  }
})

// 监听轮播数据变化，自动启动轮播
watch(featuredSeries, (newVal) => {
  if (isHomePage.value && newVal.length > 0) {
    currentIndex.value = 0
    startCarousel()
  }
})

// 切换到收藏Tab时刷新数据
watch(activeUserTab, (tab) => {
  if (tab === 'bookmarks') {
    loadBookmarkedSet()
  }
})

// 打开用户中心时重新加载全部数据
watch(showUserCenter, (visible) => {
  if (visible) {
    loadUserCenterData()
  }
})
</script>

<style lang="scss" scoped>
.page {
  min-height: 100vh;
  background: var(--background);
  padding-bottom: 60px;
}

.carousel-section {
  margin-bottom: 32px;
}

.carousel-container {
  position: relative;
  width: 100%;
  height: 600px;
  border-radius: 0;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
}

.carousel-image-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
}

.carousel-image-item {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center top;
  opacity: 0;
  transition: opacity 0.5s ease-in-out;
  cursor: pointer;

  &.active {
    opacity: 1;
  }
}

.carousel-text-list {
  position: absolute;
  right: 0;
  top: 0;
  width: auto;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 0;
  padding: 0 24px;
}

.carousel-text-item {
  flex: 0 0 auto;
  display: block;
  text-align: right;
  cursor: pointer;
  position: relative;
  padding: 6px 0;
}

.carousel-text {
  font-size: 16px;
  font-weight: 400;
  color: rgba(255, 255, 255, 0.65);
  line-height: 1.5;
  user-select: none;
  transition: font-size 0.25s ease, color 0.25s ease, text-shadow 0.25s ease, font-weight 0.25s ease;
  white-space: nowrap;
  display: inline-block;
  text-align: right;
}

/* hover 和 active 同时存在时，active 优先 */
.carousel-text-item.active .carousel-text {
  color: #fff;
  font-size: 19px;
  font-weight: 500;
  text-shadow: 0 0 12px rgba(0, 0, 0, 1), 0 0 20px rgba(0, 0, 0, 0.7);
}





.container {
  display: flex;
  padding-top: 72px;
}

.main-content {
  flex: 1;
  padding: 32px;
  /* 移除最大宽度限制，实现全屏宽屏布局 */
  /* max-width: 1400px; */
  /* margin: 0 auto; */
  width: 100%;
}

.page-header {
  margin-bottom: 32px;
  text-align: left;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 20px;
  flex-wrap: wrap;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.page-subtitle {
  font-size: 14px;
  color: var(--text-muted);
  margin: 0;
  width: 100%;
}


.loading {
  text-align: center;
  padding: 80px 20px;
  color: var(--text-muted);
}

.spinner {
  width: 48px;
  height: 48px;
  border: 3px solid var(--surface-light);
  border-top-color: var(--gold);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 16px;

  &.small {
    width: 24px;
    height: 24px;
    border-width: 2px;
  }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-state {
  text-align: center;
  padding: 100px 20px;
  color: var(--text-muted);
}

.empty-icon {
  font-size: 80px;
  display: block;
  margin-bottom: 20px;
  opacity: 0.5;
}

.empty-title {
  font-size: 24px;
  font-weight: 600;
  margin: 0 0 10px 0;
}

.empty-desc {
  font-size: 14px;
  margin: 0;
}

.series-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 24px;
}

/* 横版模式grid列宽 - 卡片更宽，需要更大的minmax */
.series-grid.horizontal {
  grid-template-columns: repeat(auto-fill, minmax(440px, 1fr));
  gap: 24px;
}

/* 超宽屏优化 - 显示更多列 */
@media screen and (min-width: 1600px) {
  .series-grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 28px;
  }

  .series-grid.horizontal {
    grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
    gap: 24px;
  }
}

@media screen and (min-width: 1920px) {
  .series-grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 32px;
  }

  .main-content {
    padding: 40px;
  }
}

@media screen and (min-width: 2560px) {
  .series-grid {
    grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
    gap: 36px;
  }

  .main-content {
    padding: 48px;
  }
}

/* 响应式断点优化 - 中等及小屏幕 */
@media screen and (max-width: 1400px) {
  .series-grid {
    grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
    gap: 20px;
  }
}

@media screen and (max-width: 1200px) {
  .series-grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 18px;
  }
}

@media screen and (max-width: 992px) {
  .series-grid {
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 16px;
  }
}

@media screen and (max-width: 768px) {
  .series-grid {
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 14px;
  }

  .main-content {
    padding: 24px;
  }
}

@media screen and (max-width: 576px) {
  .series-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }

  .main-content {
    padding: 16px;
  }
}

@media screen and (max-width: 400px) {
  .series-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }
}

.loading-more {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 24px;
  color: var(--text-muted);
  font-size: 14px;
}

.no-more {
  text-align: center;
  padding: 24px;
  color: var(--text-muted);
  font-size: 14px;
}

@media screen and (max-width: 750px) {
  .category-title-row {
    gap: 8px;
  }

  .category-icon {
    font-size: 18px;
  }

  .category-title {
    font-size: 16px;
  }

  .carousel-container {
    height: 400px;
    border-radius: 12px;
  }

  .carousel-overlay {
    padding: 24px;
  }

  .carousel-title {
    font-size: 24px;
  }

  .carousel-meta {
    font-size: 14px;
    display: flex;
    align-items: center;
    gap: 8px;
    .content-type {
      font-size: 12px;
      font-weight: 600;
    }
  }

  .carousel-arrow {
    width: 44px;
    height: 44px;
    font-size: 22px;

    &.left {
      left: 12px;
    }

    &.right {
      right: 12px;
    }
  }

  .carousel-dots {
    bottom: 16px;
    gap: 8px;
  }

  .dot {
    width: 8px;
    height: 8px;

    &.active {
      width: 24px;
    }
  }

  .container {
    padding-top: 0; /* 移动端由 MobileLayout 处理顶部间距 */
  }

  .main-content {
    margin-left: 0;
    padding: 16px;
  }

  .series-grid {
    grid-template-columns: repeat(auto-fill, minmax(168px, 1fr));
    gap: 12px;
  }
}

.user-center-panel {
  max-width: 800px;
}

.user-profile-section {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 32px;
  background: var(--surface);
  border-radius: 16px;
  margin-bottom: 24px;
  position: relative;
}

.user-avatar-large {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--gold-light), var(--gold-dark));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40px;
  font-weight: 700;
  color: #fff;
}

.user-info {
  flex: 1;
}

.user-name {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.user-email,
.user-phone {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 4px 0;
}

.close-btn {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: none;
  background: var(--surface-light);
  color: var(--text-secondary);
  font-size: 16px;
  cursor: pointer;
  transition: all 0.2s ease;

}

.user-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
}

.user-tab {
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
  background: var(--surface);
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 8px;

  &.active {
    background: var(--primary);
    color: #fff;
    box-shadow: 0 2px 8px color-mix(in srgb, var(--primary-solid) 25%, transparent);
  }
}

.tab-badge {
  background: var(--error);
  color: #fff;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 10px;
}

.user-content {
  background: var(--surface);
  border-radius: 16px;
  padding: 24px;
}

.follow-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.follow-item {
  cursor: pointer;
  transition: transform 0.2s ease;
}

.follow-cover {
  width: 100%;
  height: 120px;
  object-fit: cover;
  border-radius: 8px;
  margin-bottom: 12px;
}

.follow-info {
  padding: 0 4px;
}

.follow-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  margin: 0 0 4px 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.follow-status {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 12px;
  background: var(--surface-light);
  border-radius: 12px;
  cursor: pointer;
  transition: background 0.2s ease;
}

.history-cover {
  width: 80px;
  height: 45px;
  object-fit: cover;
  border-radius: 6px;
}

.history-info {
  flex: 1;
}

.history-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
  margin: 0 0 4px 0;
}

.history-episode {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
}

.empty-content {
  text-align: center;
  padding: 48px;
  color: var(--text-muted);
}

.empty-hint {
  font-size: 12px;
  color: var(--text-muted);
}

/* 首页分类区域 */
.category-sections {
  display: flex;
  flex-direction: column;
}

.category-section {
  padding: 0;
  padding-bottom: 32px;
  margin-bottom: 32px;
}

.category-header {
  margin-bottom: 20px;
  text-align: center;
}

.category-title-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
}

.category-icon {
  font-size: 24px;
}

.category-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0;
}

.category-divider {
  margin-top: 12px;
}

.divider-line {
  width: 100%;
  height: 1px;
  background: var(--border);
}

.category-sort-tabs {
  display: flex;
  gap: 2px;
  background: var(--surface);
  border-radius: 6px;
  padding: 2px;
}

.sort-tab {
  padding: 4px 10px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 500;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;

  &.active {
    background: var(--primary);
    color: #fff;
    box-shadow: 0 2px 8px color-mix(in srgb, var(--primary-solid) 25%, transparent);
  }
}

.category-more {
  margin-left: auto;
  padding: 6px 16px;
  border: none;
  background: var(--surface);
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.category-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 32px 0;
  color: var(--text-muted);
}

.category-empty {
  text-align: center;
  padding: 32px 0;
  color: var(--text-muted);
  font-size: 14px;
}

/* 首页分类区域的 series-grid 样式调整 */
.category-section .series-grid {
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 16px;
}

@media screen and (min-width: 1600px) {
  .category-section .series-grid {
    grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
    gap: 20px;
  }
}

@media screen and (max-width: 768px) {
  .category-section {
    padding: 0;
    padding-bottom: 24px;
    margin-bottom: 24px;
  }

  .category-section .series-grid {
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 12px;
  }

  .category-title {
    font-size: 18px;
  }

  .sort-tab {
    padding: 4px 12px;
    font-size: 12px;
  }
}

/* ==================== 横版模式响应式grid ==================== */
@media screen and (min-width: 1600px) {
  .series-grid.horizontal {
    grid-template-columns: repeat(auto-fill, minmax(480px, 1fr));
    gap: 28px;
  }
}

@media screen and (min-width: 1920px) {
  .series-grid.horizontal {
    grid-template-columns: repeat(auto-fill, minmax(520px, 1fr));
    gap: 32px;
  }
}

@media screen and (min-width: 2560px) {
  .series-grid.horizontal {
    grid-template-columns: repeat(auto-fill, minmax(560px, 1fr));
    gap: 36px;
  }
}

@media screen and (max-width: 1400px) {
  .series-grid.horizontal {
    grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
    gap: 22px;
  }
}

@media screen and (max-width: 1200px) {
  .series-grid.horizontal {
    grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
    gap: 18px;
  }
}

@media screen and (max-width: 992px) {
  .series-grid.horizontal {
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    gap: 16px;
  }
}

@media screen and (max-width: 768px) {
  .series-grid.horizontal {
    grid-template-columns: 1fr;
    gap: 14px;
  }
}

@media screen and (max-width: 576px) {
  .series-grid.horizontal {
    grid-template-columns: 1fr;
    gap: 12px;
  }
}

/* 分类区域横版grid */
.category-section .series-grid.horizontal {
  grid-template-columns: repeat(auto-fill, minmax(440px, 1fr));
  gap: 20px;
}

@media screen and (min-width: 1600px) {
  .category-section .series-grid.horizontal {
    grid-template-columns: repeat(auto-fill, minmax(480px, 1fr));
    gap: 24px;
  }
}

@media screen and (max-width: 768px) {
  .category-section .series-grid.horizontal {
    grid-template-columns: 1fr;
    gap: 12px;
  }
}

/* ==================== 布局切换按钮 ==================== */
.layout-toggle {
  display: flex;
  gap: 4px;
  margin-right: 12px;
  background: var(--surface);
  border-radius: 8px;
  padding: 4px;
}

.layout-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;

  &.active {
    background: color-mix(in srgb, var(--gold) 15%, transparent);
    color: var(--gold);
  }
}

@media screen and (max-width: 768px) {
  .layout-toggle {
    margin-right: 8px;
    padding: 2px;
  }

  .layout-btn {
    width: 32px;
    height: 32px;
  }
}

/* 一键到顶火箭 */
.back-to-top {
  position: fixed;
  right: 16px;
  bottom: 24px;
  z-index: 9999;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: none;
  cursor: pointer;
  background: var(--primary);
  color: #fff;
  font-size: 20px;
  font-weight: 900;
  line-height: 40px;
  text-align: center;
  user-select: none;
  box-shadow: 0 3px 12px rgba(0,0,0,0.3);
  transition: transform 0.2s ease;

  &:active {
    transform: scale(0.9);
  }
}

</style>
