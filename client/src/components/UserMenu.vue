<template>
  <div class="header-actions">
    <!-- 已登录：头像 + 用户名 + 下拉菜单 -->
    <div v-if="userStore.isLoggedIn" class="user-menu-wrapper" @click.stop>
      <div class="user-link" @click="toggleMenu">
        <span class="user-avatar">{{ avatarChar }}</span>
        <span class="user-name">{{ displayName }}</span>
        <span class="user-arrow">{{ menuOpen ? '▲' : '▼' }}</span>
      </div>
      <Transition name="dropdown-fade">
        <div v-if="menuOpen" class="user-dropdown">
          <div class="dropdown-item" @click="goUserCenter">
            <span class="dropdown-icon">👤</span>
            <span>个人中心</span>
          </div>
          <div class="dropdown-item vip-menu-item" @click="goVip">
            <span class="dropdown-icon">👑</span>
            <span>会员中心</span>
          </div>
          <div class="dropdown-divider"></div>
          <button class="dropdown-item logout-item" @click="handleLogout">
            <span class="dropdown-icon">🚪</span>
            <span>退出登录</span>
          </button>
        </div>
      </Transition>
    </div>

    <!-- 未登录：登录 + 注册按钮 -->
    <template v-else>
      <router-link to="/login" class="auth-btn login-btn">登录</router-link>
      <router-link to="/register" class="auth-btn register-btn">注册</router-link>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()
const router = useRouter()
const menuOpen = ref(false)

const avatarChar = computed(() => {
  return userStore.user?.username?.charAt(0).toUpperCase() || '?'
})

const displayName = computed(() => {
  return userStore.user?.username || ''
})

function toggleMenu() {
  menuOpen.value = !menuOpen.value
}

function closeMenu() {
  menuOpen.value = false
}

function goUserCenter() {
  closeMenu()
  router.push('/user')
}

function goVip() {
  closeMenu()
  router.push('/vip')
}

function handleLogout() {
  closeMenu()
  userStore.logout()
  router.push('/')
}

// 点击外部关闭下拉菜单
function onClickOutside(e: MouseEvent) {
  const target = e.target as HTMLElement
  const wrapper = document.querySelector('.user-menu-wrapper')
  // 如果点击的是下拉菜单内部，不关闭
  if (wrapper && wrapper.contains(target)) {
    return
  }
  menuOpen.value = false
}

onMounted(() => {
  document.addEventListener('click', onClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', onClickOutside)
})
</script>

<style scoped>
.header-actions {
  display: flex;
  gap: 12px;
  margin-left: auto;
  align-items: center;
}

/* ====== 用户按钮 ====== */
.user-menu-wrapper {
  position: relative;
}

.user-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 18px;
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(217, 119, 6, 0.1));
  border: 1px solid rgba(245, 158, 11, 0.3);
  border-radius: 24px;
  cursor: pointer;
  transition: all 0.3s ease;
  user-select: none;
}

.user-link:hover {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.25), rgba(217, 119, 6, 0.2));
  border-color: var(--gold);
  box-shadow: 0 0 15px var(--gold-glow);
}

.user-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--gold-light), var(--gold-dark));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  color: #000;
  flex-shrink: 0;
}

.user-name {
  font-size: 13px;
  color: var(--gold);
  font-weight: 500;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-arrow {
  font-size: 10px;
  color: var(--gold);
  margin-left: 2px;
}

/* ====== 下拉菜单 ====== */
.user-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 160px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  z-index: 100;
  overflow: hidden;
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  font-size: 14px;
  color: var(--text-secondary);
  text-decoration: none;
  background: none;
  border: none;
  width: 100%;
  text-align: left;
  cursor: pointer;
  transition: background 0.2s ease;
}

.dropdown-item:hover {
  background: var(--surface-light);
  color: var(--text-primary);
}

.dropdown-icon {
  font-size: 16px;
}

.dropdown-divider {
  height: 1px;
  background: var(--border);
  margin: 4px 0;
}

.logout-item {
  color: #ef4444;
}

.logout-item:hover {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
}

/* ====== VIP菜单项 ====== */
.vip-menu-item {
  color: var(--gold) !important;
}

.vip-menu-item:hover {
  background: rgba(245, 158, 11, 0.1) !important;
  color: var(--gold-light) !important;
}

/* ====== 登录/注册按钮 ====== */
.auth-btn {
  padding: 8px 20px;
  border-radius: 24px;
  font-size: 13px;
  font-weight: 500;
  text-decoration: none;
  transition: all 0.3s ease;
}

.login-btn {
  color: var(--text-secondary);
  border: 1px solid var(--border-light);
}

.login-btn:hover {
  color: var(--gold);
  border-color: var(--gold);
  box-shadow: 0 0 15px var(--gold-glow);
}

.register-btn {
  color: #000;
  background: linear-gradient(135deg, var(--gold-light), var(--gold-dark));
}

.register-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px var(--gold-glow);
}

/* ====== 下拉动画 ====== */
.dropdown-fade-enter-active,
.dropdown-fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.dropdown-fade-enter-from,
.dropdown-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
