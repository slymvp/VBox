<template>
  <div class="categories">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>频道管理</span>
          <el-button type="primary" @click="handleAddCategory">新增频道</el-button>
        </div>
      </template>

      <el-table :data="categoryList" stripe v-loading="loading" row-key="id" @selection-change="handleCategorySelectionChange">
        <el-table-column type="selection" width="55" />
        <el-table-column prop="key" label="频道标识" width="150" />
        <el-table-column prop="name" label="频道名称" width="150" />
        <el-table-column prop="icon" label="图标" width="100">
          <template #default="{ row }">
            <span v-if="row.icon">{{ row.icon }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column prop="sort_order" label="排序" width="100" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'danger'">{{ row.enabled ? '启用' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEditCategory(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDeleteCategory(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="selectedCategories.length > 0" style="margin-top: 16px;">
        <el-button type="success" @click="handleBatchEnableCategories">批量启用 ({{ selectedCategories.length }})</el-button>
        <el-button type="warning" @click="handleBatchDisableCategories">批量禁用 ({{ selectedCategories.length }})</el-button>
        <el-button type="danger" @click="handleBatchDeleteCategories">批量删除 ({{ selectedCategories.length }})</el-button>
      </div>
    </el-card>

    <!-- 新增/编辑频道对话框 -->
    <el-dialog v-model="categoryDialogVisible" :title="categoryDialogTitle" width="600px">
      <el-form :model="categoryForm" :rules="categoryRules" ref="categoryFormRef" label-width="100px">
        <el-form-item label="频道标识" prop="key">
          <el-input v-model="categoryForm.key" placeholder="例如：tv" :disabled="!!editingCategory" />
        </el-form-item>
        <el-form-item label="频道名称" prop="name">
          <el-input v-model="categoryForm.name" placeholder="例如：电视剧" />
        </el-form-item>
        <el-form-item label="图标" prop="icon">
          <el-input v-model="categoryForm.icon" placeholder="图标URL（可选）" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="categoryForm.description" type="textarea" :rows="3" placeholder="描述信息" />
        </el-form-item>
        <el-form-item label="排序" prop="sort_order">
          <el-input-number v-model="categoryForm.sort_order" :min="0" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="状态" prop="enabled">
          <el-switch v-model="categoryForm.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="categoryDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmitCategory" :loading="categorySubmitting">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/utils/api'

interface Category {
  id: number
  key: string
  name: string
  icon?: string
  description?: string
  sort_order: number
  enabled: boolean
  created_at?: string
  updated_at?: string
}

const loading = ref(false)
const categorySubmitting = ref(false)
const categoryList = ref<Category[]>([])

// 选中的数据
const selectedCategories = ref<Category[]>([])

// 对话框状态
const categoryDialogVisible = ref(false)
const categoryDialogTitle = computed(() => (editingCategory ? '编辑频道' : '新增频道'))

// 表单引用
const categoryFormRef = ref()

// 编辑状态
const editingCategory = ref<Category | null>(null)

// 表单数据
const categoryForm = reactive({
  key: '',
  name: '',
  icon: '',
  description: '',
  sort_order: 0,
  enabled: true
})

// 表单验证规则
const categoryRules = {
  key: [{ required: true, message: '请输入频道标识', trigger: 'blur' }],
  name: [{ required: true, message: '请输入频道名称', trigger: 'blur' }]
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await request.get('/categories')
    categoryList.value = res.data
  } catch (error) {
    console.error('获取数据失败:', error)
    ElMessage.error('获取数据失败')
  } finally {
    loading.value = false
  }
}

// 选择变化处理
const handleCategorySelectionChange = (selection: Category[]) => {
  selectedCategories.value = selection
}

const handleAddCategory = () => {
  editingCategory.value = null
  Object.assign(categoryForm, {
    key: '',
    name: '',
    icon: '',
    description: '',
    sort_order: 0,
    enabled: true
  })
  categoryDialogVisible.value = true
}

const handleEditCategory = (row: Category) => {
  editingCategory.value = row
  Object.assign(categoryForm, {
    key: row.key,
    name: row.name,
    icon: row.icon || '',
    description: row.description || '',
    sort_order: row.sort_order,
    enabled: row.enabled
  })
  categoryDialogVisible.value = true
}

const handleSubmitCategory = async () => {
  try {
    await categoryFormRef.value.validate()
    categorySubmitting.value = true
    if (editingCategory.value) {
      await request.put(`/categories/${editingCategory.value.id}`, categoryForm)
      ElMessage.success('更新成功')
    } else {
      await request.post('/categories', categoryForm)
      ElMessage.success('创建成功')
    }
    categoryDialogVisible.value = false
    await loadData()
  } catch (error: any) {
    if (error !== false) {
      console.error('提交失败:', error)
      ElMessage.error(error.message || '操作失败')
    }
  } finally {
    categorySubmitting.value = false
  }
}

const handleDeleteCategory = async (row: Category) => {
  try {
    await ElMessageBox.confirm('确定要删除该频道吗？该频道下的所有平台配置也会被删除。', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await request.delete(`/categories/${row.id}`)
    ElMessage.success('删除成功')
    await loadData()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

const handleBatchEnableCategories = async () => {
  try {
    await ElMessageBox.confirm(`确定要批量启用选中的 ${selectedCategories.value.length} 个频道吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await Promise.all(
      selectedCategories.value.map(cat =>
        request.put(`/categories/${cat.id}`, { enabled: true })
      )
    )
    ElMessage.success('批量启用成功')
    selectedCategories.value = []
    await loadData()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('批量启用失败:', error)
      ElMessage.error('批量启用失败')
    }
  }
}

const handleBatchDisableCategories = async () => {
  try {
    await ElMessageBox.confirm(`确定要批量禁用选中的 ${selectedCategories.value.length} 个频道吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await Promise.all(
      selectedCategories.value.map(cat =>
        request.put(`/categories/${cat.id}`, { enabled: false })
      )
    )
    ElMessage.success('批量禁用成功')
    selectedCategories.value = []
    await loadData()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('批量禁用失败:', error)
      ElMessage.error('批量禁用失败')
    }
  }
}

const handleBatchDeleteCategories = async () => {
  try {
    await ElMessageBox.confirm(
      `确定要批量删除选中的 ${selectedCategories.value.length} 个频道吗？\n这些频道下的所有平台配置也会被删除。`,
      '警告',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await Promise.all(
      selectedCategories.value.map(cat =>
        request.delete(`/categories/${cat.id}`)
      )
    )
    ElMessage.success('批量删除成功')
    selectedCategories.value = []
    await loadData()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('批量删除失败:', error)
      ElMessage.error('批量删除失败')
    }
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped lang="scss">
.categories {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
}
</style>
