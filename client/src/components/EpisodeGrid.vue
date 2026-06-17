<template>
  <div class="episode-grid">
    <!-- 正片区域 -->
    <div v-if="mainEpisodes.length" class="episode-group">
      <button
        v-for="(ep, index) in mainEpisodes"
        :key="ep.id || ep.vid || 'n' + index"
        :class="['episode-item', 'episode-btn', { active: isActive(ep) }]"
        @click="handleEpisodeClick(ep)"
        tabindex="0"
      >
        <span class="btn-text">{{ ep.play_title || `第${ep.episode_num}集` }}</span>
        <span v-if="ep.is_vip === 1" class="ep-vip-badge">VIP</span>
        <span v-else-if="ep.is_vip === 2" class="ep-vip-badge ppv">点播</span>
      </button>
    </div>
    <!-- 分隔线 -->
    <div v-if="mainEpisodes.length && (trailerEpisodes.length || btsEpisodes.length)" class="episode-divider"></div>
    <!-- 预告区域 -->
    <div v-if="trailerEpisodes.length" class="episode-group">
      <button
        v-for="(ep, index) in trailerEpisodes"
        :key="ep.id || ep.vid || 't' + index"
        :class="['episode-item', 'episode-btn', { active: isActive(ep) }]"
        @click="handleEpisodeClick(ep)"
        tabindex="0"
      >
        <span class="btn-text">{{ ep.play_title || `第${ep.episode_num}集` }}</span>
      </button>
    </div>
    <!-- 花絮区域 -->
    <div v-if="btsEpisodes.length" class="episode-group">
      <div v-if="trailerEpisodes.length" class="episode-divider"></div>
      <button
        v-for="(ep, index) in btsEpisodes"
        :key="ep.id || ep.vid || 'b' + index"
        :class="['episode-item', 'episode-btn', { active: isActive(ep) }]"
        @click="handleEpisodeClick(ep)"
        tabindex="0"
      >
        <span class="btn-text">{{ ep.play_title || `第${ep.episode_num}集` }}</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Episode } from '@/utils/api'

const props = defineProps<{
  episodes: Episode[]
  activeEpisodeId?: number | string
}>()

const emit = defineEmits<{
  (e: 'episodeClick', episode: Episode): void
}>()

const mainEpisodes = computed(() => {
  return props.episodes
    .filter(ep => ep.episode_type === 0)
    .sort((a, b) => {
      const numA = a.episode_num || '0'
      const numB = b.episode_num || '0'
      return String(numA).localeCompare(String(numB), 'zh-CN', { numeric: true })
    })
})

const trailerEpisodes = computed(() => {
  return props.episodes
    .filter(ep => ep.episode_type === 1)
    .sort((a, b) => {
      const numA = a.episode_num || '0'
      const numB = b.episode_num || '0'
      return String(numA).localeCompare(String(numB), 'zh-CN', { numeric: true })
    })
})

const btsEpisodes = computed(() => {
  return props.episodes
    .filter(ep => ep.episode_type === 2)
    .sort((a, b) => {
      const numA = a.episode_num || '0'
      const numB = b.episode_num || '0'
      return String(numA).localeCompare(String(numB), 'zh-CN', { numeric: true })
    })
})

function isActive(ep: Episode) {
  return (ep.id && ep.id === props.activeEpisodeId) ||
         (ep.vid && ep.vid === props.activeEpisodeId)
}

function handleEpisodeClick(ep: Episode) {
  emit('episodeClick', ep)
}
</script>

<style lang="scss" scoped>
.episode-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.episode-divider {
  width: 100%;
  height: 1px;
  background: var(--border);
  margin: 4px 0;
}

.episode-group {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  width: 100%;
}

.episode-item {
  padding: 12px 18px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  min-width: 80px;
  text-align: center;
  outline: none;
  transition: all 0.2s ease;

  &.active {
    background: var(--primary-solid);
    border-color: var(--primary-solid);
    color: #fff;
  }

  /* TV 焦点样式 */
  &:focus,
  &.tv-focus {
    outline: none;
    border-color: var(--primary-solid) !important;
    box-shadow: none !important;
    transform: none !important;
    z-index: 10;
    background: var(--primary-solid);
    color: #fff;
  }

  .btn-text {
    flex: 1;
  }

  .ep-vip-badge {
    font-size: 10px;
    font-weight: 400;
    padding: 1px 5px;
    border-radius: 3px;
    background: linear-gradient(135deg, #e8c547, #f0d76a);
    color: #1a1a1a;
    line-height: 1.3;
    flex-shrink: 0;
    margin-left: 4px;

    &.ppv {
      background: rgba(232, 197, 71, 0.2);
      color: var(--gold, #e8c547);
    }
  }
}

/* 小屏幕适配 */
@media (max-width: 768px) {
  .episode-grid {
    gap: 3px;
  }

  .episode-group {
    gap: 3px;
  }

  .episode-btn {
    padding: 10px 14px;
    font-size: 13px;
    min-width: 70px;
  }
}

@media (max-width: 480px) {
  .episode-grid {
    gap: 4px;
  }

  .episode-group {
    gap: 4px;
  }

  .episode-btn {
    padding: 8px 10px;
    font-size: 12px;
    min-width: 56px;
    border-radius: 6px;
  }
}
</style>
