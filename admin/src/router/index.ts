import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { ElMessage } from 'element-plus'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/login/Login.vue'),
    meta: { title: '登录' }
  },
  {
    path: '/',
    component: () => import('@/layout/Layout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/Dashboard.vue'),
        meta: { title: '数据看板', icon: 'Odometer' }
      },
      {
        path: 'video',
        name: 'Video',
        redirect: '/video/series',
        meta: { title: '影视数据管理', icon: 'VideoCamera' },
        children: [
          {
            path: 'series',
            name: 'Series',
            component: () => import('@/views/series/Series.vue'),
            meta: { title: '剧集管理', icon: 'Film' }
          },
          {
            path: 'episodes',
            name: 'Episodes',
            component: () => import('@/views/episodes/Episodes.vue'),
            meta: { title: '分集管理', icon: 'Tickets' }
          }
        ]
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/users/Users.vue'),
        meta: { title: '用户管理', icon: 'User' }
      },
      {
        path: 'member',
        name: 'Member',
        redirect: '/member/vip-plans',
        meta: { title: '会员管理', icon: 'Wallet' },
        children: [
          {
            path: 'vip-plans',
            name: 'VipPlans',
            component: () => import('@/views/vip-plans/VipPlans.vue'),
            meta: { title: '会员套餐', icon: 'PriceTag' }
          },
          {
            path: 'payment-qrcodes',
            name: 'PaymentQrcodes',
            component: () => import('@/views/payment-qrcodes/PaymentQrcodes.vue'),
            meta: { title: '支付二维码', icon: 'QrCode' }
          },
          {
            path: 'vip-cdkeys',
            name: 'VipCdkeys',
            component: () => import('@/views/vip-cdkeys/VipCdkeys.vue'),
            meta: { title: 'VIP卡密', icon: 'Key' }
          }
        ]
      },
      {
        path: 'categories',
        name: 'Categories',
        component: () => import('@/views/categories/Categories.vue'),
        meta: { title: '频道管理', icon: 'Setting' }
      },
      {
        path: 'platforms',
        name: 'Platforms',
        component: () => import('@/views/platforms/Platforms.vue'),
        meta: { title: '平台管理', icon: 'Monitor' }
      },
      {
        path: 'crawler',
        name: 'Crawler',
        component: () => import('@/views/crawler/Crawler.vue'),
        meta: { title: '爬虫管理', icon: 'Connection' }
      },
      {
        path: 'admin-settings',
        name: 'AdminSettings',
        component: () => import('@/views/admin-settings/AdminSettings.vue'),
        meta: { title: '管理员设置', icon: 'UserFilled' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory('/admin/'),
  routes
})

// 解析 JWT payload（不验证签名，仅提取 exp）
function parseTokenExp(token: string): number | null {
  try {
    const parts = token.split('.')
    if (parts.length === 3) {
      // 标准 JWT（base64url 编码），需转成标准 base64 给 atob
      const base64 = parts[1].replace(/-/g, '+').replace(/_/g, '/')
      const payload = JSON.parse(atob(base64))
      return payload.exp || null
    }
    // 非标准 token（fallback 模式，两段：base64.signature）
    if (parts.length === 2) {
      const base64 = parts[0].replace(/-/g, '+').replace(/_/g, '/')
      const payload = JSON.parse(atob(base64))
      return payload.exp || null
    }
    return null
  } catch {
    return null
  }
}

// 路由守卫
router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('admin_token')

  if (to.path === '/login') {
    // 已登录用户访问登录页 → 跳转首页
    if (token) {
      const exp = parseTokenExp(token)
      if (exp && exp * 1000 > Date.now()) {
        next('/')
        return
      }
      // token 已过期，清除并留在登录页
      localStorage.removeItem('admin_token')
      localStorage.removeItem('admin_user')
    }
    next()
    return
  }

  // 非登录页，检查 token
  if (!token) {
    next('/login')
    return
  }

  // 检查 token 是否过期
  const exp = parseTokenExp(token)
  if (exp && exp * 1000 <= Date.now()) {
    localStorage.removeItem('admin_token')
    localStorage.removeItem('admin_user')
    ElMessage.warning('登录已过期，请重新登录')
    next('/login')
    return
  }

  next()
})

export default router
