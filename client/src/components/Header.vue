<template>
  <header :class="['header', { 'header-hidden': isHidden }]">
    <div class="header-row header-row-top">
      <router-link to="/" class="logo">
        <div class="logo-img-wrapper">
          <img :src="logoImage" alt="VBox" class="logo-img" />
        </div>
        <span class="logo-text">VBOX</span>
      </router-link>

      <button
        :class="['home-btn', { active: isHomePage }]"
        @click="handleHomeClick"
      >
        <span class="home-icon">🏠</span>
        首页
      </button>

      <!-- PC端频道 -->
      <div v-if="showTypeFilters" class="type-filters type-filters-desktop">
        <button
          v-for="cat in displayCategories"
          :key="cat.key"
          :class="['type-btn', { active: currentCategory === cat.key }]"
          @click="handleTypeClick(cat.key)"
        >
          {{ cat.name }}
        </button>
      </div>

      <SearchDropdown />

      <div class="header-spacer"></div>

      <div v-if="showLayoutToggle" class="layout-toggle">
        <button
          :class="['layout-btn', { active: layout === 'vertical' }]"
          @click="handleLayoutChange('vertical')"
          title="竖版卡片"
        >
          <span class="layout-icon layout-icon-vertical">▦</span>
        </button>
        <button
          :class="['layout-btn', { active: layout === 'horizontal' }]"
          @click="handleLayoutChange('horizontal')"
          title="横版卡片"
        >
          <span class="layout-icon layout-icon-horizontal">▤</span>
        </button>
      </div>

      <UserMenu />
    </div>

    <!-- TV端频道 - 单独第二行 -->
    <div v-if="showTypeFilters" class="header-row header-row-bottom">
      <div class="type-filters-wrapper">
        <div class="type-filters">
          <button
            v-for="cat in displayCategories"
            :key="cat.key"
            :class="['type-btn', { active: currentCategory === cat.key }]"
            @click="handleTypeClick(cat.key)"
          >
            {{ cat.name }}
          </button>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useSeriesStore } from '@/stores/series'
import SearchDropdown from './SearchDropdown.vue'
import UserMenu from './UserMenu.vue'
import logoImage from '/logo-icon.png'
import { TYPE_MAP } from '@/utils/api'

const props = defineProps<{
  isHidden?: boolean
  showTypeFilters?: boolean
  showLayoutToggle?: boolean
  layout?: 'vertical' | 'horizontal'
}>()

const emit = defineEmits<{
  (e: 'layout-change', layout: 'vertical' | 'horizontal'): void
  (e: 'home-click'): void
}>()

const router = useRouter()
const route = useRoute()
const store = useSeriesStore()

const isHomePage = computed(() => route.path === '/')

// 显示的分类列表（从 store 获取）
const displayCategories = computed(() => {
  return store.categories
})

// 路由类型映射 - 根据 URL path 推断当前分类
const ROUTE_TYPE_MAP: Record<string, string> = {
  '/tv': 'tv',
  '/movie': 'movie',
  '/variety': 'variety',
  '/cartoon': 'cartoon',
  '/child': 'child',
  '/free': 'free',
}

const currentCategory = computed(() => {
  // 优先从 store 获取
  if (store.currentCategory) return store.currentCategory
  // 从当前路由 path 推断
  for (const [prefix, type] of Object.entries(ROUTE_TYPE_MAP)) {
    if (route.path.startsWith(prefix)) return type
  }
  return null
})

const handleHomeClick = () => {
  // 如果已经是首页，不重复操作
  if (route.path === '/') {
    return
  }
  store.resetFilters()
  emit('home-click')
  router.push('/')
}

const handleTypeClick = (key: string) => {
  const path = {
    tv: '/tv',
    movie: '/movie',
    variety: '/variety',
    cartoon: '/cartoon',
    child: '/child',
    free: '/free'
  }[key] || '/'

  // 如果已经是当前路径，不重复跳转
  if (route.path === path) {
    return
  }

  store.resetFilters()
  router.push(path)
}

// 页面加载时获取 categories
onMounted(() => {
  if (store.categories.length === 0) {
    store.loadCategories()
  }
})

const handleLayoutChange = (layout: 'vertical' | 'horizontal') => {
  emit('layout-change', layout)
}
</script>

<style lang="scss" scoped>
.header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 72px;
  background: #141419 !important;
  background-color: #141419 !important;
  display: flex;
  flex-direction: column;
  padding: 0 24px;
  z-index: 1000;
  transition: transform 0.3s ease, opacity 0.3s ease;
}

.header-row {
  display: flex;
  align-items: center;
  width: 100%;
}

.header-row-top {
  flex: 1;
}

.header-row-bottom {
  display: none;
}

.type-filters-desktop {
  display: flex;
}

.type-filters-wrapper {
  width: 100%;
}

.header-hidden {
  transform: translateY(-100%);
  opacity: 0;
  pointer-events: none;
}

.logo {
  margin-right: 32px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 12px;
  text-decoration: none;
  transition: transform 0.3s ease;
}

.logo:hover {
  transform: scale(1.03);
}

.logo:hover .logo-img {
  filter: drop-shadow(0 0 8px rgba(251, 191, 36, 0.5));
}

.logo:hover .logo-text {
  filter: drop-shadow(0 0 12px rgba(251, 191, 36, 0.4));
}

.logo-img-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: transparent !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

.logo-img {
  width: 40px;
  height: 40px;
  object-fit: contain;
  background-color: transparent !important;
  border: none !important;
  outline: none !important;
  box-shadow: none !important;
  filter: drop-shadow(0 0 4px rgba(251, 191, 36, 0.3));
  transition: filter 0.3s ease;
}

.logo-text {
  font-size: 26px;
  font-weight: 900;
  background: linear-gradient(135deg, #fde68a 0%, var(--gold-light) 30%, var(--gold-dark) 70%, #92400e 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: 2px;
  position: relative;
  filter: drop-shadow(0 0 6px rgba(251, 191, 36, 0.25));
  transition: filter 0.3s ease;
}

.logo-text::after {
  content: 'VBOX';
  position: absolute;
  left: 0;
  top: 0;
  background: linear-gradient(135deg, #fde68a, var(--gold-light), var(--gold-dark));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: 2px;
  opacity: 0;
  filter: blur(8px);
  transition: opacity 0.3s ease;
}

.logo:hover .logo-text::after {
  opacity: 0.6;
}

.home-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 18px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 16px;
  font-weight: 500;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.08);
    color: var(--text-primary);
    font-size: 18px;
  }

  &.active {
    color: var(--gold);
    font-weight: 600;
    font-size: 18px;
  }
}

.type-filters {
  display: flex;
  gap: 8px;
  flex-wrap: nowrap;
  overflow-x: auto;
  scrollbar-width: none;

  &::-webkit-scrollbar {
    display: none;
  }
}

.type-btn {
  padding: 12px 22px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 18px;
  font-weight: 500;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;

  &:hover {
    background: rgba(255, 255, 255, 0.08);
    color: var(--text-primary);
    font-size: 20px;
    padding: 14px 24px;
  }

  &.active {
    color: var(--gold);
    font-weight: 600;
    font-size: 20px;
    background: rgba(232, 197, 71, 0.1);
  }
}

.header-spacer {
  flex: 1;
}

.layout-toggle {
  display: flex;
  gap: 4px;
  margin-right: 12px;
  background: rgba(255, 255, 255, 0.06);
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
  color: #9ca3af;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  outline: none;

  &:hover {
    background: rgba(255, 255, 255, 0.08);
    color: #ffffff;
  }

  &.active {
    background: rgba(232, 197, 71, 0.15);
    color: var(--gold);
  }
}

.layout-icon {
  font-size: 20px;
  line-height: 1;
}

.layout-icon-vertical {
  font-size: 18px;
}

.layout-icon-horizontal {
  font-size: 18px;
}

/* TV 大屏幕适配 - 1080p 及以上 */
@media screen and (min-width: 1920px) {
  .header {
    height: 140px;
    padding: 12px 48px;
    flex-direction: column;
    gap: 8px;
  }

  .header-row-bottom {
    display: flex;
    justify-content: flex-start;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    padding-top: 12px;
  }

  .type-filters-wrapper {
    display: flex;
    justify-content: flex-start;
  }

  .type-filters-desktop {
    display: none;
  }

  .header-row-top {
    flex: 1;
    display: flex;
    align-items: center;
  }

  .logo {
    margin-right: 48px;
    gap: 16px;
  }

  .logo-img {
    width: 52px;
    height: 52px;
  }

  .logo-text {
    font-size: 32px;
    letter-spacing: 3px;
  }

  .home-btn {
    padding: 14px 24px;
    font-size: 22px;
    gap: 8px;

    &:hover {
      font-size: 24px;
    }

    &.active {
      font-size: 24px;
    }
  }

  .type-filters {
    gap: 12px;
  }

  .type-btn {
    padding: 16px 28px;
    font-size: 22px;
    border-radius: 12px;

    &:hover {
      font-size: 24px;
      padding: 18px 30px;
    }

    &.active {
      font-size: 24px;
      padding: 18px 30px;
    }
  }

  .layout-toggle {
    margin-right: 16px;
    padding: 6px;
  }

  .layout-btn {
    width: 44px;
    height: 44px;
    color: #9ca3af;
  }

  .layout-icon {
    font-size: 24px;
  }

  .layout-btn:hover {
    color: #ffffff;
  }

  .layout-btn.active {
    color: var(--gold);
  }
}

/* 超高清 TV 屏幕适配 */
@media screen and (min-width: 2560px) {
  .header {
    height: 160px;
    padding: 16px 64px;
    gap: 12px;
  }

  .header-row-bottom {
    padding-top: 16px;
  }

  .logo {
    margin-right: 64px;
    gap: 20px;
  }

  .logo-img {
    width: 60px;
    height: 60px;
  }

  .logo-text {
    font-size: 38px;
    letter-spacing: 4px;
  }

  .home-btn {
    padding: 18px 30px;
    font-size: 26px;

    &:hover, &.active {
      font-size: 28px;
    }
  }

  .type-filters {
    gap: 16px;
  }

  .type-btn {
    padding: 20px 34px;
    font-size: 26px;
    border-radius: 14px;

    &:hover, &.active {
      font-size: 28px;
      padding: 22px 36px;
    }
  }

  .layout-btn {
    width: 52px;
    height: 52px;
  }

  .layout-btn svg {
    width: 26px;
    height: 26px;
  }
}

@media screen and (max-width: 768px) {
  .header {
    height: 60px;
    padding: 0 16px;
  }

  .logo {
    margin-right: 16px;
    gap: 8px;
  }

  .logo-img {
    width: 32px;
    height: 32px;
  }

  .logo-text {
    font-size: 22px;
  }

  .layout-toggle {
    margin-right: 8px;
    padding: 2px;
  }

  .layout-btn {
    width: 32px;
    height: 32px;
  }
}
</style>
