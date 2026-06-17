import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import { useUserStore } from './stores/user'
import { useDeviceStore } from './stores/device'
import { useThemeStore } from './stores/theme'
import './styles/tv-focus.css'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

const userStore = useUserStore()
userStore.initFromStorage()

const deviceStore = useDeviceStore()
console.log('Platform:', deviceStore.platform)
console.log('Device Type:', deviceStore.deviceType)

// 提前初始化主题，防止首屏闪烁
const themeStore = useThemeStore()
themeStore.init()

// TV 模式键盘导航
if (deviceStore.isTV) {
  document.addEventListener('keydown', (e: KeyboardEvent) => {
    const key = e.key
    const validKeys = ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Enter', ' ']
    if (validKeys.includes(key)) {
      e.preventDefault()
    }
  })
}

app.mount('#app')
