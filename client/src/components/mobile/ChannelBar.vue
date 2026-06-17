<template>
  <div class="channel-bar">
    <div class="channel-row">
      <button
        v-for="cat in displayCategories"
        :key="cat.key"
        :class="['channel-btn', { active: currentCategory === cat.key }]"
        @click="handleChannelClick(cat.key)"
      >
        {{ cat.name }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useSeriesStore } from '@/stores/series'

const router = useRouter()
const route = useRoute()
const store = useSeriesStore()

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
  return 'tv' // 默认选中电视剧
})

const handleChannelClick = (key: string) => {
  const path = {
    tv: '/tv',
    movie: '/movie',
    variety: '/variety',
    cartoon: '/cartoon',
    child: '/child',
    free: '/free'
  }[key] || '/tv'

  // 点击频道时总是清除筛选条件
  store.resetFilters()

  if (route.path === path) {
    // 如果是同一频道，刷新数据
    store.loadSeries(true)
    return
  }

  router.push(path)
}

// 切换到下一个/上一个频道
const switchToNextChannel = () => {
  const categories = displayCategories.value
  const currentIndex = categories.findIndex(cat => cat.key === currentCategory.value)
  if (currentIndex < categories.length - 1) {
    handleChannelClick(categories[currentIndex + 1].key)
  }
}

const switchToPrevChannel = () => {
  const categories = displayCategories.value
  const currentIndex = categories.findIndex(cat => cat.key === currentCategory.value)
  if (currentIndex > 0) {
    handleChannelClick(categories[currentIndex - 1].key)
  }
}

// 暴露方法供外部调用
defineExpose({
  switchToNextChannel,
  switchToPrevChannel
})

onMounted(async () => {
  // 加载分类
  if (store.categories.length === 0) {
    await store.loadCategories()
  }
})
</script>

<style lang="scss" scoped>
.channel-bar {
  height: 40px;
  background: transparent;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 0 8px;
  z-index: 999;
  overflow: hidden;
  border-bottom: 1px solid var(--border-light);
}

.channel-row {
  display: flex;
  align-items: center;
  gap: 1px;
  overflow-x: auto;
  overflow-y: hidden;
  scrollbar-width: none;
  width: 100%;

  &::-webkit-scrollbar {
    display: none;
  }
}

.channel-btn {
  padding: 5px 14px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  font-size: 14px;
  font-weight: 500;
  border-radius: 12px;
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
  transition: all 0.2s ease;

  &:active {
    background: var(--surface-hover);
    color: var(--text-primary);
  }

  &.active {
    color: #fff;
    font-weight: 600;
    background: var(--primary);
    box-shadow: 0 2px 8px color-mix(in srgb, var(--primary-solid) 30%, transparent);
  }
}

@media screen and (max-width: 480px) {
  .channel-bar {
    padding: 0 4px;
  }

  .channel-btn {
    padding: 3px 10px;
    font-size: 14px;
  }
}
</style>
