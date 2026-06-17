import { ref } from 'vue'

export type ToastType = 'success' | 'error' | 'warning' | 'info' | 'confirm'

export interface ToastOptions {
  message: string
  type?: ToastType
  duration?: number
  onConfirm?: () => void
  onCancel?: () => void
}

const message = ref('')
const type = ref<ToastType>('info')
const duration = ref(3000)
const show = ref(false)
const confirmCallback = ref<(() => void) | null>(null)
const cancelCallback = ref<(() => void) | null>(null)

let timer: number | null = null

export function useToast() {
  function toast(options: ToastOptions) {
    message.value = options.message
    type.value = options.type || 'info'
    duration.value = options.duration || 3000
    confirmCallback.value = options.onConfirm || null
    cancelCallback.value = options.onCancel || null
    show.value = true

    if (timer) clearTimeout(timer)
    // confirm 类型不自动关闭
    if (options.type !== 'confirm') {
      timer = window.setTimeout(() => {
        show.value = false
      }, duration.value)
    }
  }

  function success(msg: string, duration?: number) {
    toast({ message: msg, type: 'success', duration })
  }

  function error(msg: string, duration?: number) {
    toast({ message: msg, type: 'error', duration })
  }

  function warning(msg: string, duration?: number) {
    toast({ message: msg, type: 'warning', duration })
  }

  function info(msg: string, duration?: number) {
    toast({ message: msg, type: 'info', duration })
  }

  function confirm(msg: string, onConfirm?: () => void, onCancel?: () => void) {
    toast({ message: msg, type: 'confirm', onConfirm, onCancel })
  }

  function dismiss() {
    show.value = false
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
  }

  return {
    message,
    type,
    show,
    toast,
    success,
    error,
    warning,
    info,
    confirm,
    dismiss
  }
}

export const toastState = {
  message,
  type,
  show,
  confirmCallback,
  cancelCallback
}
