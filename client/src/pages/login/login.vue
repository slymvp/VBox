<template>
  <div class="auth-page">
    <!-- 返回栏（移动端和PC端通用） -->
    <div class="auth-back-bar">
      <button class="auth-back-btn" @click="goBack" title="返回">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5"/><path d="M12 19l-7-7 7-7"/></svg>
      </button>
      <span class="auth-back-title">登录</span>
    </div>

    <div class="auth-card">
      <div class="auth-header">
        <h1 class="auth-title">欢迎回来</h1>
        <p class="auth-subtitle">登录 VBox，畅享精彩内容</p>
      </div>

      <div class="login-tabs">
        <button
          class="tab-btn"
          :class="{ active: loginMode === 'sms' }"
          @click="loginMode = 'sms'"
        >
          验证码登录
        </button>
        <button
          class="tab-btn"
          :class="{ active: loginMode === 'password' }"
          @click="loginMode = 'password'"
        >
          密码登录
        </button>
      </div>

      <form class="auth-form" @submit.prevent="handleLogin">
        <template v-if="loginMode === 'sms'">
          <div class="form-group">
            <label class="form-label">手机号</label>
            <input
              v-model="smsForm.phone"
              type="tel"
              class="form-input"
              placeholder="请输入手机号"
              maxlength="11"
              required
            />
          </div>

          <div class="form-group">
            <label class="form-label">验证码 <span class="test-tip">（测试阶段随便填）</span></label>
            <div class="code-input-wrapper">
              <input
                v-model="smsForm.code"
                type="text"
                class="form-input code-input"
                placeholder="测试阶段任意输入"
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
        </template>

        <template v-else>
          <div class="form-group">
            <label class="form-label">手机号 / 用户名</label>
            <input
              v-model="passwordForm.username"
              type="text"
              class="form-input"
              placeholder="请输入手机号或用户名"
              required
            />
          </div>

          <div class="form-group">
            <label class="form-label">密码</label>
            <div class="password-wrapper">
              <input
                v-model="passwordForm.password"
                :type="showPassword ? 'text' : 'password'"
                class="form-input"
                placeholder="请输入密码"
                required
              />
              <button
                type="button"
                class="password-toggle"
                @click="showPassword = !showPassword"
              >
                {{ showPassword ? '👁️' : '👁️‍🗨️' }}
              </button>
            </div>
          </div>

          <div class="form-options">
            <label class="remember-me">
              <input v-model="passwordForm.remember" type="checkbox" />
              <span>记住我</span>
            </label>
            <router-link to="/forgot-password" class="forgot-link">忘记密码？</router-link>
          </div>
        </template>

        <button type="submit" class="submit-btn" :disabled="isLoading">
          <span v-if="isLoading" class="loading-spinner"></span>
          <span v-else>登录</span>
        </button>
      </form>

      <div class="auth-footer">
        <span class="footer-text">还没有账号？</span>
        <router-link to="/register" class="footer-link">立即注册</router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useDeviceStore } from '@/stores/device'
import { smsLogin, sendSmsCode, passwordLogin } from '@/utils/api'
import { useToast } from '@/composables/useToast'
import logoImage from '/logo-icon.png'

const router = useRouter()
const userStore = useUserStore()
const deviceStore = useDeviceStore()
const toast = useToast()

function goBack() {
  const lastCategory = sessionStorage.getItem('lastCategory') || '/tv'
  router.push(lastCategory)
}

const loginMode = ref<'sms' | 'password'>('sms')
const showPassword = ref(false)
const isLoading = ref(false)
const isSending = ref(false)
const countdown = ref(0)

const smsForm = reactive({
  phone: '',
  code: ''
})

const passwordForm = reactive({
  username: '',
  password: '',
  remember: false
})

let countdownTimer: number | null = null

async function handleSendCode() {
  if (!smsForm.phone || smsForm.phone.length !== 11) {
    toast.warning('请输入正确的手机号')
    return
  }

  isSending.value = true
  try {
    const result = await sendSmsCode(smsForm.phone, 'login')
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

async function handleLogin() {
  if (isLoading.value) return

  isLoading.value = true

  try {
    if (loginMode.value === 'sms') {
      if (!smsForm.phone) {
        toast.warning('请填写手机号')
        return
      }
      const result = await smsLogin(smsForm.phone, smsForm.code)
      userStore.setLogin(result.access_token, result.refresh_token, result.user)
      toast.success('登录成功')
      router.push(deviceStore.isMobile ? '/user' : '/')
    } else {
      if (!passwordForm.username || !passwordForm.password) {
        toast.warning('请填写用户名和密码')
        return
      }
      const result = await passwordLogin(passwordForm.username, passwordForm.password)
      userStore.setLogin(result.access_token, result.refresh_token, result.user)
      toast.success('登录成功')
      router.push(deviceStore.isMobile ? '/user' : '/')
    }
  } catch (error: any) {
    toast.error(error.message || '登录失败，请重试')
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

.auth-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: var(--background);
  padding: 60px 20px 20px;
  position: relative;
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
  margin-bottom: 24px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
}

.logo-img-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: transparent !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
}

.auth-logo-img {
  width: 60px;
  height: 60px;
  object-fit: contain;
  background-color: transparent !important;
  border: none !important;
  outline: none !important;
  box-shadow: none !important;
  filter: drop-shadow(0 0 6px rgba(251, 191, 36, 0.4));
  transition: filter 0.3s ease;
}

.auth-logo-text {
  font-size: 36px;
  font-weight: 900;
  background: linear-gradient(135deg, #fde68a 0%, var(--gold-light) 30%, var(--gold-dark) 70%, #92400e 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: 3px;
  position: relative;
  filter: drop-shadow(0 0 8px rgba(251, 191, 36, 0.3));
}

.auth-logo-text::after {
  content: 'VBOX';
  position: absolute;
  left: 0;
  top: 0;
  background: linear-gradient(135deg, #fde68a, var(--gold-light), var(--gold-dark));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: 3px;
  opacity: 0;
  filter: blur(10px);
  animation: logoGlow 3s ease-in-out infinite;
}

@keyframes logoGlow {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 0.7; }
}

.auth-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.auth-subtitle {
  font-size: 14px;
  color: var(--text-muted);
  margin: 0;
}

.login-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
  padding: 4px;
  background: var(--background);
  border-radius: 12px;
}

.tab-btn {
  flex: 1;
  padding: 12px 16px;
  background: transparent;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.3s ease;

  &.active {
    background: linear-gradient(135deg, var(--gold-light), var(--gold-dark));
    color: #000;
    font-weight: 600;
  }

  &:hover:not(.active) {
    color: var(--text-primary);
  }
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
  color: var(--text-secondary);
}

.test-tip {
  font-size: 12px;
  font-weight: 400;
  color: var(--gold);
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

  &::placeholder {
    color: var(--text-muted);
  }

  &:focus {
    outline: none;
    border-color: var(--gold);
    box-shadow: 0 0 0 3px var(--gold-glow);
  }
}

.code-input-wrapper {
  display: flex;
  gap: 12px;
}

.code-input {
  flex: 1;
}

.send-code-btn {
  padding: 14px 16px;
  background: var(--surface-light);
  border: 1px solid var(--border-light);
  border-radius: 12px;
  font-size: 13px;
  font-weight: 600;
  color: var(--gold);
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.3s ease;

  &:hover:not(:disabled) {
    background: var(--gold);
    color: #000;
    border-color: var(--gold);
  }

  &:disabled {
    color: var(--text-muted);
    cursor: not-allowed;
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

  &:hover {
    opacity: 1;
  }
}

.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.remember-me {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--text-muted);
  cursor: pointer;

  input[type="checkbox"] {
    width: 16px;
    height: 16px;
    accent-color: var(--gold);
  }
}

.forgot-link {
  font-size: 14px;
  color: var(--gold);
  text-decoration: none;
  transition: color 0.2s;

  &:hover {
    color: var(--gold-light);
  }
}

.submit-btn {
  width: 100%;
  padding: 16px;
  background: linear-gradient(135deg, var(--gold-light), var(--gold-dark));
  border: none;
  border-radius: 12px;
  font-size: 16px;
  font-weight: 600;
  color: #000;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;

  &:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px var(--gold-glow);
  }

  &:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }
}

.loading-spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(0, 0, 0, 0.3);
  border-top-color: #000;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.auth-footer {
  margin-top: 28px;
  text-align: center;
  font-size: 14px;
  color: var(--text-muted);
}

.footer-link {
  color: var(--gold);
  text-decoration: none;
  font-weight: 500;
  margin-left: 4px;
  transition: color 0.2s;

  &:hover {
    color: var(--gold-light);
  }
}

@media (max-width: 480px) {
  .auth-card {
    padding: 28px 20px;
  }

  .auth-title {
    font-size: 22px;
  }
}
</style>



