<template>
  <div class="play-tab" ref="playTabRef" :class="{ maximized: isMaximized }">
    <div class="play-toolbar">
      <div class="play-title-row">
        <span v-if="title" class="play-title">{{ title }}</span>
      </div>
      <div class="play-toolbar-bottom">
        <div class="play-info">
          <span class="source-label">解析源</span>
          <select class="source-select" v-model="activeSourceKey" @change="onSourceChange">
            <option
              v-for="source in parseSources"
              :key="source.key"
              :value="source.key"
            >
              {{ source.name }}
            </option>
          </select>
          <button v-if="episodes.length > 0" class="episodes-btn" @click="showEpisodes = !showEpisodes">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/></svg>
            <span>分集</span>
          </button>
          <span class="source-tip">播放卡顿或者失败，请点击右侧刷新或切换解析源！</span>
        </div>
        <div class="play-actions">
          <button class="toolbar-btn" @click="refreshIframe">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 2v6h-6"/><path d="M3 12a9 9 0 0 1 15-6.7L21 8"/><path d="M3 22v-6h6"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16"/></svg>
            <span>刷新</span>
          </button>
          <button
            class="toolbar-btn close-btn"
            :class="{ 'btn-disabled': isClosing }"
            :disabled="isClosing"
            @click.prevent.stop="handleClose"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6L6 18"/><path d="M6 6l12 12"/></svg>
            <span>关闭</span>
          </button>
        </div>
      </div>
    </div>
    <div class="play-container">
      <iframe
        ref="iframeRef"
        :src="currentUrl"
        frameborder="0"
        allowfullscreen
        allow="autoplay; encrypted-media; fullscreen"
        sandbox="allow-same-origin allow-scripts allow-popups allow-forms allow-popups-to-escape-sandbox"
        @error="onIframeError"
      ></iframe>
      <div v-if="showFallback" class="play-fallback">
        <div class="fallback-content">
          <span class="fallback-icon">⚠️</span>
          <p class="fallback-text">加载失败，请重试</p>
          <button class="fallback-btn" @click="openExternal">
            在新标签页中打开播放
          </button>
        </div>
      </div>
      <!-- 分集列表浮层 -->
      <div v-if="showEpisodes" class="episodes-panel" @click.self="showEpisodes = false">
        <div class="episodes-panel-inner">
          <div class="episodes-panel-header">
            <span class="episodes-panel-title">分集列表</span>
            <button class="episodes-close-btn" @click="showEpisodes = false">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6L6 18"/><path d="M6 6l12 12"/></svg>
            </button>
          </div>
          <div class="episodes-panel-body">
            <button
              v-for="(ep, index) in episodes"
              :key="ep.id || ep.vid || 'ep' + index"
              :class="['ep-panel-item', { active: (ep.id && ep.id === activeEpisodeId) || (ep.vid && ep.vid === activeEpisodeId) }]"
              @click="selectEpisode(ep)"
            >
              <span class="ep-num">{{ ep.play_title || `第${ep.episode_num}集` }}</span>
              <span v-if="ep.is_vip === 1" class="ep-vip-tag">VIP</span>
              <span v-else-if="ep.is_vip === 2" class="ep-vip-tag ppv">点播</span>
            </button>
            <div v-if="episodes.length === 0" class="ep-panel-empty">暂无分集</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import type { ParseSource, Episode } from '@/utils/api'

const props = defineProps<{
  /** 原始播放地址（不含解析源前缀） */
  playUrl: string
  /** 解析源列表 */
  parseSources: ParseSource[]
  /** 当前选中的解析源 key */
  selectedSourceKey: string
  /** 分集标题（tab 栏用） */
  title: string
  /** 是否自动最大化 */
  autoMaximize?: boolean
  /** 分集列表 */
  episodes?: Episode[]
  /** 当前播放的分集 id */
  activeEpisodeId?: number | string
}>()

const emit = defineEmits<{
  (e: 'fallback', url: string): void
  (e: 'source-change', key: string): void
  (e: 'close'): void
  (e: 'maximize-change', isMaximized: boolean): void
  (e: 'episode-click', ep: Episode): void
}>()

const playTabRef = ref<HTMLElement | null>(null)
const iframeRef = ref<HTMLIFrameElement | null>(null)
const showFallback = ref(false)
const showEpisodes = ref(false)
const isMaximized = ref(props.autoMaximize ?? false)
const isClosing = ref(false)

// 内部维护当前解析源 key
const activeSourceKey = ref(props.selectedSourceKey)

// 当前解析源的前缀
const activeSourceUrl = computed(() => {
  const source = props.parseSources.find(s => s.key === activeSourceKey.value)
  return source?.url || ''
})

// 最终拼接的 iframe URL
const currentUrl = computed(() => {
  return activeSourceUrl.value + props.playUrl
})

// 切换解析源时：隐藏 fallback
function onSourceChange() {
  showFallback.value = false
  emit('source-change', activeSourceKey.value)
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

function openExternal() {
  if (currentUrl.value) {
    window.open(currentUrl.value, '_blank', 'noopener,noreferrer')
  }
}

function selectEpisode(ep: Episode) {
  showEpisodes.value = false
  showFallback.value = false
  emit('episode-click', ep)
}

// 最大化：播放区撑满视口（隐藏 header + sidebar + tab bar）
function toggleMaximize() {
  if (isMaximized.value) {
    // 还原时直接关闭播放页，避免页面结构混乱
    handleClose()
  } else {
    isMaximized.value = true
    emit('maximize-change', true)
  }
}

// 关闭：防重复点击
function handleClose() {
  if (isClosing.value) return
  isClosing.value = true
  try {
    emit('close')
  } finally {
    setTimeout(() => {
      isClosing.value = false
    }, 300)
  }
}

// Esc 键退出最大化 / 关闭分集面板
function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    if (showEpisodes.value) {
      showEpisodes.value = false
      return
    }
    if (isMaximized.value) {
      handleClose()
    }
  }
}

// 外部 selectedSourceKey 变化时同步（比如从详情页切回播放页签）
watch(() => props.selectedSourceKey, (key) => {
  if (key !== activeSourceKey.value) {
    activeSourceKey.value = key
  }
})

// playUrl 变化时（换集）隐藏 fallback
watch(() => props.playUrl, () => {
  showFallback.value = false
})

onMounted(() => {
  document.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeydown)
})
</script>

<style lang="scss" scoped>
.play-tab {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 72px); /* 固定高度：减去header(72px) */
  background: #000;
  position: fixed;
  top: 0; /* container已有padding-top: 72px */
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 50; /* 在内容区上层，但低于header的1000 */
  border-radius: 0; /* 移除圆角，因为是固定的 */
  overflow: hidden;

  &.maximized {
    position: fixed;
    inset: 0; /* 占满整个视口 */
    top: 0; /* 从顶部开始 */
    bottom: 0;
    z-index: 9999; /* 最高层级 */
    height: 100vh !important;
  }
}

.play-toolbar {
  display: flex;
  flex-direction: column;
  padding: 6px 14px;
  background: rgba(20, 20, 25, 0.2) !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  flex-shrink: 0;
  gap: 6px;
}

.play-title-row {
  display: flex;
  align-items: center;
  min-width: 0;
}

.play-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--gold, #f59e0b);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
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
  font-size: 15px;
  color: var(--text-secondary, #a1a1aa);
  white-space: nowrap;
  flex-shrink: 0;
}

.source-select {
  padding: 6px 26px 6px 12px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 6px;
  color: var(--gold, #f59e0b);
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%23f59e0b' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 8px center;
  transition: all 0.2s ease;
  flex-shrink: 0;

  &:hover {
    border-color: var(--gold, #f59e0b);
    background-color: rgba(245, 158, 11, 0.1);
  }

  &:focus {
    outline: none;
    border-color: var(--gold, #f59e0b);
    box-shadow: 0 0 10px var(--gold-glow, rgba(245, 158, 11, 0.2));
  }

  option {
    background: var(--surface, #141419);
    color: var(--text-primary, #fff);
  }
}

.source-tip {
  font-size: 14px;
  color: var(--text-secondary, #a1a1aa);
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

  &:hover {
    background: rgba(255, 255, 255, 0.15);
    color: rgba(255, 255, 255, 0.9);
    border-color: rgba(255, 255, 255, 0.25);
  }

  &:active {
    background: rgba(255, 255, 255, 0.2);
  }
}

.close-btn {
  &:hover {
    background: rgba(239, 68, 68, 0.2);
    color: #ef4444;
    border-color: rgba(239, 68, 68, 0.4);
  }
}

.toolbar-btn.btn-disabled,
.toolbar-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}

.play-container {
  flex: 1;
  position: relative;
  overflow: hidden;
}

.play-container iframe {
  width: 100%;
  height: 100%;
  border: none;
  display: block;
}

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
  color: var(--text-secondary, #a1a1aa);
  margin-bottom: 24px;
  line-height: 1.6;
}

.fallback-btn {
  padding: 12px 28px;
  background: linear-gradient(135deg, var(--gold-light, #fbbf24), var(--gold-dark, #d97706));
  border: none;
  border-radius: 24px;
  color: #000;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 16px var(--gold-glow, rgba(245, 158, 11, 0.3));
  }
}

/* ==================== 分集按钮 ==================== */
.episodes-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 14px;
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

  &:hover {
    background: rgba(255, 255, 255, 0.15);
    color: rgba(255, 255, 255, 0.9);
    border-color: rgba(255, 255, 255, 0.25);
  }
}

/* ==================== 分集列表面板 ==================== */
.episodes-panel {
  position: absolute;
  inset: 0;
  z-index: 100;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: flex-start;
  justify-content: flex-end;
  animation: fadeIn 0.2s ease;
}

.episodes-panel-inner {
  width: 320px;
  max-width: 85vw;
  height: 100%;
  background: #1a1a20;
  border-left: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  flex-direction: column;
  animation: slideIn 0.25s ease;
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
  background: rgba(255, 255, 255, 0.06);
  border: none;
  border-radius: 6px;
  color: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover {
    background: rgba(239, 68, 68, 0.2);
    color: #ef4444;
  }
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
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.85);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;

  &:hover {
    background: rgba(255, 255, 255, 0.12);
    color: #fff;
    border-color: rgba(255, 255, 255, 0.25);
  }

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

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideIn {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}

@media screen and (max-width: 750px) {
  .play-tab {
    height: calc(100vh - 60px - 42px);
  }

  .play-toolbar {
    padding: 6px 12px;
    gap: 8px;
  }

  .source-select {
    font-size: 13px;
    padding: 5px 24px 5px 10px;
  }

  .source-tip {
    display: none;
  }

  .toolbar-btn {
    padding: 5px 8px;
    font-size: 12px;
  }

  .episodes-btn {
    padding: 5px 8px;
    font-size: 12px;
  }

  .episodes-panel-inner {
    width: 280px;
    max-width: 80vw;
  }
}
</style>
