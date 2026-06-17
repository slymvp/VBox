<template>
  <div class="admin-settings">
    <!-- 修改密码 -->
    <el-card style="margin-bottom: 20px;">
      <template #header>
        <div class="card-header">
          <span>修改密码</span>
        </div>
      </template>
      <el-form :model="passwordForm" :rules="passwordRules" ref="passwordFormRef" inline>
        <el-form-item label="旧密码" prop="old_password">
          <el-input v-model="passwordForm.old_password" type="password" placeholder="请输入旧密码" show-password />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="passwordForm.new_password" type="password" placeholder="请输入新密码（至少6位）" show-password />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirm_password">
          <el-input v-model="passwordForm.confirm_password" type="password" placeholder="再次输入新密码" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleChangePassword" :loading="passwordLoading">修改密码</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 管理员账号管理 -->
    <el-card>
      <template #header>
        <div class="card-header">
          <span>管理员账号管理</span>
          <el-button type="primary" @click="showCreateDialog">添加账号</el-button>
        </div>
      </template>

      <el-table :data="adminUsers" stripe v-loading="tableLoading">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="username" label="用户名" width="150" />
        <el-table-column prop="nickname" label="昵称" width="150">
          <template #default="{ row }">
            {{ row.nickname || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="role" label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : 'primary'">
              {{ row.role === 'admin' ? '超级管理员' : '操作员' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">
              {{ row.is_active ? '启用' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_login" label="最后登录" width="180">
          <template #default="{ row }">
            {{ row.last_login || '从未登录' }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" min-width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="showEditDialog(row)">编辑</el-button>
            <el-button link type="warning" @click="showResetPasswordDialog(row)">重置密码</el-button>
            <el-button
              link
              :type="row.is_active ? 'danger' : 'success'"
              @click="handleToggleStatus(row)"
              :disabled="row.username === 'admin'"
            >
              {{ row.is_active ? '禁用' : '启用' }}
            </el-button>
            <el-button
              link
              type="danger"
              @click="handleDelete(row)"
              :disabled="row.username === 'admin'"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑账号' : '添加账号'"
      width="500px"
      @close="resetDialogForm"
    >
      <el-form :model="dialogForm" :rules="dialogRules" ref="dialogFormRef" label-width="80px">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="dialogForm.username" placeholder="请输入用户名" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="昵称" prop="nickname">
          <el-input v-model="dialogForm.nickname" placeholder="请输入昵称（可选）" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="dialogForm.role" placeholder="选择角色">
            <el-option label="操作员" value="operator" />
            <el-option label="超级管理员" value="admin" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="!isEdit" label="密码" prop="password">
          <el-input v-model="dialogForm.password" type="password" placeholder="请输入密码（至少6位）" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmitDialog" :loading="dialogLoading">确定</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码对话框 -->
    <el-dialog v-model="resetPwdVisible" title="重置密码" width="400px">
      <el-form :model="resetPwdForm" :rules="resetPwdRules" ref="resetPwdFormRef" label-width="80px">
        <el-form-item label="新密码" prop="password">
          <el-input v-model="resetPwdForm.password" type="password" placeholder="请输入新密码（至少6位）" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetPwdVisible = false">取消</el-button>
        <el-button type="primary" @click="handleResetPassword" :loading="resetPwdLoading">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import request from '@/utils/api'

// ==================== 管理员列表 ====================
const adminUsers = ref<any[]>([])
const tableLoading = ref(false)

const loadAdminUsers = async () => {
  tableLoading.value = true
  try {
    const res = await request.get('/admin-users')
    adminUsers.value = res.data || []
  } catch (error: any) {
    ElMessage.error(error.message || '加载管理员列表失败')
  } finally {
    tableLoading.value = false
  }
}

// ==================== 修改密码 ====================
const passwordFormRef = ref<FormInstance>()
const passwordLoading = ref(false)
const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

const validateConfirmPassword = (_rule: any, value: string, callback: any) => {
  if (value !== passwordForm.new_password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const passwordRules: FormRules = {
  old_password: [{ required: true, message: '请输入旧密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

const handleChangePassword = async () => {
  if (!passwordFormRef.value) return
  await passwordFormRef.value.validate(async (valid) => {
    if (valid) {
      passwordLoading.value = true
      try {
        await request.post('/change-password', {
          old_password: passwordForm.old_password,
          new_password: passwordForm.new_password
        })
        ElMessage.success('密码修改成功，请重新登录')
        localStorage.removeItem('admin_token')
        window.location.href = '/admin/login'
      } catch (error: any) {
        ElMessage.error(error.message || '修改密码失败')
      } finally {
        passwordLoading.value = false
      }
    }
  })
}

// ==================== 创建/编辑对话框 ====================
const dialogVisible = ref(false)
const dialogFormRef = ref<FormInstance>()
const dialogLoading = ref(false)
const isEdit = ref(false)
const editingUserId = ref<number | null>(null)

const dialogForm = reactive({
  username: '',
  nickname: '',
  role: 'operator',
  password: ''
})

const dialogRules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, message: '用户名至少2个字符', trigger: 'blur' }
  ],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' }
  ]
}

const showCreateDialog = () => {
  isEdit.value = false
  editingUserId.value = null
  dialogForm.username = ''
  dialogForm.nickname = ''
  dialogForm.role = 'operator'
  dialogForm.password = ''
  dialogVisible.value = true
}

const showEditDialog = (row: any) => {
  isEdit.value = true
  editingUserId.value = row.id
  dialogForm.username = row.username
  dialogForm.nickname = row.nickname || ''
  dialogForm.role = row.role
  dialogForm.password = ''
  dialogVisible.value = true
}

const resetDialogForm = () => {
  dialogForm.username = ''
  dialogForm.nickname = ''
  dialogForm.role = 'operator'
  dialogForm.password = ''
}

const handleSubmitDialog = async () => {
  if (!dialogFormRef.value) return
  await dialogFormRef.value.validate(async (valid) => {
    if (valid) {
      dialogLoading.value = true
      try {
        if (isEdit.value && editingUserId.value) {
          await request.put(`/admin-users/${editingUserId.value}`, {
            nickname: dialogForm.nickname,
            role: dialogForm.role
          })
          ElMessage.success('更新成功')
        } else {
          await request.post('/admin-users', {
            username: dialogForm.username,
            nickname: dialogForm.nickname,
            role: dialogForm.role,
            password: dialogForm.password
          })
          ElMessage.success('创建成功')
        }
        dialogVisible.value = false
        loadAdminUsers()
      } catch (error: any) {
        ElMessage.error(error.message || '操作失败')
      } finally {
        dialogLoading.value = false
      }
    }
  })
}

// ==================== 重置密码 ====================
const resetPwdVisible = ref(false)
const resetPwdFormRef = ref<FormInstance>()
const resetPwdLoading = ref(false)
const resetPwdUserId = ref<number | null>(null)

const resetPwdForm = reactive({
  password: ''
})

const resetPwdRules: FormRules = {
  password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' }
  ]
}

const showResetPasswordDialog = (row: any) => {
  resetPwdUserId.value = row.id
  resetPwdForm.password = ''
  resetPwdVisible.value = true
}

const handleResetPassword = async () => {
  if (!resetPwdFormRef.value) return
  await resetPwdFormRef.value.validate(async (valid) => {
    if (valid) {
      resetPwdLoading.value = true
      try {
        await request.put(`/admin-users/${resetPwdUserId.value}`, {
          password: resetPwdForm.password
        })
        ElMessage.success('密码重置成功')
        resetPwdVisible.value = false
      } catch (error: any) {
        ElMessage.error(error.message || '重置密码失败')
      } finally {
        resetPwdLoading.value = false
      }
    }
  })
}

// ==================== 启用/禁用 ====================
const handleToggleStatus = async (row: any) => {
  const action = row.is_active ? '禁用' : '启用'
  try {
    await ElMessageBox.confirm(`确定要${action}账号 "${row.username}" 吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await request.put(`/admin-users/${row.id}`, {
      is_active: !row.is_active
    })
    ElMessage.success(`${action}成功`)
    loadAdminUsers()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || `${action}失败`)
    }
  }
}

// ==================== 删除 ====================
const handleDelete = async (row: any) => {
  try {
    await ElMessageBox.confirm(`确定要删除账号 "${row.username}" 吗？此操作不可撤销。`, '警告', {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await request.delete(`/admin-users/${row.id}`)
    ElMessage.success('删除成功')
    loadAdminUsers()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

onMounted(() => {
  loadAdminUsers()
})
</script>

<style scoped lang="scss">
.admin-settings {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
}
</style>
