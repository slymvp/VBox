<template>
  <div class="native-player-controls" :class="{ 'controls-hidden': !controlsVisible }" @click.stop>
    <!-- 顶部信息栏 -->
    <div class="top-bar" :class="{ 'bar-hidden': !topBarVisible }">
      <button class="back-btn" data-tv-focus data-tv-zone="back-btn" @click="$emit('back')">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5"/><path d="M12 19l-7-7 7-7"/></svg>
      </button>
      <span class="play-title">{{ title }}</span>
      <button
        v-if="showNextBtn && nextEpisodeTitle"
        class="next-episode-btn"
        data-tv-focus
        data-tv-zone="next-btn"
        @click="$emit('next')"
        title="播放下一集"
      >
        <span class="next-episode-label">下一集</span>
        <span class="next-episode-title">{{ nextEpisodeTitle }}</span>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>
      </button>

      <!-- 左侧操作按钮：选集-详情-收藏-追剧 -->
      <div class="top-bar-actions">
        <button class="action-btn" :class="{ active: isEpisodesOpen }" data-tv-focus data-tv-zone="episodes-btn" @click="openEpisodes" title="选集">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
          <span>选集</span>
        </button>
        <button class="action-btn" :class="{ active: showDetail }" data-tv-focus data-tv-zone="detail-btn" @click="toggleDetail" title="详情">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
          <span>详情</span>
        </button>
        <button class="action-btn" :class="{ active: isBookmarked }" data-tv-focus data-tv-zone="bookmark-btn" @click="$emit('bookmark')" title="收藏">
          <svg viewBox="0 0 24 24" width="16" height="16">
            <path v-if="isBookmarked" fill="currentColor" d="M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 22 12 18.56 5.82 22 7 14.14l-5-4.87 6.91-1.01L12 2z"/>
            <path v-else fill="none" stroke="currentColor" stroke-width="1.8" d="M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 22 12 18.56 5.82 22 7 14.14l-5-4.87 6.91-1.01L12 2z"/>
          </svg>
          <span>{{ isBookmarked ? '已收藏' : '收藏' }}</span>
        </button>
        <button v-if="showFollowBtn" class="action-btn" :class="{ active: isFollowed }" data-tv-focus data-tv-zone="follow-btn" @click="$emit('follow')" title="追剧">
          <svg viewBox="0 0 24 24" width="16" height="16">
            <path v-if="isFollowed" fill="currentColor" d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
            <path v-else fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" d="M12 5v14M5 12h14"/>
          </svg>
          <span>{{ isFollowed ? '已追剧' : '追剧' }}</span>
        </button>
      </div>

      <!-- 右侧：基础信息（居右） -->
      <div class="top-bar-right" v-if="seriesInfo">
        <span v-if="seriesInfo.platformName" class="meta-platform" :class="seriesInfo.platformBadge">{{ seriesInfo.platformName }}</span>
        <span v-if="seriesInfo.year" class="meta-item">{{ seriesInfo.year }}</span>
        <span v-if="seriesInfo.area" class="meta-item">{{ seriesInfo.area }}</span>
        <span v-if="!seriesInfo.isMovie && seriesInfo.totalEpisodes" class="meta-item">
          <template v-if="seriesInfo.updatedEpisodes && seriesInfo.updatedEpisodes < seriesInfo.totalEpisodes">更新至{{ seriesInfo.updatedEpisodes }}集</template>
          <template v-else>共{{ seriesInfo.totalEpisodes }}集</template>
        </span>
        <span v-if="seriesInfo.score" class="meta-score">{{ seriesInfo.score }}分</span>
      </div>
    </div>

    <!-- 详情面板（简介/演员/标签） -->
    <transition name="slide-detail">
      <div v-if="showDetail" class="detail-overlay" @click="showDetail = false; emit('detail-change', false)">
        <div class="detail-panel" @click.stop>
          <div class="detail-panel-header">
            <div class="detail-tabs">
              <button
                v-for="tab in detailTabs"
                :key="tab.key"
                :class="['detail-tab', { active: activeDetailTab === tab.key }]"
                data-tv-focus
                :data-tv-zone="'detail-tab-' + tab.key"
                @click="activeDetailTab = tab.key"
              >{{ tab.label }}</button>
            </div>
            <button class="detail-close-btn" data-tv-focus data-tv-zone="detail-close-btn" @click="showDetail = false; emit('detail-change', false)">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6L6 18"/><path d="M6 6l12 12"/></svg>
            </button>
          </div>
          <div class="detail-panel-body">
            <div v-if="activeDetailTab === 'intro'" class="detail-tab-content">
              <p v-if="description" class="detail-description">{{ description }}</p>
              <div v-else class="detail-empty">暂无简介</div>
            </div>
            <div v-if="activeDetailTab === 'actors'" class="detail-tab-content">
              <div v-if="directors.length > 0" class="detail-section">
                <h4 class="detail-section-title">导演</h4>
                <div class="detail-tag-list">
                  <span v-for="director in directors" :key="director" class="detail-tag">{{ director }}</span>
                </div>
              </div>
              <div v-if="actors.length > 0" class="detail-section">
                <h4 class="detail-section-title">演员</h4>
                <div class="detail-tag-list">
                  <span v-for="actor in actors" :key="actor" class="detail-tag">{{ actor }}</span>
                </div>
              </div>
              <div v-if="directors.length === 0 && actors.length === 0" class="detail-empty">暂无演员信息</div>
            </div>
            <div v-if="activeDetailTab === 'tags'" class="detail-tab-content">
              <div v-if="tags.length > 0" class="detail-tag-list">
                <span v-for="tag in tags" :key="tag" class="detail-tag">{{ tag }}</span>
              </div>
              <div v-else class="detail-empty">暂无标签</div>
            </div>
          </div>
        </div>
      </div>
    </transition>

    <!-- 中央提示区（快进/音量等提示，加载中时不显示） -->
    <div class="center-controls" v-if="!isBuffering && !isResolving">
      <!-- 快进/快退提示 -->
      <transition name="fade">
        <div v-if="showSeekIndicator" class="seek-indicator" :class="seekDirection">
          <span>{{ seekDirection === 'seek-forward' ? `快进 ${seekAmount}秒` : `快退 ${seekAmount}秒` }}</span>
        </div>
      </transition>

      <!-- 音量变化提示 -->
      <transition name="fade">
        <div v-if="showVolumeIndicator" class="volume-indicator">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
            <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path>
          </svg>
          <div class="volume-bar">
            <div class="volume-fill" :style="{ width: `${volumeLevel}%` }"></div>
          </div>
        </div>
      </transition>
    </div>

    <!-- 底部区域 -->
    <div class="flex-spacer"></div>

    <!-- 底部控制栏 -->
    <div v-if="!iframeMode" class="bottom-bar" :class="{ 'bar-hidden': !bottomBarVisible }">
      <div class="bottom-bar-left">
        <button class="control-btn" data-tv-focus data-tv-zone="prev-btn" @click="$emit('prev')" v-if="showPrevBtn">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="19 20 9 12 19 4 19 20"/><line x1="5" y1="19" x2="5" y2="5"/></svg>
        </button>
        <button class="control-btn play-pause-btn" data-tv-focus data-tv-zone="play-btn" @click="togglePlay">
          <svg v-if="!isPlaying" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>
          <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>
        </button>
        <button class="control-btn" data-tv-focus data-tv-zone="next-btn" @click="$emit('next')" v-if="showNextBtn">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 20 15 12 5 4 5 20"/><line x1="19" y1="5" x2="19" y2="19"/></svg>
        </button>
        <button v-if="!seriesInfo?.isMovie" class="control-btn auto-play-btn" :class="{ active: autoPlay }" data-tv-focus data-tv-zone="autoplay-btn" @click="$emit('toggle-auto-play')" title="自动播放">
          <span>{{ autoPlay ? '自动播' : '手动' }}</span>
        </button>
      </div>
      <div class="bottom-bar-right">
        <!-- 倍速按钮 -->
        <div class="speed-wrapper" @mouseleave="closeSpeedMenu">
          <button class="control-btn speed-btn" data-tv-focus data-tv-zone="speed-btn" @click.stop="toggleSpeedMenu">
            <span>{{ playbackRate }}x</span>
          </button>
          <div class="speed-popup" v-show="showSpeedMenu" @mouseenter="cancelSpeedHide">
            <button
              v-for="rate in speedRates"
              :key="rate"
              :class="['speed-item', { active: playbackRate === rate }]"
              data-tv-focus
              :data-tv-zone="'speed-' + rate"
              @click="setSpeed(rate)"
            >
              {{ rate }}x
            </button>
          </div>
        </div>
        <!-- 音量 -->
        <div class="volume-wrapper" @mouseenter="onVolumeEnter" @mouseleave="onVolumeLeave">
          <button class="control-btn volume-btn" data-tv-focus data-tv-zone="volume-btn" @click="toggleMute">
            <svg v-if="!isMuted" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
              <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path>
            </svg>
            <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
              <line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/>
            </svg>
          </button>
          <div class="volume-slider-popup" v-show="showVolumeSlider" @mouseenter="onVolumeEnter" @mouseleave="onVolumeLeave">
            <input
              type="range"
              class="volume-range"
              min="0"
              max="100"
              :value="volumeLevel"
              @input="onVolumeInput"
              orient="vertical"
            />
          </div>
        </div>
        <!-- 全屏 -->
        <button class="control-btn fullscreen-btn" data-tv-focus data-tv-zone="fullscreen-btn" @click="$emit('toggle-fullscreen')">
          <svg v-if="!isFullscreen" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>
          <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3"/></svg>
        </button>
      </div>
    </div>
  </div>

  <!-- 进度条（独立于控件层，始终常显，控件隐藏后进度条变暗，时间保持明亮） -->
  <div v-if="!iframeMode" class="native-progress-bar">
    <span class="time-display">{{ formatTime(currentTime) }} / {{ formatTime(duration) }}</span>
    <div class="progress-bar" :class="{ 'bar-dimmed': !controlsVisible }" @click="seek" ref="progressBarRef">
      <div class="progress-buffer" :style="{ width: `${bufferedPercent}%` }"></div>
      <div class="progress-played" :style="{ width: `${playedPercent}%` }"></div>
      <div class="progress-handle" :style="{ left: `${playedPercent}%` }"></div>
    </div>
  </div>
</template>
<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useDeviceStore } from '@/stores/device'

const deviceStore = useDeviceStore()

// Props
const props = defineProps({
  title: {
    type: String,
    default: ''
  },
  isPlaying: {
    type: Boolean,
    default: false
  },
  isMuted: {
    type: Boolean,
    default: false
  },
  isFullscreen: {
    type: Boolean,
    default: false
  },
  currentTime: {
    type: Number,
    default: 0
  },
  duration: {
    type: Number,
    default: 0
  },
  bufferedPercent: {
    type: Number,
    default: 0
  },
  volumeLevel: {
    type: Number,
    default: 100
  },
  showPrevBtn: {
    type: Boolean,
    default: false
  },
  showNextBtn: {
    type: Boolean,
    default: false
  },
  nextEpisodeTitle: {
    type: String,
    default: ''
  },
  episodes: {
    type: Array as () => Array<{ play_title?: string; episode_num?: number; id?: number | string; vid?: string }>,
    default: () => []
  },
  currentEpisodeIndex: {
    type: Number,
    default: -1
  },
  playbackRate: {
    type: Number,
    default: 1.0
  },
  isBuffering: {
    type: Boolean,
    default: false
  },
  isResolving: {
    type: Boolean,
    default: false
  },
  autoPlay: {
    type: Boolean,
    default: true
  },
  // 基础信息（平台/年份/地区/集数/评分）
  seriesInfo: {
    type: Object as () => {
      platformName?: string
      platformBadge?: string
      year?: number | string
      area?: string
      updatedEpisodes?: number
      totalEpisodes?: number
      score?: number | string
      isMovie?: boolean
    } | null,
    default: null
  },
  // 收藏 / 追剧
  isBookmarked: {
    type: Boolean,
    default: false
  },
  isFollowed: {
    type: Boolean,
    default: false
  },
  showFollowBtn: {
    type: Boolean,
    default: false
  },
  isEpisodesOpen: {
    type: Boolean,
    default: false
  },
  // TV 模式下强制显示控件（焦点在控件上时）
  forceVisible: {
    type: Boolean,
    default: false
  },
  // 详情数据
  description: {
    type: String,
    default: ''
  },
  directors: {
    type: Array as () => string[],
    default: () => []
  },
  actors: {
    type: Array as () => string[],
    default: () => []
  },
  tags: {
    type: Array as () => string[],
    default: () => []
  },
  // iframe 嵌入模式：跨域 iframe 无法控制播放/进度/音量，隐藏底部栏和进度条
  iframeMode: {
    type: Boolean,
    default: false
  }
})

// Emits
const emit = defineEmits([
  'back',
  'episodes',
  'close-episodes',
  'detail-change',
  'prev',
  'next',
  'toggle-play',
  'toggle-mute',
  'toggle-fullscreen',
  'seek',
  'volume-change',
  'select-episode',
  'speed-change',
  'toggle-auto-play',
  'bookmark',
  'follow'
])

// 状态
const controlsVisible = ref(true)
const topBarVisible = ref(true)
const bottomBarVisible = ref(true)
const progressBarRef = ref<HTMLElement | null>(null)

// 详情面板
const showDetail = ref(false)
const activeDetailTab = ref('intro')
const detailTabs = [
  { key: 'intro', label: '简介' },
  { key: 'actors', label: '演员' },
  { key: 'tags', label: '标签' }
]
function openEpisodes() {
  // 打开选集面板时关闭详情面板（互斥）
  showDetail.value = false
  emit('episodes')
}

function toggleDetail() {
  showDetail.value = !showDetail.value
  emit('detail-change', showDetail.value)
  if (showDetail.value) {
    // 打开详情面板时关闭选集面板（互斥）
    emit('close-episodes')
    // 显示控件并暂停自动隐藏
    controlsVisible.value = true
    clearHideControlsTimer()
  }
}

// 音量滑块显示状态
const showVolumeSlider = ref(false)
let hideVolumeTimer: ReturnType<typeof setTimeout> | null = null

// 倍速相关
const speedRates = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]
const showSpeedMenu = ref(false)
let hideSpeedTimer: ReturnType<typeof setTimeout> | null = null

function toggleSpeedMenu() {
  showSpeedMenu.value = !showSpeedMenu.value
}

function closeSpeedMenu() {
  hideSpeedTimer = setTimeout(() => {
    showSpeedMenu.value = false
  }, 200)
}

function cancelSpeedHide() {
  if (hideSpeedTimer) {
    clearTimeout(hideSpeedTimer)
    hideSpeedTimer = null
  }
}

function setSpeed(rate: number) {
  emit('speed-change', rate)
  showSpeedMenu.value = false
}

// 时间格式化：秒 → MM:SS（精确到秒，不要小数点）
function formatTime(seconds: number): string {
  if (!seconds || isNaN(seconds)) return '00:00'
  const secs = Math.round(seconds)
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  const s = secs % 60
  if (h > 0) {
    return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  }
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

// 快进/快退提示状态
const showSeekIndicator = ref(false)
const seekDirection = ref<'seek-forward' | 'seek-backward'>('seek-forward')
const seekAmount = ref(10)

// 音量变化提示状态
const showVolumeIndicator = ref(false)

// 自动隐藏计时器
let hideControlsTimer: ReturnType<typeof setTimeout> | null = null
let topBarTimer: ReturnType<typeof setTimeout> | null = null
let bottomBarTimer: ReturnType<typeof setTimeout> | null = null

// 自动隐藏控件
function startHideControlsTimer() {
  // 非播放状态（暂停/缓冲/加载中）不自动隐藏
  if (!props.isPlaying || props.forceVisible) return
  clearHideControlsTimer()
  hideControlsTimer = setTimeout(() => {
    if (!props.forceVisible) {
      controlsVisible.value = false
    }
  }, 3000)
}

function clearHideControlsTimer() {
  if (hideControlsTimer) {
    clearTimeout(hideControlsTimer)
    hideControlsTimer = null
  }
}

// 显示/隐藏顶部栏
function toggleTopBar(show: boolean) {
  topBarVisible.value = show
  // TV 模式下不在播放中不自动隐藏
  if (show && (props.isPlaying || !deviceStore.isTV)) {
    clearTopBarTimer()
    topBarTimer = setTimeout(() => {
      if (!props.forceVisible) {
        topBarVisible.value = false
      }
    }, 3000)
  }
}

function clearTopBarTimer() {
  if (topBarTimer) {
    clearTimeout(topBarTimer)
    topBarTimer = null
  }
}

// 显示/隐藏底部栏
function toggleBottomBar(show: boolean) {
  bottomBarVisible.value = show
  // TV 模式下不在播放中不自动隐藏
  if (show && (props.isPlaying || !deviceStore.isTV)) {
    clearBottomBarTimer()
    bottomBarTimer = setTimeout(() => {
      if (!props.forceVisible) {
        bottomBarVisible.value = false
      }
    }, 3000)
  }
}

function clearBottomBarTimer() {
  if (bottomBarTimer) {
    clearTimeout(bottomBarTimer)
    bottomBarTimer = null
  }
}

// 播放/暂停
function togglePlay() {
  emit('toggle-play')
}

// 静音
function toggleMute() {
  emit('toggle-mute')
}

// 音量滑块
function onVolumeInput(e: Event) {
  const target = e.target as HTMLInputElement
  const vol = parseFloat(target.value)
  emit('volume-change', vol)
}

function showVolume() {
  showVolumeSlider.value = true
  if (hideVolumeTimer) clearTimeout(hideVolumeTimer)
}

function hideVolume() {
  hideVolumeTimer = setTimeout(() => {
    showVolumeSlider.value = false
  }, 300)
}

function onVolumeEnter() {
  if (hideVolumeTimer) clearTimeout(hideVolumeTimer)
  showVolumeSlider.value = true
}

function onVolumeLeave() {
  hideVolume()
}

// 进度条相关
const playedPercent = computed(() => {
  return props.duration ? (props.currentTime / props.duration) * 100 : 0
})

// 点击进度条跳转
function seek(event: MouseEvent) {
  if (!progressBarRef.value || !props.duration) return

  const rect = progressBarRef.value.getBoundingClientRect()
  const x = event.clientX - rect.left
  const percent = x / rect.width
  const newTime = percent * props.duration

  emit('seek', newTime)
}

function showSeekIndicatorFunc(direction: 'seek-forward' | 'seek-backward') {
  seekDirection.value = direction
  showSeekIndicator.value = true
  clearHideControlsTimer()
  // 非播放状态不启动隐藏计时器
  if (props.isPlaying && !props.forceVisible) {
    startHideControlsTimer()
  }

  setTimeout(() => {
    showSeekIndicator.value = false
  }, 1000)
}

// 显示音量变化提示
function showVolumeIndicatorFunc() {
  showVolumeIndicator.value = true
  clearHideControlsTimer()
  // 非播放状态不启动隐藏计时器
  if (props.isPlaying && !props.forceVisible) {
    startHideControlsTimer()
  }

  setTimeout(() => {
    showVolumeIndicator.value = false
  }, 1000)
}

// 监听播放状态变化
watch(() => props.isPlaying, (playing) => {
  if (playing && !props.forceVisible) {
    // 只有播放中才自动隐藏控件
    startHideControlsTimer()
  } else {
    // 暂停 / 缓冲 / 加载中：始终显示控件
    controlsVisible.value = true
    clearHideControlsTimer()
  }
})

// 缓冲 / 解析中也保持显示；结束后如果正在播放则恢复自动隐藏
watch(() => [props.isBuffering, props.isResolving], () => {
  if (props.isBuffering || props.isResolving) {
    controlsVisible.value = true
    clearHideControlsTimer()
  } else if (props.isPlaying && !props.forceVisible) {
    // 缓冲/解析结束，且正在播放 → 重新启动自动隐藏
    startHideControlsTimer()
  }
})

// TV 焦点在控件上时强制显示
// 使用 flush: 'sync' 同步触发，避免异步间隙导致 controlsVisible 短暂为 false
watch(() => props.forceVisible, (visible) => {
  if (visible) {
    controlsVisible.value = true
    topBarVisible.value = true
    bottomBarVisible.value = true
    clearHideControlsTimer()
  } else if (props.isPlaying) {
    // 焦点离开控件区且正在播放 → 重新启动自动隐藏
    startHideControlsTimer()
  }
}, { flush: 'sync' })

// 面板关闭时同步恢复控件可见性
// 面板打开时 forceVisible 为 true，controlsVisible 已为 true
// 面板关闭时 forceVisible 可能仍为 true（焦点回到 top-bar），watch(forceVisible) 不触发
// 但此时需要确保 controlsVisible/topBarVisible/bottomBarVisible 为 true，否则焦点样式被 opacity:0 隐藏
watch(showDetail, (open) => {
  if (!open) {
    controlsVisible.value = true
    topBarVisible.value = true
    bottomBarVisible.value = true
    clearHideControlsTimer()
  }
}, { flush: 'sync' })

watch(() => props.isEpisodesOpen, (open) => {
  if (!open) {
    controlsVisible.value = true
    topBarVisible.value = true
    bottomBarVisible.value = true
    clearHideControlsTimer()
  }
}, { flush: 'sync' })

// 键盘事件处理
function handleKeyDown(event: KeyboardEvent) {
  // TV 模式下，方向键和 Enter 由播放页的 TV 焦点系统统一处理
  // 这里只处理非 TV 模式下的键盘快捷键
  if (deviceStore.isTV) {
    // TV 模式下仅处理 Escape（全屏退出）
    if (event.key === 'Escape' && props.isFullscreen) {
      event.preventDefault()
      emit('toggle-fullscreen')
    }
    return
  }

  switch (event.key) {
    case ' ':
    case 'Enter':
      event.preventDefault()
      togglePlay()
      break

    case 'ArrowLeft':
      event.preventDefault()
      emit('seek', props.currentTime - 10)
      showSeekIndicatorFunc('seek-backward')
      break

    case 'ArrowRight':
      event.preventDefault()
      emit('seek', props.currentTime + 10)
      showSeekIndicatorFunc('seek-forward')
      break

    // ArrowUp/ArrowDown 留给 TV 端走焦，不控制音量
    // 音量由遥控器音量键 / 系统控制

    case 'Escape':
      event.preventDefault()
      if (props.isFullscreen) {
        emit('toggle-fullscreen')
      }
      break
  }
}

// 鼠标/触摸事件处理
function handleMouseMove() {
  controlsVisible.value = true
  // 只有播放中（且非 TV 模式）才启动自动隐藏计时器
  if (props.isPlaying && !props.forceVisible && !deviceStore.isTV) {
    startHideControlsTimer()
  }
}

onMounted(() => {
  // 添加事件监听
  window.addEventListener('keydown', handleKeyDown)
  document.addEventListener('mousemove', handleMouseMove)
})

onUnmounted(() => {
  // 清理事件监听
  window.removeEventListener('keydown', handleKeyDown)
  document.removeEventListener('mousemove', handleMouseMove)

  // 清理计时器
  clearHideControlsTimer()
  clearTopBarTimer()
  clearBottomBarTimer()
  if (hideSpeedTimer) clearTimeout(hideSpeedTimer)
})
</script>
<style lang="scss" scoped>
.native-player-controls {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  background: linear-gradient(to bottom,
    rgba(0, 0, 0, 0.7) 0%,
    rgba(0, 0, 0, 0) 20%,
    rgba(0, 0, 0, 0) 100%);
  pointer-events: none;
  z-index: 10;

  // TV 端关闭子像素抗锯齿，使用灰度平滑，文字不发虚
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;

  &.controls-hidden {
    opacity: 0;
    transition: opacity 0.3s ease;
  }
}

/* 顶部信息栏 */
.top-bar {
  display: flex;
  align-items: center;
  padding: 10px 16px;
  gap: 10px;
  flex-shrink: 0;
  transition: transform 0.3s ease, opacity 0.3s ease;
  pointer-events: auto;

  &.bar-hidden {
    transform: translateY(-100%);
    opacity: 0;
  }
}

.back-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  padding: 0;
  margin: 0;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 8px;
  color: #c0c0c0;
  cursor: pointer;
  flex-shrink: 0;
  font-size: 14px;

  &:hover {
    background: rgba(255, 255, 255, 0.12);
    color: #e6e6e6;
  }
}

.play-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--gold, #f59e0b);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 20vw;
  flex-shrink: 1;
  min-width: 0;
}

/* 下一集标题按钮 */
.next-episode-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 6px;
  color: #d0d0d0;
  font-size: 13px;
  cursor: pointer;
  flex-shrink: 0;
  max-width: 240px;
  transition: background 0.2s ease, color 0.2s ease;

  &:hover {
    background: rgba(245, 158, 11, 0.15);
    border-color: rgba(245, 158, 11, 0.4);
    color: var(--gold, #f59e0b);
  }
}
.next-episode-label {
  color: #a0a0a0;
  font-size: 12px;
  flex-shrink: 0;
}
.next-episode-title {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex-shrink: 1;
  min-width: 0;
}

/* 顶部左侧操作按钮区 */
.top-bar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

/* 顶部右侧区域（基础信息，居右） */
.top-bar-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  flex-wrap: wrap;
  justify-content: flex-end;
}

/* 基础信息项（直接放在 top-bar-right 中） */
.top-bar-right .meta-item,
.top-bar-right .meta-platform,
.top-bar-right .meta-score {
  font-size: 13px;
  color: #d0d0d0;
  white-space: nowrap;
}
.meta-score { color: var(--gold, #f59e0b); font-weight: 600; }
.meta-platform {
  display: inline-block;
  padding: 2px 8px;
  font-size: 12px;
  font-weight: 500;
  border-radius: 4px;
  color: #e6e6e6;
  border: 1px solid rgba(255, 255, 255, 0.2);
  letter-spacing: 0.5px;
}

/* 操作按钮（收藏/追剧/选集/详情） */
.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 8px 14px;
  margin: 0;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  color: #c0c0c0;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
  line-height: 1;
  flex-shrink: 0;

  &:hover {
    background: rgba(255, 255, 255, 0.12);
    color: #e6e6e6;
  }

  &.active {
    background: rgba(245, 158, 11, 0.2);
    border-color: var(--gold, #f59e0b);
    color: var(--gold, #f59e0b);
  }
}

/* 详情面板（避开顶部/底部栏） */
.detail-overlay {
  position: absolute;
  top: 56px;
  left: 0;
  right: 0;
  bottom: 100px;
  background: rgba(0, 0, 0, 0.5);
  z-index: 20;
  pointer-events: auto;
}
.detail-panel {
  position: absolute;
  top: 0;
  left: 0;
  bottom: 0;
  width: 33vw;
  display: flex;
  flex-direction: column;
  background: rgba(20, 20, 24, 0.96);
  border-right: 1px solid rgba(255, 255, 255, 0.1);
  overflow: hidden;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}
.detail-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  flex-shrink: 0;
}
.detail-tabs {
  display: flex;
  gap: 4px;
}
.detail-tab {
  padding: 6px 14px;
  font-size: 14px;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: #b0b0b0;
  cursor: pointer;
  font-weight: 500;
  &.active { background: var(--gold, #f59e0b); color: #000; }
}
.detail-close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  background: rgba(255, 255, 255, 0.06);
  border: none;
  border-radius: 6px;
  color: #b0b0b0;
  cursor: pointer;
  &:hover { background: rgba(255, 255, 255, 0.12); color: #e6e6e6; }
}
.detail-panel-body {
  padding: 14px 16px;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}
.detail-description {
  font-size: 14px;
  line-height: 1.7;
  color: #d9d9d9;
  margin: 0;
  white-space: pre-wrap;
}
.detail-section { margin-bottom: 14px; }
.detail-section-title { font-size: 14px; color: #e6e6e6; margin: 0 0 8px 0; font-weight: 600; }
.detail-tag-list { display: flex; flex-wrap: wrap; gap: 8px; }
.detail-tag {
  padding: 6px 14px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  font-size: 13px;
  color: #d0d0d0;
}
.detail-empty { color: #909090; font-size: 14px; text-align: center; padding: 24px 0; }

/* 详情面板入场动画（遮罩淡入，面板从左侧滑入） */
.slide-detail-enter-active, .slide-detail-leave-active {
  transition: opacity 0.25s ease;
}
.slide-detail-enter-active .detail-panel,
.slide-detail-leave-active .detail-panel {
  transition: transform 0.25s ease;
}
.slide-detail-enter-from, .slide-detail-leave-to {
  opacity: 0;
}
.slide-detail-enter-from .detail-panel,
.slide-detail-leave-to .detail-panel {
  transform: translateX(-100%);
}

/* 中央控制区域 */
.center-controls {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  justify-content: center;
  align-items: center;
  pointer-events: none;
  z-index: 5;
}

.seek-indicator {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 500;
  pointer-events: none;

  &.seek-forward {
    transform: translate(-50%, -50%);
  }

  &.seek-backward {
    transform: translate(-50%, -50%);
  }
}

.volume-indicator {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 8px;
  pointer-events: none;

  svg {
    width: 24px;
    height: 24px;
  }

  .volume-bar {
    width: 80px;
    height: 4px;
    background: rgba(255, 255, 255, 0.2);
    border-radius: 2px;
    overflow: hidden;

    .volume-fill {
      height: 100%;
      background: var(--gold, #f59e0b);
      transition: width 0.2s ease;
    }
  }
}

/* 底部控制栏 */
.bottom-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px 44px; /* 底部 padding 为进度条留出空间 */
  background: linear-gradient(to top, rgba(0, 0, 0, 0.7), rgba(0, 0, 0, 0.3));
  flex-shrink: 0;
  transition: transform 0.3s ease, opacity 0.3s ease;
  pointer-events: auto;

  &.bar-hidden {
    transform: translateY(100%);
    opacity: 0;
  }
}

.bottom-bar-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.bottom-bar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 底部区域弹性撑开器 */
.flex-spacer {
  flex: 1;
}

/* 进度条容器（始终常显，独立于控件自动隐藏层） */
.native-progress-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 16px 8px;
  background: rgba(0, 0, 0, 0.6);
  z-index: 11;
  pointer-events: auto;
}

.time-display {
  font-size: 16px;
  color: #e6e6e6;
  min-width: 120px;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
  font-weight: 500;
}

.progress-bar {
  flex: 1;
  height: 4px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  position: relative;
  cursor: pointer;
  transition: opacity 0.5s ease;

  &.bar-dimmed {
    opacity: 0.35;
  }

  .progress-buffer {
    position: absolute;
    top: 0;
    left: 0;
    height: 100%;
    background: rgba(255, 255, 255, 0.2);
  }

  .progress-played {
    position: absolute;
    top: 0;
    left: 0;
    height: 100%;
    background: var(--gold, #f59e0b);
  }

  .progress-handle {
    position: absolute;
    top: 50%;
    transform: translate(-50%, -50%);
    width: 12px;
    height: 12px;
    background: white;
    border-radius: 50%;
    box-shadow: 0 0 4px rgba(0, 0, 0, 0.3);
    opacity: 0;
    transition: opacity 0.2s ease;
  }

  &:hover .progress-handle {
    opacity: 1;
  }
}

/* 倍速按钮和弹出菜单 */
.speed-wrapper {
  position: relative;
}

.speed-btn {
  width: auto !important;
  min-width: 40px;
  padding: 0 8px !important;
  border-radius: 8px !important;
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.5px;
}

.speed-popup {
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  margin-bottom: 6px;
  display: flex;
  flex-direction: column;
  gap: 0;
  padding: 4px 0;
  background: rgba(20, 20, 20, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 8px;
  z-index: 20;
  overflow: hidden;
}

.speed-item {
  display: block;
  width: 100%;
  padding: 5px 20px;
  background: transparent;
  border: none;
  color: #b0b0b0;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  text-align: center;
  transition: all 0.15s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.08);
    color: #fff;
  }

  &.active {
    color: var(--gold, #f59e0b);
  }
}


.control-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  padding: 0;
  margin: 0;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 50%;
  color: #c0c0c0;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.12);
    color: #e6e6e6;
  }

  &.play-pause-btn {
    width: 48px;
    height: 48px;
  }

  &.volume-btn {
    &:hover {
      background: rgba(255, 255, 255, 0.12);
    }
  }

  &.fullscreen-btn {
    &:hover {
      background: rgba(255, 255, 255, 0.12);
    }
  }

  &.auto-play-btn {
    width: auto;
    padding: 0 14px;
    font-size: 13px;
    border-radius: 18px;

    &.active {
      background: rgba(245, 158, 11, 0.2);
      border-color: var(--gold, #f59e0b);
      color: var(--gold, #f59e0b);
    }
  }
}

/* 音量容器和滑块 */
.volume-wrapper {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.volume-slider-popup {
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  margin-bottom: 8px;
  padding: 12px 8px;
  background: rgba(0, 0, 0, 0.85);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 8px;
  z-index: 20;
}

.volume-range {
  writing-mode: vertical-lr;
  direction: rtl;
  width: 16px;
  height: 100px;
  appearance: none;
  -webkit-appearance: none;
  // 用 background 画居中轨道（4px 宽，位于 16px 容器的正中间）
  background: linear-gradient(
    to right,
    transparent 6px,
    rgba(255, 255, 255, 0.2) 6px,
    rgba(255, 255, 255, 0.2) 10px,
    transparent 10px
  );
  cursor: pointer;
  margin: 4px 0;
  border-radius: 0;
  border: none;

  &:focus {
    outline: none;
  }

  // 隐藏浏览器默认轨道
  &::-webkit-slider-runnable-track {
    -webkit-appearance: none;
    background: transparent;
    border: none;
  }

  &::-moz-range-track {
    background: transparent;
    border: none;
  }

  // 滑块圆点
  &::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 16px;
    height: 16px;
    background: var(--gold, #f59e0b);
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-radius: 50%;
    cursor: pointer;
    margin: 0;
  }

  &::-moz-range-thumb {
    width: 16px;
    height: 16px;
    background: var(--gold, #f59e0b);
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-radius: 50%;
    cursor: pointer;
  }
}

/* 动画 */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

/* ==================== TV 焦点样式 ==================== */
/* TV 遥控器焦点高亮：金色边框 + 放大 */
[data-tv-focus] {
  outline: none;
  -webkit-tap-highlight-color: transparent;
  transition: box-shadow 0.15s ease, transform 0.15s ease, background 0.15s ease;
}

[data-tv-focus].tv-player-focus {
  box-shadow: 0 0 0 3px var(--gold, #f59e0b), 0 0 16px rgba(245, 158, 11, 0.4);
  transform: scale(1.08);
  z-index: 100;
  background: rgba(245, 158, 11, 0.15) !important;
  border-color: var(--gold, #f59e0b) !important;
  color: var(--gold, #f59e0b) !important;
}

/* 圆形按钮聚焦时保持圆形 */
.control-btn.tv-player-focus {
  box-shadow: 0 0 0 3px var(--gold, #f59e0b), 0 0 16px rgba(245, 158, 11, 0.4);
}

/* 倍速弹出菜单项的 TV 焦点 */
.speed-item.tv-player-focus {
  background: rgba(245, 158, 11, 0.2);
  color: var(--gold, #f59e0b);
}

</style>
