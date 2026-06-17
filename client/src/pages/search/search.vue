<template>
  <div class="page">
    <!-- 移动端返回栏 -->
    <div v-if="deviceStore.isMobile" class="mobile-back-bar">
      <button class="mobile-back-btn" @click="goBack">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5"/><path d="M12 19l-7-7 7-7"/></svg>
      </button>
      <div class="mobile-search-wrap">
        <svg class="mobile-search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"/>
          <path d="m21 21-4.35-4.35"/>
        </svg>
        <input
          class="mobile-search-input"
          v-model="searchText"
          placeholder="搜索影片、演员、导演..."
          @keyup.enter="handleSearch"
          ref="searchInputRef"
        />
        <button v-if="searchText" class="mobile-clear-btn" @click="clearSearch">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- PC端搜索头部 -->
    <div v-else class="search-header">
      <button class="back-btn" @click="goBack">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M15 18l-6-6 6-6"/>
        </svg>
      </button>
      <div class="search-input-wrap">
        <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"/>
          <path d="m21 21-4.35-4.35"/>
        </svg>
        <input
          class="search-input"
          v-model="searchText"
          placeholder="搜索影片、演员、导演..."
          @keyup.enter="handleSearch"
          ref="pcSearchInputRef"
        />
        <button v-if="searchText" class="clear-btn" @click="clearSearch">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
    </div>

    <!-- 频道过滤栏（仅移动端） -->
    <div v-if="deviceStore.isMobile" class="search-filter-bar">
      <button
        v-for="cat in filterCategories"
        :key="cat.key"
        :class="['filter-chip', { active: selectedCategory === cat.key }]"
        @click="selectedCategory = cat.key"
      >
        {{ cat.name }}
      </button>
    </div>

    <!-- 搜索内容 -->
    <main class="search-content" :class="{ 'has-filter': deviceStore.isMobile }">
      <!-- 加载中 -->
      <div v-if="isLoading" class="loading-state">
        <div class="spinner"></div>
        <span>搜索中...</span>
      </div>

      <!-- 搜索提示（无输入时） -->
      <div v-else-if="!searchText" class="search-hints">
        <!-- 历史搜索 -->
        <section class="hint-section history-section" v-if="searchHistory.length > 0">
          <div class="section-header">
            <h3 class="section-title">历史搜索</h3>
            <button class="clear-history-btn" @click="clearHistory">清空</button>
          </div>
          <div class="history-tags">
            <button
              v-for="keyword in searchHistory"
              :key="keyword"
              class="history-tag"
              @click="searchText = keyword; handleSearch()"
            >
              {{ keyword }}
            </button>
          </div>
        </section>

        <!-- 热门搜索 -->
        <section class="hint-section">
          <h3 class="section-title">热门搜索</h3>
          <div class="hot-tags">
            <button
              v-for="(keyword, index) in hotKeywords"
              :key="keyword"
              class="hot-tag"
              @click="searchText = keyword; handleSearch()"
            >
              <span class="tag-index" :class="{ top: index < 3 }">{{ index + 1 }}</span>
              <span class="tag-text">{{ keyword }}</span>
            </button>
          </div>
        </section>

        <!-- 推荐 -->
        <section class="hint-section" v-if="recommendList.length > 0">
          <h3 class="section-title">为你推荐</h3>
          <div class="recommend-grid">
            <SeriesCard
              v-for="series in recommendList"
              :key="series.cid"
              :series="series"
              layout="vertical"
              @toggle-follow="() => {}"
              @toggle-bookmark="() => {}"
            />
          </div>
        </section>
      </div>

      <!-- 无结果（仅当搜索完成且确实无结果时显示，避免加载中/防抖中闪现） -->
      <div v-else-if="!isLoading && filteredResults.length === 0" class="empty-state">
        <svg class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="11" cy="11" r="8"/>
          <path d="m21 21-4.35-4.35"/>
          <path d="M8 11h6"/>
        </svg>
        <h3 class="empty-title">未找到相关结果</h3>
        <p class="empty-desc">换个关键词试试</p>
      </div>

      <!-- 搜索结果 -->
      <div v-else class="results-section">
        <div class="results-header">
          <span class="results-count">共 {{ filteredResults.length }} 个结果</span>
        </div>
        <div :class="['series-grid', cardLayout]">
          <SeriesCard
            v-for="series in filteredResults"
            :key="series.cid"
            :series="series"
            :layout="cardLayout"
            @toggle-follow="() => {}"
            @toggle-bookmark="() => {}"
          />
        </div>
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useSeriesStore } from '@/stores/series'
import { useToast } from '@/composables/useToast'
import { useDeviceStore } from '@/stores/device'
import { getWatchHistory, searchSeries, type Series } from '@/utils/api'
import { useUserStore } from '@/stores/user'
import SeriesCard from '@/components/SeriesCard.vue'

const router = useRouter()
const route = useRoute()
const store = useSeriesStore()
const userStore = useUserStore()
const deviceStore = useDeviceStore()
const toast = useToast()

const searchText = ref('')
const searchResults = ref<Series[]>([])
const searchHistory = ref<string[]>([])
const recommendList = ref<Series[]>([])

// 推荐数据缓存（会话级）
let recommendCache: { data: Series[]; timestamp: number } | null = null
const selectedCategory = ref('all')

// 频道过滤选项
const filterCategories = [
  { key: 'all', name: '全部' },
  { key: 'tv', name: '电视剧' },
  { key: 'movie', name: '电影' },
  { key: 'variety', name: '综艺' },
  { key: 'cartoon', name: '动漫' },
  { key: 'child', name: '少儿' },
]

// 卡片布局模式：移动端强制使用竖版
const cardLayout = ref<'vertical' | 'horizontal'>('vertical')
const isLoading = ref(false)
const searchInputRef = ref<HTMLInputElement | null>(null)
const pcSearchInputRef = ref<HTMLInputElement | null>(null)

// 热门搜索：只从电视剧、电影、综艺中取最热的5个标题
const hotKeywords = computed(() => {
  const allowed = new Set(['tv', 'movie', 'variety'])
  const all = [...store.allSeriesList].filter(s => allowed.has(s.category_key))
  // 优先按 is_hot 排序，再按评分降序
  all.sort((a, b) => {
    if ((b.is_hot || 0) !== (a.is_hot || 0)) return (b.is_hot || 0) - (a.is_hot || 0)
    return (Number(b.score) || 0) - (Number(a.score) || 0)
  })
  return all.slice(0, 5).map(s => s.title)
})

// 根据频道过滤结果
const filteredResults = computed(() => {
  if (selectedCategory.value === 'all') return searchResults.value
  return searchResults.value.filter(s => s.category_key === selectedCategory.value)
})

// 加载搜索历史
function loadSearchHistory() {
  try {
    const history = localStorage.getItem('searchHistory')
    if (history) {
      searchHistory.value = JSON.parse(history)
    }
  } catch (e) {
    searchHistory.value = []
  }
}

// 保存搜索历史
function saveSearchHistory(keyword: string) {
  const newHistory = [keyword, ...searchHistory.value.filter(k => k !== keyword)].slice(0, 10)
  searchHistory.value = newHistory
  localStorage.setItem('searchHistory', JSON.stringify(newHistory))
}

// 清空搜索历史
function clearHistory() {
  searchHistory.value = []
  localStorage.removeItem('searchHistory')
}

// 加载推荐内容（基于观看历史的同类题材）
async function loadRecommendations() {
  // 检查缓存（5分钟内有效）
  const now = Date.now()
  if (recommendCache && now - recommendCache.timestamp < 5 * 60 * 1000) {
    recommendList.value = recommendCache.data
    return
  }

  if (!userStore.user?.id) {
    // 未登录时加载热门内容
    await store.loadSeries(true)
    recommendList.value = store.seriesList.slice(0, 6)
    recommendCache = { data: recommendList.value, timestamp: now }
    return
  }

  try {
    // 获取观看历史
    const result = await getWatchHistory(userStore.user.id)
    if (result.code !== 0 || !result.data.items?.length) {
      // 无观看历史时加载热门内容
      await store.loadSeries(true)
      recommendList.value = store.seriesList.slice(0, 6)
      recommendCache = { data: recommendList.value, timestamp: now }
      return
    }

    // 提取观看历史中的题材标签
    const watchedTags = new Set<string>()
    result.data.items.forEach((item: any) => {
      if (item.series?.tags) {
        item.series.tags.forEach((tag: string) => watchedTags.add(tag))
      }
    })

    // 加载所有内容并筛选同类题材
    await store.loadSeries(true)
    const allSeries = store.seriesList

    // 优先推荐同类题材
    const recommended = allSeries.filter((s: Series) =>
      s.tags?.some((tag: string) => watchedTags.has(tag))
    ).slice(0, 6)

    if (recommended.length > 0) {
      recommendList.value = recommended
    } else {
      recommendList.value = allSeries.slice(0, 6)
    }

    // 更新缓存
    recommendCache = { data: recommendList.value, timestamp: now }
  } catch (e) {
    console.error('Failed to load recommendations:', e)
    await store.loadSeries(true)
    recommendList.value = store.seriesList.slice(0, 6)
    recommendCache = { data: recommendList.value, timestamp: now }
  }
}

// 防抖定时器
let debounceTimer: ReturnType<typeof setTimeout> | null = null

async function doSearch(keyword: string) {
  if (!keyword) return

  // 保存搜索历史
  saveSearchHistory(keyword)

  isLoading.value = true
  // 不清空旧结果，避免切换时闪现"无结果"提示
  selectedCategory.value = 'all'

  try {
    const data = await searchSeries(keyword)
    searchResults.value = data.items || []
  } catch (err) {
    console.error('Search error:', err)
    toast.error('搜索失败，请重试')
  } finally {
    isLoading.value = false
  }
}

function handleSearch() {
  const kw = searchText.value.trim()
  if (!kw) return
  // 取消待执行的防抖，立即搜索
  if (debounceTimer) clearTimeout(debounceTimer)
  doSearch(kw)
}

function clearSearch() {
  searchText.value = ''
  searchResults.value = []
  selectedCategory.value = 'all'
  if (debounceTimer) clearTimeout(debounceTimer)
}

function goBack() {
  const lastCategory = sessionStorage.getItem('lastCategory')
  router.push(lastCategory || '/')
}

onMounted(() => {
  loadSearchHistory()
  loadRecommendations()

  // 从路由参数读取关键词并自动搜索
  const query = route.query.q as string
  if (query) {
    searchText.value = query
    handleSearch()
  }

  nextTick(() => {
    const el = deviceStore.isMobile ? searchInputRef.value : pcSearchInputRef.value
    el?.focus()
  })
})

onBeforeUnmount(() => {
  if (debounceTimer) clearTimeout(debounceTimer)
  // 离开时恢复
  if (deviceStore.isMobile) {
    const ml = document.querySelector('.mobile-layout')
    if (ml) {
      ml.classList.remove('no-channelbar')
      ml.classList.remove('search-page-layout')
    }
  }
})

watch(searchText, (val) => {
  if (!val) {
    searchResults.value = []
    selectedCategory.value = 'all'
    if (debounceTimer) clearTimeout(debounceTimer)
    return
  }
  // 防抖：输入停顿 350ms 后自动搜索
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    const kw = val.trim()
    if (kw) doSearch(kw)
  }, 350)
})
</script>

<style lang="scss" scoped>
/* ========== 移动端返回栏 ========== */
.mobile-back-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1000;
  background: var(--surface);
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px 6px;
}

.mobile-back-btn {
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

  &:active {
    background: var(--surface-hover);
    color: var(--text-primary);
  }
}

.mobile-search-wrap {
  flex: 1;
  height: 36px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 18px;
  display: flex;
  align-items: center;
  padding: 0 10px;
  gap: 6px;
  transition: border-color 0.2s;

  &:focus-within {
    border-color: var(--primary-solid);
  }
}

.mobile-search-icon {
  width: 15px;
  height: 15px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.mobile-search-input {
  flex: 1;
  height: 100%;
  font-size: 14px;
  color: var(--text-primary);
  background: transparent;
  border: none;
  outline: none;

  &::placeholder {
    color: var(--text-muted);
  }
}

.mobile-clear-btn {
  width: 18px;
  height: 18px;
  background: var(--text-muted);
  border: none;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 0;
  flex-shrink: 0;

  svg {
    width: 10px;
    height: 10px;
    color: #fff;
  }

  &:active {
    opacity: 0.7;
  }
}

/* ========== 频道过滤栏（移动端） ========== */
.search-filter-bar {
  position: fixed;
  top: 44px;
  left: 0;
  right: 0;
  z-index: 999;
  background: var(--surface);
  display: flex;
  gap: 6px;
  padding: 4px 12px 6px;
  overflow-x: auto;
  scrollbar-width: none;

  &::-webkit-scrollbar {
    display: none;
  }
}

.filter-chip {
  padding: 4px 12px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-secondary);
  font-size: 13px;
  border-radius: 14px;
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
  transition: all 0.2s;

  &:active {
    opacity: 0.8;
  }

  &.active {
    background: var(--primary-solid);
    border-color: var(--primary-solid);
    color: #fff;
  }
}

/* ========== PC端搜索头部 ========== */
.search-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 56px;
  background: var(--surface);
  display: flex;
  align-items: center;
  padding: 0 12px;
  gap: 8px;
  z-index: 1000;
}

.back-btn {
  width: 36px;
  height: 36px;
  background: transparent;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--text-primary);

  svg {
    width: 22px;
    height: 22px;
  }

  &:active {
    opacity: 0.6;
  }
}

.search-input-wrap {
  flex: 1;
  height: 38px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 19px;
  display: flex;
  align-items: center;
  padding: 0 12px;
  gap: 8px;
  transition: border-color 0.2s;

  &:focus-within {
    border-color: var(--primary-solid);
  }
}

.search-icon {
  width: 16px;
  height: 16px;
  color: var(--text-muted);
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  height: 100%;
  font-size: 14px;
  color: var(--text-primary);
  background: transparent;
  border: none;
  outline: none;

  &::placeholder {
    color: var(--text-muted);
  }
}

.clear-btn {
  width: 20px;
  height: 20px;
  background: var(--text-muted);
  border: none;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  padding: 0;

  svg {
    width: 12px;
    height: 12px;
    color: #fff;
  }

  &:active {
    opacity: 0.7;
  }
}

/* ========== 页面 ========== */
.page {
  min-height: 100vh;
  background: var(--background);
}

/* 搜索内容 */
.search-content {
  padding-top: 68px;
}

.search-content.has-filter {
  padding-top: 80px;
}

/* 加载状态 */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  color: var(--text-muted);
  font-size: 14px;
  gap: 12px;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 2px solid var(--border);
  border-top-color: var(--primary-solid);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* 搜索提示 */
.search-hints {
  padding: 12px 16px;
}

.hint-section {
  margin-bottom: 18px;

  &.history-section {
    margin-bottom: 18px;
  }
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.section-header .section-title {
  margin: 0;
}

.clear-history-btn {
  font-size: 12px;
  color: var(--text-muted);
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px 8px;

  &:active {
    color: var(--primary-solid);
  }
}

/* 历史搜索 */
.history-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
}

.history-tag {
  padding: 6px 14px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;

  &:active {
    border-color: var(--primary-solid);
    color: var(--primary-solid);
  }
}

/* 热门搜索 - 横向展示 */
.hot-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
}

.hot-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.2s;

  &:active {
    border-color: var(--primary-solid);
    background: rgba(249, 115, 22, 0.05);
  }
}

.tag-index {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  background: var(--surface);
  border-radius: 4px;

  &.top {
    background: var(--primary-solid);
    color: #fff;
  }
}

.tag-text {
  font-size: 13px;
  color: var(--text-primary);
}

/* 推荐网格 */
.recommend-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

@media screen and (min-width: 500px) {
  .recommend-grid {
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
  }
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
}

.empty-icon {
  width: 64px;
  height: 64px;
  color: var(--text-muted);
  margin-bottom: 16px;
}

.empty-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 4px 0;
}

.empty-desc {
  font-size: 13px;
  color: var(--text-muted);
  margin: 0;
}

/* 搜索结果 */
.results-section {
  padding: 0 12px;
}

.results-header {
  padding: 12px 0;
}

.results-count {
  font-size: 12px;
  color: var(--text-muted);
}

.series-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  padding-bottom: 20px;
}

@media screen and (max-width: 400px) {
  .series-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media screen and (min-width: 600px) {
  .series-grid {
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
  }
}

@media screen and (min-width: 900px) {
  .series-grid {
    grid-template-columns: repeat(5, 1fr);
    gap: 16px;
  }
}

/* 横版模式 */
.series-grid.horizontal {
  grid-template-columns: 1fr;
  gap: 12px;
}

@media screen and (min-width: 600px) {
  .series-grid.horizontal {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media screen and (min-width: 900px) {
  .series-grid.horizontal {
    grid-template-columns: repeat(3, 1fr);
  }
}
</style>

<!-- 移动端搜索页：隐藏 MobileHeader 和 ChannelBar，重置 content padding -->
<style lang="scss">
.mobile-layout.no-channelbar.search-page-layout {
  .channel-bar {
    display: none !important;
  }

  .content {
    padding-top: 0 !important;
  }
}
</style>
