<template>
  <nav class="mobile-sidebar">
    <router-link
      to="/"
      :class="['nav-item', { active: route.path === '/' }]"
      @click="closeMenu"
    >
      <span class="nav-icon">🏠</span>
      <span class="nav-text">首页</span>
    </router-link>

    <router-link
      to="/search"
      :class="['nav-item', { active: route.path === '/search' }]"
      @click="closeMenu"
    >
      <span class="nav-icon">🔍</span>
      <span class="nav-text">搜索</span>
    </router-link>

    <div
      :class="['nav-item', { active: showMenu }]"
      @click="toggleMenu"
      class="menu-trigger"
    >
      <span class="nav-icon">{{ showMenu ? '✕' : '☰' }}</span>
      <span class="nav-text">菜单</span>
    </div>
  </nav>

  <!-- 菜单弹窗 -->
  <Transition name="fade">
    <div v-if="showMenu" class="menu-overlay" @click="closeMenu">
      <div class="menu-panel" @click.stop>
        <div class="menu-header">
          <h3 class="menu-title">菜单</h3>
          <button class="menu-close" @click="closeMenu">✕</button>
        </div>
        
        <div class="menu-content">
          <template v-if="isLoggedIn && user">
            <div class="user-profile">
              <div class="user-avatar">
                <span>{{ user.username?.charAt(0).toUpperCase() }}</span>
              </div>
              <div class="user-info">
                <p class="user-name">{{ user.username }}</p>
                <p class="user-email">{{ user.email || '未填写邮箱' }}</p>
              </div>
            </div>
            
            <div class="menu-divider"></div>
            
            <div class="menu-items">
              <router-link to="/user" class="menu-item" @click="closeMenu">
                <span class="menu-icon">👤</span>
                <span class="menu-text">个人中心</span>
              </router-link>
              
              <router-link to="/vip" class="menu-item" @click="closeMenu">
                <span class="menu-icon">👑</span>
                <span class="menu-text">会员中心</span>
              </router-link>
              
              <button class="menu-item logout-btn" @click="handleLogout">
                <span class="menu-icon">🚪</span>
                <span class="menu-text">退出登录</span>
              </button>
            </div>
          </template>
          
          <template v-else>
            <div class="login-prompt">
              <div class="login-icon">🔐</div>
              <h4 class="login-title">请先登录</h4>
              <p class="login-desc">登录后可享受更多功能</p>
              <router-link to="/login" class="login-btn" @click="closeMenu">
                立即登录
              </router-link>
            </div>
          </template>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const showMenu = ref(false)

const isLoggedIn = ref(userStore.isLoggedIn)
const user = ref(userStore.user)

function toggleMenu() {
  showMenu.value = !showMenu.value
}

function closeMenu() {
  showMenu.value = false
}

function handleLogout() {
  userStore.logout()
  isLoggedIn.value = false
  user.value = null
  closeMenu()
  router.push('/')
}
</script>

<style lang="scss" scoped>
.mobile-sidebar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 60px;
  background: var(--surface);
  backdrop-filter: blur(24px);
  display: flex;
  justify-content: space-around;
  align-items: center;
  padding: 0 8px;
  z-index: 1000;
  border-top: 1px solid var(--border-light);
  box-shadow: 0 -1px 8px rgba(0,0,0,0.04);
}

.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px 12px;
  color: var(--text-secondary);
  text-decoration: none;
  transition: all 0.2s ease;
  border-radius: 8px;
  min-width: 60px;

  &.active {
    color: var(--primary-solid);
  }
}

.nav-icon {
  font-size: 20px;
  line-height: 1;
}

.nav-text {
  font-size: 11px;
  font-weight: 500;
}

/* 菜单弹窗样式 */
.menu-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: flex-end;
  z-index: 2000;
}

.menu-panel {
  width: 100%;
  background: var(--surface);
  border-radius: 16px 16px 0 0;
  max-height: 70vh;
  overflow-y: auto;
}

.menu-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
}

.menu-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.menu-close {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: none;
  background: var(--surface-light);
  color: var(--text-secondary);
  font-size: 16px;
  cursor: pointer;

}

.menu-content {
  padding: 16px 0;
}

.user-profile {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 0 20px;
  margin-bottom: 16px;
}

.user-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--gold-light), var(--gold-dark));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 700;
  color: #fff;
}

.user-info {
  flex: 1;
}

.user-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 4px 0;
}

.user-email {
  font-size: 13px;
  color: var(--text-muted);
  margin: 0;
}

.menu-divider {
  height: 1px;
  background: var(--border);
  margin: 0 20px 16px;
}

.menu-items {
  padding: 0 12px;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  color: var(--text-primary);
  text-decoration: none;
  border-radius: 10px;
  transition: all 0.2s ease;

}

.logout-btn {
  width: 100%;
  justify-content: flex-start;
  border: none;
  background: none;
  cursor: pointer;

}

.menu-icon {
  font-size: 18px;
}

.menu-text {
  font-size: 15px;
  font-weight: 500;
}

/* 登录提示 */
.login-prompt {
  padding: 32px 20px;
  text-align: center;
}

.login-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.6;
}

.login-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.login-desc {
  font-size: 14px;
  color: var(--text-muted);
  margin: 0 0 20px 0;
}

.login-btn {
  display: inline-block;
  padding: 12px 40px;
  background: linear-gradient(135deg, var(--gold-light), var(--gold-dark));
  color: #000;
  font-weight: 600;
  border-radius: 24px;
  text-decoration: none;

}

/* 过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

@media screen and (max-width: 480px) {
  .mobile-sidebar {
    height: 56px;
    padding: 0 4px;
  }

  .nav-item {
    padding: 6px 8px;
    min-width: 56px;
  }

  .nav-icon {
    font-size: 18px;
  }

  .nav-text {
    font-size: 10px;
  }

  .menu-panel {
    max-height: 75vh;
  }
}
</style>