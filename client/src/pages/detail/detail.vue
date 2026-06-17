<template>
  <div class="page">
    <!-- PC端独立渲染 Header -->
    <component
      v-if="deviceStore.isPC"
      :is="headerComponent"
      :show-type-filters="true"
      @home-click="goBack"
    />

    <!-- 移动端标题行：返回 + 剧集名称 + 选集 -->
    <div v-if="deviceStore.isMobile && series" class="mobile-title-row">
      <button class="mobile-title-back" @click="goBack">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5"/><path d="M12 19l-7-7 7-7"/></svg>
      </button>
      <span class="mobile-title-text">{{ series.title }}<template v-if="series.total_episodes"> 选集</template></span>
    </div>

    <div class="container">
      <main class="main-content">
        <div class="content-wrapper">
          <div v-if="isLoading" class="loading">
            <div class="spinner"></div>
            <span>加载中...</span>
          </div>

          <div v-else-if="series" class="detail-card">
            <!-- ========== 封面区 ========== -->
            <div class="detail-hero" @click="playFirstEpisode">
              <img
                class="detail-cover"
                :src="coverImage"
                :alt="series.title"
                @error="handleCoverError"
              />
              <div class="detail-cover-overlay">
                <div class="detail-play-icon">
                  <svg viewBox="0 0 80 80" width="64" height="64" fill="none">
                    <circle cx="40" cy="40" r="38" fill="rgba(0,0,0,0.5)" stroke="rgba(255,255,255,0.8)" stroke-width="2"/>
                    <polygon points="32,22 32,58 62,40" fill="rgba(255,255,255,0.9)"/>
                  </svg>
                </div>
                <div class="detail-cover-bottom">
                  <div class="detail-cover-info">
                    <h1 class="detail-hero-title">{{ series.title }}</h1>
                    <div class="cover-meta-row">
                      <span class="cover-platform" :class="platformBadge">{{ platformName }}</span>
                      <span v-if="!isMovie" class="cover-ep-badge">
                        <template v-if="series.updated_episodes && series.total_episodes && series.updated_episodes < series.total_episodes">更新至{{ series.updated_episodes }}集/共{{ series.total_episodes }}集</template>
                        <template v-else-if="series.total_episodes">共{{ series.total_episodes }}集</template>
                      </span>
                    </div>
                  </div>
                  <div class="detail-cover-actions" @click.stop>
                    <button
                      :class="['action-btn', { active: isBookmarked }]"
                      @click="handleBookmark"
                    >
                      <svg viewBox="0 0 24 24" class="action-icon">
                        <path v-if="isBookmarked" fill="currentColor" d="M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 22 12 18.56 5.82 22 7 14.14l-5-4.87 6.91-1.01L12 2z"/>
                        <path v-else fill="none" stroke="currentColor" stroke-width="1.8" d="M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 22 12 18.56 5.82 22 7 14.14l-5-4.87 6.91-1.01L12 2z"/>
                      </svg>
                      <span>{{ isBookmarked ? '已收藏' : '收藏' }}</span>
                    </button>
                    <button
                      v-if="!isMovie && !isFinished"
                      :class="['action-btn', { active: isFollowed }]"
                      @click="handleFollow"
                    >
                      <svg viewBox="0 0 24 24" class="action-icon">
                        <path v-if="isFollowed" fill="currentColor" d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                        <path v-else fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" d="M12 5v14M5 12h14"/>
                      </svg>
                      <span>{{ isFollowed ? '已追剧' : '追剧' }}</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- ========== Tab 区域 ========== -->
            <div class="detail-tabs">
              <button
                v-for="tab in tabs"
                :key="tab.key"
                :class="['detail-tab', { active: activeTab === tab.key }]"
                @click="activeTab = tab.key"
              >
                {{ tab.label }}
              </button>
            </div>

            <div class="detail-body">
              <!-- 简介 Tab -->
              <div v-if="activeTab === 'intro'" class="tab-content">
                <div v-if="series.description" class="detail-description">
                  <p>{{ series.description }}</p>
                </div>
                <div v-else class="tab-empty">暂无简介</div>
              </div>

              <!-- 分集 Tab（默认） -->
              <div v-if="activeTab === 'episodes'" class="tab-content">
                <div v-if="series.episodes && series.episodes.length > 0" class="detail-episodes">
                  <EpisodeGrid
                    :episodes="series.episodes"
                    :active-episode-id="activeEpisodeId"
                    @episode-click="handleEpisodeClick"
                  />
                </div>
                <div v-else class="tab-empty">暂无分集数据</div>
              </div>

              <!-- 演员 Tab -->
              <div v-if="activeTab === 'actors'" class="tab-content">
                <div v-if="actors.length > 0" class="tag-list">
                  <button
                    v-for="actor in actors"
                    :key="actor"
                    class="tag-item"
                    @click="handleMetaClick('actor', actor)"
                  >
                    {{ actor }}
                  </button>
                </div>
                <div v-else class="tab-empty">暂无演员信息</div>
              </div>

              <!-- 标签 Tab -->
              <div v-if="activeTab === 'tags'" class="tab-content">
                <div v-if="tags.length > 0" class="tag-list">
                  <button
                    v-for="tag in tags"
                    :key="tag"
                    class="tag-item"
                    @click="handleMetaClick('tag', tag)"
                  >
                    {{ tag }}
                  </button>
                </div>
                <div v-else class="tab-empty">暂无标签</div>
              </div>
            </div>
          </div>

          <div v-else class="empty-state">
            <span class="empty-icon">📭</span>
            <h2 class="empty-title">剧集不存在</h2>
            <p class="empty-desc">找不到您要查看的剧集</p>
            <button class="back-home-btn" @click="resetFilters">返回首页</button>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, onUnmounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { fetchSeriesDetail, parseTags, parseActors, PLATFORM_MAP, TYPE_MAP, getProxyImageUrl, updateWatchHistory, addFollow, removeFollow, checkFollow, addBookmark, removeBookmark, checkBookmark, type Series, type Episode } from '@/utils/api'
import { useUserStore } from '@/stores/user'
import { useSeriesStore } from '@/stores/series'
import { useDeviceStore } from '@/stores/device'
import { useThemeStore } from '@/stores/theme'
import { useToast } from '@/composables/useToast'
import { useTVGridNavigation } from '@/composables/useTVGridNavigation'
import EpisodeGrid from '@/components/EpisodeGrid.vue'
import PcHeader from '@/components/pc/Header.vue'
import placeholderHero from '@/assets/placeholder_hero.png'

const deviceStore = useDeviceStore()
const themeStore = useThemeStore()
// PC端使用 PcHeader
const headerComponent = PcHeader

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const seriesStore = useSeriesStore()
const toast = useToast()

// TV 模式网格导航 - 分集列表
const episodeGridNav = useTVGridNavigation('.detail-episodes', '.episode-grid .episode-item')

const series = ref<Series | null>(null)
const coverImage = ref('')
const hasCoverError = ref(false)
const isLoading = ref(true)
const isBacking = ref(false)

const isFollowed = ref(false)
const isBookmarked = ref(false)
const activeEpisodeId = ref<number | string | undefined>(undefined)

const currentCategory = computed(() => seriesStore.currentCategory)
const isLoggedIn = computed(() => userStore.isLoggedIn)
const user = computed(() => userStore.user)

const platformName = computed(() => {
  if (!series.value) return ''
  return PLATFORM_MAP[series.value.platform]?.name || series.value.platform
})

const platformBadge = computed(() => {
  if (!series.value) return ''
  return PLATFORM_MAP[series.value.platform]?.badge || ''
})

const typeName = computed(() => {
  if (!series.value?.category_key) return ''
  return TYPE_MAP[series.value.category_key]?.name || series.value.category_key
})

const isMovie = computed(() => series.value?.category_key === 'movie')

const isFinished = computed(() => {
  if (!series.value) return false
  // 只有后端明确标记完结 (is_finished === 1) 才隐藏追剧按钮
  // 不再根据 total_episodes/updated_episodes 自动推断，避免数据不完整时误判
  return series.value.is_finished === 1
})

const tags = computed(() => {
  if (!series.value?.tags) return []
  return parseTags(series.value.tags)
})

const actors = computed(() => {
  if (!series.value?.actors) return []
  return parseActors(series.value.actors)
})

// Tab 状态（默认分集）
const activeTab = ref('episodes')
const tabs = [
  { key: 'intro', label: '简介' },
  { key: 'episodes', label: '分集' },
  { key: 'actors', label: '演员' },
  { key: 'tags', label: '标签' },
]

watch(series, (newSeries) => {
  if (newSeries) {
    const originalUrl = newSeries.cover_url || newSeries.thumbnail || ''
    coverImage.value = originalUrl ? getProxyImageUrl(originalUrl) : ''
  }
}, { immediate: true })

function resetFilters() {
  router.push('/')
}

function goBack() {
  if (isBacking.value) return
  isBacking.value = true
  try {
    const categoryPath = series.value?.category_key ? `/${series.value.category_key}` : '/'
    router.push(categoryPath)
  } finally {
    setTimeout(() => {
      isBacking.value = false
    }, 500)
  }
}

function handleEpisodeClick(ep: Episode) {
  activeEpisodeId.value = ep.id || ep.vid

  // 跳转到独立播放页
  const cid = route.params.cid as string
  router.push(`/play/${cid}?ep=${ep.id || ep.vid}`)

  if (isLoggedIn.value && user.value?.id && series.value?.id) {
    updateWatchHistory({
      user_id: user.value.id,
      series_id: series.value.id,
      episode_id: ep.id
    }).catch(error => {
      console.error('Failed to update watch history:', error)
    })
  }
}

function playFirstEpisode() {
  const firstEp = series.value?.episodes?.find(ep => ep.episode_type === 0 && ep.play_url)
    ?? series.value?.episodes?.find(ep => ep.play_url)
  if (firstEp) {
    handleEpisodeClick(firstEp)
  }
}

function handleCoverError() {
  if (!hasCoverError.value) {
    hasCoverError.value = true
    coverImage.value = placeholderHero
  }
}

function handleMetaClick(type: string, value: string) {
  // 设置当前分类（保持和当前剧集相同的分类）
  if (series.value?.category_key) {
    seriesStore.setCategory(series.value.category_key)
  }

  // 设置对应的筛选条件
  seriesStore.setFilter(type, value)

  // 跳转到列表页
  const categoryPath = series.value?.category_key ? `/${series.value.category_key}` : '/'
  router.push(categoryPath).then(() => {
    // 跳转后强制加载数据
    seriesStore.loadSeries(true)
    seriesStore.loadFilterOptions()
  })
}

async function checkFollowStatus() {
  if (!isLoggedIn.value || !user.value?.id || !series.value?.id) return
  try {
    const result = await checkFollow(user.value.id, series.value.id)
    if (result.code === 0) {
      isFollowed.value = result.data.followed
    }
  } catch (error) {
    console.error('Failed to check follow status:', error)
  }
}

async function handleFollow() {
  if (!isLoggedIn.value) {
    router.push('/user')
    return
  }
  if (!user.value?.id || !series.value?.id) return
  try {
    if (isFollowed.value) {
      await removeFollow(user.value.id, series.value.id)
      isFollowed.value = false
      toast.info('已取消追剧')
    } else {
      await addFollow(user.value.id, series.value.id)
      isFollowed.value = true
      toast.success('追剧成功')
    }
  } catch (error) {
    console.error('Failed to toggle follow:', error)
    toast.error('操作失败，请重试')
  }
}

async function checkBookmarkStatus() {
  if (!isLoggedIn.value || !user.value?.id || !series.value?.id) return
  try {
    const result = await checkBookmark(user.value.id, series.value.id)
    if (result.code === 0) {
      isBookmarked.value = result.data.bookmarked
    }
  } catch (error) {
    console.error('Failed to check bookmark status:', error)
  }
}

async function handleBookmark() {
  if (!isLoggedIn.value) {
    router.push('/user')
    return
  }
  if (!user.value?.id || !series.value?.id) return
  try {
    if (isBookmarked.value) {
      await removeBookmark(user.value.id, series.value.id)
      isBookmarked.value = false
      toast.info('已取消收藏')
    } else {
      await addBookmark(user.value.id, series.value.id)
      isBookmarked.value = true
      toast.success('收藏成功')
    }
  } catch (error) {
    console.error('Failed to toggle bookmark:', error)
    toast.error('操作失败，请重试')
  }
}

async function loadData() {
  isLoading.value = true
  try {
    const cid = route.params.cid as string
    if (cid) {
      series.value = await fetchSeriesDetail(cid)
      // 同步 store 分类，确保 Header 类型筛选按钮高亮正确
      if (series.value?.category_key) {
        seriesStore.setCategory(series.value.category_key)
        // 彩色主题下根据当前剧集分类切换频道配色
        themeStore.setChannel(series.value.category_key)
      }
      await checkFollowStatus()
      await checkBookmarkStatus()
    }
  } catch (error) {
    console.error('Failed to load data:', error)
  } finally {
    isLoading.value = false
  }
}

onMounted(async () => {
  userStore.initFromStorage()

  // 移动端：隐藏 MobileLayout 的 channelbar
  if (deviceStore.isMobile) {
    const ml = document.querySelector('.mobile-layout')
    if (ml) {
      ml.classList.add('detail-page')
    }
  }

  try {
    await seriesStore.loadPlatforms()
    await seriesStore.loadStats()
  } catch (error) {
    console.error('Failed to load stats or platforms:', error)
  }
  await loadData()

  // TV 模式键盘导航
  if (deviceStore.isTV) {
    document.addEventListener('keydown', handleTVKeyDown)

    // 设置初始焦点到返回按钮
    nextTick(() => {
      const backBtn = document.querySelector('.detail-back-btn') as HTMLElement
      if (backBtn) {
        backBtn.focus()
      }
    })
  }
})

// TV 遥控器键盘处理
function handleTVKeyDown(e: KeyboardEvent) {
  switch (e.key) {
    case 'Backspace':
    case 'Escape':
      e.preventDefault()
      goBack()
      break
    case 'ArrowUp':
    case 'ArrowDown':
    case 'ArrowLeft':
    case 'ArrowRight':
      // 由 useTVGridNavigation 处理
      break
    case 'Enter':
      // 由 useTVGridNavigation 处理
      break
  }
}

// 清理 TV 键盘监听
onUnmounted(() => {
  // 移动端：移除 detail-page class
  if (deviceStore.isMobile) {
    const ml = document.querySelector('.mobile-layout')
    if (ml) {
      ml.classList.remove('detail-page')
    }
  }
  if (deviceStore.isTV) {
    document.removeEventListener('keydown', handleTVKeyDown)
  }
})

watch(() => route.params.cid, async () => {
  await loadData()
})
</script>

<style lang="scss" scoped>
/* ==================== 移动端标题行 ==================== */
.mobile-title-row {
  padding: 6px 12px 4px;
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.mobile-title-back {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  margin: 0;
  background: var(--surface);
  border: 1px solid var(--border-light);
  border-radius: 8px;
  color: var(--text-secondary);
  cursor: pointer;
  flex-shrink: 0;
  font-size: 14px;

  &:active {
    background: var(--surface-hover);
    color: var(--text-primary);
  }
}

.mobile-title-text {
  flex: 1;
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.page {
  min-height: 100vh;
  background: var(--background);
}

.container {
  display: flex;
  padding-top: 72px;
  transition: padding-top 0.3s ease;
}

.main-content {
  flex: 1;
  padding: 32px;
  position: relative;
  overflow-y: auto;
  height: calc(100vh - 72px);
}

.content-wrapper {
  transition: opacity 0.3s ease;
}

.detail-card {
  background: var(--surface);
  border-radius: 16px;
  overflow: hidden;
  max-width: 900px;
  margin: 0 auto;
  box-shadow: 0 4px 32px rgba(0,0,0,0.08), 0 0 0 1px var(--border-light);
}

/* ==================== 封面区 ==================== */
.detail-hero {
  position: relative;
  width: 100%;
  aspect-ratio: 16/9;
  overflow: hidden;
  cursor: pointer;
}

.detail-cover {
  width: 100%;
  height: 100%;
  object-fit: cover;
  background: var(--surface-light);
}

.detail-cover-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(to top, rgba(0,0,0,0.75) 0%, rgba(0,0,0,0.15) 50%, rgba(0,0,0,0.05) 100%);
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  padding: 24px;
  transition: background 0.3s ease;
}

.detail-cover-bottom {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
}

.detail-play-icon {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%) scale(0.9);
  opacity: 0.85;
  transition: all 0.3s ease;
}

.detail-cover-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.cover-meta-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.detail-hero-title {
  font-size: 24px;
  font-weight: 700;
  color: #fff;
  margin: 0;
  line-height: 1.3;
  text-shadow: 0 1px 4px rgba(0,0,0,0.5);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.cover-platform {
  display: inline-block;
  width: fit-content;
  padding: 2px 10px;
  font-size: 11px;
  font-weight: 500;
  border-radius: 4px;
  color: #fff;
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(4px);
  letter-spacing: 0.5px;
  white-space: nowrap;
}

.cover-ep-badge {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.85);
  white-space: nowrap;
}

.detail-cover-actions {
  display: flex;
  gap: 6px;
  flex-wrap: nowrap;
  flex-shrink: 0;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 14px;
  border-radius: 20px;
  border: 1px solid rgba(255,255,255,0.4);
  background: rgba(0, 0, 0, 0.45);
  color: #fff;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  backdrop-filter: blur(4px);

  .action-icon {
    width: 15px;
    height: 15px;
  }

  &.active {
    background: var(--primary-solid);
    border-color: var(--primary-solid);
    color: #fff;
  }
}

/* ==================== Tab 导航 ==================== */
.detail-tabs {
  display: flex;
  border-bottom: 1px solid var(--border-light);
  padding: 0 24px;
  gap: 4px;
  background: linear-gradient(180deg, color-mix(in srgb, var(--primary-solid) 4%, transparent) 0%, transparent 100%);
}

.detail-tab {
  padding: 12px 24px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s ease;
  margin-bottom: -1px;
  position: relative;

  &.active {
    color: var(--primary-dark);
    border-bottom-color: var(--primary-solid);
    font-weight: 600;
  }
}

/* ==================== Tab 内容区 ==================== */
.detail-body {
  padding: 24px;
  background: linear-gradient(180deg, color-mix(in srgb, var(--primary-solid) 3%, transparent) 0%, transparent 80px);
}

.tab-content {
  animation: tabFadeIn 0.2s ease;
}

@keyframes tabFadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

.tab-empty {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-muted);
  font-size: 14px;
}

/* 简介 */
.detail-description {
  color: var(--text-secondary);
  font-size: 15px;
  line-height: 1.9;
  padding: 20px;
  background: linear-gradient(135deg, color-mix(in srgb, var(--primary-solid) 6%, transparent), color-mix(in srgb, var(--primary-solid) 2%, transparent));
  border-radius: 12px;
  border-left: 3px solid var(--primary-solid);

  p {
    margin: 0;
  }
}

/* 分集 */
.detail-episodes {
  margin-top: 0;
}

/* 标签列表（演员/标签 Tab 共用） */
.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-item {
  padding: 6px 14px;
  border: 1px solid var(--border);
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.2s ease;

  &:active {
    transform: scale(0.97);
  }
}

/* 加载与空状态 */
.loading {
  text-align: center;
  padding: 120px 20px;
  color: var(--text-muted);
}

.spinner {
  width: 48px;
  height: 48px;
  border: 3px solid var(--surface-light);
  border-top-color: var(--primary-solid);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-state {
  text-align: center;
  padding: 120px 20px;
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
  color: var(--text-primary);
}

.empty-desc {
  font-size: 14px;
  margin: 0 0 24px 0;
}

.back-home-btn {
  padding: 10px 28px;
  background: var(--primary);
  border: none;
  border-radius: 24px;
  color: #ffffff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;

  &:active {
    transform: scale(0.97);
  }
}

/* ==================== 响应式 ==================== */
@media screen and (max-width: 768px) {
  .container {
    padding-top: 0; /* 移动端由 MobileLayout 处理顶部间距 */
  }

  .main-content {
    padding: 12px;
    height: auto;
  }

  .detail-hero {
    aspect-ratio: 16/9;

    /* 移动端禁用hover效果 */
  }

  .detail-cover-overlay {
    padding: 16px;
  }

  .detail-hero-title {
    font-size: 20px;
  }

  .detail-tabs {
    padding: 0 12px;
    gap: 0;
  }

  .detail-tab {
    flex: 1;
    padding: 12px 8px;
    font-size: 14px;
    text-align: center;
  }

  .detail-body {
    padding: 16px;
  }
}

@media screen and (max-width: 480px) {
  .detail-hero {
    aspect-ratio: 16/9;
  }

  .detail-cover-overlay {
    padding: 10px;
  }

  .detail-cover-bottom {
    gap: 6px;
  }

  .detail-hero-title {
    font-size: 16px;
  }

  .cover-platform {
    padding: 1px 8px;
    font-size: 10px;
  }

  .cover-ep-badge {
    font-size: 11px;
  }

  .action-btn {
    padding: 5px 10px;
    font-size: 11px;
    gap: 3px;

    .action-icon {
      width: 13px;
      height: 13px;
    }
  }

  .detail-tab {
    padding: 10px 4px;
    font-size: 13px;
  }

  .detail-body {
    padding: 12px;
  }

  .detail-description {
    font-size: 14px;
    line-height: 1.7;
  }
}
</style>

<!-- 移动端详情页：保留 MobileHeader，隐藏 ChannelBar，调整间距 -->
<style lang="scss">
.mobile-layout.detail-page {
  .channel-bar {
    display: none !important;
  }

  .content {
    // header(56px) + 标题行(~16px) + safe-area
    padding-top: calc(72px + var(--safe-area-inset-top, 0px)) !important;
  }
}

@media screen and (max-width: 480px) {
  .mobile-layout.detail-page .content {
    // header(52px) + 标题行(~14px) + safe-area
    padding-top: calc(66px + var(--safe-area-inset-top, 0px)) !important;
  }
}
</style>

