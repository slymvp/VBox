<template>
  <Teleport to="body">
    <!-- 确认弹窗遮罩 -->
    <Transition name="modal">
      <div v-if="visible && type === 'confirm'" class="toast-overlay" @click.self="onCancel">
        <div class="toast-confirm-box">
          <div class="confirm-icon">?</div>
          <p class="confirm-message">{{ message }}</p>
          <div class="confirm-actions">
            <button class="confirm-btn cancel" @click="onCancel">取消</button>
            <button class="confirm-btn ok" @click="onConfirm">确定</button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 普通 Toast 提示 -->
    <Transition name="toast">
      <div v-if="visible && type !== 'confirm'" class="toast-container" :class="type">
        <svg v-if="type === 'success'" class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="20 6 9 17 4 12" />
        </svg>
        <svg v-else-if="type === 'error'" class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
        </svg>
        <svg v-else-if="type === 'warning'" class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
        <svg v-else class="toast-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10" /><line x1="12" y1="16" x2="12" y2="12" /><line x1="12" y1="8" x2="12.01" y2="8" />
        </svg>
        <span class="toast-message">{{ message }}</span>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { watch } from 'vue'
import { toastState } from '@/composables/useToast'

const { message, type, show: visible } = toastState

let timer: number | null = null

function onConfirm() {
  visible.value = false
  toastState.confirmCallback.value?.()
}

function onCancel() {
  visible.value = false
  toastState.cancelCallback.value?.()
}

watch(() => message.value, (newMessage) => {
  if (newMessage && type.value !== 'confirm') {
    if (timer) clearTimeout(timer)
    timer = window.setTimeout(() => {
      visible.value = false
    }, 3000)
  }
})

watch(visible, (val) => {
  if (!val && timer) {
    clearTimeout(timer)
    timer = null
  }
})
</script>

<style scoped>
/* ===== Toast 提示 ===== */
.toast-container {
  position: fixed;
  top: 80px;
  left: 50%;
  transform: translateX(-50%);
  padding: 12px 24px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
  z-index: 9999;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(10px);
}

.toast-container.success {
  background: rgba(34, 197, 94, 0.95);
  color: #fff;
}

.toast-container.error {
  background: rgba(239, 68, 68, 0.95);
  color: #fff;
}

.toast-container.warning {
  background: rgba(245, 158, 11, 0.95);
  color: #000;
}

.toast-container.info {
  background: rgba(59, 130, 246, 0.95);
  color: #fff;
}

.toast-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}

.toast-message {
  font-weight: 500;
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-20px);
}

/* ===== 确认弹窗 ===== */
.toast-overlay {
  position: fixed;
  inset: 0;
  z-index: 10000;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(2px);
}

.toast-confirm-box {
  background: var(--surface, #1e1e1e);
  border-radius: 16px;
  padding: 32px 28px 24px;
  width: 320px;
  max-width: 90vw;
  text-align: center;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.4);
}

.confirm-icon {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--primary, #6366f1);
  color: #fff;
  font-size: 28px;
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}

.confirm-message {
  font-size: 16px;
  color: var(--text-primary);
  margin: 0 0 24px;
  line-height: 1.5;
}

.confirm-actions {
  display: flex;
  gap: 12px;
}

.confirm-btn {
  flex: 1;
  padding: 12px 0;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  border: none;
  cursor: pointer;
  transition: opacity 0.2s;
}

.confirm-btn:hover {
  opacity: 0.85;
}

.confirm-btn.cancel {
  background: var(--surface-hover, #333);
  color: var(--text, #ccc);
}

.confirm-btn.ok {
  background: var(--primary, #6366f1);
  color: #fff;
}

/* ===== 确认弹窗动画 ===== */
.modal-enter-active,
.modal-leave-active {
  transition: all 0.25s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .toast-confirm-box,
.modal-leave-to .toast-confirm-box {
  transform: scale(0.9);
}

.modal-enter-active .toast-confirm-box,
.modal-leave-active .toast-confirm-box {
  transition: transform 0.25s ease;
}
</style>
