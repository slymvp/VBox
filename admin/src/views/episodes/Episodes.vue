<template>
  <div class="episodes">
    <el-card>
      <template #header>
        <div class="card-header">
        <div style="display: flex; align-items: center; gap: 15px;">
          <span>分集管理</span>
          <el-tag v-if="selectedSeriesTitle" type="success">
            {{ selectedSeriesTitle }}
            <el-button link style="padding: 0; margin-left: 5px;" @click="clearSeriesSelection">×</el-button>
          </el-tag>
        </div>
        <el-button type="primary" @click="handleAdd">新增分集</el-button>
        </div>
      </template>

      <div class="search-form">
        <!-- 频道按钮组 -->
        <div class="filter-section">
          <span class="filter-label">频道：</span>
          <el-radio-group v-model="currentCategory" @change="onCategoryChange">
            <el-radio-button v-for="(name, key) in categoryMap" :key="key" :value="key">{{ name }}</el-radio-button>
          </el-radio-group>
        </div>
        <!-- 剧集下拉框（支持远程搜索） -->
        <div class="filter-section">
          <span class="filter-label">剧集：</span>
          <el-select 
            v-model="selectedSeriesId" 
            placeholder="请输入关键词搜索（可选）" 
            filterable
            remote
            reserve-keyword
            :remote-method="remoteSearch"
            :loading="seriesLoading"
            :filter-method="filterMethod"
            clearable 
            style="width: 300px;" 
            @change="handleSeriesChange"
            @clear="clearSeriesSelection"
          >
            <el-option 
              v-for="item in seriesList" 
              :key="item.id" 
              :label="item.title" 
              :value="item.id" 
            />
          </el-select>
        </div>
        <div class="search-section">
          <el-input v-model="queryForm.seriesId" placeholder="搜索剧集ID" clearable style="width: 150px;" @clear="loadData" />
          <el-input v-model="queryForm.keyword" placeholder="搜索播放标题" clearable style="width: 250px;" @clear="loadData" />
          <el-button type="primary" @click="loadData" style="margin-left: 10px;">搜索</el-button>
          <el-button @click="resetQuery" style="margin-left: 10px;">重置</el-button>
        </div>
      </div>

      <el-table :data="tableData" stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="series_id" label="剧集ID" width="100" />
        <el-table-column prop="episode_num" label="集数" width="100" />
        <el-table-column prop="vid" label="VID" width="120" />
        <el-table-column prop="play_title" label="播放标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="union_title" label="联合标题" min-width="150" show-overflow-tooltip />
        <el-table-column prop="episode_type" label="类型" width="100">
          <template #default="{ row }">
            <el-tag :type="row.episode_type === 0 ? 'success' : row.episode_type === 1 ? 'warning' : 'info'">
              {{ episodeTypeMap[row.episode_type] || row.episode_type }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="duration" label="时长" width="100" />
        <el-table-column prop="publish_date" label="发布日期" width="120" />
        <el-table-column label="VIP" width="70">
          <template #default="{ row }">
            <el-tag :type="row.is_vip ? 'warning' : 'info'" size="small">{{ row.is_vip ? '是' : '否' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
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

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="700px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="剧集" prop="series_id">
              <el-select 
                v-model="form.series_id" 
                placeholder="请选择剧集" 
                filterable
                remote
                reserve-keyword
                :remote-method="remoteSearch"
                :loading="seriesLoading"
                :filter-method="filterMethod"
                style="width: 100%;"
              >
                <el-option 
                  v-for="item in seriesList" 
                  :key="item.id" 
                  :label="item.title" 
                  :value="item.id" 
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="集数" prop="episode_num">
              <el-input v-model="form.episode_num" placeholder="请输入集数" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="VID">
              <el-input v-model="form.vid" placeholder="请输入VID" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="类型" prop="episode_type">
              <el-select v-model="form.episode_type" placeholder="请选择类型" style="width: 100%;">
                <el-option label="正片" :value="0" />
                <el-option label="预告" :value="1" />
                <el-option label="花絮" :value="2" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="播放标题" prop="play_title">
          <el-input v-model="form.play_title" placeholder="请输入播放标题" />
        </el-form-item>
        <el-form-item label="联合标题">
          <el-input v-model="form.union_title" placeholder="请输入联合标题" />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="时长">
              <el-input v-model="form.duration" placeholder="请输入时长" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="发布日期">
              <el-input v-model="form.publish_date" placeholder="请输入发布日期" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="VIP">
              <el-switch v-model="form.is_vip" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="播放URL">
          <el-input v-model="form.play_url" type="textarea" :rows="2" placeholder="请输入播放URL" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitLoading">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import request from '@/utils/api'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const submitLoading = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('')
const formRef = ref<FormInstance>()
const tableData = ref<any[]>([])
const total = ref(0)
const currentCategory = ref('tv')
const selectedSeriesId = ref<number | null>(null)
const selectedSeriesTitle = ref('')
const seriesList = ref<any[]>([])
const seriesLoading = ref(false)

const queryForm = reactive({
  page: 1,
  limit: 20,
  keyword: '',
  seriesId: ''
})

const form = reactive({
  id: null as number | null,
  series_id: null as number | null,
  episode_num: '',
  vid: '',
  play_title: '',
  union_title: '',
  episode_type: 0,
  duration: '',
  publish_date: '',
  play_url: '',
  is_vip: false
})

const episodeTypeMap: Record<number, string> = {
  0: '正片',
  1: '预告',
  2: '花絮'
}

const platformMap: Record<string, string> = {
  iqiyi: '爱奇艺',
  tencent: '腾讯视频',
  youku: '优酷',
  mgtv: '芒果TV',
  sohu: '搜狐',
  bilibili: 'B站'
}

const categoryMap: Record<string, string> = {
  tv: '电视剧',
  movie: '电影',
  variety: '综艺',
  cartoon: '动漫',
  child: '少儿'
}

const rules: FormRules = {
  series_id: [{ required: true, message: '请选择剧集', trigger: 'change' }],
  episode_num: [{ required: true, message: '请输入集数', trigger: 'blur' }],
  play_title: [{ required: true, message: '请输入播放标题', trigger: 'blur' }],
  episode_type: [{ required: true, message: '请选择类型', trigger: 'change' }]
}

// 远程搜索剧集
const remoteSearch = async (query: string) => {
  if (query) {
    seriesLoading.value = true
    try {
      const params: any = {
        category: currentCategory.value,
        page: 1,
        limit: 100
      }
      // 判断是否是数字，如果是则按ID搜索，否则按关键词搜索
      if (/^\d+$/.test(query)) {
        params.id = Number(query)
      } else {
        params.keyword = query
      }
      const res = await request.get('/series', { params })
      if (res.data) {
        seriesList.value = res.data.items || []
      }
    } catch (error) {
      console.error('搜索失败:', error)
    } finally {
      seriesLoading.value = false
    }
  } else {
    seriesList.value = []
  }
}

// 本地过滤
const filterMethod = (keyword: string) => {
  return true // 已经远程搜索了，本地就不需要再过滤
}

const loadSeriesList = async () => {
  try {
    const res = await request.get('/series', {
      params: {
        category: currentCategory.value,
        page: 1,
        limit: 500
      }
    })
    if (res.data) {
      seriesList.value = res.data.items || []
    }
  } catch (error) {
    console.error('加载失败:', error)
  }
}

const loadData = async () => {
        loading.value = true
        try {
            const params: any = {
                category: currentCategory.value,
                page: queryForm.page,
                limit: queryForm.limit
            }
            if (selectedSeriesId.value) {
                params.series_id = selectedSeriesId.value
            } else if (queryForm.seriesId) {
                params.series_id = Number(queryForm.seriesId)
            }
            if (queryForm.keyword) {
                params.keyword = queryForm.keyword
            }

            const res = await request.get('/episodes', { params })
            if (res.data) {
                tableData.value = res.data.items || []
                total.value = res.data.total || 0
            }
        } catch (error) {
            console.error('加载失败:', error)
            ElMessage.error('加载失败')
        } finally {
            loading.value = false
        }
    }

const resetQuery = () => {
  queryForm.keyword = ''
  queryForm.seriesId = ''
  queryForm.page = 1
  loadData()
}

const onCategoryChange = () => {
  selectedSeriesId.value = null
  selectedSeriesTitle.value = ''
  seriesList.value = []
  loadData()
}

const clearSeriesSelection = () => {
  selectedSeriesId.value = null
  selectedSeriesTitle.value = ''
  loadData()
}

const handleSeriesChange = (seriesId: number) => {
  if (seriesId) {
    const found = seriesList.value.find(item => item.id === seriesId)
    selectedSeriesTitle.value = found ? found.title : ''
  } else {
    selectedSeriesTitle.value = ''
  }
  loadData()
}

const handleAdd = () => {
  dialogTitle.value = '新增分集'
  Object.assign(form, {
    id: null,
    series_id: selectedSeriesId.value,
    episode_num: '',
    vid: '',
    play_title: '',
    union_title: '',
    episode_type: 0,
    duration: '',
    publish_date: '',
    play_url: '',
    is_vip: false
  })
  dialogVisible.value = true
}

const handleEdit = (row: any) => {
  dialogTitle.value = '编辑分集'
  Object.assign(form, {
    id: row.id,
    series_id: row.series_id,
    episode_num: row.episode_num,
    vid: row.vid,
    play_title: row.play_title,
    union_title: row.union_title,
    episode_type: row.episode_type,
    duration: row.duration,
    publish_date: row.publish_date,
    play_url: row.play_url,
    is_vip: !!row.is_vip
  })
  // 加载一下剧集列表确保能显示关联的剧集
  loadSeriesList()
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (valid) {
      submitLoading.value = true
      try {
        const data: any = {
          category_key: currentCategory.value,
          series_id: form.series_id,
          episode_num: form.episode_num,
          vid: form.vid,
          play_title: form.play_title,
          union_title: form.union_title,
          episode_type: form.episode_type,
          duration: form.duration,
          publish_date: form.publish_date,
          play_url: form.play_url,
          is_vip: form.is_vip ? 1 : 0
        }
        if (form.id) {
          await request.put(`/episodes/${form.id}`, data)
          ElMessage.success('编辑成功')
        } else {
          await request.post('/episodes', data)
          ElMessage.success('新增成功')
        }
        dialogVisible.value = false
        loadData()
      } catch (error) {
        console.error(error)
        ElMessage.error('保存失败')
      } finally {
        submitLoading.value = false
      }
    }
  })
}

const handleDelete = async (row: any) => {
  try {
    await ElMessageBox.confirm('确定要删除该分集吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await request.delete(`/episodes/${row.id}`, { params: { category: currentCategory.value } })
    ElMessage.success('删除成功')
    loadData()
  } catch (error) {
    console.error('删除失败:', error)
    if ((error as any) !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  if (route.query.category) {
    currentCategory.value = route.query.category as string
  }
  if (route.query.seriesId) {
    selectedSeriesId.value = Number(route.query.seriesId)
    selectedSeriesTitle.value = (route.query.seriesTitle as string) || ''
    // 初始时加载一下对应频道的剧集列表，确保能显示选中的剧集
    loadSeriesList()
  }
  loadData()
})
</script>

<style scoped lang="scss">
.episodes {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .search-form {
    margin-bottom: 20px;
    .filter-section {
      display: flex;
      align-items: center;
      margin-bottom: 15px;
      .filter-label {
        margin-right: 10px;
        font-weight: 500;
        color: #606266;
        white-space: nowrap;
      }
    }
  }
  .search-form {
    margin-bottom: 20px;
    .search-form {
      margin-bottom: 0;
    }
  }
  .search-form {
    margin-bottom: 20px;
    .filter-label {
      margin-right: 10px;
      font-weight: 500;
      color: #606266;
      white-space: nowrap;
    }
  }
}
</style>
