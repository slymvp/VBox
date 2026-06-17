<template>
  <div class="series">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>剧集管理</span>
          <el-button type="primary" @click="handleAdd">新增剧集</el-button>
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
        <!-- 平台按钮组 -->
        <div class="filter-section">
          <span class="filter-label">平台：</span>
          <el-radio-group v-model="queryForm.platform" @change="loadData">
            <el-radio-button value="">全部</el-radio-button>
            <el-radio-button v-for="(name, key) in platformMap" :key="key" :value="key">{{ name }}</el-radio-button>
          </el-radio-group>
        </div>
        <!-- 搜索框 -->
        <div class="search-section">
          <el-input v-model="queryForm.keyword" placeholder="搜索剧集名称" clearable style="width: 250px;" @clear="loadData" />
          <el-button type="primary" @click="loadData" style="margin-left: 10px;">搜索</el-button>
          <el-button @click="resetQuery" style="margin-left: 10px;">重置</el-button>
        </div>
      </div>

      <el-table :data="tableData" stripe v-loading="loading">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="cid" label="剧集ID" width="120" />
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="platform" label="平台" width="100">
          <template #default="{ row }">
            <el-tag>{{ getPlatformName(row.platform) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="area" label="地区" width="80">
          <template #default="{ row }">
            <span v-if="row.area">{{ row.area }}</span>
            <span v-else style="color: #999;">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="year" label="年份" width="80" />
        <el-table-column prop="score" label="评分" width="80">
          <template #default="{ row }">
            <span v-if="row.score">{{ row.score }}</span>
            <span v-else style="color: #999;">-</span>
          </template>
        </el-table-column>
        <el-table-column label="标签" width="150" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.tags">
              <el-tag v-for="(tag, index) in getTagsList(row.tags)" :key="index" size="small" style="margin-right: 4px; margin-bottom: 4px;">
                {{ tag }}
              </el-tag>
            </span>
            <span v-else style="color: #999;">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="total_episodes" label="总集数" width="90" />
        <el-table-column prop="updated_episodes" label="已更新" width="80" />
        <el-table-column label="VIP" width="70">
          <template #default="{ row }">
            <el-tag :type="row.is_vip ? 'warning' : 'info'" size="small">{{ row.is_vip ? '是' : '否' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="140">
          <template #default="{ row }">
            <el-tag v-if="row.is_hot" type="danger" size="small" style="margin-right: 4px;">热</el-tag>
            <el-tag v-if="row.is_new" type="success" size="small" style="margin-right: 4px;">新</el-tag>
            <el-tag v-if="row.is_finished === 1" type="success" size="small" style="margin-right: 4px;">完结</el-tag>
            <el-tag v-if="row.is_finished === -1" type="warning" size="small" style="margin-right: 4px;">连载</el-tag>
            <span v-if="!row.is_hot && !row.is_new && row.is_finished === 0" style="color: #999;">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="director" label="导演" width="120" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.director">{{ getDirectorList(row.director).join(', ') }}</span>
            <span v-else style="color: #999;">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column prop="updated_at" label="更新时间" width="180" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="success" @click="goToEpisodes(row)">分集</el-button>
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

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="800px">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="平台" prop="platform">
              <el-select v-model="form.platform" placeholder="请选择平台" style="width: 100%;">
                <el-option label="爱奇艺" value="iqiyi" />
                <el-option label="腾讯视频" value="tencent" />
                <el-option label="优酷" value="youku" />
                <el-option label="芒果TV" value="mgtv" />
                <el-option label="搜狐" value="sohu" />
                <el-option label="B站" value="bilibili" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="剧集ID" prop="cid">
              <el-input v-model="form.cid" placeholder="请输入剧集ID" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" placeholder="请输入标题" />
        </el-form-item>
        <el-form-item label="播放页URL">
          <el-input v-model="form.url" placeholder="请输入播放页URL" />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="地区">
              <el-input v-model="form.area" placeholder="请输入地区" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="年份">
              <el-input v-model="form.year" placeholder="请输入年份" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="评分">
              <el-input-number v-model="form.score" :min="0" :max="10" :step="0.1" placeholder="评分" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="标签">
              <el-input v-model="tagsInput" placeholder="多个标签用逗号分隔" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="缩略图">
              <el-input v-model="form.thumbnail" placeholder="请输入缩略图URL" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="封面">
              <el-input v-model="form.cover_url" placeholder="请输入封面URL" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="演员">
          <el-input v-model="actorsInput" placeholder="多个演员用逗号分隔" />
        </el-form-item>
        <el-form-item label="简介" prop="description">
          <el-input v-model="form.description" type="textarea" :rows="3" placeholder="请输入简介" />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="总集数">
              <el-input-number v-model="form.total_episodes" :min="0" placeholder="总集数" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="已更新集数">
              <el-input-number v-model="form.updated_episodes" :min="0" placeholder="已更新集数" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="导演">
              <el-input v-model="directorInput" placeholder="多个导演用逗号分隔" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="6">
            <el-form-item label="VIP">
              <el-switch v-model="form.is_vip" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="热门">
              <el-switch v-model="form.is_hot" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="最新">
              <el-switch v-model="form.is_new" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="完结">
              <el-select v-model="form.is_finished" style="width: 100%;">
                <el-option label="已完结" :value="1" />
                <el-option label="连载中" :value="-1" />
                <el-option label="未知" :value="0" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
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
import { useRouter } from 'vue-router'
import request from '@/utils/api'

const router = useRouter()
const loading = ref(false)
const submitLoading = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('')
const formRef = ref<FormInstance>()
const tableData = ref<any[]>([])
const total = ref(0)
const currentCategory = ref('tv')

const queryForm = reactive({
  page: 1,
  limit: 20,
  platform: '',
  keyword: ''
})

const form = reactive({
  id: null as number | null,
  platform: '',
  cid: '',
  title: '',
  url: '',
  first_vid: '',
  area: '',
  year: '',
  score: null as number | null,
  tags: '' as string | null,
  thumbnail: '',
  cover_url: '',
  actors: '' as string | null,
  description: '',
  total_episodes: 0,
  updated_episodes: 0,
  director: '' as string | null,
  is_vip: false,
  is_hot: false,
  is_new: false,
  is_finished: 0 as number
})

const tagsInput = ref('')
const actorsInput = ref('')
const directorInput = ref('')

const rules: FormRules = {
  platform: [{ required: true, message: '请选择平台', trigger: 'change' }],
  cid: [{ required: true, message: '请输入剧集ID', trigger: 'blur' }],
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }]
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

const getPlatformName = (platform: string) => platformMap[platform] || platform

const getTagsList = (tagsStr: string) => {
  if (!tagsStr) return []
  try {
    const tags = JSON.parse(tagsStr)
    return Array.isArray(tags) ? tags : []
  } catch (e) {
    return tagsStr.split(',').map((t: string) => t.trim()).filter((t: string) => t)
  }
}

const getDirectorList = (directorStr: string) => {
  if (!directorStr) return []
  try {
    const arr = JSON.parse(directorStr)
    return Array.isArray(arr) ? arr : []
  } catch (e) {
    return directorStr.split(',').map((d: string) => d.trim()).filter((d: string) => d)
  }
}

const onCategoryChange = () => {
  queryForm.page = 1
  loadData()
}

const loadData = async () => {
  loading.value = true
  try {
    const params: any = {
      category: currentCategory.value,
      page: queryForm.page,
      limit: queryForm.limit
    }
    if (queryForm.platform) params.platform = queryForm.platform
    if (queryForm.keyword) params.keyword = queryForm.keyword

    const res = await request.get('/series', { params })
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
  queryForm.platform = ''
  queryForm.keyword = ''
  queryForm.page = 1
  loadData()
}

const handleAdd = () => {
  dialogTitle.value = '新增剧集'
  Object.assign(form, {
    id: null,
    platform: '',
    cid: '',
    title: '',
    url: '',
    first_vid: '',
    area: '',
    year: '',
    score: null,
    tags: '',
    thumbnail: '',
    cover_url: '',
    actors: '',
    description: '',
    total_episodes: 0,
    updated_episodes: 0,
    director: '',
    is_vip: false,
    is_hot: false,
    is_new: false,
    is_finished: 0
  })
  tagsInput.value = ''
  actorsInput.value = ''
  directorInput.value = ''
  dialogVisible.value = true
}

const handleEdit = (row: any) => {
  dialogTitle.value = '编辑剧集'
  Object.assign(form, {
    id: row.id,
    platform: row.platform,
    cid: row.cid,
    title: row.title,
    url: row.url || '',
    first_vid: row.first_vid || '',
    area: row.area || '',
    year: row.year || '',
    score: row.score,
    tags: row.tags || '',
    thumbnail: row.thumbnail || '',
    cover_url: row.cover_url || '',
    actors: row.actors || '',
    description: row.description || '',
    total_episodes: row.total_episodes || 0,
    updated_episodes: row.updated_episodes || 0,
    director: row.director || '',
    is_vip: !!row.is_vip,
    is_hot: !!row.is_hot,
    is_new: !!row.is_new,
    is_finished: row.is_finished ?? 0
  })
  try {
    if (row.tags) {
      const tags = JSON.parse(row.tags)
      tagsInput.value = Array.isArray(tags) ? tags.join(', ') : ''
    } else {
      tagsInput.value = ''
    }
  } catch (e) {
    tagsInput.value = row.tags || ''
  }
  try {
    if (row.actors) {
      const actors = JSON.parse(row.actors)
      actorsInput.value = Array.isArray(actors) ? actors.join(', ') : ''
    } else {
      actorsInput.value = ''
    }
  } catch (e) {
    actorsInput.value = row.actors || ''
  }
  try {
    if (row.director) {
      const director = JSON.parse(row.director)
      directorInput.value = Array.isArray(director) ? director.join(', ') : ''
    } else {
      directorInput.value = ''
    }
  } catch (e) {
    directorInput.value = row.director || ''
  }
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
          platform: form.platform,
          cid: form.cid,
          title: form.title,
          url: form.url,
          first_vid: form.first_vid,
          area: form.area,
          year: form.year,
          score: form.score,
          thumbnail: form.thumbnail,
          cover_url: form.cover_url,
          description: form.description,
          total_episodes: form.total_episodes,
          updated_episodes: form.updated_episodes,
          is_vip: form.is_vip ? 1 : 0,
          is_hot: form.is_hot ? 1 : 0,
          is_new: form.is_new ? 1 : 0,
          is_finished: form.is_finished
        }
        if (tagsInput.value.trim()) {
          const tagsArray = tagsInput.value.split(',').map((t: string) => t.trim()).filter((t: string) => t)
          data.tags = JSON.stringify(tagsArray)
        }
        if (actorsInput.value.trim()) {
          const actorsArray = actorsInput.value.split(',').map((a: string) => a.trim()).filter((a: string) => a)
          data.actors = JSON.stringify(actorsArray)
        }
        if (directorInput.value.trim()) {
          const directorArray = directorInput.value.split(',').map((d: string) => d.trim()).filter((d: string) => d)
          data.director = JSON.stringify(directorArray)
        }
        if (form.id) {
          await request.put(`/series/${form.id}`, data)
          ElMessage.success('编辑成功')
        } else {
          await request.post('/series', data)
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
    await ElMessageBox.confirm(`确定要删除《${row.title}》吗？`, '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await request.delete(`/series/${row.id}`, { params: { category: currentCategory.value } })
    ElMessage.success('删除成功')
    loadData()
  } catch (error) {
    console.error('删除失败:', error)
    if ((error as any) !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const goToEpisodes = (row: any) => {
  router.push({
    path: '/video/episodes',
    query: {
      category: currentCategory.value,
      seriesId: row.id,
      seriesTitle: row.title
    }
  })
}

onMounted(() => {
  loadData()
})
</script>

<style scoped lang="scss">
.series {
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
    .search-section {
      display: flex;
      align-items: center;
    }
  }
}
</style>
