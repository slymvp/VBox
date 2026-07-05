<template>
  <div class="parse-sources">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>解析源管理</span>
          <div class="header-actions">
            <el-button size="small" @click="handleResetAllStats" type="warning" plain>重置所有统计</el-button>
            <el-button size="small" @click="downloadTemplate">下载模板</el-button>
            <el-upload
              ref="uploadRef"
              :show-file-list="false"
              :before-upload="handleBatchImport"
              accept=".csv"
              style="display: inline-block; margin-left: 10px;"
            >
              <el-button type="success" size="small">批量导入</el-button>
            </el-upload>
            <el-button type="primary" @click="handleAdd" style="margin-left: 10px;">新增解析源</el-button>
          </div>
        </div>
      </template>

      <!-- 解析源列表 -->
      <div v-loading="loading">
        <draggable
          v-model="parseSourceList"
          item-key="id"
          handle=".drag-handle"
          @end="handleDragEnd"
        >
          <template #item="{ element }">
            <div class="parse-source-item">
              <div class="drag-handle">
                <el-icon><Sort /></el-icon>
              </div>
              <span class="parse-source-name">{{ element.name }}</span>
              <span class="parse-source-url" :title="element.url">{{ element.url }}</span>
              <span class="sort-order">#{{ element.sort_order }}</span>
              <span class="success-rate" v-if="element.success_rate !== null" :class="{ 'high-rate': element.success_rate >= 70, 'mid-rate': element.success_rate >= 30 && element.success_rate < 70, 'low-rate': element.success_rate < 30 }">
                {{ element.success_rate }}%
              </span>
              <span class="success-rate no-data" v-else>无数据</span>
              <div class="parse-source-actions">
                <el-tag :type="element.enabled ? 'success' : 'danger'" size="small">
                  {{ element.enabled ? '启用' : '禁用' }}
                </el-tag>
                <el-button link type="warning" size="small" @click="handleResetStats(element)">重置</el-button>
                <el-button link type="primary" size="small" @click="handleEdit(element)">编辑</el-button>
                <el-button link type="danger" size="small" @click="handleDelete(element)">删除</el-button>
              </div>
            </div>
          </template>
        </draggable>

        <el-empty v-if="!loading && parseSourceList.length === 0" description="暂无解析源，请点击新增" />
      </div>
    </el-card>

    <!-- 新增/编辑解析源对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="550px">
      <el-form :model="form" :rules="formRules" ref="formRef" label-width="100px">
        <el-form-item label="名称" prop="name">
          <el-input v-model="form.name" placeholder="解析源名称" />
        </el-form-item>
        <el-form-item label="解析地址" prop="url">
          <el-input v-model="form.url" placeholder="https://example.com/api/parse" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.sort_order" :min="0" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="form.enabled" active-text="启用" inactive-text="禁用" />
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
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Sort } from '@element-plus/icons-vue'
import draggable from 'vuedraggable'
import request from '@/utils/api'

interface ParseSource {
  id: number
  platform_id: number | null
  key: string
  name: string
  type: string
  url: string
  sort_order: number
  success_count: number
  fail_count: number
  success_rate: number | null
  enabled: boolean
}

const loading = ref(false)
const submitting = ref(false)
const parseSourceList = ref<ParseSource[]>([])
const dialogVisible = ref(false)
const formRef = ref()
const editingItem = ref<ParseSource | null>(null)

const dialogTitle = computed(() => (editingItem.value ? '编辑解析源' : '新增解析源'))

const form = reactive({
  name: '',
  url: '',
  type: 'json',
  sort_order: 0,
  enabled: true
})

const formRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  url: [{ required: true, message: '请输入解析地址', trigger: 'blur' }]
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await request.get('/parse-sources')
    parseSourceList.value = res.data || []
  } catch (error) {
    ElMessage.error('获取解析源列表失败')
  } finally {
    loading.value = false
  }
}

const handleAdd = () => {
  editingItem.value = null
  Object.assign(form, {
    name: '',
    url: '',
    type: 'json',
    sort_order: parseSourceList.value.length,
    enabled: true
  })
  dialogVisible.value = true
}

const handleEdit = (row: ParseSource) => {
  editingItem.value = row
  Object.assign(form, {
    name: row.name,
    url: row.url,
    type: row.type || 'json',
    sort_order: row.sort_order,
    enabled: row.enabled
  })
  dialogVisible.value = true
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
    submitting.value = true
    if (editingItem.value) {
      await request.put(`/parse-sources/${editingItem.value.id}`, form)
      ElMessage.success('更新成功')
    } else {
      await request.post('/parse-sources', form)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    await loadData()
  } catch (error: any) {
    if (error !== false) {
      ElMessage.error(error.message || '操作失败')
    }
  } finally {
    submitting.value = false
  }
}

const handleDelete = async (row: ParseSource) => {
  try {
    await ElMessageBox.confirm(`确定要删除解析源「${row.name}」吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await request.delete(`/parse-sources/${row.id}`)
    ElMessage.success('删除成功')
    await loadData()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const handleDragEnd = async () => {
  try {
    const items = parseSourceList.value.map((item, index) => ({
      id: item.id,
      sort_order: index
    }))
    await request.put('/parse-sources/batch-sort', { items })
  } catch (error: any) {
    console.error('更新排序失败:', error)
  }
}

const downloadTemplate = () => {
  window.open('/admin-api/parse-sources/template', '_blank')
}

const handleBatchImport = async (file: File) => {
  try {
    const formData = new FormData()
    formData.append('file', file)
    const res = await request.post('/parse-sources/batch-import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    ElMessage.success(res.message || '导入成功')
    await loadData()
  } catch (error: any) {
    ElMessage.error('导入失败: ' + (error.message || '未知错误'))
  }
  return false
}

const handleResetStats = async (row: ParseSource) => {
  try {
    await ElMessageBox.confirm(`确定要重置「${row.name}」的统计数据吗？`, '重置统计', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await request.post(`/parse-sources/${row.id}/reset-stats`)
    ElMessage.success('统计已重置')
    await loadData()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('重置失败')
    }
  }
}

const handleResetAllStats = async () => {
  try {
    await ElMessageBox.confirm('确定要重置所有解析源的统计数据吗？成功率和排序将从头开始。', '重置所有统计', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await request.post('/parse-sources/reset-all-stats')
    ElMessage.success('所有统计已重置')
    await loadData()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('重置失败')
    }
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped lang="scss">
.parse-sources {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .header-actions {
      display: flex;
      align-items: center;
    }
  }

  .parse-source-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 16px;
    border: 1px solid #ebeef5;
    border-radius: 8px;
    margin-bottom: 8px;
    transition: box-shadow 0.2s;
    flex-wrap: nowrap;
    line-height: 32px;

    &:hover {
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    }

    &:last-child {
      margin-bottom: 0;
    }

    .drag-handle {
      cursor: grab;
      color: #909399;
      display: flex;
      align-items: center;
      padding: 4px;
      flex-shrink: 0;

      &:active {
        cursor: grabbing;
      }
    }

    .parse-source-name {
      font-size: 14px;
      font-weight: 600;
      color: #303133;
      flex-shrink: 0;
      min-width: 60px;
    }

    .parse-source-url {
      font-size: 12px;
      color: #909399;
      flex: 1;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .sort-order {
      font-size: 12px;
      color: #c0c4cc;
      flex-shrink: 0;
    }

    .success-rate {
      font-size: 12px;
      font-weight: 600;
      flex-shrink: 0;
      min-width: 48px;

      &.high-rate {
        color: #67c23a;
      }
      &.mid-rate {
        color: #e6a23c;
      }
      &.low-rate {
        color: #f56c6c;
      }
      &.no-data {
        color: #c0c4cc;
        font-weight: 400;
      }
    }


    .parse-source-actions {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-shrink: 0;
    }
  }
}
</style>
