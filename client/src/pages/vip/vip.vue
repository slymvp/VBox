<template>
  <div class="vip-page">
    <component v-if="!deviceStore.isMobile" :is="headerComponent" />

    <div class="vip-container">
      <!-- 左侧导航 -->
      <aside class="sidebar-nav">
        <div :class="['sidebar-profile', { 'is-vip-user': vipStatus && vipStatus.is_vip && !vipStatus.is_expired }]">
          <div :class="['sidebar-avatar', { 'is-vip': vipStatus && vipStatus.is_vip && !vipStatus.is_expired }]">
            <div class="avatar-icon">
              <template v-if="vipStatus && vipStatus.is_vip && !vipStatus.is_expired">👑</template>
              <template v-else>👤</template>
            </div>
            <div v-if="vipStatus && vipStatus.is_vip && !vipStatus.is_expired" class="vip-badge">VIP</div>
          </div>
          <div :class="['sidebar-title', { 'is-vip-title': vipStatus && vipStatus.is_vip && !vipStatus.is_expired }]">
            <template v-if="vipStatus && vipStatus.is_vip && !vipStatus.is_expired">会员</template>
            <template v-else>普通用户</template>
          </div>
          <div v-if="vipStatus" class="sidebar-expire">
            <span v-if="vipStatus.is_vip && !vipStatus.is_expired">
              剩余 <span class="days-count">{{ vipStatus.remaining_days }}</span> 天
            </span>
            <span v-else-if="vipStatus.is_expired" class="expired">
              会员已过期，请续费
            </span>
            <span v-else class="not-vip">
              立即开通VIP
            </span>
          </div>
          <div v-else class="sidebar-expire loading">
            <span class="loading-dots">加载中</span>
          </div>
          <!-- 已开通套餐 -->
          <div v-if="vipStatus && vipStatus.vip_plans && vipStatus.vip_plans.length > 0" class="sidebar-plans">
            <div class="plans-title">已开通套餐</div>
            <div class="plans-list">
              <div v-for="plan in vipStatus.vip_plans" :key="plan.id" class="plan-item">
                <span class="plan-name">{{ plan.name }}</span>
                <span v-if="plan.terminal" class="plan-terminal">{{ formatTerminal(plan.terminal) }}</span>
              </div>
            </div>
          </div>
        </div>
        <nav class="sidebar-menu">
          <div
            :class="['sidebar-menu-item', { active: activeTab === 'pay' }]"
            @click="activeTab = 'pay'"
          >
            <span class="menu-icon">👑</span>
            <span class="menu-label">开通会员</span>
          </div>
          <div
            :class="['sidebar-menu-item', { active: activeTab === 'cdkey' }]"
            @click="activeTab = 'cdkey'"
          >
            <span class="menu-icon">🔑</span>
            <span class="menu-label">卡密兑换</span>
          </div>
          <div
            :class="['sidebar-menu-item', { active: activeTab === 'orders' }]"
            @click="activeTab = 'orders'"
          >
            <span class="menu-icon">📋</span>
            <span class="menu-label">我的订单</span>
          </div>
        </nav>
      </aside>

      <!-- 右侧内容区 -->
      <div class="content-area">
      <!-- 开通会员页签 -->
      <div v-if="activeTab === 'pay'" class="pay-section">
        <!-- 会员特权展示 -->
        <div class="privilege-section">
          <h2 class="section-title">
            <span class="title-icon">✨</span>
            VIP尊享特权
          </h2>
          <div class="privilege-grid">
            <div class="privilege-card" v-for="item in privileges" :key="item.icon">
              <div class="privilege-icon">{{ item.icon }}</div>
              <div class="privilege-name">{{ item.name }}</div>
              <div class="privilege-desc">{{ item.desc }}</div>
            </div>
          </div>
        </div>

        <!-- 套餐选择 -->
        <div class="plan-section">
          <h2 class="section-title">
            <span class="title-icon">💎</span>
            选择套餐
          </h2>

          <!-- 提示语 -->
          <div v-if="currentPlanTip" class="plan-tip">
            <span class="tip-icon">💡</span>
            <span class="tip-text">{{ currentPlanTip }}</span>
          </div>

          <!-- 套餐列表 -->
          <div class="plan-grid">
            <div
              v-for="plan in plans"
              :key="plan.id"
              :class="['plan-card', { active: selectedPlans.includes(plan.id), recommend: plan.is_recommend }]"
              @click="togglePlan(plan.id)"
            >
              <div class="plan-checkbox">
                <input
                  type="checkbox"
                  :checked="selectedPlans.includes(plan.id)"
                  @click.stop="togglePlan(plan.id)"
                  :id="`plan-${plan.id}`"
                />
                <label :for="`plan-${plan.id}`"></label>
              </div>
              <div v-if="plan.is_recommend" class="plan-badge">推荐</div>
              <div class="plan-content">
                <div class="plan-name">{{ plan.name }}</div>
                <div class="plan-main">
                  <div class="plan-price">
                    <span class="price-symbol">¥</span>
                    <span class="price-amount">{{ formatPrice(plan.price) }}</span>
                  </div>
                  <div class="plan-original" v-if="plan.original_price">
                    原价 ¥{{ formatPrice(plan.original_price) }}
                  </div>
                  <div v-if="plan.save_amount" class="plan-save">省 ¥{{ formatPrice(plan.save_amount) }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 支付通道 -->
        <div class="payment-section">
          <!-- 套餐汇总 -->
          <div class="selected-summary">
            <div class="summary-title">
              <span class="summary-icon">📋</span>
              <span>已选套餐</span>
            </div>
            <div class="summary-content">
              <div v-if="selectedPlans.length > 0" class="selected-plans">
                <div v-for="planId in selectedPlans" :key="planId" class="selected-plan-item">
                  {{ getPlanName(planId) }} - ¥{{ formatPrice(getPlanPrice(planId)) }}
                </div>
              </div>
              <div v-else class="no-selection">
                请选择套餐
              </div>
            </div>
            <div class="summary-total">
              <span class="total-label">合计金额：</span>
              <span class="total-price">¥{{ formatPrice(totalPrice) }}</span>
            </div>
          </div>

          <!-- 微信通道 -->
          <div class="channel-card wechat-channel">
            <div class="channel-header">
              <span class="channel-icon wechat-icon">
                <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor">
                  <path d="M8.691 2.188C3.891 2.188 0 5.476 0 9.53c0 2.212 1.17 4.203 3.002 5.55a.59.59 0 0 1 .213.665l-.39 1.48c-.019.07-.048.141-.048.213 0 .163.13.295.29.295a.326.326 0 0 0 .167-.054l1.903-1.114a.864.864 0 0 1 .717-.098 10.16 10.16 0 0 0 2.837.403c.276 0 .543-.027.811-.05-.857-2.578.157-4.972 1.932-6.446 1.703-1.415 3.882-1.98 5.853-1.838-.576-3.583-4.196-6.348-8.596-6.348zM5.785 5.991c.642 0 1.162.529 1.162 1.18a1.17 1.17 0 0 1-1.162 1.178A1.17 1.17 0 0 1 4.623 7.17c0-.651.52-1.18 1.162-1.18zm5.813 0c.642 0 1.162.529 1.162 1.18a1.17 1.17 0 0 1-1.162 1.178 1.17 1.17 0 0 1-1.162-1.178c0-.651.52-1.18 1.162-1.18zm5.34 2.867c-1.797-.052-3.746.512-5.28 1.786-1.72 1.428-2.687 3.72-1.78 6.22.942 2.453 3.666 4.229 6.884 4.229.826 0 1.622-.12 2.361-.336a.722.722 0 0 1 .598.082l1.584.926a.272.272 0 0 0 .14.047c.134 0 .24-.111.24-.247 0-.06-.023-.12-.038-.177l-.327-1.233a.582.582 0 0 1-.023-.156.49.49 0 0 1 .201-.398C23.024 18.48 24 16.82 24 14.98c0-3.21-2.931-5.837-7.062-6.122zM14.033 13.3c.535 0 .969.44.969.982a.976.976 0 0 1-.969.983.976.976 0 0 1-.969-.983c0-.542.434-.982.97-.982zm4.844 0c.535 0 .969.44.969.982a.976.976 0 0 1-.969.983.976.976 0 0 1-.969-.983c0-.542.434-.982.97-.982z"/>
                </svg>
              </span>
              <div class="channel-title-group">
                <h3 class="channel-title">微信通道</h3>
                <p class="channel-subtitle">🔑 开通专属服务（微信通道）</p>
              </div>
            </div>
            <div class="channel-body">
              <div class="qrcode-wrapper">
                <div class="qrcode-placeholder">
                  <div class="qrcode-mock">
                    <div class="qr-grid">
                      <div class="qr-corner tl"></div>
                      <div class="qr-corner tr"></div>
                      <div class="qr-corner bl"></div>
                      <div class="qr-center"></div>
                      <div class="qr-corner br"></div>
                    </div>
                  </div>
                  <p class="qrcode-tip">请使用微信扫一扫</p>
                </div>
              </div>
              <div class="channel-instructions">
                <p class="instruction-text">请扫码转账 <span class="highlight-price">{{ formatPrice(totalPrice) }} 元</span>，务必备注：<span class="highlight-tag">你的微信号 + {{ selectedPlans.length }}</span></p>
                <p class="instruction-text">转账成功后，系统将自动发送激活密钥到你的微信，无需等待。</p>
              </div>
            </div>
          </div>

          <!-- 支付宝备用通道 -->
          <div class="channel-card alipay-channel">
            <div class="channel-header">
              <span class="channel-icon alipay-icon">
                <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor">
                  <path d="M21.422 15.358c-3.32-1.326-6.092-3.014-6.092-3.014s1.439-3.667 1.853-5.943H13.01V4.79h5.16V3.478h-5.16V.296h-2.384s-.036.012-.036.048v3.134H5.43v1.312h5.16V6.4H6.18v1.312h8.492c-.317 1.467-1.108 3.66-1.108 3.66s-3.926-1.6-6.968-2.22C3.554 8.53 0 10.39 0 13.692c0 3.302 2.856 5.048 5.508 5.296 2.652.248 5.196-.744 7.236-2.436 1.236 1.068 2.64 2.052 4.356 2.94l1.2-2.22c-1.596-.744-2.964-1.656-4.164-2.64.012-.012.036-.024.048-.036 0 0 2.82 1.704 6.216 3.06l1.032-2.298z"/>
                </svg>
              </span>
              <div class="channel-title-group">
                <h3 class="channel-title">备用通道（支付宝）</h3>
                <p class="channel-subtitle">🔑 备用通道（支付宝）</p>
              </div>
            </div>
            <div class="channel-body">
              <div class="alipay-link-area">
                <a href="https://example.com/buy" target="_blank" class="alipay-link" rel="noopener noreferrer">
                  <span class="link-icon">🔗</span>
                  点击此处自助购卡
                </a>
                <span class="link-arrow">→</span>
                <span class="link-step">支付宝付款</span>
                <span class="link-arrow">→</span>
                <span class="link-step">立即自动出密钥</span>
              </div>
              <p class="alipay-note">全程自助，24 小时可用。</p>
            </div>
          </div>
        </div>
      </div>

      <!-- 卡密兑换页签 -->
      <div v-if="activeTab === 'cdkey'" class="cdkey-section">
        <div class="cdkey-card">
          <div class="cdkey-header">
            <div class="cdkey-icon-wrap">🔑</div>
            <h2 class="cdkey-title">卡密兑换</h2>
            <p class="cdkey-desc">输入您获取的卡密兑换码，即可激活对应会员权益</p>
          </div>

          <div class="cdkey-form">
            <div class="input-group">
              <label class="input-label">卡密兑换码</label>
              <div class="input-wrapper">
                <input
                  v-model="cdkeyCode"
                  type="text"
                  class="cdkey-input"
                  placeholder="请输入卡密兑换码"
                  maxlength="32"
                  @input="onCdkeyInput"
                />
                <button v-if="cdkeyCode" class="input-clear" @click="cdkeyCode = ''">✕</button>
              </div>
              <div class="input-hint">
                <span>卡密为16-32位字母数字组合</span>
                <span class="char-count">{{ cdkeyCode.length }}/32</span>
              </div>
            </div>

            <div class="input-group">
              <label class="input-label">激活终端类型</label>
              <div class="terminal-options">
                <div
                  v-for="option in terminalOptions"
                  :key="option.value"
                  :class="['terminal-option', { active: selectedTerminal === option.value }]"
                  @click="selectedTerminal = option.value"
                >
                  <span class="terminal-icon">{{ option.icon }}</span>
                  <span class="terminal-label">{{ option.label }}</span>
                </div>
              </div>
            </div>

            <button
              :class="['cdkey-submit', { disabled: !cdkeyCode.trim(), loading: isSubmitting }]"
              :disabled="!cdkeyCode.trim() || isSubmitting"
              @click="handleCdkeySubmit"
            >
              <span v-if="isSubmitting" class="btn-loading"></span>
              <span v-else>激活</span>
            </button>

            <div class="cdkey-tips">
              <h3 class="tips-title">💡 使用须知</h3>
              <ul class="tips-list">
                <li>卡密兑换码为一次性使用，兑换后即失效</li>
                <li>每个账号仅可使用同一卡密一次</li>
                <li>卡密兑换的会员时长将叠加至当前会员有效期</li>
                <li>如兑换遇到问题，请联系客服处理</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <!-- 我的订单页签 -->
      <div v-if="activeTab === 'orders'" class="orders-section">
        <div class="orders-card">
          <div class="orders-header">
            <div class="orders-icon-wrap">📋</div>
            <h2 class="orders-title">我的订单</h2>
            <p class="orders-desc">查看您的VIP会员购买记录</p>
          </div>

          <div v-if="loadingOrders" class="orders-loading">
            <div class="loading-spinner"></div>
            <p>加载订单中...</p>
          </div>

          <div v-else-if="orders.length > 0" class="orders-list">
            <div v-for="order in orders" :key="order.id" class="order-item">
              <div class="order-left">
                <div class="order-icon">💎</div>
                <div class="order-info">
                  <div class="order-name">{{ order.plan_name || 'VIP会员套餐' }}</div>
                  <div class="order-time">订单号：{{ order.order_no }} · {{ formatTime(order.created_at) }}</div>
                </div>
              </div>
              <div class="order-right">
                <div class="order-price">¥{{ order.amount }}</div>
                <div :class="['order-status', order.pay_status]">{{ getStatusText(order.pay_status) }}</div>
              </div>
            </div>
          </div>

          <div v-else class="orders-empty">
            <div class="empty-icon">📦</div>
            <p class="empty-text">暂无订单记录</p>
            <button class="go-buy-btn" @click="activeTab = 'pay'">去开通VIP</button>
          </div>
        </div>
      </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useDeviceStore } from '@/stores/device'
import { useToast } from '@/composables/useToast'
import PcHeader from '@/components/pc/Header.vue'
import MobileHeader from '@/components/mobile/Header.vue'
import { getVipStatus, redeemCdkey, getMyVipOrders, getVipPlans, type VipStatus, type VipPlan, type VipOrder, type VipPlanConfig } from '@/utils/api'

const router = useRouter()
const userStore = useUserStore()
const deviceStore = useDeviceStore()
const { showToast } = useToast()

// 根据设备类型选择 Header
const headerComponent = computed(() => {
  return deviceStore.isMobile ? MobileHeader : PcHeader
})

const activeTab = ref<'pay' | 'cdkey' | 'orders'>('pay')
const selectedPlans = ref<number[]>([])
const cdkeyCode = ref('')
const selectedTerminal = ref<'mobile' | 'tv' | 'pc'>('mobile')
const isSubmitting = ref(false)
const loadingOrders = ref(false)
const loadingPlans = ref(false)
const vipStatus = ref<VipStatus | null>(null)
const plans = ref<VipPlan[]>([])
const orders = ref<VipOrder[]>([])
const planConfigs = ref<Record<string, VipPlanConfig>>({})

// 终端类型选项
const terminalOptions = [
  { value: 'mobile', label: '移动端', icon: '📱' },
  { value: 'tv', label: 'TV端', icon: '📺' },
  { value: 'pc', label: 'PC端', icon: '💻' }
]

// 会员特权
const privileges = [
  { icon: '🎬', name: '超级片库', desc: '全网资源任意播' },
  { icon: '🚀', name: '每日更新', desc: '各种免费/VIP影视' },
  { icon: '📺', name: '极速加载', desc: '专属CDN通道加速' },
  { icon: '🎁', name: '用户至上', desc: '可定制功能，打造专属' },
  { icon: '🎯', name: '优先更新', desc: '新剧第一时间推送' },
  { icon: '💬', name: '专属客服', desc: '7×24小时VIP通道' },
]

const totalPrice = computed(() => {
  return selectedPlans.value.reduce((sum, planId) => {
    const plan = plans.value.find(p => p.id === planId)
    return sum + (plan ? plan.price : 0)
  }, 0)
})

// 格式化价格，保留一位小数
function formatPrice(price: number): string {
  return price.toFixed(1)
}

// 格式化终端类型
function formatTerminal(terminal: string): string {
  if (!terminal) return ''
  const labels: Record<string, string> = {
    mobile: '移动端',
    tv: 'TV端',
    pc: 'PC端'
  }
  const parts = terminal.split(',').map(t => labels[t.trim()] || t.trim())
  return parts.filter(Boolean).join(' ')
}

function getPlanName(planId: number): string {
  const plan = plans.value.find(p => p.id === planId)
  return plan ? plan.name : ''
}

function getPlanPrice(planId: number): number {
  const plan = plans.value.find(p => p.id === planId)
  return plan ? plan.price : 0
}

function togglePlan(planId: number) {
  const index = selectedPlans.value.indexOf(planId)
  if (index > -1) {
    selectedPlans.value.splice(index, 1)
  } else {
    selectedPlans.value.push(planId)
  }
}

const currentPlanTip = computed(() => {
  // 优先显示正式套餐的提示语，如果没有，再显示优惠套餐的提示语
  if (planConfigs.value.formal?.tip_text) {
    return planConfigs.value.formal.tip_text
  }
  if (planConfigs.value.promotion?.tip_text) {
    return planConfigs.value.promotion.tip_text
  }
  return ''
})

const isCdkeyValid = computed(() => {
  return cdkeyCode.value.trim().length >= 16
})

function onCdkeyInput() {
  // 只允许字母数字
  cdkeyCode.value = cdkeyCode.value.replace(/[^a-zA-Z0-9]/g, '')
}

function formatTime(timeStr: string): string {
  const date = new Date(timeStr)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}

function getStatusText(status: string): string {
  const statusMap: Record<string, string> = {
    pending: '待支付',
    paid: '已支付',
    refund: '已退款'
  }
  return statusMap[status] || status
}

async function fetchVipStatus() {
  // 检查是否有 token
  const token = localStorage.getItem('access_token') || localStorage.getItem('token')
  if (!token) return

  try {
    const result = await getVipStatus()
    if (result.code === 0) {
      vipStatus.value = result.data

      // 更新用户store中的vip信息
      if (userStore.user) {
        userStore.user.is_vip = result.data.is_vip
        userStore.user.vip_expire_at = result.data.vip_expire_at
      }
    }
  } catch (error) {
    console.error('获取VIP状态失败:', error)
  }
}

async function fetchPlans() {
  loadingPlans.value = true
  try {
    const result = await getVipPlans()
    if (result.code === 0 && result.data) {
      // 保存配置
      if (result.data.configs) {
        planConfigs.value = result.data.configs
      }

      if (result.data.plans && result.data.plans.length > 0) {
        plans.value = result.data.plans
        // 默认全选中所有套餐
        selectedPlans.value = plans.value.map(p => p.id)
      } else {
        // 如果没有套餐，使用默认套餐
        plans.value = [
          { id: 1, name: '月度会员', price: 10, original_price: 20, duration_days: 30, save_amount: 10, is_recommend: false, plan_type: 'monthly', duration_type: 'monthly' },
          { id: 2, name: '季度会员', price: 25, original_price: 55, duration_days: 90, save_amount: 30, is_recommend: false, plan_type: 'quarterly', duration_type: 'quarterly' },
          { id: 3, name: '年度会员', price: 88, original_price: 198, duration_days: 365, save_amount: 110, is_recommend: true, plan_type: 'yearly', duration_type: 'yearly' },
        ]
        // 默认全选中所有套餐
        selectedPlans.value = plans.value.map(p => p.id)
      }
    }
  } catch (error) {
    console.error('获取套餐失败:', error)
    // 使用默认套餐
    plans.value = [
      { id: 1, name: '月度会员', price: 10, original_price: 20, duration_days: 30, save_amount: 10, is_recommend: false, plan_type: 'monthly', duration_type: 'monthly' },
      { id: 2, name: '季度会员', price: 25, original_price: 55, duration_days: 90, save_amount: 30, is_recommend: false, plan_type: 'quarterly', duration_type: 'quarterly' },
      { id: 3, name: '年度会员', price: 88, original_price: 198, duration_days: 365, save_amount: 110, is_recommend: true, plan_type: 'yearly', duration_type: 'yearly' },
    ]
    // 默认全选中所有套餐
    selectedPlans.value = plans.value.map(p => p.id)
  } finally {
    loadingPlans.value = false
  }
}

async function fetchOrders() {
  if (!userStore.isLoggedIn) return

  loadingOrders.value = true
  try {
    const result = await getMyVipOrders(1, 20)
    if (result.code === 0) {
      orders.value = result.data.items || []
    }
  } catch (error) {
    console.error('获取订单失败:', error)
  } finally {
    loadingOrders.value = false
  }
}

async function handleCdkeySubmit() {
  if (!isCdkeyValid.value || isSubmitting.value) return

  if (!userStore.isLoggedIn) {
    showToast('请先登录后再兑换卡密', 'warning')
    router.push('/login')
    return
  }

  isSubmitting.value = true
  try {
    const result = await redeemCdkey(cdkeyCode.value.trim())
    if (result.code === 0) {
      showToast(`🎉 卡密兑换成功，获得${result.data.duration_days}天会员！`, 'success')
      cdkeyCode.value = ''
      // 刷新VIP状态
      await fetchVipStatus()
      // 刷新用户信息
      await userStore.fetchUserInfo()
    } else {
      showToast(result.message || '卡密兑换失败，请检查兑换码是否正确', 'error')
    }
  } catch (error: any) {
    showToast(error.message || '卡密兑换失败，请稍后重试', 'error')
  } finally {
    isSubmitting.value = false
  }
}

onMounted(() => {
  // 先初始化用户信息
  userStore.initFromStorage()
  fetchVipStatus()
  fetchPlans()
  if (activeTab.value === 'orders') {
    fetchOrders()
  }
})

// 监听页签变化
const handleTabChange = (tab: string) => {
  activeTab.value = tab as any
  if (tab === 'orders') {
    fetchOrders()
  }
}
</script>

<style scoped>
.vip-page {
  min-height: 100vh;
  background: var(--background);
}

/* ====== 容器 ====== */
.vip-container {
  max-width: 1100px;
  margin: 0 auto;
  padding: 72px 24px 60px;
  display: flex;
  gap: 24px;
  align-items: flex-start;
}

/* ====== 左侧导航 ====== */
.sidebar-nav {
  width: 260px;
  flex-shrink: 0;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: fixed;
  top: 88px;
  height: calc(100vh - 104px);
}

.sidebar-profile {
  padding: 24px 20px;
  text-align: center;
  border-bottom: 1px solid var(--border);
  background: linear-gradient(180deg, rgba(245, 158, 11, 0.1), transparent);
}

.sidebar-plans {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px dashed var(--border);
}

.plans-title {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 10px;
}

.plans-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.plan-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: rgba(245, 158, 11, 0.1);
  border-radius: 8px;
  font-size: 13px;
}

.plan-name {
  color: var(--text-primary);
  font-weight: 500;
}

.plan-terminal {
  color: var(--gold-dark);
  font-size: 12px;
}

.sidebar-avatar {
  position: relative;
  width: 80px;
  height: 80px;
  margin: 0 auto 12px;
}

.avatar-icon {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #4b5563, #374151);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 32px;
  color: #fff;
  transition: all 0.3s;
}

/* 会员头像样式 */
.sidebar-avatar.is-vip .avatar-icon {
  background: linear-gradient(135deg, var(--gold-light), var(--gold-dark));
  box-shadow: 0 4px 20px var(--gold-glow);
}

.vip-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  padding: 2px 8px;
  background: linear-gradient(135deg, var(--gold-light), var(--gold-dark));
  color: #0a0a0f;
  font-size: 11px;
  font-weight: 700;
  border-radius: 10px;
  border: 2px solid var(--surface);
}

.sidebar-vip-icon {
  font-size: 36px;
  margin-bottom: 8px;
}

.sidebar-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-secondary);
  transition: all 0.3s;
}

/* 会员标题样式 */
.sidebar-title.is-vip-title {
  background: linear-gradient(135deg, var(--gold-light), var(--gold-dark));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.sidebar-expire {
  margin-top: 8px;
  font-size: 13px;
  color: var(--text-muted);
}

.sidebar-expire .expired {
  color: #ef4444;
}

.active-badge {
  display: inline-block;
  padding: 2px 8px;
  background: linear-gradient(135deg, var(--gold-light), var(--gold-dark));
  color: #0a0a0f;
  border-radius: 4px;
  font-weight: 600;
  font-size: 11px;
  margin-right: 6px;
}

.expired-badge {
  display: inline-block;
  padding: 2px 8px;
  background: rgba(239, 68, 68, 0.15);
  color: #ef4444;
  border-radius: 4px;
  font-weight: 600;
  font-size: 11px;
  margin-right: 6px;
}

.normal-badge {
  display: inline-block;
  padding: 2px 8px;
  background: rgba(156, 163, 175, 0.15);
  color: var(--text-muted);
  border-radius: 4px;
  font-weight: 600;
  font-size: 11px;
  margin-right: 6px;
}

.days-count {
  color: var(--gold);
  font-weight: 700;
  font-size: 15px;
}

.sidebar-menu {
  padding: 8px;
  flex: 1;
}

.sidebar-menu-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: var(--text-secondary);
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
  text-align: left;
}

.sidebar-menu-item:hover {
  color: var(--text-primary);
  background: var(--surface-hover);
}

.sidebar-menu-item.active {
  background: linear-gradient(135deg, var(--gold-light), var(--gold-dark));
  color: #0a0a0f;
  font-weight: 600;
  box-shadow: 0 2px 8px var(--gold-glow);
}

.menu-icon {
  font-size: 18px;
  flex-shrink: 0;
}

.menu-label {
  flex: 1;
}

/* ====== 右侧内容区 ====== */
.content-area {
  margin-left: 284px;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* ====== 套餐选择 ====== */
.privilege-section,
.plan-section,
.payment-section {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 24px;
}

.section-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 20px 0;
  display: flex;
  align-items: center;
  gap: 10px;
}



.title-icon {
  font-size: 20px;
}

.plan-tip {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: rgba(103, 194, 58, 0.06);
  border: 1px solid rgba(103, 194, 58, 0.2);
  border-radius: 10px;
  margin-bottom: 20px;
}

.tip-icon {
  font-size: 18px;
}

.tip-text {
  font-size: 14px;
  color: var(--text-secondary);
}

.privilege-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.privilege-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 20px;
  background: var(--surface-hover);
  border-radius: 12px;
  text-align: center;
  transition: all 0.2s;
}

.privilege-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
}

.privilege-icon {
  font-size: 32px;
  margin-bottom: 12px;
}

.privilege-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 4px;
}

.privilege-desc {
  font-size: 13px;
  color: var(--text-muted);
}

.plan-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.plan-card {
  position: relative;
  padding: 16px 20px 16px 52px;
  border: 2px solid var(--border);
  border-radius: 12px;
  background: var(--surface-hover);
  cursor: pointer;
  transition: all 0.2s;
  align-items: center;
}

.plan-checkbox {
  position: absolute;
  top: 12px;
  left: 12px;
  width: 20px;
  height: 20px;
}

.plan-checkbox input {
  display: none;
}

.plan-checkbox label {
  display: block;
  width: 100%;
  height: 100%;
  border: 2px solid var(--border);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}

.plan-checkbox label:hover {
  border-color: var(--gold);
}

.plan-checkbox input:checked + label {
  background: linear-gradient(135deg, var(--gold-light), var(--gold-dark));
  border-color: var(--gold);
}

.plan-checkbox input:checked + label::after {
  content: '✓';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: #0a0a0f;
  font-size: 12px;
  font-weight: 700;
}

.plan-card:hover {
  border-color: var(--gold);
  transform: translateY(-2px);
}

.plan-card.active {
  border-color: var(--gold);
  background: linear-gradient(180deg, rgba(245, 158, 11, 0.1), transparent);
  box-shadow: 0 4px 16px var(--gold-glow);
}

.plan-card.recommend {
  /* 推荐卡片默认样式和其他卡片保持一致，只保留推荐标签 */
}

.plan-badge {
  position: absolute;
  top: 0;
  right: 0;
  padding: 6px 14px;
  background: linear-gradient(135deg, var(--gold-light), var(--gold-dark));
  color: #0a0a0f;
  font-size: 11px;
  font-weight: 700;
  border-radius: 0 12px 0 12px;
}

.plan-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  gap: 16px;
}

.plan-name {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  white-space: nowrap;
  flex-shrink: 0;
}

.plan-main {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  justify-content: flex-end;
}

.plan-price {
  display: flex;
  align-items: baseline;
  gap: 2px;
}

.price-symbol {
  font-size: 14px;
  color: var(--gold);
  font-weight: 600;
}

.price-amount {
  font-size: 20px;
  color: var(--gold);
  font-weight: 700;
}

.plan-original {
  font-size: 12px;
  color: var(--text-muted);
  text-decoration: line-through;
}

.plan-save {
  padding: 2px 8px;
  background: rgba(34, 197, 94, 0.15);
  color: var(--success);
  font-size: 12px;
  font-weight: 600;
  border-radius: 4px;
  white-space: nowrap;
}

/* ====== 套餐汇总 ====== */
.selected-summary {
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.08), rgba(245, 158, 11, 0.02));
  border: 1px solid rgba(245, 158, 11, 0.2);
  border-radius: 12px;
  padding: 20px;
}

.summary-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.summary-icon {
  font-size: 18px;
}

.summary-content {
  margin-bottom: 12px;
}

.selected-plans {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.selected-plan-item {
  padding: 6px 12px;
  background: var(--surface);
  border-radius: 6px;
  font-size: 14px;
  color: var(--text-secondary);
}

.no-selection {
  font-size: 14px;
  color: var(--text-muted);
}

.summary-total {
  display: flex;
  align-items: baseline;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 12px;
  border-top: 1px dashed var(--border);
}

.total-label {
  font-size: 14px;
  color: var(--text-secondary);
}

.total-price {
  font-size: 24px;
  font-weight: 700;
  color: var(--gold);
}

/* ====== 支付通道 ====== */
.payment-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.channel-card {
  border: 2px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.2s;
}

.channel-card:hover {
  border-color: var(--gold);
}

.channel-header {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 20px;
  background: var(--surface-hover);
  border-bottom: 1px solid var(--border);
}

.channel-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.wechat-icon {
  background: linear-gradient(135deg, #07c160, #06ad56);
}

.alipay-icon {
  background: linear-gradient(135deg, #1677ff, #0958d9);
}

.channel-title-group {
  flex: 1;
}

.channel-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 2px 0;
}

.channel-subtitle {
  font-size: 13px;
  color: var(--text-muted);
  margin: 0;
}

.channel-body {
  padding: 20px;
}

.qrcode-wrapper {
  display: flex;
  justify-content: center;
  margin-bottom: 20px;
}

.qrcode-placeholder {
  text-align: center;
}

.qrcode-mock {
  width: 160px;
  height: 160px;
  background: #fff;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
  position: relative;
}

.qr-grid {
  width: 120px;
  height: 120px;
  background-image:
    linear-gradient(45deg, #333 25%, transparent 25%),
    linear-gradient(-45deg, #333 25%, transparent 25%),
    linear-gradient(45deg, transparent 75%, #333 75%),
    linear-gradient(-45deg, transparent 75%, #333 75%);
  background-size: 10px 10px;
  background-position: 0 0, 0 5px, 5px -5px, -5px 0px;
  opacity: 0.3;
  border-radius: 8px;
  position: relative;
}

.qr-corner {
  width: 30px;
  height: 30px;
  border: 4px solid #333;
  border-radius: 6px;
  position: absolute;
  background: #fff;
}

.qr-corner.tl {
  top: 4px;
  left: 4px;
  border-right: none;
  border-bottom: none;
}

.qr-corner.tr {
  top: 4px;
  right: 4px;
  border-left: none;
  border-bottom: none;
}

.qr-corner.bl {
  bottom: 4px;
  left: 4px;
  border-right: none;
  border-top: none;
}

.qr-corner.br {
  bottom: 4px;
  right: 4px;
  border-left: none;
  border-top: none;
}

.qr-center {
  width: 30px;
  height: 30px;
  background: linear-gradient(135deg, var(--gold-light), var(--gold-dark));
  border-radius: 6px;
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.qrcode-tip {
  font-size: 13px;
  color: var(--text-muted);
  margin: 0;
}

.channel-instructions {
  text-align: center;
}

.instruction-text {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0 0 12px 0;
  line-height: 1.6;
}

.instruction-text:last-child {
  margin-bottom: 0;
}

.highlight-price {
  color: var(--gold);
  font-weight: 700;
  font-size: 18px;
}

.highlight-tag {
  color: var(--gold);
  font-weight: 600;
}

.alipay-link-area {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.alipay-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background: linear-gradient(135deg, #1677ff, #0958d9);
  color: white;
  text-decoration: none;
  border-radius: 8px;
  font-weight: 600;
  transition: all 0.2s;
}

.alipay-link:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(22, 119, 255, 0.3);
}

.link-icon {
  font-size: 18px;
}

.link-arrow {
  font-size: 14px;
  color: var(--text-muted);
}

.link-step {
  font-size: 14px;
  color: var(--text-secondary);
}

.alipay-note {
  font-size: 14px;
  color: var(--text-muted);
  text-align: center;
  margin: 0;
}

/* ====== 卡密兑换 ====== */
.cdkey-section {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 24px;
}

.cdkey-card {
  max-width: 500px;
  margin: 0 auto;
}

.cdkey-header {
  text-align: center;
  margin-bottom: 32px;
}

.cdkey-icon-wrap {
  font-size: 48px;
  margin-bottom: 12px;
}

.cdkey-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.cdkey-desc {
  font-size: 14px;
  color: var(--text-muted);
  margin: 0;
}

.cdkey-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.input-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
}

.terminal-options {
  display: flex;
  gap: 12px;
}

.terminal-option {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px;
  background: var(--surface-hover);
  border: 2px solid var(--border);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.terminal-option:hover {
  border-color: var(--gold);
  background: rgba(245, 158, 11, 0.05);
}

.terminal-option.active {
  border-color: var(--gold);
  background: linear-gradient(180deg, rgba(245, 158, 11, 0.15), rgba(245, 158, 11, 0.05));
}

.terminal-icon {
  font-size: 28px;
}

.terminal-label {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
}

.terminal-option.active .terminal-label {
  color: var(--gold);
}

.input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.cdkey-input {
  width: 100%;
  padding: 16px 52px 16px 16px;
  background: var(--surface-hover);
  border: 2px solid var(--border);
  border-radius: 10px;
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 2px;
  text-transform: uppercase;
  transition: all 0.2s;
}

.cdkey-input:focus {
  outline: none;
  border-color: var(--gold);
  box-shadow: 0 0 0 4px rgba(245, 158, 11, 0.1);
}

.cdkey-input::placeholder {
  color: var(--text-muted);
  font-weight: 400;
  letter-spacing: normal;
  text-transform: none;
}

.input-clear {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 50%;
  background: rgba(156, 163, 175, 0.2);
  color: var(--text-muted);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.input-clear:hover {
  background: rgba(156, 163, 175, 0.3);
  color: var(--text-secondary);
}

.input-hint {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: var(--text-muted);
}

.char-count {
  color: var(--text-secondary);
}

.cdkey-submit {
  width: 100%;
  padding: 16px 24px;
  background: linear-gradient(135deg, var(--gold-light), var(--gold-dark));
  color: #0a0a0f;
  border: none;
  border-radius: 10px;
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.cdkey-submit:hover:not(.disabled):not(.loading) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px var(--gold-glow);
}

.cdkey-submit:active:not(.disabled):not(.loading) {
  transform: translateY(0);
}

.cdkey-submit.disabled {
  background: var(--border);
  color: var(--text-muted);
  cursor: not-allowed;
}

.btn-loading {
  display: inline-block;
  width: 20px;
  height: 20px;
  border: 2px solid transparent;
  border-top-color: #0a0a0f;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.cdkey-tips {
  margin-top: 12px;
  padding: 16px;
  background: rgba(245, 158, 11, 0.05);
  border-radius: 10px;
  border: 1px solid rgba(245, 158, 11, 0.2);
}

.tips-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 12px 0;
}

.tips-list {
  margin: 0;
  padding-left: 18px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tips-list li {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
}

/* ====== 订单管理 ====== */
.orders-section {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 24px;
}

.orders-card {
  max-width: 700px;
  margin: 0 auto;
}

.orders-header {
  text-align: center;
  margin-bottom: 32px;
}

.orders-icon-wrap {
  font-size: 48px;
  margin-bottom: 12px;
}

.orders-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 0 0 8px 0;
}

.orders-desc {
  font-size: 14px;
  color: var(--text-muted);
  margin: 0;
}

.orders-loading {
  text-align: center;
  padding: 40px;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--border);
  border-top-color: var(--gold);
  border-radius: 50%;
  margin: 0 auto 16px;
  animation: spin 0.8s linear infinite;
}

.orders-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.order-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  background: var(--surface-hover);
  border-radius: 10px;
  border: 1px solid var(--border);
  transition: all 0.2s;
}

.order-item:hover {
  border-color: var(--gold);
}

.order-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.order-icon {
  font-size: 28px;
}

.order-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.order-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.order-time {
  font-size: 12px;
  color: var(--text-muted);
}

.order-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.order-price {
  font-size: 18px;
  font-weight: 700;
  color: var(--gold);
}

.order-status {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 100px;
  font-weight: 600;
}

.order-status.pending {
  background: rgba(156, 163, 175, 0.15);
  color: var(--text-muted);
}

.order-status.paid {
  background: rgba(34, 197, 94, 0.15);
  color: var(--success);
}

.order-status.refund {
  background: rgba(239, 68, 68, 0.15);
  color: var(--error);
}

.orders-empty {
  text-align: center;
  padding: 40px;
}

.empty-icon {
  font-size: 48px;
  opacity: 0.4;
  margin-bottom: 16px;
}

.empty-text {
  font-size: 14px;
  color: var(--text-muted);
  margin: 0 0 20px 0;
}

.go-buy-btn {
  padding: 10px 24px;
  background: linear-gradient(135deg, var(--gold-light), var(--gold-dark));
  color: #0a0a0f;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.go-buy-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px var(--gold-glow);
}

/* ====== 响应式 ====== */
@media screen and (max-width: 1024px) {
  .privilege-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .plan-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media screen and (max-width: 768px) {
  .vip-container {
    padding: 0 16px 16px; /* 移动端由 MobileLayout 处理顶部间距 */
    flex-direction: column;
  }

  .sidebar-nav {
    width: 100%;
    position: static;
    height: auto;
  }

  .sidebar-profile {
    display: flex;
    align-items: center;
    gap: 16px;
    text-align: left;
    padding: 16px 20px;
  }

  .sidebar-menu {
    display: flex;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    scrollbar-width: none;
    padding: 6px;
    gap: 4px;
  }

  .sidebar-menu::-webkit-scrollbar {
    display: none;
  }

  .sidebar-menu-item {
    flex: none;
    padding: 8px 14px;
    font-size: 13px;
    border-radius: 8px;
  }

  .content-area {
    margin-left: 0;
  }

  .privilege-grid {
    grid-template-columns: 1fr;
  }

  .plan-grid {
    grid-template-columns: 1fr;
  }

  .device-filter {
    flex-direction: column;
    align-items: flex-start;
  }

  .prompt-buttons {
    flex-direction: column;
  }
}
</style>
