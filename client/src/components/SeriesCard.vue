<template>
  <div
    :class="['series-card', layout]"
    @click="handleClick"
    tabindex="0"
    @touchstart="startLongPress"
    @touchend="cancelLongPress"
    @touchmove="checkMove"
    @touchcancel="cancelLongPress"
  >
    <div
      class="series-thumbnail-wrapper"
      @touchstart="startLongPress"
      @touchend="cancelLongPress"
      @touchmove="checkMove"
      @touchcancel="cancelLongPress"
    >
      <img
        class="series-thumbnail"
        :src="imageSrc"
        :alt="series.title"
        @error="handleImageError"
      />
      <!-- 左上角操作按钮组（PC端 hover 显示） -->
      <div class="cover-action-group" v-if="!isTV && !isMobile">
        <!-- 收藏按钮 -->
        <button
          :class="['bookmark-btn', { active: isBookmarked }]"
          @click.stop="handleBookmarkToggle"
          :title="isBookmarked ? '取消收藏' : '收藏'"
        >
          <svg viewBox="0 0 24 24" class="bookmark-icon">
            <path v-if="isBookmarked" fill="currentColor" d="M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 22 12 18.56 5.82 22 7 14.14l-5-4.87 6.91-1.01L12 2z"/>
            <path v-else fill="none" stroke="currentColor" stroke-width="1.8" d="M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 22 12 18.56 5.82 22 7 14.14l-5-4.87 6.91-1.01L12 2z"/>
          </svg>
          <span class="btn-text">{{ isBookmarked ? '已收藏' : '收藏' }}</span>
        </button>
        <!-- 追剧按钮（仅非电影且未完结） -->
        <button
          v-if="!isMovie && !isFinished"
          :class="['follow-btn', { active: isFollowed }]"
          @click.stop="handleFollowToggle"
          :title="isFollowed ? '取消追剧' : '追剧'"
        >
          <svg viewBox="0 0 24 24" class="follow-icon">
            <path v-if="isFollowed" fill="currentColor" d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
            <path v-else fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" d="M12 5v14M5 12h14"/>
          </svg>
          <span class="btn-text">{{ isFollowed ? '已追剧' : '追剧' }}</span>
        </button>
      </div>
      <!-- 移动端长按信息区遮罩 -->
      <div v-if="isMobile && showLongPressPanel" class="longpress-overlay" @click.stop="closeLongPress">
        <div class="longpress-panel" @click.stop>
          <div class="longpress-actions">
            <button
              :class="['longpress-action-btn', { active: isBookmarked }]"
              @click.stop="handleBookmarkToggle"
            >
              <svg viewBox="0 0 24 24" class="longpress-icon">
                <path v-if="isBookmarked" fill="currentColor" d="M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 22 12 18.56 5.82 22 7 14.14l-5-4.87 6.91-1.01L12 2z"/>
                <path v-else fill="none" stroke="currentColor" stroke-width="1.8" d="M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 22 12 18.56 5.82 22 7 14.14l-5-4.87 6.91-1.01L12 2z"/>
              </svg>
              <span class="btn-text">{{ isBookmarked ? '已收藏' : '收藏' }}</span>
            </button>
            <button
              v-if="!isMovie && !isFinished"
              :class="['longpress-action-btn', { active: isFollowed }]"
              @click.stop="handleFollowToggle"
            >
              <svg viewBox="0 0 24 24" class="longpress-icon">
                <path v-if="isFollowed" fill="currentColor" d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                <path v-else fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" d="M12 5v14M5 12h14"/>
              </svg>
              <span class="btn-text">{{ isFollowed ? '已追剧' : '追剧' }}</span>
            </button>
          </div>
        </div>
      </div>

      <!-- 右上角 VIP/免费标识 -->
      <span :class="['vip-badge', series.is_vip === 0 ? 'free' : 'vip']">
        {{ series.is_vip === 0 ? '免费' : 'VIP' }}
      </span>
      <!-- 已看集数 - 右下角 -->
      <div v-if="watchedCount > 0" class="watched-badge">
        <span>{{ watchedCount }}</span>
        <svg viewBox="0 0 24 24" class="watched-eye-icon">
          <path fill="currentColor" d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/>
        </svg>
      </div>
      <!-- 竖版模式：集数覆盖在封面底部 -->
      <div v-if="layout === 'vertical' && !isMovie && episodesCount" class="cover-episodes-badge">
        <span class="cover-ep-text">{{ episodesCount }}</span>
      </div>
      <!-- 横版模式：集数覆盖在封面右下角 -->
      <div v-if="layout === 'horizontal' && episodesCount" class="cover-episodes-badge">
        <span v-if="isMovie" class="cover-movie-tag">电影</span>
        <span v-else class="cover-ep-text">{{ episodesCount }}</span>
      </div>
    </div>
    <div class="series-info">
      <div class="series-row-1">
        <span class="series-title">{{ series.title }}</span>
        <span v-if="series.score" class="series-score">⭐ {{ series.score }}</span>
      </div>
      <div class="series-row-2">
        <span v-if="series.year" class="series-year">{{ series.year }}</span>
        <span v-if="tagsText" class="series-tags">{{ tagsText }}</span>
        <span v-if="isMovie && series.area" class="series-area">{{ series.area }}</span>
      </div>
      <div class="series-row-3">
        <span class="series-actors">{{ actorsText }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRouter } from 'vue-router'
import type { Series } from '@/utils/api'
import { getProxyImageUrl, parseActors, parseTags } from '@/utils/api'
import placeholderCard from '@/assets/placeholder_card.png'
import placeholderHero from '@/assets/placeholder_hero.png'
import { useDeviceStore } from '@/stores/device'

const router = useRouter()
const deviceStore = useDeviceStore()

const isTV = computed(() => deviceStore.isTV)
const isMobile = computed(() => deviceStore.isMobile)

// 长按逻辑（移动端）
const showLongPressPanel = ref(false)
const isLongPressed = ref(false)
let longPressTimer: ReturnType<typeof setTimeout> | null = null
const LONG_PRESS_DURATION = 2000
const MOVE_THRESHOLD = 10

let startX = 0
let startY = 0

// 滚动监听器，滑动页面时隐藏遮罩层
function handleScroll() {
  if (showLongPressPanel.value) {
    closeLongPress()
  }
}

onMounted(() => {
  if (isMobile.value) {
    document.addEventListener('scroll', handleScroll, { passive: true })
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('scroll', handleScroll)
})

function startLongPress(e: TouchEvent) {
  if (!isMobile.value) return
  isLongPressed.value = false
  const touch = e.touches[0]
  startX = touch.clientX
  startY = touch.clientY
  longPressTimer = setTimeout(() => {
    isLongPressed.value = true
    showLongPressPanel.value = true
  }, LONG_PRESS_DURATION)
}

function cancelLongPress() {
  if (longPressTimer) {
    clearTimeout(longPressTimer)
    longPressTimer = null
  }
}

function checkMove(e: TouchEvent) {
  const touch = e.touches[0]
  const dx = Math.abs(touch.clientX - startX)
  const dy = Math.abs(touch.clientY - startY)
  if (dx > MOVE_THRESHOLD || dy > MOVE_THRESHOLD) {
    cancelLongPress()
  }
}

function closeLongPress() {
  showLongPressPanel.value = false
  isLongPressed.value = false
}

const props = withDefaults(defineProps<{
  series: Series
  watchedCount?: number
  isFollowed?: boolean
  isBookmarked?: boolean
  layout?: 'vertical' | 'horizontal'
}>(), {
  watchedCount: 0,
  isFollowed: false,
  isBookmarked: false,
  layout: 'vertical'
})

const episodesCount = computed(() => {
  const total = props.series.total_episodes || 0
  const updated = props.series.updated_episodes || 0
  if (!total) return ''
  if (updated > 0 && updated < total) return `更新至${updated}集/共${total}集`
  return `共${total}集`
})

const emit = defineEmits<{
  'toggle-follow': [seriesId: number]
  'toggle-bookmark': [seriesId: number]
}>()

const imageSrc = ref('')
const hasError = ref(false)

const actorsText = computed(() => {
  if (!props.series.actors) return ''
  const actors = parseActors(props.series.actors)
  return actors.join('、')
})

const tagsText = computed(() => {
  if (!props.series.tags) return ''
  const tags = parseTags(props.series.tags)
  return tags.slice(0, 3).join(' / ')
})

const isFinished = computed(() => props.series.is_finished === 1)

const isMovie = computed(() => props.series.category_key === 'movie')

// 根据布局模式选择图片源：横版用cover_url，竖版用thumbnail
function updateImageSrc() {
  hasError.value = false
  const originalUrl = props.layout === 'horizontal'
    ? (props.series.cover_url || props.series.thumbnail || '')
    : (props.series.thumbnail || props.series.cover_url || '')
  imageSrc.value = originalUrl ? getProxyImageUrl(originalUrl) : ''
}

onMounted(() => {
  updateImageSrc()
})

// 布局切换时更新图片
watch(() => props.layout, () => {
  updateImageSrc()
})

function handleClick() {
  // 长按弹出面板时，点击关闭面板不跳转
  if (showLongPressPanel.value) {
    closeLongPress()
    return
  }
  // 移动端刚刚发生了长按，阻止本次点击跳转
  if (isMobile.value && isLongPressed.value) {
    isLongPressed.value = false
    return
  }
  router.push(`/detail/${props.series.cid}`)
}

function handleImageError() {
  if (!hasError.value) {
    hasError.value = true
    imageSrc.value = props.layout === 'horizontal' ? placeholderHero : placeholderCard
  }
}

function handleFollowToggle() {
  emit('toggle-follow', props.series.id)
}

function handleBookmarkToggle() {
  emit('toggle-bookmark', props.series.id)
}
</script>

<style lang="scss" scoped>
/* ==================== 公共样式 ==================== */
.series-card {
  background: var(--surface);
  border-radius: 12px;
  overflow: hidden;
  cursor: pointer;
  border: 1px solid var(--border-light);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  transition: transform 0.2s, box-shadow 0.2s;

  /* TV端焦点样式 */
  &:focus,
  &.tv-focus {
    outline: none;
    border-color: #f59e0b !important;
    box-shadow: none !important;
    transform: none !important;
    z-index: 10;
  }
}

.series-thumbnail-wrapper {
  position: relative;
  width: 100%;
  overflow: hidden;
}

.series-thumbnail {
  width: 100%;
  height: 100%;
  object-fit: cover;
  background: var(--surface-light);
}

/* 左上角操作按钮组 */
.cover-action-group {
  position: absolute;
  top: 8px;
  left: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  z-index: 2;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.25s ease;
}

/* 右上角 VIP/免费标识 */
.vip-badge {
  position: absolute;
  top: 0;
  right: 0;
  padding: 3px 10px;
  border-radius: 0 0 0 6px;
  font-size: 11px;
  font-weight: 400;
  letter-spacing: 0.5px;
  z-index: 2;
  line-height: 1.5;

  &.free {
    background: rgba(76, 175, 80, 0.9);
    color: #fff;
  }

  &.vip {
    background: linear-gradient(135deg, #e8c547, #f5d96a);
    color: #1a1a1a;
  }
}

/* 收藏按钮 - 左侧操作组内 */
.bookmark-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 6px 14px;
  border-radius: 14px;
  border: 1px solid rgba(0, 0, 0, 0.15);
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(6px);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s ease;
  white-space: nowrap;

  .bookmark-icon {
    width: 15px;
    height: 15px;
    display: block;
  }

  .btn-text {
    line-height: 1;
  }

  &:hover {
    background: rgba(255, 255, 255, 0.95);
    border-color: rgba(0, 0, 0, 0.25);
    transform: scale(1.05);
  }

  &.active {
    background: var(--gold, #e8c547);
    border-color: var(--gold, #e8c547);
    color: #1a1a1a;

    &:hover {
      background: rgba(232, 197, 71, 0.85);
    }
  }
}

/* 已看集数 - 右下角 */
.watched-badge {
  position: absolute;
  bottom: 8px;
  right: 8px;
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 16px;
  font-weight: 400;
  color: rgba(255, 255, 255, 0.85);
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.6);
  z-index: 2;
  line-height: 1;
  opacity: 0;
  transition: opacity 0.25s ease;

  .watched-eye-icon {
    width: 16px;
    height: 16px;
    flex-shrink: 0;
    opacity: 0.8;
  }
}

.series-info {
  padding: 10px 12px;
}

.series-row-1 {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.series-title {
  flex: 1;
  font-size: 14px;
  font-weight: 400;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-right: 8px;
}

.series-score {
  font-size: 13px;
  color: var(--gold);
  font-weight: 600;
  flex-shrink: 0;
}

.series-row-2 {
  display: flex;
  align-items: center;
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  gap: 6px;
  margin-bottom: 4px;
}

.series-year {
  flex-shrink: 0;
}

.series-tags {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.series-area {
  flex-shrink: 0;
}

.series-row-3 {
  font-size: 12px;
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 追剧按钮 - 左侧操作组内 */
.follow-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 6px 14px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.3);
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(6px);
  color: rgba(255, 255, 255, 0.9);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s ease;
  white-space: nowrap;

  .follow-icon {
    width: 15px;
    height: 15px;
    display: block;
  }

  .btn-text {
    line-height: 1;
  }

  &:hover {
    background: rgba(255, 255, 255, 0.2);
    border-color: rgba(255, 255, 255, 0.5);
    transform: scale(1.05);
  }

  &.active {
    background: var(--gold, #e8c547);
    border-color: var(--gold, #e8c547);
    color: #000;

    &:hover {
      background: rgba(232, 197, 71, 0.85);
    }
  }
}

/* 封面 hover 时显示操作按钮和已看集数 */
.series-card:hover {
  .cover-action-group {
    opacity: 1;
    pointer-events: auto;
  }

  .watched-badge {
    opacity: 1;
  }
}

/* ==================== 竖版模式（默认） ==================== */
.series-card.vertical {
  .series-thumbnail-wrapper {
    aspect-ratio: 3/4;
  }

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.12);
  }
}

/* ==================== 横版模式 ==================== */
.series-card.horizontal {
  display: flex;
  flex-direction: row;

  .series-thumbnail-wrapper {
    width: 50%;
    flex-shrink: 0;
    aspect-ratio: 16/9;
  }

  .series-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 18px 20px;
    min-width: 0;
  }

  .series-title {
    font-size: 18px;
    font-weight: 700;
    margin-bottom: 10px;
  }

  .series-score {
    font-size: 16px;
  }

  .series-row-2 {
    font-size: 14px;
    margin-bottom: 10px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .episodes-status {
    font-size: 14px;
  }

  .series-row-3 {
    font-size: 14px;
    white-space: normal;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    line-height: 1.6;
  }

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.4), 0 0 20px var(--gold-glow);
  }
}

/* 封面上的集数标签 */
.cover-episodes-badge {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 6px 14px;
  background: linear-gradient(transparent, rgba(0, 0, 0, 0.8));
  display: flex;
  align-items: center;
  justify-content: flex-end;
  z-index: 2;
  gap: 4px;

  .cover-movie-tag,
  .cover-ep-text {
    font-size: 14px;
    color: rgba(255, 255, 255, 0.95);
    font-weight: 500;
  }

  .cover-ep-divider {
    color: rgba(255, 255, 255, 0.5);
  }

  .cover-ep-status {
    font-size: 12px;
    font-weight: 600;

    &.finished {
      color: var(--success);
    }
  }

  // 竖版模式样式微调
  .series-card.vertical & {
    padding: 8px 12px;
  }
}

/* ==================== 响应式断点 ==================== */
@media screen and (max-width: 1200px) {
  .series-info {
    padding: 8px 10px;
  }

  .series-title {
    font-size: 13px;
  }

  .series-score {
    font-size: 12px;
  }

  .series-card.horizontal {
    .series-info {
      padding: 10px 12px;
    }
  }
}

@media screen and (max-width: 992px) {
  .series-card:hover {
    transform: translateY(-4px);
  }

  .series-info {
    padding: 8px;
  }

  .series-title {
    font-size: 14px;
    font-weight: 400;
  }

  .series-row-2,
  .series-row-3 {
    font-size: 12px;
  }

  .bookmark-btn,
  .follow-btn {
    padding: 3px 8px;
    font-size: 10px;

    .bookmark-icon,
    .follow-icon {
      width: 12px;
      height: 12px;
    }
  }

  .series-card.horizontal {
    .series-thumbnail-wrapper {
      width: 40%;
    }
  }
}

@media screen and (max-width: 768px) {
  .series-info {
    padding: 6px;
  }

  .series-title {
    font-size: 14px;
    font-weight: 400;
  }

  .series-score {
    font-size: 12px;
  }

  .series-row-2,
  .series-row-3 {
    font-size: 12px;
  }

  .bookmark-btn,
  .follow-btn {
    padding: 3px 8px;
    font-size: 10px;
  }

  .watched-badge {
    font-size: 14px;
    bottom: 6px;
    right: 6px;

    .watched-eye-icon {
      width: 14px;
      height: 14px;
    }
  }

  .series-card.horizontal {
    .series-info {
      padding: 8px 10px;
    }

    .series-title {
      font-size: 13px;
    }

    .series-row-2,
    .series-row-3 {
      font-size: 10px;
    }
  }
}

@media screen and (max-width: 576px) {
  .series-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.3);
  }

  .series-info {
    padding: 8px;
  }

  .series-title {
    font-size: 14px;
    font-weight: 400;
  }

  .series-row-2,
  .series-row-3 {
    font-size: 12px;
  }

  /* 在手机上图标始终可见 */
  .bookmark-btn,
  .follow-icon-btn,
  .watched-badge {
    opacity: 1 !important;
    pointer-events: auto !important;
  }

  .bookmark-btn,
  .follow-btn {
    padding: 3px 8px;
    font-size: 10px;
  }
}

@media screen and (max-width: 400px) {
  .series-info {
    padding: 8px;
  }

  .series-title {
    font-size: 14px;
    font-weight: 400;
  }

  .series-row-2,
  .series-row-3 {
    font-size: 12px;
  }
}

/* ==================== 移动端长按信息区 ==================== */
.longpress-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(4px);
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.longpress-panel {
  width: 85%;
  max-width: 200px;
  text-align: center;
  animation: panelIn 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes panelIn {
  from { transform: scale(0.85); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}

.longpress-actions {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.longpress-action-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px 32px;
  border: none;
  border-radius: 0;
  background: transparent;
  color: rgba(255, 255, 255, 0.9);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;

  .longpress-icon {
    width: 22px;
    height: 22px;
    display: block;
  }

  .btn-text {
    white-space: nowrap;
  }

  &:active {
    background: rgba(255, 255, 255, 0.15);
    transform: scale(0.95);
  }

  &.active {
    background: var(--gold, #e8c547);
    border-color: var(--gold, #e8c547);
    color: #1a1a1a;
  }
}
</style>
