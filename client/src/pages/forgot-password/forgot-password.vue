<template>
  <div class="auth-page">
    <!-- 返回栏 -->
    <div class="auth-back-bar">
      <button class="auth-back-btn" @click="goBack" title="返回">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5"/><path d="M12 19l-7-7 7-7"/></svg>
      </button>
      <span class="auth-back-title">找回密码</span>
    </div>

    <div class="auth-card">
      <div class="auth-header">
        <h1 class="auth-title">重置密码</h1>
        <p class="auth-subtitle">请输入您的手机号以重置密码</p>
      </div>

      <form class="auth-form" @submit.prevent="handleResetPassword">
        <div class="form-group">
          <label class="form-label">手机号</label>
          <input
            v-model="formData.phone"
            type="tel"
            class="form-input"
            placeholder="请输入手机号"
            maxlength="11"
            required
          />
        </div>

        <div class="form-group">
          <label class="form-label">验证码</label>
          <div class="code-input-wrapper">
            <input
              v-model="formData.code"
              type="text"
              class="form-input code-input"
              placeholder="请输入验证码"
              maxlength="6"
            />
            <button
              type="button"
              class="send-code-btn"
              :disabled="countdown > 0 || isSending"
              @click="handleSendCode"
            >
              {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
            </button>
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">新密码</label>
          <div class="password-wrapper">
            <input
              v-model="formData.newPassword"
              :type="formData.showPassword ? 'text' : 'password'"
              class="form-input"
              placeholder="请设置新密码（至少6位）"
              minlength="6"
              required
            />
            <button
              type="button"
              class="password-toggle"
              @click="formData.showPassword = !formData.showPassword"
            >
              {{ formData.showPassword ? '👁️' : '👁️‍🗨️' }}
            </button>
          </div>
        </div>

        <button type="submit" class="submit-btn" :disabled="isLoading">
          <span v-if="isLoading" class="loading-spinner"></span>
          <span v-else>重置密码</span>
        </button>
      </form>

      <div class="auth-footer">
        <span class="footer-text">想起密码了？</span>
        <router-link to="/login" class="footer-link">返回登录</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { sendSmsCode, resetPassword } from '@/utils/api'
import { useToast } from '@/composables/useToast'
import logoImage from '/logo-icon.png'

const router = useRouter()
const toast = useToast()

function goBack() {
  router.push('/login')
}

const isLoading = ref(false)
const isSending = ref(false)
const countdown = ref(0)

const formData = reactive({
  phone: '',
  code: '',
  newPassword: '',
  showPassword: false
})

let countdownTimer: number | null = null

async function handleSendCode() {
  if (!formData.phone || formData.phone.length !== 11) {
    toast.warning('请输入正确的手机号')
    return
  }

  isSending.value = true
  try {
    const result = await sendSmsCode(formData.phone, 'reset_password')
    if (result.code) {
      toast.info(`验证码: ${result.code}`)
    }
    if (result.tip) {
      toast.info(result.tip)
    } else {
      toast.success('验证码已发送')
    }
    countdown.value = 60
    if (countdownTimer) clearInterval(countdownTimer)
    countdownTimer = window.setInterval(() => {
      countdown.value--
      if (countdown.value <= 0) {
        if (countdownTimer) clearInterval(countdownTimer)
      }
    }, 1000)
  } catch (error: any) {
    toast.error(error.message || '发送验证码失败')
  } finally {
    isSending.value = false
  }
}

async function handleResetPassword() {
  if (!formData.phone) {
    toast.warning('请填写手机号')
    return
  }
  if (!formData.code) {
    toast.warning('请填写验证码')
    return
  }
  if (!formData.newPassword || formData.newPassword.length < 6) {
    toast.warning('密码长度不能少于6位')
    return
  }

  isLoading.value = true
  try {
    await resetPassword(formData.phone, formData.code, formData.newPassword)
    toast.success('密码重置成功，请使用新密码登录')
    router.push('/login')
  } catch (error: any) {
    toast.error(error.message || '重置密码失败，请重试')
  } finally {
    isLoading.value = false
  }
}

onUnmounted(() => {
  if (countdownTimer) {
    clearInterval(countdownTimer)
  }
})
</script>

<style lang="scss" scoped>
.auth-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--background);
  padding: 60px 20px 20px;
  position: relative;
}

/* ========== 返回栏 ========== */
.auth-back-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 12px 4px;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 1001;
  background: var(--surface);
}

.auth-back-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: var(--text-primary);
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.2s ease;

  &:hover {
    background: var(--surface-hover);
  }
}

.auth-back-title {
  font-size: 16px;
  color: var(--text-primary);
  flex: 1;
  text-align: center;
}

.auth-card {
  width: 100%;
  max-width: 420px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 40px;
  backdrop-filter: blur(20px);
}

.auth-header {
  text-align: center;
  margin-bottom: 32px;
}

.auth-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-bottom: 20px;
}

.logo-img-wrapper {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  overflow: hidden;
}

.auth-logo-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.auth-logo-text {
  font-size: 20px;
  font-weight: 700;
  color: var(--gold);
}

.auth-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.auth-subtitle {
  font-size: 14px;
  color: var(--text-muted);
  margin: 0;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.form-input {
  width: 100%;
  padding: 14px 16px;
  background: var(--background);
  border: 1px solid var(--border);
  border-radius: 12px;
  font-size: 15px;
  color: var(--text-primary);
  transition: all 0.3s ease;
  box-sizing: border-box;

  &::placeholder {
    color: var(--text-muted);
  }

  &:focus {
    outline: none;
    border-color: var(--gold);
    box-shadow: 0 0 0 3px var(--gold-glow);
  }
}

.password-wrapper {
  position: relative;
}

.password-toggle {
  position: absolute;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  cursor: pointer;
  font-size: 18px;
  opacity: 0.6;
  color: var(--text-muted);
  transition: opacity 0.2s;
}

.password-toggle:hover {
  opacity: 1;
}

.code-input-wrapper {
  display: flex;
  gap: 12px;
}

.code-input {
  flex: 1;
}

.send-code-btn {
  padding: 0 20px;
  background: var(--gold);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  white-space: nowrap;

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  &:hover:not(:disabled) {
    opacity: 0.9;
  }
}

.agreement {
  display: flex;
  gap: 8px;
  font-size: 13px;
  color: var(--text-muted);
  align-items: flex-start;
}

.agreement input[type="checkbox"] {
  margin-top: 2px;
  width: 16px;
  height: 16px;
}

.link {
  color: var(--gold);
  text-decoration: none;

  &:hover {
    text-decoration: underline;
  }
}

.submit-btn {
  width: 100%;
  padding: 15px;
  background: var(--gold);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;

  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  &:hover:not(:disabled) {
    opacity: 0.9;
  }
}

.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.auth-footer {
  text-align: center;
  margin-top: 24px;
  font-size: 14px;
  color: var(--text-muted);
}

.footer-link {
  color: var(--gold);
  text-decoration: none;
  margin-left: 4px;

  &:hover {
    text-decoration: underline;
  }
}
</style>
