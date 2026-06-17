<template>
  <div class="play-page" :class="{ 'fullscreen': isFullscreen }">
    <!-- 加载中 -->
    <div v-if="store.isLoading" class="play-loading">
      <div class="spinner"></div>
      <span>加载中...</span>
    </div>

    <!-- 播放内容 -->
    <template v-else-if="store.series">
      <!-- 工具栏 (playbar) - 置于顶层 -->
      <div :class="['play-toolbar', { 'toolbar-hidden': isLandscape ? !landscapeToolbarVisible : false }]">
        <div class="play-toolbar-top">
          <button class="back-btn" @click="goBack">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5"/><path d="M12 19l-7-7 7-7"/></svg>
          </button>
          <span class="play-title">{{ store.playTitle }}</span>
          <button v-if="store.episodes.length > 0" class="episodes-btn" @click="showEpisodes = !showEpisodes">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
            <span>分集</span>
          </button>
        </div>
        <div class="play-toolbar-bottom">
          <div class="play-info">
            <span class="source-label">解析源</span>
            <select class="source-select" :value="store.selectedSourceKey" @change="onSourceChange(($event.target as HTMLSelectElement).value)">
              <option
                v-for="source in store.parseSources"
                :key="source.key"
                :value="source.key"
              >
                {{ source.name }}
              </option>
            </select>
            <span class="source-tip">播放卡顿或者失败，请点击右侧刷新或切换解析源！</span>
          </div>
          <div class="play-actions">
            <button class="toolbar-btn" @click="refreshIframe">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 2v6h-6"/><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M3 22v-6h6"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/></svg>
              <span>刷新</span>
            </button>
          </div>
        </div>
      </div>

      <!-- 播放区域 -->
      <div class="play-container">
        <!-- 透明触摸层：iframe 会吞掉点击，需要这个层来切换工具栏显示隐藏 -->
        <div class="play-touch-layer" @click="onPlayAreaClick"></div>
        <iframe
          v-if="store.fullPlayUrl"
          ref="iframeRef"
          :src="store.fullPlayUrl"
          frameborder="0"
          allowfullscreen
          allow="autoplay; encrypted-media; fullscreen"
          sandbox="allow-same-origin allow-scripts allow-popups allow-forms allow-popups-to-escape-sandbox"
          @error="onIframeError"
        ></iframe>

        <!-- 加载失败 -->
        <div v-if="showFallback" class="play-fallback">
          <div class="fallback-content">
            <span class="fallback-icon">⚠️</span>
            <p class="fallback-text">加载失败，请点击右上角刷新或切换解析源</p>
          </div>
        </div>

        <!-- 分集列表面板 -->
        <div v-if="showEpisodes" :class="['episodes-panel', isLandscape ? 'panel-landscape' : 'panel-portrait']" @click.self="showEpisodes = false">
          <div class="episodes-panel-inner">
            <div class="episodes-panel-header">
              <span class="episodes-panel-title">{{ store.series?.title }}</span>
              <button class="episodes-close-btn" @click="showEpisodes = false">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6L6 18"/><path d="M6 6l12 12"/></svg>
              </button>
            </div>
            <div class="episodes-panel-body">
              <button
                v-for="(ep, index) in store.episodes"
                :key="ep.id || ep.vid || 'ep' + index"
                :class="['ep-panel-item', { active: isActiveEpisode(ep) }]"
                @click="selectEpisode(ep)"
              >
                <span class="ep-num">{{ ep.play_title || `第${ep.episode_num}集` }}</span>
                <span v-if="ep.is_vip === 1" class="ep-vip-tag">VIP</span>
                <span v-else-if="ep.is_vip === 2" class="ep-vip-tag ppv">点播</span>
              </button>
              <div v-if="store.episodes.length === 0" class="ep-panel-empty">暂无分集</div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- 剧集不存在 -->
    <div v-else class="play-empty">
      <span class="empty-icon">📭</span>
      <h2>剧集不存在</h2>
      <p>找不到您要查看的剧集</p>
      <button class="back-home-btn" @click="goHome">返回首页</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { usePlayStore } from '@/stores/play'
import { useThemeStore } from '@/stores/theme'
import { usePlayerState } from '@/composables/usePlayerState'
import { useUserStore } from '@/stores/user'
import { updateWatchHistory, type Episode } from '@/utils/api'

const router = useRouter()
const route = useRoute()
const store = usePlayStore()
const themeStore = useThemeStore()
const userStore = useUserStore()
const { setPlaying } = usePlayerState()

const iframeRef = ref<HTMLIFrameElement | null>(null)
const showFallback = ref(false)
const showEpisodes = ref(false)

// 全屏状态
const isFullscreen = ref(false)

// 横屏检测
const isLandscape = ref(false)
// 横屏时工具栏是否可见（竖屏始终可见）
const landscapeToolbarVisible = ref(false)
// 横屏工具栏自动隐藏定时器
let landscapeToolbarTimer: ReturnType<typeof setTimeout> | null = null

function checkLandscape() {
  const newVal = window.matchMedia('(orientation: landscape)').matches
  if (isLandscape.value !== newVal) {
    isLandscape.value = newVal
    onOrientationChange(newVal)
  }
}

function onMatchMediaChange(e: MediaQueryListEvent) {
  isLandscape.value = e.matches
  onOrientationChange(e.matches)
}

function onOrientationChange(landscape: boolean) {
  if (landscape) {
    // 横屏：默认隐藏工具栏，3秒后自动隐藏
    landscapeToolbarVisible.value = false
    showLandscapeToolbarTemporarily()
  } else {
    // 竖屏：始终显示工具栏
    landscapeToolbarVisible.value = true
    clearLandscapeTimer()
  }
}

// 横屏时短暂显示工具栏（3秒后自动隐藏）
function showLandscapeToolbarTemporarily() {
  clearLandscapeTimer()
  landscapeToolbarVisible.value = true
  landscapeToolbarTimer = setTimeout(() => {
    if (isLandscape.value) {
      landscapeToolbarVisible.value = false
    }
  }, 3000)
}

function clearLandscapeTimer() {
  if (landscapeToolbarTimer) {
    clearTimeout(landscapeToolbarTimer)
    landscapeToolbarTimer = null
  }
}

// 点击播放区域：横屏时切换工具栏显示/隐藏
function onPlayAreaClick() {
  if (isLandscape.value) {
    if (landscapeToolbarVisible.value) {
      landscapeToolbarVisible.value = false
    } else {
      showLandscapeToolbarTemporarily()
    }
  }
}

function isActiveEpisode(ep: Episode) {
  const aid = store.activeEpisodeId
  return (ep.id && ep.id === aid) || (ep.vid && ep.vid === aid)
}

function selectEpisode(ep: Episode) {
  showEpisodes.value = false
  showFallback.value = false
  store.playEpisode(ep)

  // 记录观看历史
  if (userStore.isLoggedIn && userStore.user?.id && store.series?.id) {
    updateWatchHistory({
      user_id: userStore.user.id,
      series_id: store.series.id,
      episode_id: ep.id
    }).catch(error => {
      console.error('Failed to update watch history:', error)
    })
  }
}

function onSourceChange(key: string) {
  showFallback.value = false
  store.setSourceKey(key)
}

function onIframeError() {
  showFallback.value = true
}

function refreshIframe() {
  if (iframeRef.value) {
    showFallback.value = false
    const currentSrc = iframeRef.value.src
    iframeRef.value.src = ''
    requestAnimationFrame(() => {
      if (iframeRef.value) {
        iframeRef.value.src = currentSrc
      }
    })
  }
}

// 切换全屏
function toggleFullscreen() {
  if (!document.fullscreenElement) {
    // 进入全屏
    document.documentElement.requestFullscreen().then(() => {
      isFullscreen.value = true
    }).catch(err => {
      console.error('Failed to enter fullscreen:', err)
    })
  } else {
    // 退出全屏
    document.exitFullscreen().then(() => {
      isFullscreen.value = false
    }).catch(err => {
      console.error('Failed to exit fullscreen:', err)
    })
  }
}

// 监听全屏状态变化
function onFullscreenChange() {
  isFullscreen.value = !!document.fullscreenElement
}

function goBack() {
  if (store.series?.cid) {
    router.push(`/detail/${store.series.cid}`)
  } else {
    router.push('/')
  }
}

function goHome() {
  router.push('/')
}

// 监听播放状态
watch(() => store.isPlaying, (playing) => {
  setPlaying(playing)
})

// 切换分集时重置 fallback
watch(() => store.playUrl, () => {
  showFallback.value = false
})

// Esc 关闭分集面板或退出全屏
function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    if (showEpisodes.value) {
      showEpisodes.value = false
    } else if (document.fullscreenElement) {
      document.exitFullscreen()
    }
  }
}

onMounted(async () => {
  document.addEventListener('keydown', onKeydown)
  document.addEventListener('fullscreenchange', onFullscreenChange)

  // 初始化横屏检测
  checkLandscape()
  window.matchMedia('(orientation: landscape)').addEventListener('change', onMatchMediaChange)
  // 根据初始方向设置工具栏状态
  onOrientationChange(isLandscape.value)

  const cid = route.params.cid as string
  const epId = route.query.ep as string

  if (cid) {
    await store.loadPlayData(cid)
    // 彩色主题下根据当前剧集分类切换频道配色
    if (store.series?.category_key) {
      themeStore.setChannel(store.series.category_key)
    }

    // 如果指定了分集，自动播放
    if (epId && store.episodes.length > 0) {
      const ep = store.episodes.find(e => String(e.id) === epId || e.vid === epId)
      if (ep) {
        store.playEpisode(ep)
        return
      }
    }

    // 默认播放第一个正片
    const firstEp = store.episodes.find(ep => ep.episode_type === 0 && ep.play_url)
      ?? store.episodes.find(ep => ep.play_url)
    if (firstEp) {
      store.playEpisode(firstEp)
    }
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeydown)
  document.removeEventListener('fullscreenchange', onFullscreenChange)
  window.matchMedia('(orientation: landscape)').removeEventListener('change', onMatchMediaChange)
  clearLandscapeTimer()
  store.stop()
})
</script>

<style lang="scss" scoped>
.play-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  height: 100dvh;
  background: #000;
  overflow: hidden;
  position: fixed;
  inset: 0;
  // 竖屏：不占用状态栏，视频延伸到状态栏下方
  // 横屏：通过 JS 控制工具栏显示/隐藏
}

/* 横屏时占满全屏，工具栏浮动在顶部 */
@media (orientation: landscape) {
  .play-page {
    padding-top: 0;
  }
}

/* ==================== 工具栏 (playbar) ==================== */
.play-toolbar {
  display: flex;
  flex-direction: column;
  padding: 10px 16px;
  background: #141419;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  gap: 8px;
  transition: transform 0.4s ease, opacity 0.4s ease;
  position: absolute;
  top: var(--safe-area-inset-top, 0px);
  left: 0;
  right: 0;
  z-index: 100;
}

// 横屏时工具栏向下偏移，错开系统状态栏
// safe-area-inset-top 在横屏时通常为 0，这里硬偏移 24px 错开状态栏
@media (orientation: landscape) {
  .play-toolbar {
    top: 24px;
  }
}

.play-toolbar.toolbar-hidden {
  transform: translateY(-100%);
  opacity: 0;
  pointer-events: none;
}

.play-toolbar-top {
  display: flex;
  align-items: center;
  gap: 10px;
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
  color: rgba(255, 255, 255, 0.65);
  cursor: pointer;
  flex-shrink: 0;
  font-size: 14px;
}

.play-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--gold, #f59e0b);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
}

.play-toolbar-bottom {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.play-info {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  flex-wrap: wrap;
  flex: 1;
}

.source-label {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.5);
  white-space: nowrap;
  flex-shrink: 0;
}

.source-select {
  padding: 6px 26px 6px 12px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 6px;
  color: var(--gold, #f59e0b);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%23f59e0b' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 8px center;
  transition: all 0.2s ease;
  flex-shrink: 0;

  &:focus {
    outline: none;
    border-color: var(--gold, #f59e0b);
    box-shadow: 0 0 10px rgba(245, 158, 11, 0.2);
  }

  option {
    background: #141419;
    color: #fff;
  }
}

.source-tip {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.55);
  white-space: nowrap;
}

.play-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.toolbar-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 14px;
  margin: 0;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  color: rgba(255, 255, 255, 0.65);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
  line-height: 1;

  svg {
    flex-shrink: 0;
    width: 14px;
    height: 14px;
  }

  &:active {
    background: rgba(255, 255, 255, 0.2);
  }
}

/* ==================== 分集按钮 ==================== */
.episodes-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 14px;
  margin: 0;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 6px;
  color: rgba(255, 255, 255, 0.65);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
  line-height: 1;
  flex-shrink: 0;

  svg {
    width: 14px;
    height: 14px;
  }
}

/* ==================== 播放区域 ==================== */
.play-container {
  flex: 1;
  position: relative;
  overflow: hidden;
  background: #000;
}

.play-touch-layer {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 50%;
  z-index: 50;
  background: transparent;
  cursor: pointer;
}

.play-container iframe {
  width: 100%;
  height: 100%;
  border: none;
  display: block;
  position: absolute;
  inset: 0;
}

/* ==================== 加载失败 ==================== */
.play-fallback {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.85);
  z-index: 10;
}

.fallback-content {
  text-align: center;
  padding: 40px;
}

.fallback-icon {
  font-size: 48px;
  display: block;
  margin-bottom: 16px;
}

.fallback-text {
  font-size: 15px;
  color: rgba(255, 255, 255, 0.6);
  margin-bottom: 24px;
  line-height: 1.6;
}

.fallback-btn {
  padding: 12px 28px;
  background: linear-gradient(135deg, #fbbf24, #d97706);
  border: none;
  border-radius: 24px;
  color: #000;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  margin: 0;
}

/* ==================== 分集列表面板 ==================== */
.episodes-panel {
  position: absolute;
  inset: 0;
  z-index: 100;
  background: rgba(0, 0, 0, 0.6);
  animation: fadeIn 0.2s ease;
}

/* 竖屏：从底部弹出，横向占满 */
.episodes-panel.panel-portrait {
  display: flex;
  align-items: flex-end;
  justify-content: stretch;

  .episodes-panel-inner {
    width: 100%;
    max-height: 70vh;
    background: #1a1a20;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px 16px 0 0;
    border-left: none;
    display: flex;
    flex-direction: column;
    animation: slideUp 0.25s ease;
  }
}

/* 横屏：从右侧弹出，纵向占满 */
.episodes-panel.panel-landscape {
  display: flex;
  align-items: stretch;
  justify-content: flex-end;

  .episodes-panel-inner {
    width: 320px;
    max-width: 45vw;
    height: 100%;
    background: #1a1a20;
    border-left: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 0;
    display: flex;
    flex-direction: column;
    animation: slideInRight 0.25s ease;
  }
}

.episodes-panel-inner {
  display: flex;
  flex-direction: column;
}

.episodes-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  flex-shrink: 0;
}

.episodes-panel-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--gold, #f59e0b);
}

.episodes-close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  margin: 0;
  background: rgba(255, 255, 255, 0.06);
  border: none;
  border-radius: 6px;
  color: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  transition: all 0.2s ease;
}

.episodes-panel-body {
  flex: 1;
  padding: 12px 16px;
  overflow-y: auto;
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
  gap: 8px;
}

.ep-panel-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 10px 18px;
  margin: 0;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.85);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;

  &.active {
    background: rgba(251, 191, 36, 0.2);
    border-color: var(--gold, #f59e0b);
    color: var(--gold, #f59e0b);
  }
}

.ep-vip-tag {
  font-size: 10px;
  padding: 1px 4px;
  border-radius: 3px;
  background: rgba(251, 191, 36, 0.25);
  color: var(--gold, #f59e0b);

  &.ppv {
    background: rgba(239, 68, 68, 0.25);
    color: #f87171;
  }
}

.ep-panel-empty {
  width: 100%;
  text-align: center;
  padding: 60px 0;
  color: rgba(255, 255, 255, 0.3);
  font-size: 14px;
}

/* ==================== 加载与空状态 ==================== */
.play-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 16px;
  color: rgba(255, 255, 255, 0.5);
  font-size: 15px;
}

.spinner {
  width: 48px;
  height: 48px;
  border: 3px solid rgba(255, 255, 255, 0.1);
  border-top-color: var(--gold, #f59e0b);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.play-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 12px;
  color: rgba(255, 255, 255, 0.6);
}

.empty-icon {
  font-size: 64px;
  opacity: 0.5;
  margin-bottom: 8px;
}

.play-empty h2 {
  font-size: 22px;
  color: rgba(255, 255, 255, 0.8);
  margin: 0;
}

.play-empty p {
  font-size: 14px;
  margin: 0;
}

.back-home-btn {
  margin-top: 16px;
  padding: 10px 24px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  color: #fff;
  font-size: 14px;
  cursor: pointer;
}

/* ==================== 动画 ==================== */
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideInRight {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}

@keyframes slideUp {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}

/* ==================== 响应式 ==================== */
@media screen and (max-width: 750px) {
  .play-toolbar {
    padding: 8px 12px;
    gap: 8px;
  }

  .source-select {
    font-size: 13px;
    padding: 5px 24px 5px 10px;
  }

  .source-tip {
    font-size: 11px;
  }

  .toolbar-btn {
    padding: 5px 8px;
    font-size: 12px;
  }

  .episodes-btn {
    padding: 5px 8px;
    font-size: 12px;
  }
}
</style>
