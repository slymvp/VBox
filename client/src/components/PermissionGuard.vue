<template>
  <div v-if="result !== PermissionResult.ALLOWED" class="permission-block">
    <div class="block-content">
      <div class="block-icon">🔒</div>
      <div class="block-title">{{ title }}</div>
      <div class="block-desc">{{ description }}</div>
      <div class="block-actions">
        <button v-if="result === PermissionResult.NEED_LOGIN" @click="goLogin" class="btn-primary">
          去登录
        </button>
        <button v-else-if="result === PermissionResult.NEED_VIP" @click="goVip" class="btn-primary">
          开通会员
        </button>
      </div>
    </div>
  </div>
  <slot v-else />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { usePermission, PermissionResult } from '@/composables/usePermission'
import type { Series, Episode } from '@/utils/api'

const props = defineProps<{
  series: Series
  episode?: Episode
}>()

const router = useRouter()
const { checkSeriesPermission, checkEpisodePermission } = usePermission()

const result = computed(() => {
  if (props.episode) {
    return checkEpisodePermission(props.series, props.episode)
  }
  return PermissionResult.ALLOWED
})

const title = computed(() => {
  switch (result.value) {
    case PermissionResult.NEED_LOGIN:
      return '请先登录'
    case PermissionResult.NEED_VIP:
      return '需要会员权限'
    default:
      return ''
  }
})

const description = computed(() => {
  switch (result.value) {
    case PermissionResult.NEED_LOGIN:
      return '登录后可观看更多精彩内容'
    case PermissionResult.NEED_VIP:
      return '开通会员即可解锁全部内容'
    default:
      return ''
  }
})

function goLogin() {
  router.push('/login')
}

function goVip() {
  router.push('/vip')
}
</script>

<style scoped>
.permission-block {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.block-content {
  background: var(--bg-secondary);
  border-radius: 16px;
  padding: 32px;
  text-align: center;
  max-width: 320px;
  width: 90%;
}

.block-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.block-title {
  font-size: 20px;
  font-weight: 600;
  color: #fff;
  margin-bottom: 8px;
}

.block-desc {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 24px;
}

.block-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.btn-primary {
  background: var(--primary);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 12px 24px;
  font-size: 16px;
  font-weight: 500;
  cursor: pointer;
}

.btn-primary:active {
  opacity: 0.8;
}
</style>