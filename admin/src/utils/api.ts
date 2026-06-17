import axios from 'axios'
import { ElMessage } from 'element-plus'

const API_BASE = (import.meta.env.VITE_API_BASE as string) || ''

const request = axios.create({
  baseURL: API_BASE ? `${API_BASE}/admin-api` : '/admin-api',
  timeout: 30000
})

// 401 防抖：避免多个请求同时触发多次跳转
let isRedirecting = false

// 请求拦截器
request.interceptors.request.use(
  config => {
    const token = localStorage.getItem('admin_token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  error => {
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  response => {
    const res = response.data
    if (res.code !== 0) {
      console.error('API Error:', res.message)
      return Promise.reject(new Error(res.message || 'Error'))
    }
    return res
  },
  error => {
    if (error.response?.status === 401) {
      if (!isRedirecting) {
        isRedirecting = true
        localStorage.removeItem('admin_token')
        localStorage.removeItem('admin_user')
        ElMessage.warning('登录已过期，请重新登录')
        setTimeout(() => {
          window.location.href = '/admin/login'
        }, 1500)
      }
      return Promise.reject(new Error('登录已过期，请重新登录'))
    }
    console.error('Request Error:', error)
    return Promise.reject(error)
  }
)

export default request

// 声明模块类型，让 TypeScript 知道 request 返回的是 data 而非 AxiosResponse
declare module 'axios' {
  interface AxiosInstance {
    request<T = any>(config: any): Promise<T>;
    get<T = any>(url: string, config?: any): Promise<T>;
    delete<T = any>(url: string, config?: any): Promise<T>;
    post<T = any>(url: string, data?: any, config?: any): Promise<T>;
    put<T = any>(url: string, data?: any, config?: any): Promise<T>;
  }
}
