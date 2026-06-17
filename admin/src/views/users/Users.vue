<template>
  <div class="users">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>用户管理</span>
          <div class="header-actions">
            <el-button @click="downloadTemplate">下载模板</el-button>
            <el-upload
              ref="uploadRef"
              :show-file-list="false"
              :before-upload="handleImport"
              accept=".csv"
              style="display: inline-block;"
            >
              <el-button type="primary">批量导入</el-button>
            </el-upload>
            <el-button type="success" @click="handleExport">导出数据</el-button>
            <el-button @click="resetQuery" :disabled="!hasActiveFilter">重置</el-button>
            <el-button type="primary" @click="loadData">刷新</el-button>
          </div>
        </div>
      </template>

      <!-- 搜索区域 -->
      <div class="search-form">
        <div class="filter-section">
          <span class="filter-label">用户状态：</span>
          <el-radio-group v-model="queryForm.status" size="default" @change="loadData">
            <el-radio-button value="">全部</el-radio-button>
            <el-radio-button value="active">正常</el-radio-button>
            <el-radio-button value="banned">禁用</el-radio-button>
          </el-radio-group>
        </div>
        <div class="filter-section">
          <span class="filter-label">邀请人ID：</span>
          <el-input v-model="queryForm.invited_by" placeholder="输入邀请人ID" clearable style="width: 150px;" @clear="loadData" @keyup.enter="loadData" />
        </div>
        <div class="search-section">
          <el-input v-model="queryForm.keyword" placeholder="搜索用户名/手机号/昵称" clearable style="width: 300px;" @clear="loadData" @keyup.enter="loadData"/>
          <el-button type="primary" @click="loadData">搜索</el-button>
        </div>
      </div>

      <el-table :data="tableData" stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" width="150" />
        <el-table-column prop="phone" label="手机号" width="150" />
        <el-table-column prop="nickname" label="昵称" min-width="150" />
        <el-table-column prop="vip_status" label="VIP状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.vip_status" :type="row.vip_status === 'vip' ? 'success' : 'info'">
              {{ row.vip_status === 'vip' ? 'VIP用户' : '普通用户' }}
            </el-tag>
            <span v-else style="color: #999;">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="vip_plans" label="VIP类型" min-width="240">
          <template #default="{ row }">
            <div v-if="row.vip_plans && row.vip_plans.length > 0" class="vip-plans-cell">
              <el-tag
                v-for="(plan, index) in row.vip_plans"
                :key="index"
                type="warning"
                size="small"
                style="margin: 2px;"
              >
                {{ plan.name }}
                <span v-if="plan.terminal"> ({{ formatTerminal(plan.terminal) }})</span>
              </el-tag>
            </div>
            <span v-else style="color: #999;">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="账号状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'danger'">
              {{ row.status === 'active' ? '正常' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="invite_code" label="邀请码" width="100">
          <template #default="{ row }">
            <span v-if="row.invite_code" style="font-family: monospace; color: #e6a23c;">{{ row.invite_code }}</span>
            <span v-else style="color: #999;">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="points" label="积分" width="80">
          <template #default="{ row }">
            <span style="color: #e6a23c; font-weight: 600;">{{ row.points || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="注册时间" width="170" />
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleViewDetail(row)">详情</el-button>
            <el-button link type="success" @click="handleSetVip(row)">设置VIP</el-button>
            <el-button 
              link 
              :type="row.status === 'active' ? 'danger' : 'success'" 
              @click="handleToggleStatus(row)"
            >
              {{ row.status === 'active' ? '禁用' : '启用' }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="queryForm.page"
        v-model:page-size="queryForm.limit"
        :total="total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="loadData"
        @current-change="loadData"
        style="margin-top: 20px; justify-content: flex-end;"
      />
    </el-card>

    <!-- 用户详情弹窗 -->
    <el-dialog v-model="detailDialogVisible" title="用户详情" width="600px">
      <div v-if="currentUser" class="user-detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="用户ID">{{ currentUser.id }}</el-descriptions-item>
          <el-descriptions-item label="用户名">{{ currentUser.username || '-' }}</el-descriptions-item>
          <el-descriptions-item label="手机号">{{ currentUser.phone || '-' }}</el-descriptions-item>
          <el-descriptions-item label="昵称">{{ currentUser.nickname || '-' }}</el-descriptions-item>
          <el-descriptions-item label="VIP状态">
            <el-tag v-if="currentUser.vip_status" :type="currentUser.vip_status === 'vip' ? 'success' : 'info'">
              {{ currentUser.vip_status === 'vip' ? 'VIP用户' : '普通用户' }}
            </el-tag>
            <span v-else style="color: #999;">-</span>
          </el-descriptions-item>
          <el-descriptions-item label="VIP到期时间">{{ currentUser.vip_expire_time || '-' }}</el-descriptions-item>
          <el-descriptions-item label="账号状态">
            <el-tag :type="currentUser.status === 'active' ? 'success' : 'danger'">
              {{ currentUser.status === 'active' ? '正常' : '禁用' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="邀请码">
            <span v-if="currentUser.invite_code" style="font-family: monospace; color: #e6a23c; font-weight: 600;">{{ currentUser.invite_code }}</span>
            <span v-else style="color: #999;">-</span>
          </el-descriptions-item>
          <el-descriptions-item label="积分">
            <span style="color: #e6a23c; font-weight: 600;">{{ currentUser.points || 0 }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="邀请人ID">
            <span v-if="currentUser.invited_by">{{ currentUser.invited_by }}</span>
            <span v-else style="color: #999;">-</span>
          </el-descriptions-item>
          <el-descriptions-item label="注册时间">{{ currentUser.created_at || '-' }}</el-descriptions-item>
          <el-descriptions-item label="最后登录">{{ currentUser.last_login_at || '-' }}</el-descriptions-item>
        </el-descriptions>
      </div>
      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 设置VIP弹窗 -->
    <el-dialog v-model="vipDialogVisible" title="设置VIP" width="500px">
      <div v-if="currentUser" class="vip-setting-form">
        <el-form :model="vipForm" label-width="100px">
          <el-form-item label="当前用户">
            <span>{{ currentUser.username }}<span v-if="currentUser.nickname && currentUser.nickname !== currentUser.username"> ({{ currentUser.nickname }})</span></span>
          </el-form-item>
          
          <el-form-item label="VIP状态">
            <el-radio-group v-model="vipForm.is_vip">
              <el-radio :value="true">开通VIP</el-radio>
              <el-radio :value="false">关闭VIP</el-radio>
            </el-radio-group>
          </el-form-item>

          <template v-if="vipForm.is_vip">
            <el-form-item label="设置方式">
              <el-radio-group v-model="vipForm.setting_type">
                <el-radio value="plan">选择套餐</el-radio>
                <el-radio value="duration">按天数</el-radio>
                <el-radio value="expire">指定时间</el-radio>
              </el-radio-group>
            </el-form-item>

            <el-form-item v-if="vipForm.setting_type === 'duration'" label="天数">
              <el-input-number v-model="vipForm.duration_days" :min="1" :max="3650" />
              <span style="margin-left: 10px;">天</span>
            </el-form-item>

            <el-form-item v-if="vipForm.setting_type === 'expire'" label="到期时间">
              <el-date-picker
                v-model="vipForm.expire_at"
                type="datetime"
                placeholder="选择过期时间"
                format="YYYY-MM-DD HH:mm:ss"
                value-format="YYYY-MM-DD HH:mm:ss"
                style="width: 100%;"
              />
            </el-form-item>

            <el-form-item v-if="vipForm.setting_type === 'plan'" label="选择套餐">
              <el-checkbox-group v-model="vipForm.plan_ids">
                <el-checkbox
                  v-for="plan in vipPlans"
                  :key="plan.id"
                  :value="plan.id"
                  :label="plan.name"
                />
              </el-checkbox-group>
            </el-form-item>
          </template>

          <template v-else>
            <el-form-item v-if="currentUser.vip_plans && currentUser.vip_plans.length > 0" label="选择要关闭的套餐">
              <el-checkbox-group v-model="vipForm.cancel_plan_ids">
                <el-checkbox
                  v-for="(plan, index) in currentUser.vip_plans"
                  :key="index"
                  :value="plan.id"
                  :label="plan.name"
                />
              </el-checkbox-group>
            </el-form-item>
            <el-form-item v-else label="当前套餐">
              <span style="color: #999;">该用户没有激活的套餐</span>
            </el-form-item>
          </template>

          <el-form-item label="备注">
            <el-input v-model="vipForm.remark" type="textarea" :rows="2" placeholder="可选，填写操作说明" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="vipDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingVip" @click="handleSaveVip">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/utils/api'

const loading = ref(false)
const tableData = ref<any[]>([])
const total = ref(0)
const detailDialogVisible = ref(false)
const vipDialogVisible = ref(false)
const savingVip = ref(false)
const currentUser = ref<any>(null)
const vipPlans = ref<any[]>([])
const uploadRef = ref()

const queryForm = reactive({
  page: 1,
  limit: 20,
  keyword: '',
  status: '',
  invited_by: ''
})

const vipForm = reactive({
  is_vip: true,
  setting_type: 'plan',
  duration_days: 30,
  expire_at: '',
  plan_ids: [] as number[],
  cancel_plan_ids: [] as number[],
  remark: ''
})

const hasActiveFilter = computed(() => {
  return queryForm.keyword || queryForm.status || queryForm.invited_by
})

// 格式化终端类型
function formatTerminal(terminal: string): string {
  if (!terminal) return ''
  const labels: { [key: string]: string } = {
    mobile: '移动端',
    tv: 'TV端',
    pc: 'PC端'
  }
  const parts = terminal.split(',').map(t => labels[t.trim()] || t.trim())
  return parts.filter(Boolean).join(' ')
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await request.get('/users', { params: queryForm })
    if (res.data) {
      tableData.value = res.data.items || []
      total.value = res.data.total || 0
    }
  } catch (error) {
    console.error('加载数据失败:', error)
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

const resetQuery = () => {
  queryForm.keyword = ''
  queryForm.status = ''
  queryForm.invited_by = ''
  queryForm.page = 1
  loadData()
}

const handleViewDetail = async (row: any) => {
  currentUser.value = row
  detailDialogVisible.value = true
}

const handleSetVip = async (row: any) => {
  currentUser.value = row

  // 重置表单
  vipForm.is_vip = true  // 默认选中开通VIP
  vipForm.setting_type = 'plan'  // 默认选中选择套餐
  vipForm.duration_days = 30
  vipForm.expire_at = ''
  vipForm.plan_ids = []
  vipForm.cancel_plan_ids = []
  vipForm.remark = ''

  // 加载VIP套餐
  await loadVipPlans()

  vipDialogVisible.value = true
}

const loadVipPlans = async () => {
  try {
    const res = await request.get('/vip/plans')
    if (res.data) {
      vipPlans.value = res.data
    }
  } catch (error) {
    console.error('加载VIP套餐失败:', error)
  }
}

const handleSaveVip = async () => {
  if (!currentUser.value) return

  let duration_days = null
  let expire_at = null

  if (vipForm.is_vip) {
    if (vipForm.setting_type === 'duration') {
      duration_days = vipForm.duration_days
    } else if (vipForm.setting_type === 'expire') {
      if (!vipForm.expire_at) {
        ElMessage.warning('请选择到期时间')
        return
      }
      expire_at = vipForm.expire_at
    } else if (vipForm.setting_type === 'plan') {
      if (!vipForm.plan_ids || vipForm.plan_ids.length === 0) {
        ElMessage.warning('请选择套餐')
        return
      }
      // 多选套餐时取最大天数
      let max_duration = 0
      for (const pid of vipForm.plan_ids) {
        const plan = vipPlans.value.find(p => p.id === pid)
        if (plan && plan.duration_days > max_duration) {
          max_duration = plan.duration_days
        }
      }
      duration_days = max_duration
    }

    if (!duration_days && !expire_at) {
      ElMessage.warning('请设置VIP有效期')
      return
    }
  } else {
    // 关闭VIP时检查是否选择了套餐
    if (!vipForm.cancel_plan_ids || vipForm.cancel_plan_ids.length === 0) {
      ElMessage.warning('请选择要关闭的套餐')
      return
    }
  }

  savingVip.value = true
  try {
    const res = await request.post(`/users/${currentUser.value.id}/set-vip`, {
      is_vip: vipForm.is_vip,
      duration_days: duration_days,
      expire_at: expire_at,
      plan_ids: vipForm.plan_ids,
      cancel_plan_ids: vipForm.cancel_plan_ids,
      remark: vipForm.remark
    })
    
    if (res.code === 0) {
      ElMessage.success('设置成功')
      vipDialogVisible.value = false
      loadData()
    } else {
      ElMessage.error(res.message || '设置失败')
    }
  } catch (error) {
    console.error('设置VIP失败:', error)
    ElMessage.error('设置失败')
  } finally {
    savingVip.value = false
  }
}

const handleToggleStatus = async (row: any) => {
  const newStatus = row.status === 'active' ? 'banned' : 'active'
  const actionText = row.status === 'active' ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(`确定要${actionText}用户「${row.username}」吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await request.put(`/users/${row.id}/status`, null, { params: { status: newStatus } })
    ElMessage.success(`${actionText}成功`)
    loadData()
  } catch (error) {
    if ((error as any) !== 'cancel') {
      console.error('操作失败:', error)
      ElMessage.error('操作失败')
    }
  }
}

// 用户导入导出
const downloadTemplate = () => {
  window.open('/admin-api/users/template', '_blank')
}

const handleImport = async (file: File) => {
  try {
    const formData = new FormData()
    formData.append('file', file)
    const res = await request.post('/users/batch-import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    ElMessage.success(res.message || '导入成功')
    loadData()
  } catch (error: any) {
    ElMessage.error('导入失败: ' + (error.message || '未知错误'))
  }
  return false
}

const handleExport = () => {
  let url = '/admin-api/users/export'
  const params: string[] = []
  if (queryForm.keyword) {
    params.push(`keyword=${encodeURIComponent(queryForm.keyword)}`)
  }
  if (queryForm.status) {
    params.push(`status=${queryForm.status}`)
  }
  if (queryForm.invited_by) {
    params.push(`invited_by=${queryForm.invited_by}`)
  }
  if (params.length > 0) {
    url += '?' + params.join('&')
  }
  window.open(url, '_blank')
}

onMounted(() => {
  loadData()
})
</script>

<style scoped lang="scss">
.users {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .header-actions {
      display: flex;
      gap: 10px;
    }
  }

  .vip-plans-cell {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }
  
  .search-form {
    margin-bottom: 20px;
    
    .filter-section {
      display: flex;
      align-items: center;
      margin-bottom: 15px;
      
      .filter-label {
        font-size: 14px;
        color: #606266;
        margin-right: 10px;
        font-weight: 500;
        white-space: nowrap;
      }
    }
    
    .search-section {
      display: flex;
      align-items: center;
      gap: 10px;
    }
  }
}
</style>
