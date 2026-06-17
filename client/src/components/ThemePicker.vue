<template>
  <!-- 遮罩 -->
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="visible" class="theme-mask" @click.self="close" />
    </Transition>
    <Transition name="slide-up">
      <div v-if="visible" :class="['theme-sheet', { 'is-dark': themeStore.mode === 'dark' }]">
        <!-- 拖动条 -->
        <div class="sheet-handle" />

        <div class="sheet-header">
          <span class="sheet-title">🎨 外观设置</span>
          <button class="sheet-close" @click="close">✕</button>
        </div>

        <!-- 主题模式选择 -->
        <div class="section">
          <div class="section-label">主题模式</div>
          <div class="mode-grid">
            <button
              v-for="m in modes"
              :key="m.key"
              :class="['mode-card', { active: themeStore.mode === m.key }]"
              @click="selectMode(m.key)"
            >
              <div class="mode-preview" :style="m.previewStyle">
                <div class="preview-header" :style="m.headerStyle" />
                <div class="preview-channel-bar" :style="m.channelStyle" />
                <div class="preview-cards">
                  <div class="preview-card" :style="m.cardStyle" />
                  <div class="preview-card" :style="m.cardStyle" />
                  <div class="preview-card" :style="m.cardStyle" />
                </div>
              </div>
              <div class="mode-name">{{ m.name }}</div>
              <div v-if="themeStore.mode === m.key" class="mode-check">✓</div>
            </button>
          </div>
        </div>

        <!-- 彩色模式：频道色卡预览 -->
        <Transition name="fade-in">
          <div v-if="themeStore.mode === 'colorful'" class="section">
            <div class="section-label">频道颜色预览</div>
            <div class="channel-palette">
              <div
                v-for="ch in channels"
                :key="ch.key"
                class="channel-chip"
                :style="{ background: CHANNEL_COLORS[ch.key].gradient, boxShadow: `0 3px 10px ${CHANNEL_COLORS[ch.key].channelGlow}` }"
              >
                <span class="chip-icon">{{ ch.icon }}</span>
                <span class="chip-name">{{ ch.name }}</span>
              </div>
            </div>
            <p class="colorful-hint">切换频道时自动变色 ✨</p>
          </div>
        </Transition>

        <!-- 当前效果说明 -->
        <div class="current-badge">
          <span class="badge-dot" :style="{ background: currentModeColor }" />
          当前：{{ currentModeName }}
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useThemeStore, CHANNEL_COLORS, type ThemeMode } from '@/stores/theme'

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ (e: 'close'): void }>()

const themeStore = useThemeStore()

function close() {
  emit('close')
}

function selectMode(m: ThemeMode) {
  themeStore.setMode(m)
}

const modes = [
  {
    key: 'light' as ThemeMode,
    name: '浅色',
    previewStyle: { background: '#f7f6f3', border: '2px solid #e2e2de' },
    headerStyle: { background: '#ffffff', borderBottom: '1px solid #e2e2de' },
    channelStyle: { background: '#faf9f6' },
    cardStyle: { background: '#edebe6' },
  },
  {
    key: 'dark' as ThemeMode,
    name: '深色',
    previewStyle: { background: '#0a0a0f', border: '2px solid #2a2a38' },
    headerStyle: { background: '#16161e', borderBottom: '1px solid #2a2a38' },
    channelStyle: { background: '#16161e' },
    cardStyle: { background: '#1e1e28' },
  },
  {
    key: 'colorful' as ThemeMode,
    name: '彩色',
    previewStyle: {
      background: 'linear-gradient(135deg, #f5fdfc 0%, #fef5f5 50%, #faf6fe 100%)',
      border: '2px solid #99f6e4',
    },
    headerStyle: { background: 'linear-gradient(90deg, #e6faf8, #feeaea, #f3e8ff)' },
    channelStyle: { background: 'linear-gradient(90deg, #99f6e4, #fecaca, #e9d5ff)' },
    cardStyle: { background: '#ffffff', borderRadius: '4px', boxShadow: '0 1px 3px rgba(0,0,0,0.08)' },
  },
]

const channels = [
  { key: 'tv', name: '电视剧', icon: '📺' },
  { key: 'movie', name: '电影', icon: '🎬' },
  { key: 'variety', name: '综艺', icon: '🎭' },
  { key: 'cartoon', name: '动漫', icon: '✨' },
  { key: 'child', name: '儿童', icon: '🌈' },
  { key: 'free', name: '免费', icon: '🆓' },
]

const modeNames: Record<ThemeMode, string> = {
  light: '浅色模式',
  dark: '深色模式',
  colorful: '彩色模式',
}

const modeColors: Record<ThemeMode, string> = {
  light: '#f97316',
  dark: '#f0d76a',
  colorful: '#a855f7',
}

const currentModeName = computed(() => modeNames[themeStore.mode])
const currentModeColor = computed(() => modeColors[themeStore.mode])

// 选中颜色随主题变化
const activeOutlineColor = computed(() => {
  if (themeStore.mode === 'dark') return '#f0d76a'
  if (themeStore.mode === 'colorful') return '#a855f7'
  return '#f97316'
})
</script>

<style scoped>
/* ====== 遮罩 ====== */
.theme-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 9998;
  backdrop-filter: blur(2px);
}

/* ====== 底部弹窗 ====== */
.theme-sheet {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 9999;
  background: #ffffff;
  border-radius: 20px 20px 0 0;
  padding: 12px 20px 40px;
  box-shadow: 0 -8px 40px rgba(0, 0, 0, 0.18);
  max-height: 85vh;
  overflow-y: auto;
}

/* ====== 深色主题时弹窗适配 ====== */
.theme-sheet.is-dark {
  background: #16161e;
}

.theme-sheet.is-dark .sheet-title {
  color: #f0f0f5;
}

.theme-sheet.is-dark .section-label {
  color: #6b7280;
}

.theme-sheet.is-dark .sheet-close {
  background: #2a2a38;
  color: #a0a0b0;
}

.theme-sheet.is-dark .mode-name {
  color: #d1d5db;
}

.theme-sheet.is-dark .current-badge {
  background: #1e1e28;
  color: #d1d5db;
}

.theme-sheet.is-dark .colorful-hint {
  color: #6b7280;
}

.theme-sheet.is-dark .sheet-handle {
  background: #2a2a38;
}

.sheet-handle {
  width: 40px;
  height: 4px;
  background: #d1d5db;
  border-radius: 2px;
  margin: 0 auto 16px;
}

.sheet-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.sheet-title {
  font-size: 17px;
  font-weight: 700;
  color: #1a1a1a;
}

.sheet-close {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: none;
  background: #f3f4f6;
  color: #6b7280;
  font-size: 13px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  margin: 0;
  transition: background 0.2s;
}

.sheet-close:hover {
  background: #e5e7eb;
}

/* ====== 区块 ====== */
.section {
  margin-bottom: 24px;
}

.section-label {
  font-size: 13px;
  font-weight: 600;
  color: #9ca3af;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  margin-bottom: 12px;
}

/* ====== 主题模式卡片 ====== */
.mode-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.mode-card {
  position: relative;
  background: none;
  border: none;
  padding: 0;
  margin: 0;
  cursor: pointer;
  border-radius: 14px;
  overflow: hidden;
  transition: transform 0.2s;
}

.mode-card:active {
  transform: scale(0.96);
}

.mode-card.active .mode-preview {
  outline: 3px solid v-bind(activeOutlineColor);
  outline-offset: 0px;
}

.mode-preview {
  width: 100%;
  aspect-ratio: 9/16;
  border-radius: 12px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 5px;
}

.preview-header {
  height: 14%;
  border-radius: 6px;
  flex-shrink: 0;
}

.preview-channel-bar {
  height: 8%;
  border-radius: 4px;
  flex-shrink: 0;
}

.preview-cards {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 3px;
  min-height: 0;
}

.preview-card {
  border-radius: 4px;
  aspect-ratio: 3/4;
}

.mode-name {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  text-align: center;
  margin-top: 8px;
}

.mode-check {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 22px;
  height: 22px;
  background: #f97316;
  color: white;
  font-size: 12px;
  font-weight: 700;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* ====== 彩色频道色卡 ====== */
.channel-palette {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-bottom: 10px;
}

.channel-chip {
  border-radius: 12px;
  padding: 10px 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.chip-icon {
  font-size: 20px;
}

.chip-name {
  font-size: 12px;
  font-weight: 600;
  color: #ffffff;
  text-shadow: 0 1px 3px rgba(0,0,0,0.3);
}

.colorful-hint {
  font-size: 12px;
  color: #9ca3af;
  text-align: center;
  margin-top: 4px;
}

/* ====== 当前状态 ====== */
.current-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #f9fafb;
  border-radius: 12px;
  font-size: 14px;
  color: #374151;
  font-weight: 500;
}

.badge-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* ====== 动画 ====== */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-up-enter-active {
  transition: transform 0.32s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.25s ease;
}
.slide-up-leave-active {
  transition: transform 0.22s ease-in, opacity 0.2s ease;
}
.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(100%);
  opacity: 0;
}

.fade-in-enter-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}
.fade-in-enter-from {
  opacity: 0;
  transform: translateY(6px);
}
</style>
