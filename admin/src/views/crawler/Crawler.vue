
<template>
  <div class="crawler">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>爬虫管理</span>
          <div class="header-actions">
            <el-button @click="refreshAll">刷新</el-button>
            <el-button type="primary" @click="showTriggerDialog">添加任务</el-button>
            <el-button type="warning" @click="handleResetTasks">重置状态</el-button>
            <el-button type="danger" @click="handleStopAllTasks">停止所有</el-button>
            <el-button @click="showLogDialog">查看日志</el-button>
          </div>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="任务队列" name="queue">
          <div style="margin-bottom: 20px;">
            <el-alert
              :title="`全局运行: ${queueStatus.global_active || 0}/5 | 等待: ${queueStatus.pending?.length || 0} 个`"
              type="info"
              :closable="false"
              show-icon
            />
          </div>
          
          <!-- 平台并发状态 -->
          <div style="margin-bottom: 20px;" v-if="queueStatus.platform_running">
            <el-tag style="margin-right: 10px;" v-for="(count, platform) in queueStatus.platform_running" :key="platform">
              {{ platformMap[platform] || platform }}: {{ count }}/2
            </el-tag>
          </div>

          <el-divider content-position="left">运行中任务</el-divider>
          <el-table :data="queueStatus.running" stripe style="margin-top: 10px">
            <el-table-column prop="task_id" label="任务ID" width="120" />
            <el-table-column prop="platform_key" label="平台" width="120">
              <template #default="{ row }">
                <el-tag>{{ platformMap[row.platform_key] || row.platform_key }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="channel_key" label="频道" width="120" />
            <el-table-column prop="task_type" label="类型" width="100">
              <template #default="{ row }">
                <el-tag :type="row.task_type === 'manual' ? 'primary' : 'success'">
                  {{ row.task_type === 'manual' ? '手动' : '定时' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="开始时间" width="180">
              <template #default="{ row }">
                {{ formatDateTime(row.started_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80" fixed="right">
              <template #default="{ row }">
                <el-button type="danger" link @click="handleStopTask(row.task_id)">停止</el-button>
              </template>
            </el-table-column>
          </el-table>
          
          <el-divider content-position="left" style="margin-top: 30px;" v-if="queueStatus.pending?.length > 0">等待中任务</el-divider>
          <el-table :data="queueStatus.pending" stripe style="margin-top: 10px" v-if="queueStatus.pending?.length > 0">
            <el-table-column prop="task_id" label="任务ID" width="120" />
            <el-table-column prop="platform_key" label="平台" width="120">
              <template #default="{ row }">
                <el-tag>{{ platformMap[row.platform_key] || row.platform_key }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="channel_key" label="频道" width="120" />
            <el-table-column prop="task_type" label="类型" width="100">
              <template #default="{ row }">
                <el-tag :type="row.task_type === 'manual' ? 'primary' : 'success'">
                  {{ row.task_type === 'manual' ? '手动' : '定时' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="创建时间" width="180">
              <template #default="{ row }">
                {{ formatDateTime(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80" fixed="right">
              <template #default="{ row }">
                <el-button type="danger" link @click="handleStopTask(row.task_id)">取消</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-divider content-position="left" style="margin-top: 30px;">最近完成任务</el-divider>
            <el-table :data="queueStatus.completed" stripe style="margin-top: 10px">
              <el-table-column prop="task_id" label="任务ID" width="120" />
              <el-table-column prop="platform_key" label="平台" width="120">
                <template #default="{ row }">
                  <el-tag>{{ platformMap[row.platform_key] || row.platform_key }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="channel_key" label="频道" width="120" />
              <el-table-column prop="status" label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.status === 'completed' ? 'success' : 'danger'">
                    {{ row.status === 'completed' ? '成功' : '失败' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="task_type" label="类型" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.task_type === 'manual' ? 'primary' : 'success'">
                    {{ row.task_type === 'manual' ? '手动' : '定时' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="完成时间" width="180">
                <template #default="{ row }">
                  {{ formatDateTime(row.completed_at) }}
                </template>
              </el-table-column>
              <el-table-column label="错误信息" min-width="200" show-overflow-tooltip>
                <template #default="{ row }">
                  {{ row.error || '-' }}
                </template>
              </el-table-column>
            </el-table>
            <el-pagination
              v-if="queueStatus.completed_total > 0"
              v-model:current-page="completedPagination.page"
              v-model:page-size="completedPagination.limit"
              :total="queueStatus.completed_total"
              :page-sizes="[10, 20, 50, 100]"
              layout="total, sizes, prev, pager, next, jumper"
              @size-change="loadQueueStatus"
              @current-change="loadQueueStatus"
              style="margin-top: 20px; justify-content: flex-end;"
            />
        </el-tab-pane>

        <el-tab-pane label="爬虫任务" name="tasks">
          <div style="margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center;">
            <div>
              <el-button 
                type="danger" 
                @click="handleBatchDelete" 
                :disabled="selectedTaskIds.length === 0"
              >
                批量删除 ({{ selectedTaskIds.length }})
              </el-button>
            </div>
          </div>
          <el-table 
            ref="tableRef"
            :data="tasks" 
            stripe 
            v-loading="loading" 
            style="margin-top: 10px"
            row-key="id"
            @selection-change="handleSelectionChange"
          >
            <el-table-column 
              type="selection" 
              width="55" 
              :selectable="selectableRow"
              reserve-selection
            />
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column prop="platform" label="平台" width="120">
              <template #default="{ row }">
                <el-tag>{{ platformMap[row.platform] || row.platform }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="channel" label="频道" width="100" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="statusTypeMap[row.status]">
                  {{ statusTextMap[row.status] || row.status }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="items_fetched" label="获取数量" width="100" />
            <el-table-column prop="error_message" label="错误信息" min-width="200" show-overflow-tooltip />
            <el-table-column label="创建时间" width="180">
              <template #default="{ row }">
                {{ formatDateTime(row.created_at || row.started_at) }}
              </template>
            </el-table-column>
            <el-table-column label="完成时间" width="180">
              <template #default="{ row }">
                {{ formatDateTime(row.completed_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150">
              <template #default="{ row }">
                <el-button v-if="row.status === 'running'" type="danger" link @click="handleStopTaskByDbId(row.id)">停止</el-button>
                <el-button type="primary" link @click="viewTaskLogs(row.id)">日志</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-pagination
            v-model:current-page="pagination.page"
            v-model:page-size="pagination.limit"
            :total="pagination.total"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="loadTasks"
            @current-change="loadTasks"
            style="margin-top: 20px; justify-content: flex-end;"
          />
        </el-tab-pane>
        
        <el-tab-pane label="定时任务" name="scheduled">
          <el-table :data="scheduledTasks" stripe v-loading="scheduledLoading" style="margin-top: 10px">
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column prop="platform" label="平台" width="120">
              <template #default="{ row }">
                <el-tag>{{ platformMap[row.platform] || row.platform }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="channel" label="频道" width="100">
              <template #default="{ row }">
                {{ row.channel || '全部频道' }}
              </template>
            </el-table-column>
            <el-table-column label="列表排序" width="120">
              <template #default="{ row }">
                <el-tag v-if="row.sort === 'hot'" type="danger" size="small">热门</el-tag>
                <el-tag v-else-if="row.sort === 'new'" type="success" size="small">最新</el-tag>
                <span v-else style="color: #999;">默认</span>
              </template>
            </el-table-column>
            <el-table-column prop="cron_expression" label="执行频率" min-width="180" />
            <el-table-column label="下次执行" width="200">
              <template #default="{ row }">
                {{ row.next_run_time ? formatTime(row.next_run_time) : '-' }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button type="danger" link @click="deleteScheduledTask(row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-dialog v-model="triggerDialogVisible" :title="dialogMode === 'manual' ? '手动触发爬虫' : '创建定时任务'" width="600px">
      <el-tabs v-model="dialogMode">
        <el-tab-pane label="手动触发" name="manual">
          <el-form :model="triggerForm" :rules="triggerRules" ref="triggerFormRef" label-width="100px">
            <el-form-item label="平台" prop="platform">
              <el-radio-group v-model="triggerForm.platform" @change="onPlatformChange">
                <el-radio-button v-for="p in platforms" :key="p.key" :value="p.key">
                  {{ p.name }}
                </el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="频道" prop="channels">
              <div v-if="triggerForm.platform === 'all'" style="color: #909399; font-size: 14px;">
                选中"全部平台"时，将遍历所有平台的所有频道
              </div>
              <el-checkbox-group v-else v-model="triggerForm.channels">
                <el-checkbox label="">全部频道</el-checkbox>
                <el-checkbox v-for="ch in currentChannels" :key="ch.key" :label="ch.key">
                  {{ ch.name }}
                </el-checkbox>
              </el-checkbox-group>
            </el-form-item>
            <el-form-item label="运行模式" prop="mode">
              <el-radio-group v-model="triggerForm.mode">
                <el-radio-button value="test">测试模式</el-radio-button>
                <el-radio-button value="prod">生产模式</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="爬取数量" prop="maxItems" v-if="triggerForm.mode === 'test'">
              <el-input-number v-model="triggerForm.maxItems" :min="1" :max="500" style="width: 100%;" />
            </el-form-item>
            <el-form-item label="爬取类型" prop="prodType" v-if="triggerForm.mode === 'prod'">
              <el-radio-group v-model="triggerForm.prodType">
                <el-radio-button value="incremental">增量</el-radio-button>
                <el-radio-button value="full">全量</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="列表排序" prop="sort" v-if="triggerForm.mode === 'prod'">
              <el-radio-group v-model="triggerForm.sort">
                <el-radio-button value="">默认(不刷is_hot/is_new)</el-radio-button>
                <el-radio-button value="hot">热门列表(刷is_hot)</el-radio-button>
                <el-radio-button value="new">最新列表(刷is_new)</el-radio-button>
              </el-radio-group>
            </el-form-item>
          </el-form>
        </el-tab-pane>
        
        <el-tab-pane label="定时任务" name="scheduled">
            <el-form :model="scheduledForm" :rules="scheduledRules" ref="scheduledFormRef" label-width="100px">
                <el-form-item label="平台" prop="platform">
                    <el-radio-group v-model="scheduledForm.platform" @change="onScheduledPlatformChange">
                        <el-radio-button v-for="p in platforms" :key="p.key" :value="p.key">
                            {{ p.name }}
                        </el-radio-button>
                    </el-radio-group>
                </el-form-item>
                <el-form-item label="频道" prop="channels">
                    <div v-if="scheduledForm.platform === 'all'" style="color: #909399; font-size: 14px;">
                      选中"全部平台"时，将遍历所有平台的所有频道
                    </div>
                    <el-checkbox-group v-else v-model="scheduledForm.channels">
                        <el-checkbox value="">全部频道</el-checkbox>
                        <el-checkbox 
                            v-for="ch in currentScheduledChannels" 
                            :key="ch.key" 
                            :value="ch.key"
                            :disabled="scheduledForm.channels && scheduledForm.channels.includes('')"
                        >
                            {{ ch.name }}
                        </el-checkbox>
                    </el-checkbox-group>
                </el-form-item>
            <el-form-item label="列表排序" prop="sort">
              <el-radio-group v-model="scheduledForm.sort">
                <el-radio-button value="">默认(不刷is_hot/is_new)</el-radio-button>
                <el-radio-button value="hot">热门列表(刷is_hot)</el-radio-button>
                <el-radio-button value="new">最新列表(刷is_new)</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="执行频率" prop="frequencyType">
              <el-radio-group v-model="scheduledForm.frequencyType" @change="onFrequencyChange">
                <el-radio-button value="daily">每天</el-radio-button>
                <el-radio-button value="weekly">每周</el-radio-button>
                <el-radio-button value="monthly">每月</el-radio-button>
                <el-radio-button value="custom">自定义</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="执行时间" prop="hour" v-if="['daily', 'weekly', 'monthly'].includes(scheduledForm.frequencyType)">
              <el-time-picker
                v-model="scheduledForm.time"
                format="HH:mm"
                value-format="HH:mm"
                style="width: 100%;"
              />
            </el-form-item>
            <el-form-item label="星期" prop="dayOfWeek" v-if="scheduledForm.frequencyType === 'weekly'">
              <el-checkbox-group v-model="scheduledForm.dayOfWeek">
                <el-checkbox label="0">周日</el-checkbox>
                <el-checkbox label="1">周一</el-checkbox>
                <el-checkbox label="2">周二</el-checkbox>
                <el-checkbox label="3">周三</el-checkbox>
                <el-checkbox label="4">周四</el-checkbox>
                <el-checkbox label="5">周五</el-checkbox>
                <el-checkbox label="6">周六</el-checkbox>
              </el-checkbox-group>
            </el-form-item>
            <el-form-item label="日期" prop="dayOfMonth" v-if="scheduledForm.frequencyType === 'monthly'">
              <el-input-number v-model="scheduledForm.dayOfMonth" :min="1" :max="31" style="width: 100%;" />
            </el-form-item>
            <el-form-item label="Cron表达式" prop="cronExpression" v-if="scheduledForm.frequencyType === 'custom'">
              <el-input v-model="scheduledForm.cronExpression" placeholder="例如：0 0 * * * 表示每天0点执行" />
              <div style="font-size: 12px; color: #999; margin-top: 5px;">
                格式：分 时 日 月 周
              </div>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
      
      <template #footer>
        <el-button @click="triggerDialogVisible = false">取消</el-button>
        <el-button 
          type="primary" 
          @click="dialogMode === 'manual' ? handleTrigger() : handleCreateScheduledTask()" 
          :loading="triggerLoading" 
          :disabled="dialogMode === 'manual' ? !triggerForm.platform : !scheduledForm.platform"
        >
          {{ dialogMode === 'manual' ? '开始爬取' : '创建定时任务' }}
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="logDialogVisible" :title="currentTaskId ? `任务 #${currentTaskId} 日志` : '实时日志'" width="80%" top="5vh">
      <div class="log-container">
        <div class="log-toolbar">
          <el-button size="small" @click="clearLogs" v-if="!currentTaskId">清空</el-button>
          <el-button size="small" @click="downloadLogs">下载</el-button>
          <div class="log-filter">
            <el-select v-model="logLevelFilter" size="small" placeholder="日志级别" style="width: 120px">
              <el-option label="全部" value=""></el-option>
              <el-option label="DEBUG" value="DEBUG"></el-option>
              <el-option label="INFO" value="INFO"></el-option>
              <el-option label="WARNING" value="WARNING"></el-option>
              <el-option label="ERROR" value="ERROR"></el-option>
            </el-select>
          </div>
        </div>
        <div class="log-content" ref="logContentRef">
          <div v-for="(log, index) in filteredLogs" :key="index" :class="['log-line', `log-level-${log.level.toLowerCase()}`]">
            <span class="log-time">{{ formatTime(log.timestamp || log.created_at) }}</span>
            <span class="log-level" :class="`log-level-${log.level.toLowerCase()}`">[{{ log.level }}]</span>
            <span class="log-message">{{ log.message }}</span>
          </div>
          <el-pagination
            v-if="currentTaskId"
            v-model:current-page="taskLogPage"
            v-model:page-size="taskLogLimit"
            :total="taskLogTotal"
            layout="total, prev, pager, next"
            @current-change="loadTaskLogs"
            style="margin-top: 10px; justify-content: center;"
          />
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, computed, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import request from '@/utils/api'

const activeTab = ref('tasks')
const loading = ref(false)
const scheduledLoading = ref(false)
const triggerLoading = ref(false)
const triggerDialogVisible = ref(false)
const dialogMode = ref('manual')
const tasks = ref<any[]>([])
const scheduledTasks = ref<any[]>([])
const platforms = ref<any[]>([])
const logDialogVisible = ref(false)
const logs = ref<any[]>([])
const logLevelFilter = ref('')
const logContentRef = ref<HTMLElement>()
let eventSource: EventSource | null = null
const currentTaskId = ref<number | null>(null)
const taskLogPage = ref(1)
const taskLogLimit = ref(100)
const taskLogTotal = ref(0)
const selectedTaskIds = ref<number[]>([])
const tableRef = ref()

// 已完成任务的分页
const completedPagination = reactive({
  page: 1,
  limit: 20,
  total: 0
})

const queueStatus = reactive({
  pending_count: 0,
  running: [] as any[],
  pending: [] as any[],
  completed: [] as any[],
  completed_total: 0,
  platform_running: {} as Record<string, number>,
  global_active: 0
})

// 格式化时间为本地时间
const formatDateTime = (dateStr: string | null | undefined) => {
  if (!dateStr) return '-'
  try {
    const date = new Date(dateStr)
    if (isNaN(date.getTime())) return '-'
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  } catch (e) {
    return dateStr
  }
}

const platformMap: Record<string, string> = {
  all: '全部平台',
  iqiyi: '爱奇艺',
  tencent: '腾讯视频',
  youku: '优酷',
  mgtv: '芒果TV',
  sohu: '搜狐视频',
  bilibili: '哔哩哔哩'
}

const statusTypeMap: Record<string, any> = {
  pending: 'info',
  running: 'warning',
  completed: 'success',
  failed: 'danger'
}

const statusTextMap: Record<string, string> = {
  pending: '待执行',
  running: '运行中',
  completed: '已完成',
  failed: '失败'
}

const pagination = reactive({
  page: 1,
  limit: 20,
  total: 0
})

const triggerForm = reactive({
  platform: '',
  channels: [] as string[],
  mode: 'test',
  maxItems: 10,
  prodType: 'incremental',
  sort: ''
})

const triggerRules: FormRules = {
  platform: [{ required: true, message: '请选择平台', trigger: 'change' }]
}

const triggerFormRef = ref<FormInstance>()

const scheduledForm = reactive({
    platform: '',
    channel: '',
    channels: [] as string[],
    sort: '',
    frequencyType: 'daily',
    time: '00:00',
    dayOfWeek: ['0'],
    dayOfMonth: 1,
    cronExpression: '0 0 * * *'
})

const scheduledRules: FormRules = {
  platform: [{ required: true, message: '请选择平台', trigger: 'change' }],
  time: [{ required: true, message: '请选择执行时间', trigger: 'change' }],
  dayOfWeek: [{ required: true, message: '请选择星期', trigger: 'change' }],
  dayOfMonth: [{ required: true, message: '请选择日期', trigger: 'change' }],
  cronExpression: [{ required: true, message: '请输入Cron表达式', trigger: 'change' }]
}

const scheduledFormRef = ref<FormInstance>()

const currentChannels = computed(() => {
  const p = platforms.value.find(p => p.key === triggerForm.platform)
  return p?.channels || []
})

const currentScheduledChannels = computed(() => {
  const p = platforms.value.find(p => p.key === scheduledForm.platform)
  return p?.channels || []
})

const filteredLogs = computed(() => {
  if (!logLevelFilter.value) return logs.value
  return logs.value.filter(log => log.level === logLevelFilter.value)
})

const hasRunningTasks = computed(() => {
  return queueStatus.running.length > 0 || queueStatus.pending.length > 0
})

const loadTasks = async () => {
  loading.value = true
  try {
    const res = await request.get('/crawl-tasks', {
      params: {
        page: pagination.page,
        limit: pagination.limit
      }
    })
    if (res.data) {
      tasks.value = res.data.items || []
      pagination.total = res.data.total || 0
      
      // 加载完成后恢复选中状态
      await nextTick()
      if (tableRef.value && selectedTaskIds.value.length > 0) {
        tableRef.value.clearSelection()
        for (const row of tasks.value) {
          if (selectedTaskIds.value.includes(row.id) && row.status !== 'running') {
            tableRef.value.toggleRowSelection(row, true)
          }
        }
      }
    }
  } catch (error) {
    console.error('加载任务失败:', error)
    ElMessage.error('加载任务失败')
  } finally {
    loading.value = false
  }
}

const loadQueueStatus = async () => {
  try {
    const res = await request.get('/task-status', {
      params: {
        page: completedPagination.page,
        limit: completedPagination.limit
      }
    })
    if (res.data) {
      // 使用 res.data.data 获取正确的数据结构
      const data = res.data.data || res.data
      queueStatus.pending_count = (data.pending || []).length
      queueStatus.running = data.running || []
      queueStatus.pending = data.pending || []
      queueStatus.completed = data.completed || []
      queueStatus.completed_total = data.completed_total || 0
      queueStatus.platform_running = data.platform_running || {}
      queueStatus.global_active = data.global_active || 0
      
      completedPagination.total = data.completed_total || 0
    }
  } catch (error) {
    console.error('加载队列状态失败:', error)
  }
}

const refreshAll = () => {
  if (activeTab.value === 'queue') {
    loadQueueStatus()
  } else if (activeTab.value === 'tasks') {
    loadTasks()
  } else {
    loadScheduledTasks()
  }
}

// 监听标签切换，根据当前标签刷新
watch(activeTab, (newTab) => {
  if (newTab === 'scheduled') {
    loadScheduledTasks()
  } else if (newTab === 'tasks') {
    loadTasks()
  } else if (newTab === 'queue') {
    loadQueueStatus()
  }
})

const loadScheduledTasks = async () => {
  scheduledLoading.value = true
  try {
    const res = await request.get('/scheduled-tasks')
    if (res.data) {
      scheduledTasks.value = res.data || []
    }
  } catch (error) {
    console.error('加载定时任务失败:', error)
    ElMessage.error('加载定时任务失败')
  } finally {
    scheduledLoading.value = false
  }
}

const loadPlatforms = async () => {
  try {
    const res = await request.get('/platforms')
    if (res.data) {
      platforms.value = res.data
    }
  } catch (error) {
    console.error('加载平台失败:', error)
  }
}

const showTriggerDialog = () => {
    triggerForm.platform = 'all'
    triggerForm.channels = []
    triggerForm.mode = 'test'
    triggerForm.maxItems = 10
    triggerForm.prodType = 'incremental'
    triggerForm.sort = ''
    scheduledForm.platform = 'all'
    scheduledForm.channels = []
    scheduledForm.sort = ''
    scheduledForm.frequencyType = 'daily'
    scheduledForm.time = '00:00'
    scheduledForm.dayOfWeek = ['0']
    scheduledForm.dayOfMonth = 1
    scheduledForm.cronExpression = '0 0 * * *'
    triggerDialogVisible.value = true
}

const onPlatformChange = () => {
  triggerForm.channels = []
}

const onScheduledPlatformChange = () => {
    scheduledForm.channels = []
}

// 监听 triggerForm.channels 变化，选择全部时清空其他
watch(() => triggerForm.channels, (newVal) => {
    if (newVal && newVal.length > 1 && newVal.includes('')) {
        triggerForm.channels = ['']
    }
}, { deep: true })

// 监听 scheduledForm.channels 变化，选择全部时清空其他
watch(() => scheduledForm.channels, (newVal) => {
    if (newVal && newVal.length > 1 && newVal.includes('')) {
        scheduledForm.channels = ['']
    }
}, { deep: true })

const onFrequencyChange = () => {
  // 频率改变时重置相关字段
}

const handleTrigger = async () => {
  if (!triggerFormRef.value) return
  await triggerFormRef.value.validate(async (valid) => {
    if (valid) {
      if (triggerLoading.value) {
        ElMessage.warning('任务正在提交中，请稍候...')
        return
      }
      
      triggerLoading.value = true
      try {
        // 如果选中了"全部频道"或者未选择任何频道，则不指定具体频道
        let channels: string[] | undefined = undefined
        if (triggerForm.channels.length > 0) {
          // 如果选择了"全部频道"，则不指定频道过滤
          if (!triggerForm.channels.includes('')) {
            channels = triggerForm.channels
          }
        }
        
        const payload: any = {
          platform: triggerForm.platform,
          channels: channels
        }
        
        if (triggerForm.mode === 'test') {
          payload.max_items = triggerForm.maxItems
        } else {
          payload.prod_type = triggerForm.prodType
          payload.sort = triggerForm.sort || undefined
        }
        
        const res = await request.post('/trigger-crawl', payload)
        ElMessage.success(`已提交 ${res.data?.data?.count || 0} 个频道任务`)
        triggerDialogVisible.value = false
        
        // 无论当前在哪个标签页，都刷新队列状态
        setTimeout(() => {
          loadQueueStatus()
          if (activeTab.value === 'tasks') {
            loadTasks()
          }
        }, 500)
      } catch (error) {
        console.error('触发爬虫失败:', error)
        ElMessage.error('触发爬虫失败')
      } finally {
        triggerLoading.value = false
      }
    }
  })
}

const generateCronExpression = () => {
  const [hour, minute] = scheduledForm.time.split(':')
  
  if (scheduledForm.frequencyType === 'daily') {
    return `${minute} ${hour} * * *`
  } else if (scheduledForm.frequencyType === 'weekly') {
    const dayOfWeek = scheduledForm.dayOfWeek.join(',')
    return `${minute} ${hour} * * ${dayOfWeek}`
  } else if (scheduledForm.frequencyType === 'monthly') {
    return `${minute} ${hour} ${scheduledForm.dayOfMonth} * *`
  } else {
    return scheduledForm.cronExpression
  }
}

const handleCreateScheduledTask = async () => {
  if (!scheduledFormRef.value) return
  await scheduledFormRef.value.validate(async (valid) => {
    if (valid) {
      triggerLoading.value = true
      try {
        const cronExpression = generateCronExpression()
        
        // 如果选中了"全部频道"或者未选择任何频道，则不指定具体频道
        let channels: string[] | undefined = undefined
        if (scheduledForm.channels.length > 0) {
          // 如果选择了"全部频道"，则不指定频道过滤
          if (!scheduledForm.channels.includes('')) {
            channels = scheduledForm.channels
          }
        }
        
        const payload: any = {
          platform: scheduledForm.platform,
          channels: channels,
          cron_expression: cronExpression,
          sort: scheduledForm.sort || undefined
        }
        
        await request.post('/scheduled-tasks', payload)
        ElMessage.success('定时任务已创建')
        triggerDialogVisible.value = false
        setTimeout(loadScheduledTasks, 500)
      } catch (error) {
        console.error('创建定时任务失败:', error)
        ElMessage.error('创建定时任务失败')
      } finally {
        triggerLoading.value = false
      }
    }
  })
}

const handleStopTask = async (taskId: string) => {
  try {
    await ElMessageBox.confirm('确定要停止该任务吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await request.post(`/stop-task/${taskId}`)
    ElMessage.success('任务已停止')
    loadQueueStatus()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('停止任务失败:', error)
      ElMessage.error(error.message || '停止任务失败')
    }
  }
}

const handleStopTaskByDbId = async (dbTaskId: number) => {
  try {
    await ElMessageBox.confirm('确定要停止该任务吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await request.post(`/stop-task-by-db-id/${dbTaskId}`)
    ElMessage.success('任务已停止')
    loadTasks()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('停止任务失败:', error)
      ElMessage.error(error.message || '停止任务失败')
    }
  }
}

const handleStopAllTasks = async () => {
  try {
    await ElMessageBox.confirm('确定要停止所有运行中的任务吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await request.post('/stop-all-tasks')
    ElMessage.success('所有任务已停止')
    loadQueueStatus()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('停止任务失败:', error)
      ElMessage.error(error.message || '停止任务失败')
    }
  }
}

const handleResetTasks = async () => {
  try {
    await ElMessageBox.confirm('确定要重置所有任务状态吗？这将强制终止所有运行中的任务。', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await request.post('/reset-all-tasks')
    ElMessage.success('任务状态已重置')
    loadQueueStatus()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('重置任务失败:', error)
      ElMessage.error(error.message || '重置任务失败')
    }
  }
}

const selectableRow = (row: any) => {
  return true // 所有任务都可以选择
}

const handleSelectionChange = (selection: any[]) => {
  selectedTaskIds.value = selection.map(row => row.id)
}

const handleDelete = async (row: any) => {
  try {
    await ElMessageBox.confirm('确定要删除这个任务吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await request.delete(`/crawl-tasks/${row.id}`)
    ElMessage.success('删除成功')
    selectedTaskIds.value = [] // 清空选中状态
    await loadTasks()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除任务失败:', error)
      ElMessage.error('删除任务失败')
    }
  }
}

const handleBatchDelete = async () => {
  try {
    await ElMessageBox.confirm(`确定要删除选中的 ${selectedTaskIds.value.length} 个任务吗？运行中的任务会先停止再删除。`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    const result = await request.post('/crawl-tasks/batch-delete', {
      task_ids: selectedTaskIds.value
    })
    const { deleted_count, stopped_count } = result.data || {}
    let msg = `删除成功，共删除 ${deleted_count || 0} 个任务`
    if (stopped_count > 0) {
      msg += `，停止 ${stopped_count} 个运行中任务`
    }
    ElMessage.success(msg)
    selectedTaskIds.value = []
    await loadTasks()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除任务失败:', error)
      ElMessage.error('批量删除任务失败')
    }
  }
}

const deleteScheduledTask = async (taskId: string) => {
  try {
    await ElMessageBox.confirm('确定要删除这个定时任务吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await request.delete(`/scheduled-tasks/${taskId}`)
    ElMessage.success('删除成功')
    await loadScheduledTasks()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除定时任务失败:', error)
      ElMessage.error('删除定时任务失败')
    }
  }
}

const showLogDialog = async () => {
  currentTaskId.value = null
  logDialogVisible.value = true
  // 先加载历史日志
  try {
    const res = await request.get('/logs')
    if (res.data) {
      logs.value = res.data || []
    }
  } catch (e) {
    console.error('加载日志失败', e)
  }
  // 启动 SSE 连接
  startLogStream()
}

const viewTaskLogs = async (taskId: number) => {
  currentTaskId.value = taskId
  taskLogPage.value = 1
  logs.value = []
  logDialogVisible.value = true
  stopLogStream() // 查看历史日志时不需要实时流
  await loadTaskLogs()
}

const loadTaskLogs = async () => {
  if (!currentTaskId.value) return
  try {
    const res = await request.get(`/tasks/${currentTaskId.value}/logs`, {
      params: {
        page: taskLogPage.value,
        limit: taskLogLimit.value
      }
    })
    if (res.data) {
      if (taskLogPage.value === 1) {
        logs.value = res.data.items
      } else {
        logs.value = [...logs.value, ...res.data.items]
      }
      taskLogTotal.value = res.data.total
    }
  } catch (e) {
    console.error('加载任务日志失败', e)
  }
}

const startLogStream = () => {
  // 先关闭之前的连接
  if (eventSource) {
    eventSource.close()
  }
  
  const lastLog = logs.value[logs.value.length - 1]
  const since = lastLog ? lastLog.timestamp : ''
  const url = since ? `/logs/stream?since=${encodeURIComponent(since)}` : '/logs/stream'
  
  eventSource = new EventSource(url)
  
  eventSource.onmessage = (event) => {
    try {
      const log = JSON.parse(event.data)
      logs.value.push(log)
      // 自动滚动到底部
      nextTick(() => {
        if (logContentRef.value) {
          logContentRef.value.scrollTop = logContentRef.value.scrollHeight
        }
      })
    } catch (e) {
      console.error('解析日志失败', e)
    }
  }
  
  eventSource.onerror = (error) => {
    console.error('SSE 连接错误', error)
    // 5 秒后重试
    setTimeout(() => {
      if (logDialogVisible.value) {
        startLogStream()
      }
    }, 5000)
  }
}

const stopLogStream = () => {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
}

const clearLogs = () => {
  logs.value = []
}

const downloadLogs = () => {
  const content = logs.value.map(log => 
    `${log.timestamp} [${log.level}] ${log.message}`
  ).join('\n')
  
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `vbox-logs-${new Date().toISOString().slice(0, 10)}.txt`
  a.click()
  URL.revokeObjectURL(url)
}

const formatTime = (timestamp: string) => {
  return new Date(timestamp).toLocaleString('zh-CN')
}

// 监听对话框关闭，停止 SSE 连接
watch(logDialogVisible, (visible) => {
  if (!visible) {
    stopLogStream()
  }
})

onMounted(() => {
  loadTasks()
  loadPlatforms()
  loadQueueStatus()
})

onUnmounted(() => {
  stopLogStream()
})
</script>

<style scoped lang="scss">
.crawler {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .header-actions {
      display: flex;
      gap: 10px;
      align-items: center;
    }
  }
}

.log-container {
  height: 70vh;
  display: flex;
  flex-direction: column;
  
  .log-toolbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 0;
    border-bottom: 1px solid #e4e7ed;
    margin-bottom: 10px;
    
    .log-filter {
      display: flex;
      align-items: center;
    }
  }
  
  .log-content {
    flex: 1;
    overflow-y: auto;
    background: #1e1e1e;
    border-radius: 4px;
    padding: 10px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 13px;
    line-height: 1.6;
    
    .log-line {
      white-space: pre-wrap;
      word-break: break-all;
      margin-bottom: 4px;
      
      .log-time {
        color: #888;
        margin-right: 8px;
      }
      
      .log-level {
        margin-right: 8px;
        font-weight: bold;
        
        &.log-level-debug { color: #808080; }
        &.log-level-info { color: #67c23a; }
        &.log-level-warning { color: #e6a23c; }
        &.log-level-error { color: #f56c6c; }
      }
      
      .log-message {
        color: #d4d4d4;
      }
    }
  }
}
</style>
