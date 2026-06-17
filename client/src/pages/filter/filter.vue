<template>
  <div class="filter-page">
    <!-- 返回栏 -->
    <div class="mobile-back-bar">
      <button class="mobile-back-btn" @click="handleBack">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5"/><path d="M12 19l-7-7 7-7"/></svg>
      </button>
      <h1 class="filter-title">筛选</h1>
    </div>

    <div class="filter-content">
      <!-- 平台 -->
      <div class="filter-section">
        <div class="filter-options">
          <span class="filter-section-label">平台</span>
          <button :class="['filter-chip', { active: currentPlatform === 'all' }]" @click="setPlatform('all')">全部</button>
          <button v-for="p in platforms" :key="p.key" :class="['filter-chip', { active: currentPlatform === p.key }]" @click="setPlatform(p.key)">
            {{ PLATFORM_MAP[p.key]?.icon || '📺' }} {{ PLATFORM_MAP[p.key]?.name || p.name }}
          </button>
        </div>
      </div>

      <!-- 评分 -->
      <div class="filter-section">
        <div class="filter-options">
          <span class="filter-section-label">评分</span>
          <button :class="['filter-chip', { active: currentMinScore === 0 }]" @click="setFilter('min_score', 0)">不限</button>
          <button :class="['filter-chip', { active: currentMinScore === 9 }]" @click="setFilter('min_score', 9)">9分以上</button>
          <button :class="['filter-chip', { active: currentMinScore === 8 }]" @click="setFilter('min_score', 8)">8分以上</button>
          <button :class="['filter-chip', { active: currentMinScore === 7 }]" @click="setFilter('min_score', 7)">7分以上</button>
          <button :class="['filter-chip', { active: currentMinScore === 6 }]" @click="setFilter('min_score', 6)">6分以上</button>
        </div>
      </div>

      <!-- 年份 -->
      <div class="filter-section" v-if="filterOptions.years.length">
        <div class="filter-options">
          <span class="filter-section-label">年份</span>
          <button :class="['filter-chip', { active: currentYear === 'all' }]" @click="setFilter('year', 'all')">全部</button>
          <button v-for="y in filterOptions.years" :key="y" :class="['filter-chip', { active: currentYear === y }]" @click="setFilter('year', y)">{{ y }}</button>
        </div>
      </div>

      <!-- 地区 -->
      <div class="filter-section" v-if="filterOptions.areas.length">
        <div class="filter-options">
          <span class="filter-section-label">地区</span>
          <button :class="['filter-chip', { active: currentArea === 'all' }]" @click="setFilter('area', 'all')">全部</button>
          <button v-for="a in filterOptions.areas" :key="a" :class="['filter-chip', { active: currentArea === a }]" @click="setFilter('area', a)">{{ a }}</button>
        </div>
      </div>

      <!-- 题材 -->
      <div class="filter-section" v-if="filterOptions.tags.length">
        <div class="filter-options">
          <span class="filter-section-label">题材</span>
          <button :class="['filter-chip', { active: currentTag === 'all' }]" @click="setFilter('tag', 'all')">全部</button>
          <button v-for="t in filterOptions.tags" :key="t" :class="['filter-chip', { active: currentTag === t }]" @click="setFilter('tag', t)">{{ t }}</button>
        </div>
      </div>

      <!-- 导演 -->
      <div class="filter-section" v-if="filterOptions.directors.length">
        <div class="filter-options">
          <span class="filter-section-label">导演</span>
          <button :class="['filter-chip', { active: currentDirector === 'all' }]" @click="setFilter('director', 'all')">全部</button>
          <button v-for="d in filterOptions.directors" :key="d" :class="['filter-chip', { active: currentDirector === d }]" @click="setFilter('director', d)">{{ d }}</button>
        </div>
      </div>

      <!-- 演员 -->
      <div class="filter-section" v-if="filterOptions.actors.length">
        <div class="filter-options">
          <span class="filter-section-label">演员</span>
          <button :class="['filter-chip', { active: currentActor === 'all' }]" @click="setFilter('actor', 'all')">全部</button>
          <button v-for="a in filterOptions.actors" :key="a" :class="['filter-chip', { active: currentActor === a }]" @click="setFilter('actor', a)">{{ a }}</button>
        </div>
      </div>

    </div>

    <!-- 底部确认栏 -->
    <div class="filter-footer">
      <button class="confirm-btn" @click="handleConfirm">查看结果</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useSeriesStore } from '@/stores/series'
import { PLATFORM_MAP } from '@/utils/api'

const router = useRouter()
const store = useSeriesStore()

const platforms = computed(() => store.platforms)
const filterOptions = computed(() => store.filterOptions)
const currentPlatform = computed(() => store.currentPlatform)
const currentYear = computed(() => store.currentYear)
const currentArea = computed(() => store.currentArea)
const currentTag = computed(() => store.currentTag)
const currentDirector = computed(() => store.currentDirector)
const currentActor = computed(() => store.currentActor)
const currentSort = computed(() => store.currentSort)
const currentMinScore = computed(() => store.currentMinScore)

function setPlatform(platform: string) {
  store.setPlatform(platform)
  store.loadFilterOptions()
}

function setFilter(type: string, value: string | number) {
  store.setFilter(type, value)
}

function handleReset() {
  store.resetFilters()
  store.loadFilterOptions()
}

function handleBack() {
  // 返回时清除所有筛选条件，恢复初始状态
  store.resetFilters()
  const lastCategory = sessionStorage.getItem('lastCategory')
  router.push(lastCategory || '/')
}

function handleConfirm() {
  store.loadSeries(true)
  // 标记需要滚动到顶部
  sessionStorage.setItem('scrollToTop', 'true')
  router.back()
}

onMounted(() => {
  // 移动端隐藏 ChannelBar
  const ml = document.querySelector('.mobile-layout')
  if (ml) ml.classList.add('no-channelbar')

  if (store.categories.length === 0) {
    store.loadCategories()
  }
  if (store.platforms.length === 0) {
    store.loadPlatforms()
  }
  store.loadFilterOptions()
})

onBeforeUnmount(() => {
  const ml = document.querySelector('.mobile-layout')
  if (ml) ml.classList.remove('no-channelbar')
})
</script>

<style lang="scss" scoped>
.filter-page {
  min-height: 100vh;
  background: var(--background);
  padding-bottom: 80px;
}

/* ========== 返回栏 ========== */
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
  }
}

.filter-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.filter-content {
  padding-top: 52px;
  padding-left: 12px;
  padding-right: 12px;
}

.filter-section {
  margin-bottom: 6px;
}

.filter-options {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 2px;
}

.filter-section-label {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-primary);
  flex-shrink: 0;
  margin-right: 2px;
}

.filter-chip {
  padding: 2px 8px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text-secondary);
  font-size: 14px;
  border-radius: 14px;
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
  transition: all 0.2s;

  &:active {
    background: var(--surface-hover);
  }

  &.active {
    color: var(--primary-solid);
    background: rgba(249, 115, 22, 0.1);
    border-color: var(--primary-solid);
  }
}

.filter-footer {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 12px 16px;
  background: var(--surface);
  z-index: 1000;
  display: flex;
  justify-content: center;
}

.confirm-btn {
  width: 200px;
  height: 40px;
  border: none;
  background: var(--primary-solid);
  color: #ffffff;
  font-size: 15px;
  font-weight: 600;
  border-radius: 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;

  &:active {
    opacity: 0.9;
  }
}
</style>

<!-- 移动端筛选页：隐藏 Header 和 ChannelBar -->
<style lang="scss">
.mobile-layout.no-channelbar {
  .header {
    display: none !important;
  }

  .channel-bar {
    display: none !important;
  }

  .content {
    padding-top: 0 !important;
  }
}
</style>

