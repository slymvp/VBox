<template>
  <header :class="['header', { 'header-hidden': isHidden }]">
    <div class="header-row">
      <!-- 左侧：搜索框 -->
      <div class="search-wrap" @click="handleSearchClick">
        <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"/>
          <path d="m21 21-4.35-4.35"/>
        </svg>
        <span class="search-placeholder">搜索影片</span>
      </div>

      <!-- 右侧：我的/登录按钮 -->
      <button class="user-btn" @click="handleUserClick">
        <svg class="user-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
          <circle cx="12" cy="7" r="4"/>
        </svg>
        <span class="user-text">{{ userStore.isLoggedIn ? '我的' : '登录' }}</span>
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const props = defineProps<{
  isHidden?: boolean
}>()

const isHidden = ref(props.isHidden || false)

const handleSearchClick = () => {
  router.push('/search')
}

const handleUserClick = () => {
  // 直接跳转到用户中心页面
  router.push('/user')
}
</script>

<style lang="scss" scoped>
.header {
  height: 48px;
  background: var(--surface);
  display: flex;
  align-items: center;
  padding: 0 10px;
  z-index: 1000;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.header-hidden {
  transform: translateY(-100%);
  opacity: 0;
  pointer-events: none;
}

/* 搜索框 */
.search-wrap {
  flex: 1;
  max-width: 280px;
  height: 36px;
  background: var(--surface);
  border: 1px solid color-mix(in srgb, var(--primary-solid) 30%, transparent);
  border-radius: 18px;
  display: flex;
  align-items: center;
  padding: 0 16px;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease;

  &:active {
    background: var(--surface-hover);
  }
}

.search-icon {
  width: 16px;
  height: 16px;
  color: var(--text-muted);
  margin-right: 8px;
}

.search-placeholder {
  font-size: 14px;
  color: var(--text-muted);
}

/* 我的按钮 */
.user-btn {
  height: 36px;
  border-radius: 18px;
  border: 1px solid color-mix(in srgb, var(--primary-solid) 30%, transparent);
  background: var(--surface);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 0 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-left: 12px;

  &:active {
    background: var(--surface-hover);
    transform: scale(0.95);
  }
}

.user-icon {
  width: 18px;
  height: 18px;
  color: var(--text-secondary);
}

.user-text {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}

/* 下拉菜单 */
.menu-overlay {
  position: fixed;
  top: 48px;
  right: 10px;
  left: 10px;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 999;
}

.menu-panel {
  position: absolute;
  top: 8px;
  right: 0;
  width: 200px;
  background: var(--surface);
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  overflow: hidden;
}

.menu-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border);
}

.menu-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
}

.menu-close {
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;

  &:active {
    background: var(--surface-hover);
  }
}

.menu-list {
  padding: 8px 0;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 12px 16px;
  border: none;
  background: transparent;
  color: var(--text-primary);
  font-size: 14px;
  cursor: pointer;
  text-align: left;
  transition: background 0.2s ease;

  &:active {
    background: var(--surface-hover);
  }

  &.logout {
    color: var(--danger);
  }
}

.menu-icon {
  font-size: 18px;
}

.menu-divider {
  height: 1px;
  background: var(--border);
  margin: 8px 16px;
}

/* 动画 */
.menu-fade-enter-active,
.menu-fade-leave-active {
  transition: opacity 0.2s ease;

  .menu-panel {
    transition: transform 0.2s ease, opacity 0.2s ease;
  }
}

.menu-fade-enter-from,
.menu-fade-leave-to {
  opacity: 0;

  .menu-panel {
    transform: translateY(-10px);
    opacity: 0;
  }
}

@media screen and (max-width: 480px) {
  .header {
    height: 44px;
    padding: 0 8px;
  }

  .search-wrap {
    max-width: 220px;
    height: 32px;
    padding: 0 12px;
  }

  .search-placeholder {
    font-size: 13px;
  }

  .menu-overlay {
    top: 44px;
  }
}
</style>
