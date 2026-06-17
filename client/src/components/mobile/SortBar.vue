<template>
  <div class="sort-bar">
    <div class="sort-btns">
      <button :class="['sort-btn', { active: currentSort === '' }]" @click="setSort('')">默认</button>
      <button :class="['sort-btn', { active: currentSort === 'hot' }]" @click="setSort('hot')">🔥 最热</button>
      <button :class="['sort-btn', { active: currentSort === 'new' }]" @click="setSort('new')">✨ 最新</button>
    </div>
    <div class="action-btns">
      <button v-if="isFilterPage" class="reset-btn" @click="handleReset">重置</button>
      <button v-if="!isFilterPage" class="filter-btn" @click="handleFilterClick">
        <svg class="filter-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="4" y1="6" x2="20" y2="6"/>
          <line x1="10" y1="12" x2="20" y2="12"/>
          <line x1="6" y1="18" x2="20" y2="18"/>
        </svg>
        <span>筛选</span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useSeriesStore } from '@/stores/series'

const router = useRouter()
const route = useRoute()
const store = useSeriesStore()

const isFilterPage = computed(() => route.path === '/filter')
const currentSort = computed(() => store.currentSort)

const setSort = (sort: string) => {
  store.setFilter('sort', sort)
  store.loadSeries(true)
}

const handleFilterClick = () => {
  router.push('/filter')
}

const handleReset = () => {
  store.resetFilterOptions()
  store.loadSeries(true)
  store.loadFilterOptions()
}
</script>

<style lang="scss" scoped>
.sort-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 16px;
  margin: 0 -16px;
  background: var(--background);
}

.sort-btns {
  display: flex;
  gap: 4px;
}

.action-btns {
  display: flex;
  gap: 4px;
}

.sort-btn {
  padding: 4px 10px;
  border: none;
  background: var(--surface);
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 500;
  border-radius: 14px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s ease;

  &:active {
    background: var(--surface-hover);
  }

  &.active {
    color: var(--primary-solid);
    font-weight: 600;
    background: color-mix(in srgb, var(--primary-solid) 14%, transparent);
  }
}

.filter-btn {
  display: flex;
  align-items: center;
  gap: 3px;
  padding: 4px 10px;
  border: none;
  background: var(--surface);
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 500;
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.2s ease;

  &:active {
    background: var(--surface-hover);
    color: var(--primary-solid);
  }
}

.filter-icon {
  width: 14px;
  height: 14px;
}

.reset-btn {
  padding: 4px 10px;
  border: none;
  background: var(--surface);
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 500;
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.2s ease;

  &:active {
    background: var(--surface-hover);
  }
}

@media screen and (max-width: 480px) {
  .sort-bar {
    padding: 4px 12px;
    margin: 0 -12px;
  }

  .sort-btn {
    padding: 3px 8px;
    font-size: 13px;
  }

  .filter-btn {
    padding: 3px 8px;
    font-size: 13px;
  }
}
</style>
