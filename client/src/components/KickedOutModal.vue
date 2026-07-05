<template>
  <div v-if="show" class="kicked-out-modal" @click="close">
    <div class="modal-content" @click.stop>
      <div class="modal-icon">⚠️</div>
      <div class="modal-title">账号已被踢出</div>
      <div class="modal-desc">您的账号在其他同类型设备上登录，当前设备已被强制退出</div>
      <div class="modal-actions">
        <button class="modal-btn modal-btn-secondary" @click="close">返回首页</button>
        <button class="modal-btn modal-btn-primary" @click="goLogin">重新登录</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useKickedOut } from '@/composables/useKickedOut'

const { showKickedOutModal: show, closeKickedOutModal: close, goToLogin: goLogin } = useKickedOut()
</script>

<style lang="scss" scoped>
.kicked-out-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 99999;
}

.modal-content {
  background: #1a1a2e;
  border-radius: 16px;
  padding: 32px;
  text-align: center;
  max-width: 320px;
  width: 90%;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
}

.modal-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.modal-title {
  font-size: 20px;
  font-weight: 600;
  color: #fff;
  margin-bottom: 8px;
}

.modal-desc {
  font-size: 14px;
  color: #e6e6e6;
  margin-bottom: 24px;
}

.modal-actions {
  display: flex;
  gap: 12px;
}

.modal-btn {
  flex: 1;
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  border: none;
  white-space: nowrap;
  transition: opacity 0.2s;

  &:active {
    opacity: 0.9;
  }
}

.modal-btn-secondary {
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
}

.modal-btn-primary {
  background: linear-gradient(135deg, #f59e0b, #d97706);
  color: #fff;
}
</style>