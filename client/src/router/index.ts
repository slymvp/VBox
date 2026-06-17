import { createRouter, createWebHashHistory } from 'vue-router'
import Index from '@/pages/index/index.vue'
import Search from '@/pages/search/search.vue'
import Detail from '@/pages/detail/detail.vue'
import Play from '@/pages/play/index.vue'
import Login from '@/pages/login/login.vue'
import Register from '@/pages/register/register.vue'
import ForgotPassword from '@/pages/forgot-password/forgot-password.vue'
import User from '@/pages/user/user.vue'
import Vip from '@/pages/vip/vip.vue'
import Filter from '@/pages/filter/filter.vue'

const routes = [
  {
    path: '/',
    name: 'Index',
    component: Index
  },
  {
    path: '/search',
    name: 'Search',
    component: Search
  },
  {
    path: '/filter',
    name: 'Filter',
    component: Filter
  },
  {
    path: '/tv',
    name: 'TV',
    component: Index
  },
  {
    path: '/movie',
    name: 'Movie',
    component: Index
  },
  {
    path: '/variety',
    name: 'Variety',
    component: Index
  },
  {
    path: '/cartoon',
    name: 'Cartoon',
    component: Index
  },
  {
    path: '/child',
    name: 'Child',
    component: Index
  },
  {
    path: '/free',
    name: 'Free',
    component: Index
  },
  {
    path: '/detail/:cid',
    name: 'Detail',
    component: Detail
  },
  {
    path: '/play/:cid',
    name: 'Play',
    component: Play
  },
  {
    path: '/login',
    name: 'Login',
    component: Login
  },
  {
    path: '/register',
    name: 'Register',
    component: Register
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: ForgotPassword
  },
  {
    path: '/user',
    name: 'User',
    component: User
  },
  {
    path: '/vip',
    name: 'Vip',
    component: Vip
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
  scrollBehavior() {
    return { top: 0, left: 0 }
  }
})

export default router
