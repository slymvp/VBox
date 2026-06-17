<template>
  <aside class="tv-sidebar">
    <div class="nav-section">
      <h3 class="nav-title">平台</h3>
      <div class="nav-items">
        <div
          :class="['nav-item', { active: currentPlatform === 'all' }]"
          @click="handlePlatformClick('all')"
          class="focusable"
          tabindex="0"
        >
          <span class="nav-icon">📺</span>
          <span>全部</span>
        </div>
        <div
          v-for="platform in platforms"
          :key="platform.key"
          :class="['nav-item', { active: currentPlatform === platform.key }]"
          @click="handlePlatformClick(platform.key)"
          class="focusable"
          tabindex="0"
        >
          <span class="nav-icon">{{ PLATFORM_MAP[platform.key]?.icon || '📺' }}</span>
          <span>{{ PLATFORM_MAP[platform.key]?.name || platform.name }}</span>
        </div>
      </div>
    </div>

    <div class="sidebar-stats">
      <div class="stats-title">📊 数据统计</div>
      <div class="stats-grid">
        <div class="stat-item">
          <span class="stat-value">{{ stats?.total_series || 0 }}</span>
          <span class="stat-label">剧集</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ stats?.total_episodes || 0 }}</span>
          <span class="stat-label">分集</span>
        </div>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import type { Platform, Stats } from '@/utils/api'
import { PLATFORM_MAP } from '@/utils/api'

defineProps<{
  platforms: Platform[]
  currentPlatform: string
  stats: Stats
}>()

const emit = defineEmits<{
  (e: 'platformChange', platform: string): void
}>()

function handlePlatformClick(platform: string) {
  emit('platformChange', platform)
}
</script>

<style lang="scss" scoped>
.tv-sidebar {
  width: 280px;
  padding: 32px 0;
  height: calc(100vh - 140px);
  position: fixed;
  left: 0;
  top: 140px;
  overflow-y: auto;
  z-index: 100;
  display: flex;
  flex-direction: column;

  &::-webkit-scrollbar {
    width: 8px;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background: var(--surface-light);
    border-radius: 4px;
  }

  &::-webkit-scrollbar-thumb:hover {
    background: var(--gold);
  }
}

.nav-section {
  margin-bottom: 32px;
}

.nav-title {
  padding: 0 24px;
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 2px;
  color: var(--text-muted);
  margin: 0 0 16px 0;
}

.nav-items {
  padding: 0 12px;
}

.nav-item {
  padding: 16px 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  color: var(--text-secondary);
  transition: all 0.2s ease;
  border-radius: 12px;
  margin: 0 12px;
  cursor: pointer;
  font-size: 20px;

  &:hover {
    background: rgba(255, 255, 255, 0.06);
    color: var(--text-primary);
  }

  &.active {
    color: var(--gold);
    font-weight: 600;
  }
}

.nav-icon {
  font-size: 24px;
}

.sidebar-stats {
  margin-top: auto;
  padding: 24px;
}

.stats-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 16px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.stats-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 12px;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--gold);
}

.stat-label {
  font-size: 18px;
  color: var(--text-muted);
}

/* TV遥控器焦点样式 */
.focusable {
  outline: none;
}

.focusable:focus {
  outline: 3px solid #f59e0b !important;
  outline-offset: 2px;
}

/* 超高清 TV 屏幕适配 */
@media screen and (min-width: 2560px) {
  .tv-sidebar {
    width: 320px;
    padding: 40px 0;
    height: calc(100vh - 160px);
    top: 160px;
  }

  .nav-section {
    margin-bottom: 40px;
  }

  .nav-title {
    padding: 0 32px;
    font-size: 16px;
    margin-bottom: 20px;
  }

  .nav-items {
    padding: 0 16px;
  }

  .nav-item {
    padding: 20px 32px;
    gap: 20px;
    margin: 0 16px;
    font-size: 24px;
    border-radius: 14px;
  }

  .nav-icon {
    font-size: 28px;
  }

  .sidebar-stats {
    padding: 32px;
  }

  .stats-title {
    font-size: 18px;
    margin-bottom: 20px;
  }

  .stats-grid {
    gap: 16px;
  }

  .stat-item {
    padding: 20px 24px;
    border-radius: 14px;
  }

  .stat-value {
    font-size: 28px;
  }

  .stat-label {
    font-size: 20px;
  }
}

@media screen and (max-width: 1366px) {
  .tv-sidebar {
    width: 240px;
    padding: 24px 0;
    height: calc(100vh - 120px);
    top: 120px;
  }

  .nav-section {
    margin-bottom: 24px;
  }

  .nav-title {
    padding: 0 20px;
    font-size: 13px;
    margin-bottom: 14px;
  }

  .nav-items {
    padding: 0 10px;
  }

  .nav-item {
    padding: 14px 20px;
    gap: 14px;
    margin: 0 10px;
    font-size: 18px;
    border-radius: 10px;
  }

  .nav-icon {
    font-size: 22px;
  }

  .sidebar-stats {
    padding: 20px;
  }

  .stats-title {
    font-size: 15px;
    margin-bottom: 14px;
  }

  .stats-grid {
    gap: 10px;
  }

  .stat-item {
    padding: 14px 16px;
    border-radius: 10px;
  }

  .stat-value {
    font-size: 22px;
  }

  .stat-label {
    font-size: 16px;
  }
}
</style>