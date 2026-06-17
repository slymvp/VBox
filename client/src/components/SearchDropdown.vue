<template>
  <div class="search-dropdown-wrapper" ref="wrapperRef">
    <div 
      class="search-input-wrap focusable tv-btn"
      :class="{ 'focused': isOpen }"
      @click="handleWrapClick"
      tabindex="0"
      @keydown.enter="handleWrapClick"
    >
      <span class="search-icon">🔍</span>
      <input 
        v-if="isOpen"
        v-model="searchText"
        class="search-input" 
        placeholder="搜索剧集、电影..."
        @input="handleInput"
        @keyup.enter="handleSearch"
        @click.stop
        @mousedown.stop
        ref="searchInputRef"
      />
      <span v-else class="search-placeholder">搜索剧集、电影...</span>
      <button v-if="searchText" class="clear-btn" @click.stop="clearSearch">✕</button>
    </div>

    <Transition name="dropdown">
      <div v-if="isOpen" class="search-dropdown">
        <!-- 历史搜索 -->
        <div v-if="searchHistory.length > 0" class="dropdown-section">
          <div class="section-header">
            <span class="section-title">历史搜索</span>
            <button class="clear-history-btn tv-btn focusable" @click="clearHistory" tabindex="0" @keydown.enter="clearHistory">清空</button>
          </div>
          <div class="history-tags">
            <span 
              v-for="keyword in searchHistory" 
              :key="keyword" 
              class="history-tag tv-btn focusable"
              @click="selectKeyword(keyword)"
              tabindex="0"
              @keydown.enter="selectKeyword(keyword)"
            >{{ keyword }}</span>
          </div>
        </div>

        <!-- 热门搜索 -->
        <div class="dropdown-section">
          <div class="section-header">
            <span class="section-title">热门搜索</span>
          </div>
          <div class="hot-tags">
            <span 
              v-for="(keyword, index) in hotKeywords" 
              :key="keyword" 
              class="hot-tag tv-btn focusable"
              @click="selectKeyword(keyword)"
              tabindex="0"
              @keydown.enter="selectKeyword(keyword)"
            >
              <span :class="['hot-rank', index < 3 ? 'top' : '']">{{ index + 1 }}</span>
              {{ keyword }}
            </span>
          </div>
        </div>

        <!-- 最近热播 -->
        <div class="dropdown-section">
          <div class="section-header">
            <span class="section-title">最近热播</span>
          </div>
          <div class="hot-series">
            <div 
              v-for="(series, index) in hotSeries" 
              :key="series.cid" 
              class="hot-series-item tv-btn focusable"
              @click="goToDetail(series.cid)"
              tabindex="0"
              @keydown.enter="goToDetail(series.cid)"
            >
              <div class="series-rank">{{ index + 1 }}</div>
              <div class="series-info">
                <span class="series-name">{{ series.title }}</span>
                <span v-if="series.actors && series.actors.length > 0" class="series-actors">
                  <span v-for="(actor, i) in series.actors.slice(0, 3)" :key="i" class="actor-name">
                    {{ actor }}{{ i < Math.min(series.actors.length, 3) - 1 ? '、' : '' }}
                  </span>
                </span>
                <span v-if="series.score" class="series-score">{{ series.score }}分</span>
                <span v-if="series.year" class="series-year">{{ series.year }}</span>
                <span v-if="series.category_key === 'tv'" class="series-status">
                  {{ series.is_finished ? '已完结' : '更新中' }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useSeriesStore } from '@/stores/series'
import { PLATFORM_MAP, TYPE_MAP, parseActors, type Series } from '@/utils/api'

const router = useRouter()
const store = useSeriesStore()

const isOpen = ref(false)
const searchText = ref('')
const searchHistory = ref<string[]>([])
const wrapperRef = ref<HTMLElement | null>(null)
const searchInputRef = ref<HTMLInputElement | null>(null)

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

const hotSeries = computed(() => {
  return store.allSeriesList
    .sort((a, b) => (b.score || 0) - (a.score || 0))
    .slice(0, 9)
    .map(series => {
      const actors = parseActors(series.actors)
      const isFinished = series.is_finished === 1 ? true
        : series.is_finished === -1 ? false
        : series.category_key === 'tv' && series.total_episodes > 0 && series.updated_episodes >= series.total_episodes
      return {
        ...series,
        actors,
        is_finished: isFinished
      }
    })
})

function loadHistory() {
  const saved = localStorage.getItem('searchHistory')
  if (saved) {
    searchHistory.value = JSON.parse(saved)
  }
}

function saveHistory() {
  localStorage.setItem('searchHistory', JSON.stringify(searchHistory.value))
}

function addToHistory(keyword: string) {
  if (!keyword.trim()) return
  searchHistory.value = [keyword, ...searchHistory.value.filter(k => k !== keyword)].slice(0, 10)
  saveHistory()
}

function handleWrapClick() {
  if (isOpen.value) {
    // 已打开时，点击聚焦到输入框
    nextTick(() => {
      searchInputRef.value?.focus()
    })
  } else {
    // 未打开时，打开下拉
    toggleDropdown()
  }
}

function toggleDropdown() {
  isOpen.value = !isOpen.value
  if (isOpen.value) {
    nextTick(() => {
      searchInputRef.value?.focus()
    })
  }
}

function selectKeyword(keyword: string) {
  searchText.value = keyword
  handleSearch()
}

function closeDropdown() {
  isOpen.value = false
}

function handleInput() {
  // 实时搜索可以在这里实现
}

function handleSearch() {
  if (!searchText.value.trim()) return
  addToHistory(searchText.value.trim())
  isOpen.value = false
  // 跳转到搜索页面，通过query参数传递关键词
  router.push({
    path: '/search',
    query: { q: searchText.value.trim() }
  })
}

function clearSearch() {
  searchText.value = ''
}

function clearHistory() {
  searchHistory.value = []
  saveHistory()
}

function goToDetail(cid: string) {
  isOpen.value = false
  router.push(`/detail/${cid}`)
}

function handleClickOutside(event: MouseEvent) {
  if (wrapperRef.value && !wrapperRef.value.contains(event.target as Node)) {
    closeDropdown()
  }
}

onMounted(() => {
  loadHistory()
  document.addEventListener('click', handleClickOutside)
  // 确保热门数据已加载
  if (!store.allSeriesList.length) {
    store.loadSeries(true)
  }
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style lang="scss" scoped>
.search-dropdown-wrapper {
  position: relative;
  z-index: 1001;
}

.search-input-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 24px;
  cursor: pointer;
  transition: all 0.2s ease;
  min-width: 280px;

  &:hover {
    background: rgba(255, 255, 255, 0.08);
  }

  &.focused {
    background: rgba(255, 255, 255, 0.1);
    border-color: rgba(251, 191, 36, 0.5);
  }
}

.search-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.search-placeholder {
  flex: 1;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.5);
  white-space: nowrap;
  user-select: none;
  pointer-events: none;
}

.search-input {
  flex: 1;
  font-size: 14px;
  color: var(--text-primary);
  background: transparent;
  border: none;
  outline: none;
  min-width: 0;
  width: 100%;
  cursor: text;

  &::placeholder {
    color: rgba(255, 255, 255, 0.5);
  }
}

.clear-btn {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.5);
  background: none;
  border: none;
  cursor: pointer;
  padding: 2px;
  transition: color 0.2s;

  &:hover {
    color: var(--text-primary);
  }
}

.search-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 500px;
  max-height: 480px;
  background: rgba(20, 20, 25, 0.98);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 20px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
  overflow-y: auto;
}

.dropdown-section {
  margin-bottom: 24px;

  &:last-child {
    margin-bottom: 0;
  }
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.clear-history-btn {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px 8px;
  transition: color 0.2s;

  &:hover {
    color: rgba(255, 255, 255, 0.7);
  }
}

.history-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.history-tag {
  padding: 6px 14px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    color: var(--text-primary);
  }
}

.hot-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.hot-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.7);
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: rgba(251, 191, 36, 0.15);
    border-color: rgba(251, 191, 36, 0.3);
    color: var(--gold);
  }
}

.hot-rank {
  width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.5);
  background: rgba(255, 255, 255, 0.08);
  border-radius: 4px;

  &.top {
    background: linear-gradient(135deg, rgba(251, 191, 36, 0.3), rgba(251, 191, 36, 0.1));
    color: var(--gold);
  }
}

.hot-series {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.series-column {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.hot-series-item {
  display: flex;
  gap: 12px;
  cursor: pointer;
  transition: background 0.2s ease;
  padding: 8px 12px;
  border-radius: 6px;

  &:hover {
    background: rgba(255, 255, 255, 0.05);

    .series-name {
      color: var(--text-primary);
    }
  }
}

.series-rank {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, rgba(251, 191, 36, 0.2), rgba(251, 191, 36, 0.08));
  border-radius: 4px;
  font-size: 14px;
  font-weight: 700;
  color: var(--gold);
  flex-shrink: 0;
}

.series-info {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.series-name {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
  transition: color 0.2s ease;
}

.series-score {
  font-size: 12px;
  color: var(--gold);
  font-weight: 500;
  flex-shrink: 0;
}

.series-year {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
  flex-shrink: 0;
}

.series-status {
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 3px;
  background: rgba(251, 191, 36, 0.15);
  color: var(--gold);
  flex-shrink: 0;
}

.series-actors {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.actor-name {
  color: rgba(255, 255, 255, 0.5);
}

.dropdown-enter-active,
.dropdown-leave-active {
  transition: all 0.2s ease;
}

.dropdown-enter-from,
.dropdown-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

@media screen and (max-width: 768px) {
  .search-input-wrap {
    min-width: auto;
    padding: 8px 12px;
  }

  .search-dropdown {
    width: calc(100vw - 32px);
    right: -8px;
    max-height: 400px;
    padding: 16px;
  }

  .series-rank {
    width: 22px;
    height: 22px;
    font-size: 13px;
  }

  .series-name {
    font-size: 13px;
  }

  .series-actors {
    font-size: 11px;
  }
}
</style>
