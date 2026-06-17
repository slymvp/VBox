import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Series, Platform, Stats, FilterOptions, Category } from '@/utils/api'
import { fetchPlatforms, fetchStats, fetchSeries, searchSeries, fetchFilterOptions, PLATFORM_MAP, TYPE_MAP, fetchCategories } from '@/utils/api'

export const useSeriesStore = defineStore('series', () => {
  const platforms = ref<Platform[]>([])
  const categories = ref<Category[]>([])
  const stats = ref<Stats>({ total_series: 0, total_episodes: 0 })
  const seriesList = ref<Series[]>([])
  const allSeriesList = ref<Series[]>([])
  const currentPlatform = ref<string>('all')
  const currentCategory = ref<string | null>(null)
  const currentPage = ref(1)
  const hasMore = ref(true)
  const isLoading = ref(false)
  const searchKeyword = ref('')

  // 筛选相关
  const currentYear = ref<string>('all')
  const currentArea = ref<string>('all')
  const currentTag = ref<string>('all')
  const currentDirector = ref<string>('all')
  const currentActor = ref<string>('all')
  const currentSort = ref<string>('')
  const currentMinScore = ref<number>(0)
  const filterOptions = ref<FilterOptions>({ years: [], areas: [], tags: [], directors: [], actors: [] })

  // 首页分类数据相关
  const homeCategoryData = ref<Record<string, Series[]>>({})
  const homeSortMap = ref<Record<string, string>>({})
  const homeLoading = ref<Record<string, boolean>>({})

  const filteredSeries = computed(() => {
    let result = [...seriesList.value]
    if (currentPlatform.value !== 'all') {
      result = result.filter(s => s.platform === currentPlatform.value)
    }
    if (currentCategory.value) {
      result = result.filter(s => s.category_key === currentCategory.value)
    }
    return result
  })

  const currentCategoryName = computed(() => {
    if (!currentCategory.value) return null
    return categoryMap.value[currentCategory.value]?.name || currentCategory.value
  })

  const currentPlatformName = computed(() => {
    if (currentPlatform.value === 'all') return '全部'
    return PLATFORM_MAP[currentPlatform.value]?.name || currentPlatform.value
  })

  async function loadPlatforms() {
    platforms.value = await fetchPlatforms()
  }

  let categoriesLoading = false
  let categoriesPromise: Promise<void> | null = null

  async function loadCategories() {
    // 如果已有数据，直接返回
    if (categories.value.length > 0) {
      return
    }
    // 如果正在加载，等待加载完成
    if (categoriesLoading && categoriesPromise) {
      await categoriesPromise
      return
    }
    // 无缓存数据时开始加载
    categoriesLoading = true
    categoriesPromise = (async () => {
      try {
        categories.value = await fetchCategories()
      } finally {
        categoriesLoading = false
        categoriesPromise = null
      }
    })()
    await categoriesPromise
  }

  async function loadStats() {
    stats.value = await fetchStats()
  }

  // 生成 category 到配置的 map（兼容旧的 TYPE_MAP）
  const categoryMap = computed(() => {
    const map: Record<string, { name: string; icon?: string }> = {}
    categories.value.forEach(cat => {
      // 优先从 TYPE_MAP 取 icon，没有的话用 cat.icon，最后用默认值
      const defaultConfig = TYPE_MAP[cat.key] || { name: cat.name, icon: '📁' }
      map[cat.key] = {
        name: cat.name,
        icon: defaultConfig.icon
      }
    })
    return map
  })

  async function loadSeries(reset = false) {
    if (isLoading.value) return

    isLoading.value = true
    const page = reset ? 1 : currentPage.value

    try {
      const data = await fetchSeries({
        page,
        platform: currentPlatform.value,
        category: currentCategory.value,
        year: currentYear.value !== 'all' ? currentYear.value : undefined,
        area: currentArea.value !== 'all' ? currentArea.value : undefined,
        tag: currentTag.value !== 'all' ? currentTag.value : undefined,
        director: currentDirector.value !== 'all' ? currentDirector.value : undefined,
        actor: currentActor.value !== 'all' ? currentActor.value : undefined,
        sort: currentSort.value || undefined,
        min_score: currentMinScore.value > 0 ? currentMinScore.value : undefined,
      })

      if (reset) {
        // 重置模式：完全清空并重新赋值
        seriesList.value = [...data.items]
        allSeriesList.value = [...data.items]
      } else {
        // 追加模式：对 seriesList 也要去重
        const existingIds = new Set(seriesList.value.map(item => item.id))
        const newItems = data.items.filter(item => !existingIds.has(item.id))
        seriesList.value = [...seriesList.value, ...newItems]

        // 对 allSeriesList 去重
        const allSeriesMap = new Map(allSeriesList.value.map(item => [item.id, item]))
        data.items.forEach(item => allSeriesMap.set(item.id, item))
        allSeriesList.value = [...allSeriesMap.values()]
      }

      hasMore.value = data.items.length === 20
      if (hasMore.value) {
        currentPage.value = page + 1
      }
    } finally {
      isLoading.value = false
    }
  }

  async function handleSearch(keyword: string) {
    searchKeyword.value = keyword
    if (!keyword) {
      currentPage.value = 1
      hasMore.value = true
      await loadSeries(true)
      return
    }

    isLoading.value = true
    try {
      const data = await searchSeries(keyword, {
        platform: currentPlatform.value,
        category: currentCategory.value
      })
      seriesList.value = data.items
      hasMore.value = false
    } finally {
      isLoading.value = false
    }
  }

  function setPlatform(platform: string) {
    currentPlatform.value = platform
    currentPage.value = 1
    hasMore.value = true
    searchKeyword.value = ''
  }

  function setCategory(category: string) {
    currentCategory.value = category
    currentPage.value = 1
    hasMore.value = true
    searchKeyword.value = ''
  }

  function resetFilters() {
    currentPlatform.value = 'all'
    // 不重置 currentCategory，保留当前频道
    currentYear.value = 'all'
    currentArea.value = 'all'
    currentTag.value = 'all'
    currentDirector.value = 'all'
    currentActor.value = 'all'
    currentSort.value = ''
    currentMinScore.value = 0
    currentPage.value = 1
    hasMore.value = true
    searchKeyword.value = ''
    seriesList.value = []
    allSeriesList.value = []
  }

  function resetFilterOptions() {
    currentYear.value = 'all'
    currentArea.value = 'all'
    currentTag.value = 'all'
    currentDirector.value = 'all'
    currentActor.value = 'all'
    currentSort.value = ''
    currentMinScore.value = 0
    currentPlatform.value = 'all'
    currentPage.value = 1
    hasMore.value = true
  }

  function setFilter(type: string, value: string | number) {
    switch (type) {
      case 'year': currentYear.value = String(value); break
      case 'area': currentArea.value = String(value); break
      case 'tag': currentTag.value = String(value); break
      case 'director': currentDirector.value = String(value); break
      case 'actor': currentActor.value = String(value); break
      case 'sort': currentSort.value = String(value); break
      case 'min_score': currentMinScore.value = Number(value); break
    }
    currentPage.value = 1
    hasMore.value = true
  }

  async function loadFilterOptions() {
    if (!currentCategory.value) return
    try {
      filterOptions.value = await fetchFilterOptions(currentCategory.value, currentPlatform.value)
    } catch (error) {
      console.error('Failed to load filter options:', error)
    }
  }

  // 加载首页分类数据
  async function loadHomeCategoryData(categoryKey: string, sort: string = 'new') {
    homeLoading.value[categoryKey] = true
    homeSortMap.value[categoryKey] = sort

    try {
      const data = await fetchSeries({
        category: categoryKey,
        page: 1,
        limit: 20,
        sort: sort || undefined,
      })

      homeCategoryData.value[categoryKey] = data.items
    } catch (error) {
      console.error(`Failed to load ${categoryKey} data:`, error)
    } finally {
      homeLoading.value[categoryKey] = false
    }
  }

  // 加载全部剧集（用于搜索下拉显示热播内容）
  async function loadAllSeries() {
    try {
      const data = await fetchSeries({
        page: 1,
        limit: 100,
      })
      allSeriesList.value = data.items
    } catch (error) {
      console.error('Failed to load all series:', error)
    }
  }

  // 初始化首页所有分类数据
  function initHomeData() {
    const categoryKeys = categories.value.map(cat => cat.key)
    categoryKeys.forEach(category => {
      if (!homeCategoryData.value[category]) {
        loadHomeCategoryData(category, 'new')
      }
    })
  }

  return {
    platforms,
    categories,
    categoryMap,
    stats,
    seriesList,
    allSeriesList,
    currentPlatform,
    currentCategory,
    currentPage,
    hasMore,
    isLoading,
    searchKeyword,
    filteredSeries,
    currentCategoryName,
    currentPlatformName,
    PLATFORM_MAP,
    TYPE_MAP,
    loadPlatforms,
    loadCategories,
    loadStats,
    loadSeries,
    handleSearch,
    setPlatform,
    setCategory,
    resetFilters,
    loadAllSeries,
    // 筛选相关
    currentYear,
    currentArea,
    currentTag,
    currentDirector,
    currentActor,
    currentSort,
    currentMinScore,
    filterOptions,
    setFilter,
    loadFilterOptions,
    resetFilterOptions,
    // 首页数据
    homeCategoryData,
    homeSortMap,
    homeLoading,
    loadHomeCategoryData,
    initHomeData,
  }
})
