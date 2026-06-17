<template>
  <div class="vip-cdkeys">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>VIP卡密管理</span>
          <div class="header-actions">
            <el-button @click="resetQuery" :disabled="!hasActiveFilter">重置</el-button>
            <el-button type="success" @click="exportAllData" :disabled="tableData.length === 0">
              <el-icon><Download /></el-icon>
              导出当前数据
            </el-button>
            <el-button type="primary" @click="showGenerateDialog">
              <el-icon><Plus /></el-icon>
              生成卡密
            </el-button>
          </div>
        </div>
      </template>

      <!-- 搜索区域 -->
      <div class="search-form">
        <div class="filter-section">
          <span class="filter-label">使用状态：</span>
          <el-radio-group v-model="queryForm.is_used" size="default" @change="loadData">
            <el-radio-button :value="null">全部</el-radio-button>
            <el-radio-button :value="false">未使用</el-radio-button>
            <el-radio-button :value="true">已使用</el-radio-button>
          </el-radio-group>
        </div>
        <div class="filter-section">
          <span class="filter-label">关联套餐：</span>
          <el-select v-model="queryForm.plan_id" placeholder="选择套餐" clearable style="width: 200px;" @change="loadData">
            <el-option v-for="plan in plans" :key="plan.id" :label="plan.name" :value="plan.id" />
          </el-select>
        </div>
        <div class="search-section">
          <el-input v-model="queryForm.keyword" placeholder="搜索卡密" clearable style="width: 300px;" @clear="loadData" @keyup.enter="loadData"/>
          <el-button type="primary" @click="loadData">搜索</el-button>
        </div>
      </div>

      <el-table :data="tableData" stripe v-loading="loading" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="55" />
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="code" label="卡密" min-width="250">
          <template #default="{ row }">
            <el-tag type="info" style="font-family: 'Courier New', monospace; letter-spacing: 1px; max-width: 220px;">
              {{ row.code }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="关联套餐" min-width="150">
          <template #default="{ row }">
            <span v-if="row.plan_name">{{ row.plan_name }}</span>
            <span v-else class="text-gray">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="duration_days" label="会员天数" width="120">
          <template #default="{ row }">
            {{ row.duration_days === 0 ? '永久' : row.duration_days + ' 天' }}
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_used ? 'info' : 'success'">
              {{ row.is_used ? '已使用' : '未使用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="used_at" label="使用时间" width="180" />
        <el-table-column prop="used_by" label="使用用户" width="120" />
        <el-table-column prop="expired_at" label="过期时间" width="180" />
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="copyCode(row)" v-if="!row.is_used">复制</el-button>
            <el-button link type="danger" @click="handleDelete(row)" :disabled="row.is_used">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div style="margin-top: 15px;">
        <el-button type="primary" @click="exportSelected" :disabled="selectedIds.length === 0">
          <el-icon><Download /></el-icon>
          导出选中 ({{ selectedIds.length }})
        </el-button>
      </div>

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

    <!-- 生成卡密对话框 -->
    <el-dialog v-model="generateDialogVisible" title="生成卡密" width="600px">
      <el-form :model="generateForm" :rules="generateRules" ref="generateFormRef" label-width="120px">
        <el-form-item label="关联套餐" prop="plan_id">
          <el-select v-model="generateForm.plan_id" placeholder="请选择套餐（可选）" style="width: 100%;" clearable>
            <el-option v-for="plan in plans" :key="plan.id" :label="plan.name" :value="plan.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="会员天数" prop="duration_days">
          <el-input-number v-model="generateForm.duration_days" :min="0" placeholder="0表示永久" style="width: 100%;" />
          <div class="form-tip">0表示永久</div>
        </el-form-item>
        <el-form-item label="生成数量" prop="count">
          <el-input-number v-model="generateForm.count" :min="1" :max="100" placeholder="生成数量" style="width: 100%;" />
          <div class="form-tip">最多生成100张</div>
        </el-form-item>
        <el-form-item label="过期天数" prop="expired_days">
          <el-input-number v-model="generateForm.expired_days" :min="1" placeholder="卡密多少天后过期" style="width: 100%;" />
          <div class="form-tip">卡密多少天后过期，默认365天</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="generateDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleGenerate" :loading="generating">生成</el-button>
      </template>
    </el-dialog>

    <!-- 生成结果对话框 -->
    <el-dialog v-model="resultDialogVisible" title="生成成功" width="600px">
      <div class="result-content">
        <p class="result-tip">以下是新生成的卡密，请妥善保存：</p>
        <el-input
          v-model="newCdkeysText"
          type="textarea"
          :rows="10"
          readonly
          style="margin-top: 10px;"
        />
        <div style="margin-top: 15px; text-align: right;">
          <el-button type="primary" @click="copyCdkeys">复制全部</el-button>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, Plus } from '@element-plus/icons-vue'
import request from '@/utils/api'

interface VipCdkey {
  id?: number
  code: string
  plan_id?: number
  plan_name?: string
  duration_days: number
  is_used: boolean
  used_at?: string
  used_by?: number
  expired_at?: string
  created_at?: string
}

interface VipPlan {
  id: number
  name: string
  price: number
  duration_days: number
}

const loading = ref(false)
const generating = ref(false)
const tableData = ref<VipCdkey[]>([])
const plans = ref<VipPlan[]>([])
const total = ref(0)
const generateDialogVisible = ref(false)
const resultDialogVisible = ref(false)
const newCdkeysText = ref('')
const generateFormRef = ref()
const selectedIds = ref<number[]>([])
const selectedRows = ref<any[]>([])

const queryForm = reactive({
  page: 1,
  limit: 20,
  is_used: null as boolean | null,
  keyword: '',
  plan_id: null as number | null
})

const hasActiveFilter = computed(() => {
  return queryForm.keyword || queryForm.is_used !== null || queryForm.plan_id !== null
})

const generateForm = reactive({
  plan_id: undefined as number | undefined,
  duration_days: 30,
  count: 1,
  expired_days: 365
})

const generateRules = {
  duration_days: [{ required: true, message: '请输入会员天数', trigger: 'blur' }],
  count: [{ required: true, message: '请输入生成数量', trigger: 'blur' }],
  expired_days: [{ required: true, message: '请输入过期天数', trigger: 'blur' }]
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await request.get('/vip-cdkeys', { params: queryForm })
    tableData.value = res.data.items
    total.value = res.data.total
  } catch (error) {
    console.error('获取卡密列表失败:', error)
    ElMessage.error('获取卡密列表失败')
  } finally {
    loading.value = false
  }
}

const loadPlans = async () => {
  try {
    const res = await request.get('/vip-plans', { params: { is_enabled: true } })
    plans.value = res.data.items
  } catch (error) {
    console.error('获取套餐列表失败:', error)
  }
}

const resetQuery = () => {
  queryForm.keyword = ''
  queryForm.is_used = null
  queryForm.plan_id = null
  queryForm.page = 1
  selectedIds.value = []
  loadData()
}

const showGenerateDialog = () => {
  Object.assign(generateForm, {
    plan_id: undefined,
    duration_days: 30,
    count: 1,
    expired_days: 365
  })
  generateDialogVisible.value = true
}

const handleGenerate = async () => {
  try {
    await generateFormRef.value.validate()
    generating.value = true
    const res = await request.post('/vip-cdkeys', generateForm)
    generateDialogVisible.value = false
    newCdkeysText.value = res.data.items.map((item: VipCdkey) => item.code).join('\n')
    resultDialogVisible.value = true
    loadData()
  } catch (error: any) {
    if (error !== false) {
      console.error('生成卡密失败:', error)
      ElMessage.error(error.message || '生成卡密失败')
    }
  } finally {
    generating.value = false
  }
}

const copyCdkeys = async () => {
  try {
    await navigator.clipboard.writeText(newCdkeysText.value)
    ElMessage.success('复制成功')
  } catch (error) {
    ElMessage.error('复制失败，请手动复制')
  }
}

const handleSelectionChange = (selection: any[]) => {
  selectedIds.value = selection.map(row => row.id)
  selectedRows.value = selection
}

const copyCode = async (row: VipCdkey) => {
  try {
    await navigator.clipboard.writeText(row.code)
    ElMessage.success('卡密已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败')
  }
}

const handleDelete = async (row: VipCdkey) => {
  try {
    await ElMessageBox.confirm('确定要删除该卡密吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await request.delete(`/vip-cdkeys/${row.id}`)
    ElMessage.success('删除成功')
    loadData()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

// 导出选中数据
const exportSelected = () => {
  exportToExcel(selectedRows.value, '选中卡密')
}

// 导出当前页面数据
const exportAllData = () => {
  exportToExcel(tableData.value, 'VIP卡密列表')
}

// 导出Excel函数
const exportToExcel = (data: any[], filename: string) => {
  // 简单的CSV导出实现
  const headers = ['ID', '卡密', '关联套餐', '会员天数', '状态', '使用时间', '使用用户', '过期时间', '创建时间']
  const csvContent = [
    headers.join(','),
    ...data.map(row => [
      row.id,
      `"${row.code}"`,
      `"${row.plan_name || ''}"`,
      row.duration_days === 0 ? '永久' : row.duration_days,
      row.is_used ? '已使用' : '未使用',
      `"${row.used_at || ''}"`,
      row.used_by || '',
      `"${row.expired_at || ''}"`,
      `"${row.created_at || ''}"`
    ].join(','))
  ].join('\n')

  // 添加BOM防止中文乱码
  const BOM = '\uFEFF'
  const blob = new Blob([BOM + csvContent], { type: 'text/csv;charset=utf-8;' })
  
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  link.setAttribute('href', url)
  link.setAttribute('download', `${filename}_${new Date().toISOString().slice(0,10)}.csv`)
  link.style.visibility = 'hidden'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  
  ElMessage.success('导出成功')
}

onMounted(() => {
  loadData()
  loadPlans()
})
</script>

<style scoped lang="scss">
.vip-cdkeys {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    
    .header-actions {
      display: flex;
      gap: 10px;
    }
  }

  .search-form {
    margin-bottom: 20px;

    .filter-section,
    .search-section {
      margin-bottom: 15px;
      display: flex;
      align-items: center;

      .filter-label {
        font-size: 14px;
        color: #606266;
        margin-right: 10px;
        font-weight: 500;
        white-space: nowrap;
      }
      
      .search-section {
        gap: 10px;
      }
    }
  }

  .text-gray {
    color: #909399;
  }

  .form-tip {
    margin-top: 5px;
    font-size: 12px;
    color: #909399;
  }

  .result-content {
    .result-tip {
      margin-bottom: 10px;
      font-size: 14px;
      color: #606266;
    }
  }
}
</style>
