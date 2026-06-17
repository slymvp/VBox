import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'

export type ThemeMode = 'light' | 'dark' | 'colorful'

// 彩色主题：各频道对应的主色（大背景低饱和度偏亮，白色模块，深色文字）
export const CHANNEL_COLORS: Record<string, {
  primary: string
  gradient: string
  bg: string
  bgDeep: string
  surface: string
  surfaceHover: string
  border: string
  channelGlow: string
}> = {
  tv: {
    primary: '#14b8a6',
    gradient: 'linear-gradient(135deg, #2dd4bf 0%, #14b8a6 50%, #0f766e 100%)',
    bg: '#f5fdfc',
    bgDeep: '#e6faf8',
    surface: '#ffffff',
    surfaceHover: '#f2fdfb',
    border: '#99f6e4',
    channelGlow: 'rgba(20, 184, 166, 0.12)',
  },
  movie: {
    primary: '#6b7280',
    gradient: 'linear-gradient(135deg, #9ca3af 0%, #6b7280 50%, #4b5563 100%)',
    bg: '#f8f8fa',
    bgDeep: '#f0f0f3',
    surface: '#ffffff',
    surfaceHover: '#f5f5f7',
    border: '#d1d5db',
    channelGlow: 'rgba(107, 114, 128, 0.12)',
  },
  variety: {
    primary: '#ef4444',
    gradient: 'linear-gradient(135deg, #f87171 0%, #ef4444 50%, #dc2626 100%)',
    bg: '#fef5f5',
    bgDeep: '#feeaea',
    surface: '#ffffff',
    surfaceHover: '#fdf2f2',
    border: '#fecaca',
    channelGlow: 'rgba(239, 68, 68, 0.12)',
  },
  cartoon: {
    primary: '#a855f7',
    gradient: 'linear-gradient(135deg, #c084fc 0%, #a855f7 50%, #9333ea 100%)',
    bg: '#faf6fe',
    bgDeep: '#f3e8ff',
    surface: '#ffffff',
    surfaceHover: '#f7f2fe',
    border: '#e9d5ff',
    channelGlow: 'rgba(168, 85, 247, 0.12)',
  },
  child: {
    primary: '#f97316',
    gradient: 'linear-gradient(135deg, #fb923c 0%, #f97316 50%, #ea580c 100%)',
    bg: '#fffaf6',
    bgDeep: '#fff0e6',
    surface: '#ffffff',
    surfaceHover: '#fef7f2',
    border: '#fed7aa',
    channelGlow: 'rgba(249, 115, 22, 0.12)',
  },
  free: {
    primary: '#22c55e',
    gradient: 'linear-gradient(135deg, #4ade80 0%, #22c55e 50%, #16a34a 100%)',
    bg: '#f6fdf8',
    bgDeep: '#e6f9ed',
    surface: '#ffffff',
    surfaceHover: '#f2fdf6',
    border: '#bbf7d0',
    channelGlow: 'rgba(34, 197, 94, 0.12)',
  },
  default: {
    primary: '#6b7280',
    gradient: 'linear-gradient(135deg, #9ca3af 0%, #6b7280 50%, #4b5563 100%)',
    bg: '#fafaf8',
    bgDeep: '#f0efec',
    surface: '#ffffff',
    surfaceHover: '#f7f6f3',
    border: '#e5e5e5',
    channelGlow: 'rgba(107, 114, 128, 0.15)',
  },
}

const ROUTE_CHANNEL_MAP: Record<string, string> = {
  '/tv': 'tv',
  '/movie': 'movie',
  '/variety': 'variety',
  '/cartoon': 'cartoon',
  '/child': 'child',
  '/free': 'free',
}

export const useThemeStore = defineStore('theme', () => {
  const mode = ref<ThemeMode>((localStorage.getItem('themeMode') as ThemeMode) || 'colorful')
  const currentChannel = ref<string>('default')

  watch(mode, (val) => {
    localStorage.setItem('themeMode', val)
    applyTheme(val, currentChannel.value)
  })

  function setMode(m: ThemeMode) {
    mode.value = m
  }

  function setChannel(channel: string) {
    currentChannel.value = channel
    if (mode.value === 'colorful') {
      applyColorfulTheme(channel)
    }
  }

  function applyTheme(m: ThemeMode, channel: string) {
    const root = document.documentElement
    if (m === 'light') {
      applyLightTheme(root)
    } else if (m === 'dark') {
      applyDarkTheme(root)
    } else {
      applyColorfulTheme(channel)
    }
  }

  // ====== 浅色主题 ======
  // 不同灰+白组合，页面背景用暖灰白，模块用纯白，文字深色，亮橙色突出
  function applyLightTheme(root: HTMLElement) {
    root.style.setProperty('--background', '#f2f2f2')
    root.style.setProperty('--background-deep', '#e8e8e8')
    root.style.setProperty('--surface', '#ffffff')
    root.style.setProperty('--surface-hover', '#f7f7f7')
    root.style.setProperty('--surface-light', '#fafafa')
    root.style.setProperty('--text-primary', '#1a1a1a')
    root.style.setProperty('--text-secondary', '#6b6b6b')
    root.style.setProperty('--text-muted', '#9a9a9a')
    root.style.setProperty('--border', '#e0e0e0')
    root.style.setProperty('--border-light', '#eeeeee')
    // 亮橙色突出（按钮背景用渐变，文字/边框用实色）
    root.style.setProperty('--primary', 'linear-gradient(135deg, #ffa033 0%, #ff8c00 50%, #e07b00 100%)')
    root.style.setProperty('--primary-solid', '#ff8c00')
    root.style.setProperty('--primary-dark', '#e07b00')
    document.body.setAttribute('data-theme', 'light')
    overrideHeaderBg('#ffffff')
  }

  // ====== 深色主题 ======
  // 深色背景，白/灰文字，亮橙色突出
  function applyDarkTheme(root: HTMLElement) {
    root.style.setProperty('--background', '#0a0a0f')
    root.style.setProperty('--background-deep', '#111118')
    root.style.setProperty('--surface', '#16161e')
    root.style.setProperty('--surface-hover', '#1e1e28')
    root.style.setProperty('--surface-light', '#1a1a24')
    // 白色/灰色文字
    root.style.setProperty('--text-primary', '#ffffff')
    root.style.setProperty('--text-secondary', '#b0b0c0')
    root.style.setProperty('--text-muted', '#6a6a7a')
    root.style.setProperty('--border', '#2a2a38')
    root.style.setProperty('--border-light', '#222230')
    // 亮橙色突出
    root.style.setProperty('--primary', 'linear-gradient(135deg, #ffa033 0%, #ff8c00 50%, #e07b00 100%)')
    root.style.setProperty('--primary-solid', '#ff8c00')
    root.style.setProperty('--primary-dark', '#e07b00')
    document.body.setAttribute('data-theme', 'dark')
    overrideHeaderBg('#16161e')
  }

  // ====== 彩色主题 ======
  // 大背景低饱和度偏亮，白色模块，深色文字，各频道主色仅用于按钮/突出元素
  function applyColorfulTheme(channel: string) {
    const root = document.documentElement
    const c = CHANNEL_COLORS[channel] || CHANNEL_COLORS.default
    root.style.setProperty('--background', c.bg)
    root.style.setProperty('--background-deep', c.bgDeep)
    root.style.setProperty('--surface', c.surface)
    root.style.setProperty('--surface-hover', c.surfaceHover)
    root.style.setProperty('--surface-light', c.surface)
    // 深色文字
    root.style.setProperty('--text-primary', '#1a1a1a')
    root.style.setProperty('--text-secondary', '#555566')
    root.style.setProperty('--text-muted', '#888899')
    root.style.setProperty('--border', c.border)
    root.style.setProperty('--border-light', c.border)
    // 频道主色用于按钮/突出元素
    root.style.setProperty('--primary', c.primary)
    root.style.setProperty('--primary-solid', c.primary)
    root.style.setProperty('--primary-dark', c.primary)
    root.style.setProperty('--primary-gradient', c.gradient)
    root.style.setProperty('--channel-glow', c.channelGlow)
    document.body.setAttribute('data-theme', 'colorful')
    overrideHeaderBg(c.bg)
  }

  function overrideHeaderBg(color: string) {
    document.documentElement.style.setProperty('--header-bg-override', color)
  }

  function init() {
    applyTheme(mode.value, currentChannel.value)
  }

  return { mode, currentChannel, setMode, setChannel, applyTheme, init }
})
