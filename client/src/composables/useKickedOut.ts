import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore, KICKED_OUT_CODE as USER_KICKED_OUT_CODE, setKickedOutHandler } from '@/stores/user'
import { setKickedOutCallback, KICKED_OUT_CODE as API_KICKED_OUT_CODE } from '@/utils/api'
import { useToast } from '@/composables/useToast'

const showKickedOutModal = ref(false)
let initialized = false

export const KICKED_OUT_CODE = API_KICKED_OUT_CODE

export function useKickedOut() {
  const router = useRouter()
  const userStore = useUserStore()
  const toast = useToast()

  function initKickedOutHandler() {
    if (initialized) return
    initialized = true

    const handler = () => {
      showKickedOutModal.value = true
    }

    // 设置 store 和 api 的踢出处理函数
    setKickedOutHandler(handler)
    setKickedOutCallback(handler)
  }

  function closeKickedOutModal() {
    showKickedOutModal.value = false
    userStore.logout()
    router.push('/')
  }

  function goToLogin() {
    showKickedOutModal.value = false
    userStore.logout()
    router.push('/login')
  }

  /**
   * 检查API响应，如果返回踢出错误码则触发踢出处理
   */
  function checkKickedOutResponse(data: { code?: number; message?: string }): boolean {
    if (data.code === KICKED_OUT_CODE) {
      showKickedOutModal.value = true
      return true
    }
    return false
  }

  return {
    showKickedOutModal,
    initKickedOutHandler,
    closeKickedOutModal,
    goToLogin,
    checkKickedOutResponse,
    KICKED_OUT_CODE
  }
}
