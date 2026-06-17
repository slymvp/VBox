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
      <div v-if="showTypeFilters" class="type-filters">
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
  </header>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useSeriesStore } from '@/stores/series'
import SearchDropdown from '@/components/SearchDropdown.vue'
import UserMenu from '@/components/UserMenu.vue'
import logoImage from '/logo-icon.png'

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

const displayCategories = computed(() => {
  return store.categories
})

const ROUTE_TYPE_MAP: Record<string, string> = {
  '/tv': 'tv',
  '/movie': 'movie',
  '/variety': 'variety',
  '/cartoon': 'cartoon',
  '/child': 'child',
  '/free': 'free',
}

const currentCategory = computed(() => {
  if (store.currentCategory) return store.currentCategory
  for (const [prefix, type] of Object.entries(ROUTE_TYPE_MAP)) {
    if (route.path.startsWith(prefix)) return type
  }
  return null
})

const handleHomeClick = () => {
  if (route.path === '/') return
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

  if (route.path === path) return
  store.resetFilters()
  router.push(path)
}

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
  align-items: center;
  padding: 0 24px;
  z-index: 1000;
  transition: transform 0.3s ease, opacity 0.3s ease;
}

.header-row {
  display: flex;
  align-items: center;
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

  &:hover {
    transform: scale(1.03);

    .logo-img {
      filter: drop-shadow(0 0 8px rgba(251, 191, 36, 0.5));
    }

    .logo-text {
      filter: drop-shadow(0 0 12px rgba(251, 191, 36, 0.4));
    }
  }
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

.layout-icon-vertical,
.layout-icon-horizontal {
  font-size: 18px;
}

/* 小屏幕适配 */
@media screen and (max-width: 1200px) {
  .header {
    padding: 0 16px;
  }

  .logo {
    margin-right: 20px;
    gap: 8px;
  }

  .type-btn {
    padding: 8px 14px;
    font-size: 14px;

    &:hover {
      font-size: 16px;
      padding: 10px 16px;
    }

    &.active {
      font-size: 16px;
    }
  }
}

@media screen and (max-width: 992px) {
  .header {
    height: 60px;
    padding: 0 16px;
  }

  .logo {
    margin-right: 12px;
  }

  .logo-img {
    width: 32px;
    height: 32px;
  }

  .logo-text {
    font-size: 20px;
  }

  .home-btn {
    padding: 8px 12px;
    font-size: 14px;

    &:hover, &.active {
      font-size: 15px;
    }
  }

  .type-btn {
    padding: 6px 12px;
    font-size: 13px;

    &:hover {
      font-size: 14px;
      padding: 8px 14px;
    }

    &.active {
      font-size: 14px;
    }
  }

  .layout-btn {
    width: 32px;
    height: 32px;
  }
}
</style>
