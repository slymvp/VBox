<template>
  <div class="payment-qrcodes">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>支付二维码管理</span>
          <el-button type="primary" @click="handleAdd">新增二维码</el-button>
        </div>
      </template>

      <!-- 搜索栏 -->
      <div class="search-form">
        <div class="filter-section">
          <span class="filter-label">类型：</span>
          <el-radio-group v-model="queryForm.type" size="default">
            <el-radio-button value="">全部</el-radio-button>
            <el-radio-button value="wechat">微信</el-radio-button>
            <el-radio-button value="alipay">支付宝</el-radio-button>
          </el-radio-group>
        </div>
        <div class="filter-section">
          <span class="filter-label">状态：</span>
          <el-radio-group v-model="queryForm.is_enabled" size="default">
            <el-radio-button :label="null">全部</el-radio-button>
            <el-radio-button :label="true">启用</el-radio-button>
            <el-radio-button :label="false">禁用</el-radio-button>
          </el-radio-group>
        </div>
      </div>

      <!-- 数据表格 -->
      <el-table :data="tableData" stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="name" label="名称" min-width="150" />
        <el-table-column prop="type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.type === 'wechat' ? 'success' : 'primary'">
              {{ row.type === 'wechat' ? '微信' : '支付宝' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="二维码" width="120">
          <template #default="{ row }">
            <el-image
              :src="row.image_url"
              :preview-src-list="[row.image_url]"
              style="width: 60px; height: 60px;"
              fit="cover"
              :preview-teleported="true"
            >
              <template #error>
                <div class="image-error">加载失败</div>
              </template>
            </el-image>
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="固定金额" width="120">
          <template #default="{ row }">
            <span v-if="row.amount !== null && row.amount !== undefined">¥{{ row.amount }}</span>
            <span v-else class="text-gray">动态金额</span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="说明" min-width="200" />
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
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入名称" />
        </el-form-item>
        <el-form-item label="类型" prop="type">
          <el-radio-group v-model="form.type">
            <el-radio value="wechat">微信</el-radio>
            <el-radio value="alipay">支付宝</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="二维码地址" prop="image_url">
          <el-input v-model="form.image_url" placeholder="请输入二维码图片URL" />
          <div class="image-preview" v-if="form.image_url">
            <el-image
              :src="form.image_url"
              style="width: 150px; height: 150px; margin-top: 10px;"
              fit="cover"
              :preview-src-list="[form.image_url]"
            >
              <template #error>
                <div class="image-error">图片加载失败</div>
              </template>
            </el-image>
          </div>
        </el-form-item>
        <el-form-item label="固定金额" prop="amount">
          <el-input-number v-model="form.amount" :min="0" :precision="2" placeholder="不填表示动态金额" style="width: 100%;" />
          <div class="form-tip">不填表示动态金额</div>
        </el-form-item>
        <el-form-item label="说明" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="请输入说明" />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="是否启用" prop="is_enabled">
              <el-switch v-model="form.is_enabled" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="排序" prop="sort_order">
              <el-input-number v-model="form.sort_order" :min="0" placeholder="排序" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>
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
import request from '@/utils/api'

interface PaymentQrcode {
  id?: number
  name: string
  type: 'wechat' | 'alipay'
  image_url: string
  amount?: number | null
  description?: string
  is_enabled?: boolean
  sort_order?: number
  created_at?: string
  updated_at?: string
}

const loading = ref(false)
const submitting = ref(false)
const tableData = ref<PaymentQrcode[]>([])
const total = ref(0)
const dialogVisible = ref(false)
const dialogTitle = computed(() => (form.id ? '编辑二维码' : '新增二维码'))
const formRef = ref()

const queryForm = reactive({
  page: 1,
  limit: 20,
  type: '',
  is_enabled: null as boolean | null
})

const form = reactive<PaymentQrcode>({
  name: '',
  type: 'wechat',
  image_url: '',
  amount: null,
  description: '',
  is_enabled: true,
  sort_order: 0
})

const rules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择类型', trigger: 'change' }],
  image_url: [{ required: true, message: '请输入二维码图片URL', trigger: 'blur' }]
}

const loadData = async () => {
  loading.value = true
  try {
    const params: any = {
      page: queryForm.page,
      limit: queryForm.limit
    }
    if (queryForm.type) {
      params.type = queryForm.type
    }
    if (queryForm.is_enabled !== null) {
      params.is_enabled = queryForm.is_enabled
    }
    const res = await request.get('/payment-qrcodes', { params })
    tableData.value = res.data.items
    total.value = res.data.total
  } catch (error) {
    console.error('获取二维码列表失败:', error)
    ElMessage.error('获取二维码列表失败')
  } finally {
    loading.value = false
  }
}

const resetQuery = () => {
  queryForm.page = 1
  queryForm.type = ''
  queryForm.is_enabled = null
  loadData()
}

const handleAdd = () => {
  Object.assign(form, {
    id: undefined,
    name: '',
    type: 'wechat',
    image_url: '',
    amount: null,
    description: '',
    is_enabled: true,
    sort_order: 0
  })
  dialogVisible.value = true
}

const handleEdit = (row: PaymentQrcode) => {
  Object.assign(form, row)
  dialogVisible.value = true
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
    submitting.value = true
    if (form.id) {
      await request.put(`/payment-qrcodes/${form.id}`, form)
      ElMessage.success('更新成功')
    } else {
      await request.post('/payment-qrcodes', form)
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

const handleDelete = async (row: PaymentQrcode) => {
  try {
    await ElMessageBox.confirm('确定要删除该二维码吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await request.delete(`/payment-qrcodes/${row.id}`)
    ElMessage.success('删除成功')
    loadData()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped lang="scss">
.payment-qrcodes {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .search-form {
    margin-bottom: 20px;

    .filter-section {
      margin-bottom: 15px;
      display: flex;
      align-items: center;

      .filter-label {
        font-size: 14px;
        color: #606266;
        margin-right: 10px;
      }
    }
  }

  .text-gray {
    color: #909399;
  }

  .image-error {
    width: 60px;
    height: 60px;
    line-height: 60px;
    text-align: center;
    background: #f5f7fa;
    color: #909399;
    font-size: 12px;
  }

  .form-tip {
    margin-top: 5px;
    font-size: 12px;
    color: #909399;
  }
}
</style>
