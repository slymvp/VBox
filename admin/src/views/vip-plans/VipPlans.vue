<template>
  <div class="vip-plans">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>VIP套餐管理</span>
          <div class="header-actions">
            <el-button @click="downloadTemplate">
              下载模板
            </el-button>
            <el-upload
              ref="uploadRef"
              :show-file-list="false"
              :before-upload="handleUpload"
              accept=".csv"
              style="display: inline-block;"
            >
              <el-button type="primary">批量导入</el-button>
            </el-upload>
            <el-button type="success" @click="handleBatchEnable" :disabled="selectedIds.length === 0">
              批量启用
            </el-button>
            <el-button type="warning" @click="handleBatchDisable" :disabled="selectedIds.length === 0">
              批量禁用
            </el-button>
            <el-button type="primary" @click="handleAdd">
              <el-icon><Plus /></el-icon>
              新增套餐
            </el-button>
          </div>
        </div>
      </template>

      <!-- 套餐类型 Tab -->
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="正式套餐" name="formal" />
        <el-tab-pane label="优惠套餐" name="promotion" />
      </el-tabs>

      <!-- 搜索区域 -->
      <div class="search-form">
        <div class="filter-section">
          <span class="filter-label">状态：</span>
          <el-radio-group v-model="queryForm.is_enabled" size="default" @change="loadData">
            <el-radio-button :value="null">全部</el-radio-button>
            <el-radio-button :value="true">启用</el-radio-button>
            <el-radio-button :value="false">禁用</el-radio-button>
          </el-radio-group>
        </div>
        <div class="search-section">
          <el-input v-model="queryForm.keyword" placeholder="搜索套餐名称" clearable style="width: 300px;" @clear="loadData" @keyup.enter="loadData"/>
          <el-button type="primary" @click="loadData">搜索</el-button>
        </div>
      </div>

      <!-- 提示信息 -->
      <div class="sort-tip">
        <el-icon><Rank /></el-icon>
        <span>提示：拖动套餐可以调整显示顺序</span>
      </div>

      <!-- 数据表格 -->
      <el-table 
        :data="tableData" 
        stripe 
        v-loading="loading"
        row-key="id"
        @row-drop="handleRowDrop"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column type="drag" width="60">
          <template #default>
            <el-icon class="drag-icon"><Rank /></el-icon>
          </template>
        </el-table-column>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="套餐名称" min-width="150" />
        <el-table-column label="套餐类型" width="120">
          <template #default="{ row }">
            <el-tag>
              {{ getPlanTypeLabel(row.plan_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="时长类型" width="120">
          <template #default="{ row }">
            <el-tag>
              {{ getDurationTypeLabel(row.duration_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="价格" width="150">
          <template #default="{ row }">
            <span class="price">¥{{ row.price }}</span>
            <span v-if="row.original_price" class="original-price">¥{{ row.original_price }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="duration_days" label="有效天数" width="120">
          <template #default="{ row }">
            <span>{{ row.duration_days === 0 ? '永久' : row.duration_days + ' 天' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="unit" label="单位描述" width="150" />
        <el-table-column label="设备类型" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.devices === 'pc'" size="small" type="info">
              <span style="margin-right: 3px;">💻</span>PC端
            </el-tag>
            <el-tag v-else-if="row.devices === 'mobile'" size="small" type="success">
              <span style="margin-right: 3px;">📱</span>移动端
            </el-tag>
            <el-tag v-else-if="row.devices === 'tv'" size="small" type="warning">
              <span style="margin-right: 3px;">📺</span>TV端
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="是否推荐" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_recommend ? 'warning' : 'info'">
              {{ row.is_recommend ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_enabled ? 'success' : 'danger'">
              {{ row.is_enabled ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="sort_order" label="排序" width="80" />
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
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

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item label="套餐名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入套餐名称" />
        </el-form-item>
        <el-form-item label="套餐类型" prop="plan_type">
          <el-radio-group v-model="form.plan_type">
            <el-radio-button value="formal">正式套餐</el-radio-button>
            <el-radio-button value="promotion">优惠套餐</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="时长类型" prop="duration_type">
          <el-radio-group v-model="form.duration_type">
            <el-radio-button value="monthly">月度</el-radio-button>
            <el-radio-button value="quarterly">季度</el-radio-button>
            <el-radio-button value="yearly">年度</el-radio-button>
            <el-radio-button value="permanent">永久</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="价格" prop="price">
              <el-input-number v-model="form.price" :min="0" :precision="2" placeholder="价格" style="width: 100%;" @change="autoCalculate" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="原价" prop="original_price">
              <el-input-number v-model="form.original_price" :min="0" :precision="2" placeholder="原价" style="width: 100%;" @change="autoCalculate" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="有效天数" prop="duration_days">
              <el-input-number v-model="form.duration_days" :min="0" placeholder="0表示永久" style="width: 100%;" @change="autoCalculate" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="节省金额" prop="save_amount">
              <el-input-number v-model="form.save_amount" :min="0" :precision="2" placeholder="自动计算" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="单位描述" prop="unit">
          <el-input v-model="form.unit" placeholder="自动计算，例如：约0.33元/天" />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="是否推荐" prop="is_recommend">
              <el-switch v-model="form.is_recommend" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="是否启用" prop="is_enabled">
              <el-switch v-model="form.is_enabled" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="排序" prop="sort_order">
          <el-input-number v-model="form.sort_order" :min="0" placeholder="排序" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="设备类型" prop="devices">
          <el-radio-group v-model="form.devices">
            <el-radio value="pc" label="PC端" />
            <el-radio value="mobile" label="移动端" />
            <el-radio value="tv" label="TV端" />
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Rank } from '@element-plus/icons-vue'
import request from '@/utils/api'

interface VipPlan {
  id?: number
  name: string
  price: number
  original_price?: number
  duration_days: number
  unit?: string
  save_amount?: number
  is_recommend?: boolean
  is_enabled?: boolean
  sort_order?: number
  plan_type?: 'formal' | 'promotion'
  duration_type?: 'monthly' | 'quarterly' | 'yearly' | 'permanent'
  devices?: string
  created_at?: string
  updated_at?: string
}

const loading = ref(false)
const submitting = ref(false)
const tableData = ref<VipPlan[]>([])
const total = ref(0)
const dialogVisible = ref(false)
const dialogTitle = computed(() => (form.id ? '编辑套餐' : '新增套餐'))
const formRef = ref()
const uploadRef = ref()
const selectedIds = ref<number[]>([])
const activeTab = ref('formal')

const queryForm = reactive({
  page: 1,
  limit: 20,
  is_enabled: null as boolean | null,
  keyword: '',
  plan_type: 'formal' as 'formal' | 'promotion'
})

const form = reactive<VipPlan>({
  name: '',
  price: 0,
  original_price: 0,
  duration_days: 30,
  unit: '',
  save_amount: 0,
  is_recommend: false,
  is_enabled: true,
  sort_order: 0,
  plan_type: 'formal',
  duration_type: 'monthly',
  devices: 'pc'
})

const rules = {
  name: [{ required: true, message: '请输入套餐名称', trigger: 'blur' }],
  price: [{ required: true, message: '请输入价格', trigger: 'blur' }],
  duration_days: [{ required: true, message: '请输入有效天数', trigger: 'blur' }],
  plan_type: [{ required: true, message: '请选择套餐类型', trigger: 'change' }],
  duration_type: [{ required: true, message: '请选择时长类型', trigger: 'change' }]
}

const planTypeLabels = {
  formal: '正式套餐',
  promotion: '优惠套餐'
}

const durationTypeLabels = {
  monthly: '月度',
  quarterly: '季度',
  yearly: '年度',
  permanent: '永久'
}

const getPlanTypeLabel = (type: string | undefined) => {
  return type ? planTypeLabels[type as keyof typeof planTypeLabels] : '未知'
}

const getDurationTypeLabel = (type: string | undefined) => {
  return type ? durationTypeLabels[type as keyof typeof durationTypeLabels] : '未知'
}

const handleTabChange = (tabName: string) => {
  queryForm.plan_type = tabName as 'formal' | 'promotion'
  queryForm.page = 1
  loadData()
}

const autoCalculate = () => {
  // 自动计算节省金额
  if (form.original_price && form.price && form.original_price > form.price) {
    form.save_amount = Math.round((form.original_price - form.price) * 100) / 100
  } else {
    form.save_amount = 0
  }

  // 自动计算单位描述
  if (form.duration_days && form.duration_days > 0 && form.price && form.price > 0) {
    const perDay = form.price / form.duration_days
    if (perDay >= 1) {
      form.unit = `约${perDay.toFixed(2)}元/天`
    } else {
      form.unit = `约${perDay.toFixed(3)}元/天`
    }
  } else if (form.duration_days === 0) {
    form.unit = '永久VIP'
  } else {
    form.unit = ''
  }
}

const loadData = async () => {
  loading.value = true
  try {
    const params: any = {
      page: queryForm.page,
      limit: queryForm.limit,
      plan_type: queryForm.plan_type
    }
    if (queryForm.is_enabled !== null) {
      params.is_enabled = queryForm.is_enabled
    }
    if (queryForm.keyword) {
      params.keyword = queryForm.keyword
    }
    const res = await request.get('/vip-plans', { params })
    tableData.value = res.data.items
    total.value = res.data.total
  } catch (error) {
    console.error('获取套餐列表失败:', error)
    ElMessage.error('获取套餐列表失败')
  } finally {
    loading.value = false
  }
}

const handleSelectionChange = (selection: any[]) => {
  selectedIds.value = selection.map(item => item.id)
}

const handleBatchEnable = async () => {
  try {
    await ElMessageBox.confirm('确定要启用选中的套餐吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await request.put('/vip-plans/batch-update-status', {
      plan_ids: selectedIds.value,
      is_enabled: true
    })
    ElMessage.success('批量启用成功')
    selectedIds.value = []
    loadData()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('批量启用失败:', error)
      ElMessage.error('批量启用失败')
    }
  }
}

const handleBatchDisable = async () => {
  try {
    await ElMessageBox.confirm('确定要禁用选中的套餐吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await request.put('/vip-plans/batch-update-status', {
      plan_ids: selectedIds.value,
      is_enabled: false
    })
    ElMessage.success('批量禁用成功')
    selectedIds.value = []
    loadData()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('批量禁用失败:', error)
      ElMessage.error('批量禁用失败')
    }
  }
}

const handleAdd = () => {
  Object.assign(form, {
    id: undefined,
    name: '',
    price: 0,
    original_price: 0,
    duration_days: 30,
    unit: '',
    save_amount: 0,
    is_recommend: false,
    is_enabled: true,
    sort_order: 0,
    plan_type: activeTab.value,
    duration_type: 'monthly',
    devices: 'pc'
  })
  dialogVisible.value = true
}

const handleEdit = (row: VipPlan) => {
  Object.assign(form, row)
  dialogVisible.value = true
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
    submitting.value = true
    if (form.id) {
      await request.put(`/vip-plans/${form.id}`, form)
      ElMessage.success('更新成功')
    } else {
      await request.post('/vip-plans', form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } catch (error: any) {
    if (error !== false) {
      console.error('提交失败:', error)
      ElMessage.error(error.message || '操作失败')
    }
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (row: VipPlan) => {
  try {
    await ElMessageBox.confirm('确定要删除该套餐吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await request.delete(`/vip-plans/${row.id}`)
    ElMessage.success('删除成功')
    loadData()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

const handleRowDrop = async (dropRow: any, dropType: any, targetRow: any) => {
  try {
    const newOrder = targetRow.sort_order
    await request.put(`/vip-plans/${dropRow.id}`, {
      sort_order: newOrder
    })
    ElMessage.success('排序更新成功')
    loadData()
  } catch (error) {
    console.error('更新排序失败:', error)
    ElMessage.error('更新排序失败')
    loadData()
  }
}

// 批量导入和模板
const downloadTemplate = () => {
  window.open('/admin-api/vip-plans/template', '_blank')
}

const handleUpload = async (file: File) => {
  try {
    const formData = new FormData()
    formData.append('file', file)
    const res = await request.post('/vip-plans/batch-import', formData, {
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

onMounted(() => {
  loadData()
})
</script>

<style scoped lang="scss">
.vip-plans {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .header-actions {
      display: flex;
      gap: 10px;
    }
  }

  .tab-content {
    padding-top: 20px;
  }

  .config-section {
    margin-bottom: 20px;
    padding: 16px;
    background-color: #f5f7fa;
    border-radius: 8px;

    .config-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;

      .config-label {
        font-weight: 600;
        color: #303133;
        font-size: 14px;
      }
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

  .sort-tip {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 15px;
    padding: 10px 15px;
    background-color: #f0f9eb;
    border: 1px solid #e1f3d8;
    border-radius: 4px;
    color: #67c23a;
    font-size: 14px;

    .el-icon {
      font-size: 16px;
    }
  }

  .drag-icon {
    cursor: grab;
    color: #909399;
    font-size: 18px;

    &:active {
      cursor: grabbing;
    }
  }

  .price {
    color: #f56c6c;
    font-weight: bold;
    font-size: 16px;
  }

  .original-price {
    color: #909399;
    font-size: 12px;
    text-decoration: line-through;
    margin-left: 8px;
  }
}
</style>
