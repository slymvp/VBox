<template>
  <div class="dashboard">
    <!-- 统计卡片区域 -->
    <el-row :gutter="20">
      <el-col :span="6" v-for="stat in stats" :key="stat.title">
        <el-card class="stat-card" shadow="hover">
          <div class="stat-content">
            <div class="stat-icon" :style="{ backgroundColor: stat.color }">
              <el-icon :size="30"><component :is="stat.icon" /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stat.value }}</div>
              <div class="stat-title">{{ stat.title }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 平台统计区域 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>平台剧集分布</span>
              <el-button size="small" @click="loadStats">刷新</el-button>
            </div>
          </template>
          <div class="platform-stats">
            <div v-for="(count, platform) in platformStats" :key="platform" class="platform-item">
              <div class="platform-name">{{ platformNames[platform] || platform }}</div>
              <el-progress :percentage="getPlatformPercentage(count)" :stroke-width="10"></el-progress>
              <div class="platform-count">{{ count }} 部</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>频道剧集分布</span>
            </div>
          </template>
          <div class="category-stats">
            <div v-for="(count, category) in categoryStats" :key="category" class="category-item">
              <div class="category-name">{{ categoryNames[category] || category }}</div>
              <el-progress :percentage="getCategoryPercentage(count)" :stroke-width="10"></el-progress>
              <div class="category-count">{{ count }} 部</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 数据质量统计 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>VIP 分布</span>
          </template>
          <div class="stat-grid">
            <div class="stat-item free">
              <div class="stat-label">免费</div>
              <div class="stat-num">{{ vipStats.free || 0 }}</div>
            </div>
            <div class="stat-item vip">
              <div class="stat-label">会员</div>
              <div class="stat-num">{{ vipStats.vip || 0 }}</div>
            </div>
            <div class="stat-item ppp">
              <div class="stat-label">点播</div>
              <div class="stat-num">{{ vipStats.ppp || 0 }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>完结状态</span>
          </template>
          <div class="stat-grid">
            <div class="stat-item finished">
              <div class="stat-label">已完结</div>
              <div class="stat-num">{{ finishStats.finished || 0 }}</div>
            </div>
            <div class="stat-item ongoing">
              <div class="stat-label">连载中</div>
              <div class="stat-num">{{ finishStats.ongoing || 0 }}</div>
            </div>
            <div class="stat-item unknown">
              <div class="stat-label">未知</div>
              <div class="stat-num">{{ finishStats.unknown || 0 }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card>
          <template #header>
            <span>分集完整度</span>
          </template>
          <div class="stat-grid">
            <div class="stat-item complete">
              <div class="stat-label">完整</div>
              <div class="stat-num">{{ epQualityStats.complete || 0 }}</div>
            </div>
            <div class="stat-item incomplete">
              <div class="stat-label">部分</div>
              <div class="stat-num">{{ epQualityStats.incomplete || 0 }}</div>
            </div>
            <div class="stat-item nodata">
              <div class="stat-label">无数据</div>
              <div class="stat-num">{{ epQualityStats.no_data || 0 }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 快捷操作和最近更新 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="12">
        <el-card>
          <template #header>
            <span>快捷操作</span>
          </template>
          <div class="quick-actions">
            <el-button type="primary" @click="$router.push('/series')">
              <el-icon><VideoCamera /></el-icon> 管理剧集
            </el-button>
            <el-button type="success" @click="$router.push('/users')">
              <el-icon><User /></el-icon> 管理用户
            </el-button>
            <el-button type="warning" @click="$router.push('/crawler')">
              <el-icon><Connection /></el-icon> 爬虫管理
            </el-button>
            <el-button type="info" @click="$router.push('/member/vip-plans')">
              <el-icon><Wallet /></el-icon> VIP套餐
            </el-button>
          </div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>系统信息</span>
            </div>
          </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="最后更新时间">
              {{ lastUpdateTime || '--' }}
            </el-descriptions-item>
            <el-descriptions-item label="系统版本">
              1.0.0
            </el-descriptions-item>
            <el-descriptions-item label="当前时间">
              {{ currentTime }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { VideoCamera, Tickets, User, Wallet, Platform } from '@element-plus/icons-vue'
import request from '@/utils/api'

interface Stat {
  title: string
  value: string | number
  icon: any
  color: string
}

const stats = ref<Stat[]>([
  { title: '剧集总数', value: '--', icon: VideoCamera, color: '#409EFF' },
  { title: '分集总数', value: '--', icon: Tickets, color: '#67C23A' },
  { title: '用户总数', value: '--', icon: User, color: '#E6A23C' },
  { title: '平台数量', value: '--', icon: Platform, color: '#F56C6C' }
])

const platformStats = ref<Record<string, number>>({})
const categoryStats = ref<Record<string, number>>({})
const lastUpdateTime = ref<string>('')
const currentTime = ref<string>('')
let timer: number | null = null

const vipStats = ref<Record<string, number>>({free: 0, vip: 0, ppp: 0})
const finishStats = ref<Record<string, number>>({finished: 0, ongoing: 0, unknown: 0})
const epQualityStats = ref<Record<string, number>>({complete: 0, incomplete: 0, no_data: 0})

const platformNames: Record<string, string> = {
  'iqiyi': '爱奇艺',
  'tencent': '腾讯视频',
  'youku': '优酷',
  'mgtv': '芒果TV',

  'bilibili': '哔哩哔哩'
}

const categoryNames: Record<string, string> = {
  'tv': '电视剧',
  'movie': '电影',
  'variety': '综艺',
  'cartoon': '动漫',
  'child': '少儿'
}

const totalSeries = computed(() => {
  const total = Object.values(platformStats.value).reduce((sum, count) => sum + count, 0)
  return total > 0 ? total : 100
})

const totalCategorySeries = computed(() => {
  const total = Object.values(categoryStats.value).reduce((sum, count) => sum + count, 0)
  return total > 0 ? total : 100
})

const getPlatformPercentage = (count: number) => {
  return Math.round((count / totalSeries.value) * 100)
}

const getCategoryPercentage = (count: number) => {
  return Math.round((count / totalCategorySeries.value) * 100)
}

const updateCurrentTime = () => {
  const now = new Date()
  currentTime.value = now.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const loadStats = async () => {
  try {
    const res = await request.get('/stats')
    if (res.data) {
      stats.value[0].value = res.data.total_series || 0
      stats.value[1].value = res.data.total_episodes || 0
      stats.value[2].value = res.data.total_users || 0
      stats.value[3].value = res.data.total_platforms || 0
      platformStats.value = res.data.platform_stats || {}
      categoryStats.value = res.data.category_stats || {}
      vipStats.value = res.data.vip_stats || {free: 0, vip: 0, ppp: 0}
      finishStats.value = res.data.finish_stats || {finished: 0, ongoing: 0, unknown: 0}
      epQualityStats.value = res.data.ep_quality_stats || {complete: 0, incomplete: 0, no_data: 0}
      lastUpdateTime.value = res.data.last_update || ''
    }
  } catch (error) {
    console.error('加载统计数据失败:', error)
    ElMessage.error('加载统计数据失败')
  }
}

onMounted(() => {
  loadStats()
  updateCurrentTime()
  timer = window.setInterval(updateCurrentTime, 1000)
})

onUnmounted(() => {
  if (timer !== null) {
    clearInterval(timer)
  }
})
</script>

<style scoped lang="scss">
.dashboard {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .stat-card {
    .stat-content {
      display: flex;
      align-items: center;
      gap: 20px;
    }

    .stat-icon {
      width: 60px;
      height: 60px;
      border-radius: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
    }

    .stat-info {
      .stat-value {
        font-size: 28px;
        font-weight: bold;
        color: #303133;
      }

      .stat-title {
        font-size: 14px;
        color: #909399;
        margin-top: 5px;
      }
    }
  }

  .platform-stats,
  .category-stats {
    .platform-item,
    .category-item {
      display: flex;
      align-items: center;
      margin-bottom: 15px;

      .platform-name,
      .category-name {
        width: 100px;
        font-size: 14px;
        color: #606266;
      }

      .platform-count,
      .category-count {
        width: 60px;
        text-align: right;
        margin-left: 15px;
        font-size: 14px;
        font-weight: bold;
        color: #409EFF;
      }

      .el-progress {
        flex: 1;
      }
    }
  }

  .quick-actions {
    display: flex;
    gap: 15px;
    flex-wrap: wrap;
  }

  .stat-grid {
    display: flex;
    justify-content: space-around;
    gap: 10px;

    .stat-item {
      text-align: center;
      flex: 1;

      .stat-label {
        font-size: 13px;
        color: #909399;
        margin-bottom: 4px;
      }

      .stat-num {
        font-size: 26px;
        font-weight: bold;
      }

      &.free .stat-num { color: #67C23A; }
      &.vip .stat-num { color: #E6A23C; }
      &.ppp .stat-num { color: #F56C6C; }
      &.finished .stat-num { color: #67C23A; }
      &.ongoing .stat-num { color: #409EFF; }
      &.unknown .stat-num { color: #909399; }
      &.complete .stat-num { color: #67C23A; }
      &.incomplete .stat-num { color: #E6A23C; }
      &.nodata .stat-num { color: #F56C6C; }
    }
  }
}
</style>
