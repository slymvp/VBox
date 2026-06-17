/**
 * 设备检测工具
 * 用于检测当前设备类型（手机 / Pad / PC / TV）
 *
 * 检测策略（优先级从高到低）：
 * 1. UA 匹配 TV 设备特征 → TV
 * 2. UA 匹配手机特征 → 进一步判断手机还是 Pad
 * 3. 支持触摸 + 不支持鼠标悬停 → 触屏设备（手机或 Pad，按尺寸细分）
 * 4. 纯视窗尺寸兜底
 */

export enum DeviceType {
  MOBILE = 'mobile',
  PAD = 'pad',
  PC = 'pc',
  TV = 'tv'
}

export interface DeviceInfo {
  type: DeviceType
  isTV: boolean
  isPC: boolean
  isPad: boolean
  isMobile: boolean
  screenWidth: number
  screenHeight: number
  pixelRatio: number
}

/**
 * 检测设备类型
 */
export function detectDevice(): DeviceInfo {
  const width = window.innerWidth
  const height = window.innerHeight
  const ua = navigator.userAgent
  const pixelRatio = window.devicePixelRatio || 1

  // --- 第 1 层：TV 设备特征（最高优先级）---
  const tvKeywords = ['TV', 'Tizen', 'WebOS', 'SmartTV', 'Android TV', 'Roku', 'PlayStation', 'Xbox', 'Nintendo']
  const isTV = tvKeywords.some(kw => ua.includes(kw))

  if (isTV) {
    return makeResult(DeviceType.TV, width, height, pixelRatio)
  }

  // --- 第 2 层：手机/平板特征 ---
  const isIOS = /iPhone|iPad|iPod/.test(ua)
  const isAndroid = /Android/.test(ua)

  if (isIOS) {
    // iOS: iPad 和 iPhone 通过 UA 区分
    if (/iPad/.test(ua)) {
      return makeResult(DeviceType.PAD, width, height, pixelRatio)
    }
    if (/iPhone|iPod/.test(ua)) {
      return makeResult(DeviceType.MOBILE, width, height, pixelRatio)
    }
  }

  if (isAndroid) {
    // Android: UA 中有 Mobile 标记 → 手机，否则 → 平板
    if (/Mobile/.test(ua)) {
      return makeResult(DeviceType.MOBILE, width, height, pixelRatio)
    }
    // Android 但没有 Mobile 标记 → 很可能是平板
    return makeResult(DeviceType.PAD, width, height, pixelRatio)
  }

  // --- 第 3 层：触摸屏特征 ---
  const hasTouch = 'ontouchstart' in window || navigator.maxTouchPoints > 0
  const hasCoarsePointer = window.matchMedia('(pointer: coarse)').matches
  const hasFinePointer = window.matchMedia('(pointer: fine)').matches
  const canHover = window.matchMedia('(hover: hover)').matches

  // 触屏 + 不支持 hover → 移动设备
  if (hasTouch && hasCoarsePointer && !canHover) {
    // 按物理尺寸（CSS像素 × 设备像素比）判断
    const physicalWidth = width * pixelRatio
    if (physicalWidth >= 1536) {
      // 物理宽度 ≥ 1536 → 大屏平板（如 iPad Pro 12.9" = 2048）
      return makeResult(DeviceType.PAD, width, height, pixelRatio)
    }
    if (width >= 768) {
      // CSS 宽度 ≥ 768 → 中等平板
      return makeResult(DeviceType.PAD, width, height, pixelRatio)
    }
    return makeResult(DeviceType.MOBILE, width, height, pixelRatio)
  }

  // --- 第 4 层：纯视窗尺寸兜底 ---
  // 有精细指针 + 支持 hover → 桌面设备
  if (hasFinePointer && canHover) {
    // 极小窗口（比如开发工具模拟器）→ 按尺寸判断
    if (width < 768) {
      return makeResult(DeviceType.MOBILE, width, height, pixelRatio)
    }
    return makeResult(DeviceType.PC, width, height, pixelRatio)
  }

  // 最后的兜底：纯尺寸判断
  if (width < 768) {
    return makeResult(DeviceType.MOBILE, width, height, pixelRatio)
  }
  if (width < 1024) {
    return makeResult(DeviceType.PAD, width, height, pixelRatio)
  }
  return makeResult(DeviceType.PC, width, height, pixelRatio)
}

function makeResult(type: DeviceType, width: number, height: number, pixelRatio: number): DeviceInfo {
  return {
    type,
    isTV: type === DeviceType.TV,
    isPC: type === DeviceType.PC,
    isPad: type === DeviceType.PAD,
    isMobile: type === DeviceType.MOBILE,
    screenWidth: width,
    screenHeight: height,
    pixelRatio,
  }
}

/**
 * 检查是否为 TV 环境
 */
export function isTVEnvironment(): boolean {
  return import.meta.env.VITE_PLATFORM === 'tv' || detectDevice().isTV
}

/**
 * 检查是否为移动端环境（含手机和平板）
 */
export function isMobileEnvironment(): boolean {
  const d = detectDevice()
  return import.meta.env.VITE_PLATFORM === 'mobile' || d.isMobile || d.isPad
}
