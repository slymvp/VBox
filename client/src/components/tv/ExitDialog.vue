<template>
  <Teleport to="body">
    <div
      v-if="visible"
      class="tv-exit-overlay"
      @keydown="handleDialogKeydown"
    >
      <div class="tv-exit-dialog" ref="dialogRef">
        <div class="tv-exit-icon">📺</div>
        <h2 class="tv-exit-title">确认退出应用？</h2>
        <p class="tv-exit-subtitle">按返回键可继续浏览</p>
        <div class="tv-exit-buttons">
          <button
            class="tv-exit-btn tv-exit-btn--cancel"
            ref="cancelBtnRef"
            @click="$emit('cancel')"
            @focus="focusedBtn = 'cancel'"
          >
            取 消
          </button>
          <button
            class="tv-exit-btn tv-exit-btn--confirm"
            ref="confirmBtnRef"
            @click="$emit('confirm')"
            @focus="focusedBtn = 'confirm'"
          >
            确认退出
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'

const props = defineProps<{
  visible: boolean
}>()

defineEmits<{
  confirm: []
  cancel: []
}>()

const dialogRef = ref<HTMLElement | null>(null)
const cancelBtnRef = ref<HTMLElement | null>(null)
const confirmBtnRef = ref<HTMLElement | null>(null)
const focusedBtn = ref<'cancel' | 'confirm'>('cancel')

/** 弹窗打开时自动聚焦取消按钮（默认安全选项） */
watch(() => props.visible, async (v) => {
  if (v) {
    focusedBtn.value = 'cancel'
    await nextTick()
    cancelBtnRef.value?.focus()
  }
})

/** 弹窗内键盘导航：左右切换，回车确认 */
function handleDialogKeydown(e: KeyboardEvent) {
  switch (e.key) {
    case 'ArrowLeft':
    case 'ArrowRight':
      e.preventDefault()
      e.stopPropagation()
      focusedBtn.value = focusedBtn.value === 'cancel' ? 'confirm' : 'cancel'
      nextTick(() => {
        if (focusedBtn.value === 'cancel') {
          cancelBtnRef.value?.focus()
        } else {
          confirmBtnRef.value?.focus()
        }
      })
      break
    case 'Enter':
    case ' ':
      e.preventDefault()
      e.stopPropagation()
      if (focusedBtn.value === 'cancel') {
        cancelBtnRef.value?.click()
      } else {
        confirmBtnRef.value?.click()
      }
      break
    case 'Backspace':
    case 'Escape':
      e.preventDefault()
      e.stopPropagation()
      // 弹窗内按返回 → 取消退出
      cancelBtnRef.value?.click()
      break
  }
}
</script>

<style lang="scss" scoped>
.tv-exit-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
}

.tv-exit-dialog {
  background: var(--surface);
  border-radius: 24px;
  padding: 50px 60px;
  text-align: center;
  min-width: 480px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  border: 2px solid var(--border);
}

.tv-exit-icon {
  font-size: 56px;
  margin-bottom: 20px;
}

.tv-exit-title {
  font-size: 36px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 12px;
}

.tv-exit-subtitle {
  font-size: 22px;
  color: var(--text-muted);
  margin-bottom: 40px;
}

.tv-exit-buttons {
  display: flex;
  gap: 30px;
  justify-content: center;
}

.tv-exit-btn {
  font-size: 26px;
  font-weight: 600;
  padding: 16px 50px;
  border-radius: 14px;
  border: 2px solid transparent;
  cursor: pointer;
  transition: all 0.15s ease;
  outline: none;

  &:focus {
    outline: 3px solid var(--gold);
    outline-offset: 3px;
    transform: scale(1.05);
  }
}

.tv-exit-btn--cancel {
  background: var(--surface-hover);
  color: var(--text-primary);
  border-color: var(--border);

  &:hover, &:focus {
    background: var(--border-light);
  }
}

.tv-exit-btn--confirm {
  background: var(--error);
  color: #fff;

  &:hover, &:focus {
    background: #dc2626;
  }
}
</style>
