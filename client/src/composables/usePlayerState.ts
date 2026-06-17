// 全局播放状态管理
import { ref } from 'vue'

// 是否正在播放
const isPlaying = ref(false)

export function usePlayerState() {
  return {
    isPlaying,
    setPlaying: (playing: boolean) => {
      isPlaying.value = playing
    }
  }
}
