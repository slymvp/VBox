<template>
  <div class="tv-layout" ref="layoutRef">
    <TVHeader ref="headerRef" :show-type-filters="true" />
    <main class="content">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import TVHeader from '@/components/tv/Header.vue'

const layoutRef = ref<HTMLElement | null>(null)
const headerRef = ref<InstanceType<typeof TVHeader> | null>(null)

// 初始化TV端焦点
function initTVFocus() {
  const firstChannelBtn = document.querySelector('.type-filters .type-btn') as HTMLElement
  if (firstChannelBtn) {
    firstChannelBtn.focus()
    return true
  }
  return false
}

onMounted(() => {
  // TV端默认聚焦到第一个频道按钮
  let attempts = 0
  const tryFocus = () => {
    if (initTVFocus()) return
    attempts++
    if (attempts < 5) {
      setTimeout(tryFocus, 100)
    }
  }
  setTimeout(tryFocus, 100)
})
</script>

<style lang="scss">
.tv-layout {
  min-height: 100vh;
  background: var(--background);
  font-size: 24px;

  .content {
    padding: 20px;
  }
}
</style>
