import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { fetchSeriesDetail, fetchParseSources, type Series, type Episode, type ParseSource } from '@/utils/api'

export const usePlayStore = defineStore('play', () => {
  // 剧集数据
  const series = ref<Series | null>(null)
  const parseSources = ref<ParseSource[]>([])
  const selectedSourceKey = ref('')

  // 当前播放
  const currentCid = ref('')
  const activeEpisodeId = ref<number | string | undefined>(undefined)
  const playUrl = ref('')
  const playTitle = ref('')

  // 加载状态
  const isLoading = ref(false)
  const isPlaying = ref(false)

  // 计算属性
  const episodes = computed(() => series.value?.episodes || [])
  const isMovie = computed(() => series.value?.category_key === 'movie')

  const currentSourceUrl = computed(() => {
    const source = parseSources.value.find(s => s.key === selectedSourceKey.value)
    return source?.url || ''
  })

  const fullPlayUrl = computed(() => {
    if (!playUrl.value) return ''
    return currentSourceUrl.value + playUrl.value
  })

  // 操作
  async function loadPlayData(cid: string) {
    if (currentCid.value === cid && series.value) {
      // 同剧集切换分集，不需要重新加载
      return
    }

    currentCid.value = cid
    isLoading.value = true
    try {
      series.value = await fetchSeriesDetail(cid)
      await loadParseSources()
    } finally {
      isLoading.value = false
    }
  }

  async function loadParseSources() {
    try {
      const platformKey = series.value?.platform || ''
      parseSources.value = await fetchParseSources(platformKey)
      if (parseSources.value.length > 0) {
        selectedSourceKey.value = parseSources.value[0].key
      }
    } catch (error) {
      console.error('Failed to load parse sources:', error)
    }
  }

  function playEpisode(ep: Episode) {
    if (!ep.play_url) return
    activeEpisodeId.value = ep.id || ep.vid
    playUrl.value = ep.play_url
    playTitle.value = ep.play_title || `第${ep.episode_num}集`
    isPlaying.value = true
  }

  function setSourceKey(key: string) {
    selectedSourceKey.value = key
  }

  function stop() {
    playUrl.value = ''
    playTitle.value = ''
    isPlaying.value = false
  }

  function reset() {
    series.value = null
    parseSources.value = []
    selectedSourceKey.value = ''
    currentCid.value = ''
    activeEpisodeId.value = undefined
    playUrl.value = ''
    playTitle.value = ''
    isLoading.value = false
    isPlaying.value = false
  }

  return {
    // 状态
    series,
    parseSources,
    selectedSourceKey,
    currentCid,
    activeEpisodeId,
    playUrl,
    playTitle,
    isLoading,
    isPlaying,
    // 计算属性
    episodes,
    isMovie,
    currentSourceUrl,
    fullPlayUrl,
    // 操作
    loadPlayData,
    loadParseSources,
    playEpisode,
    setSourceKey,
    stop,
    reset,
  }
})
