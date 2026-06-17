<template>
  <header :class="['header', { 'header-hidden': isHidden }]">
    <div class="header-row">
      <!-- TV端频道 - 焦点组 -->
      <div v-if="showTypeFilters" class="type-filters-wrapper">
        <div class="type-filters">
          <button
            v-for="(cat, index) in displayCategories"
            :key="cat.key"
            :class="['type-btn', { active: currentCategory === cat.key }]"
            @click="handleTypeClick(cat.key)"
            class="focusable tv-btn"
            :data-row="0"
            :data-col="index + 1"
            tabindex="0"
          >
            {{ cat.name }}
          </button>
        </div>
      </div>

      <SearchDropdown />

      <div class="header-spacer"></div>

      <UserMenu />
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useSeriesStore } from '@/stores/series'
import { useDeviceStore } from '@/stores/device'
import SearchDropdown from '@/components/SearchDropdown.vue'
import UserMenu from '@/components/UserMenu.vue'

const props = defineProps<{
  isHidden?: boolean
  showTypeFilters?: boolean
}>()

const router = useRouter()
const route = useRoute()
const store = useSeriesStore()
const deviceStore = useDeviceStore()

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

const handleTypeClick = (key: string) => {
  const path = {
    tv: '/tv',
    movie: '/movie',
    variety: '/variety',
    cartoon: '/cartoon',
    child: '/child',
    free: '/free'
  }[key] || '/tv'

  if (route.path === path) {
    return
  }

  store.resetFilters()
  router.push(path)
}

onMounted(() => {
  if (store.categories.length === 0) {
    store.loadCategories()
  }

  // TV 模式键盘导航
  if (deviceStore.isTV) {
    const headerBtns = document.querySelectorAll('.tv-btn')

    document.addEventListener('keydown', (e: KeyboardEvent) => {
      const btns = Array.from(headerBtns) as HTMLElement[]
      const focused = document.activeElement as HTMLElement
      const currentIndex = btns.indexOf(focused)

      switch (e.key) {
        case 'ArrowLeft':
          e.preventDefault()
          if (currentIndex > 0) {
            btns[currentIndex - 1].focus()
          }
          break
        case 'ArrowRight':
          e.preventDefault()
          if (currentIndex < btns.length - 1) {
            btns[currentIndex + 1].focus()
          }
          break
        case 'Enter':
          if (focused && typeof focused.click === 'function') {
            focused.click()
          }
          break
      }
    })

    // 设置初始焦点
    nextTick(() => {
      if (headerBtns.length > 0) {
        (headerBtns[0] as HTMLElement).focus()
      }
    })
  }
})
</script>

<style lang="scss" scoped>
.header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 80px;
  background: #0a0a0f;
  display: flex;
  align-items: center;
  padding: 0 48px;
  z-index: 1000;
}

.header-row {
  display: flex;
  align-items: center;
  width: 100%;
  gap: 16px;
}

.type-filters-wrapper {
  display: flex;
  flex: 0 1 auto;
  min-width: 0;
  padding-right: 16px;
  overflow: hidden;
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

.header-spacer {
  flex: 1;
  min-width: 8px;
}

.header-hidden {
  display: none;
}

.type-btn {
  padding: 8px 16px;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 18px;
  font-weight: 500;
  border-radius: 6px;
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;

  &.active {
    color: var(--gold);
    font-weight: 600;
    background: rgba(232, 197, 71, 0.2);
  }
}

.header-spacer {
  flex: 1;
}

/* TV遥控器焦点样式 */
.focusable {
  outline: none;
}

.tv-btn {
  outline: none;

  &:focus-visible,
  &:focus {
    outline: 3px solid #f59e0b !important;
    outline-offset: 2px;
    transform: none !important;
    box-shadow: none !important;
  }
}

/* 超高清 TV 屏幕适配 */
@media screen and (min-width: 2560px) {
  .header {
    height: 140px;
    padding: 16px 64px;
    gap: 12px;
  }

  .header-row-bottom {
    padding-top: 16px;
  }

  .type-filters {
    gap: 16px;
  }

  .type-btn {
    padding: 20px 34px;
    font-size: 26px;
    border-radius: 14px;

    &.active {
      font-size: 28px;
      padding: 22px 36px;
    }
  }

  .layout-btn {
    width: 52px;
    height: 52px;
  }

  .layout-icon {
    font-size: 26px;
  }
}

@media screen and (max-width: 1366px) {
  .header {
    height: 100px;
    padding: 10px 32px;
  }

  .type-filters {
    gap: 10px;
  }

  .type-btn {
    padding: 14px 24px;
    font-size: 20px;
    border-radius: 10px;

    &.active {
      font-size: 22px;
      padding: 16px 26px;
    }
  }

  .layout-btn {
    width: 40px;
    height: 40px;
  }

  .layout-icon {
    font-size: 22px;
  }
}
</style>
