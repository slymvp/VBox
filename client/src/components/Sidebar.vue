<template>
  <aside class="sidebar">
    <div class="nav-section">
      <h3 class="nav-title">平台</h3>
      <div class="nav-items">
        <div 
          :class="['nav-item', { active: currentPlatform === 'all' }]"
          @click="handlePlatformClick('all')"
        >
          <span class="nav-icon">📺</span>
          <span>全部</span>
        </div>
        <div 
          v-for="platform in platforms" 
          :key="platform.key"
          :class="['nav-item', { active: currentPlatform === platform.key }]"
          @click="handlePlatformClick(platform.key)"
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
          <span class="stat-value">{{ stats.total_series || 0 }}</span>
          <span class="stat-label">剧集</span>
        </div>
        <div class="stat-item">
          <span class="stat-value">{{ stats.total_episodes || 0 }}</span>
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
.sidebar {
  width: 240px;
  padding: 24px 0;
  height: calc(100vh - 72px);
  position: fixed;
  left: 0;
  top: 72px;
  overflow-y: auto;
  z-index: 100;
  display: flex;
  flex-direction: column;

  &::-webkit-scrollbar {
    width: 0;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background: transparent;
  }
}

.nav-section {
  margin-bottom: 28px;
}

.nav-title {
  padding: 0 20px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 2px;
  color: var(--text-muted);
  margin: 0 0 12px 0;
}

.nav-items {
  padding: 0 8px;
}

.nav-item {
  padding: 12px 20px;
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--text-secondary);
  transition: all 0.2s ease;
  border-radius: 10px;
  margin: 0 12px;
  cursor: pointer;

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
  font-size: 20px;
}

.sidebar-stats {
  margin-top: auto;
  padding: 20px;
}

.stats-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 14px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.stats-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: 8px;
}

.stat-value {
  font-size: 16px;
  font-weight: 700;
  color: var(--gold);
}

.stat-label {
  font-size: 13px;
  color: var(--text-muted);
}

@media screen and (max-width: 750px) {
  .sidebar {
    display: none;
  }
}
</style>