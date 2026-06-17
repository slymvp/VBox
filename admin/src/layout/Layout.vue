<template>
  <el-container class="layout-container">
    <el-aside width="240px">
      <div class="logo">
        <h2>VBox 管理后台</h2>
      </div>
      <el-menu
        :default-active="activeMenu"
        :default-openeds="defaultOpeneds"
        router
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409EFF"
      >
        <template v-for="route in menuRoutes" :key="route.path">
          <el-sub-menu v-if="route.children && route.children.length > 0" :index="`/${route.path}`">
            <template #title>
              <el-icon><component :is="route.meta?.icon || 'Document'" /></el-icon>
              <span>{{ route.meta?.title }}</span>
            </template>
            <el-menu-item
              v-for="child in route.children.filter(r => r.meta?.title)"
              :key="child.path"
              :index="`/${route.path}/${child.path}`"
            >
              <el-icon><component :is="child.meta?.icon || 'Document'" /></el-icon>
              <span>{{ child.meta?.title }}</span>
            </el-menu-item>
          </el-sub-menu>
          <el-menu-item v-else :index="`/${route.path}`">
            <el-icon><component :is="route.meta?.icon || 'Document'" /></el-icon>
            <span>{{ route.meta?.title }}</span>
          </el-menu-item>
        </template>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header>
        <div class="header-right">
          <span class="admin-name">{{ adminNickname }}</span>
          <el-button type="danger" @click="handleLogout">退出登录</el-button>
        </div>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const menuRoutes = computed(() => {
  const parentRoute = router.getRoutes().find(r => r.path === '/')
  let routes = parentRoute?.children?.filter(r => r.meta?.title) || []

  // 只允许超级管理员看到管理员设置
  const adminUser = JSON.parse(localStorage.getItem('admin_user') || '{}')
  if (adminUser.role !== 'admin') {
    routes = routes.filter(route => route.path !== 'admin-settings')
  }

  return routes
})

const activeMenu = computed(() => route.path)

const defaultOpeneds = computed(() => {
  // 让所有有子菜单的父菜单默认展开
  const parentRoute = router.getRoutes().find(r => r.path === '/')
  const opened = parentRoute?.children?.filter(r => r.children && r.children.length > 0).map(r => `/${r.path}`) || []
  return opened
})

const adminNickname = computed(() => {
  try {
    const user = JSON.parse(localStorage.getItem('admin_user') || '{}')
    return user.nickname || user.username || '管理员'
  } catch {
    return '管理员'
  }
})

const handleLogout = () => {
  localStorage.removeItem('admin_token')
  localStorage.removeItem('admin_user')
  router.push('/login')
}
</script>

<style scoped lang="scss">
.layout-container {
  height: 100vh;
}

.el-aside {
  background-color: #304156;
  overflow-x: hidden;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  border-bottom: 1px solid #1f2d3d;
  h2 {
    font-size: 18px;
    margin: 0;
  }
}

.el-header {
  background-color: #fff;
  border-bottom: 1px solid #e6e6e6;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 0 20px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.admin-name {
  color: #606266;
  font-size: 14px;
}

.el-main {
  background-color: #f0f2f5;
  padding: 20px;
}
</style>
