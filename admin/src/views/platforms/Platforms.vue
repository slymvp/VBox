<template>
  <div class="platforms">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>平台管理</span>
          <div class="header-actions">
            <el-button @click="handleExportPlatforms">导出数据</el-button>
            <el-upload
              :show-file-list="false"
              :before-upload="handleImportPlatforms"
              accept=".json"
              style="display: inline-block; margin-left: 10px;"
            >
              <el-button type="primary">导入数据</el-button>
            </el-upload>
            <el-button type="primary" @click="handleAddPlatform">新增平台</el-button>
          </div>
        </div>
      </template>

      <!-- 平台列表 -->
      <el-table :data="platformList" stripe v-loading="loading" row-key="id" @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="55" />
        <el-table-column prop="key" label="平台标识" width="150" />
        <el-table-column prop="name" label="平台名称" min-width="150" />
        <el-table-column prop="official_site" label="官网地址" min-width="200" show-overflow-tooltip />
        <el-table-column prop="spider" label="爬虫类" min-width="250" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'danger'">{{ row.enabled ? '启用' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="350" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleManageParseSources(row)">解析源</el-button>
            <el-button link type="primary" @click="handleManageChannels(row)">频道</el-button>
            <el-button link type="primary" @click="handleManageKeywords(row)">关键词</el-button>
            <el-button link type="primary" @click="handleEditPlatform(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDeletePlatform(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="selectedPlatforms.length > 0" style="margin-top: 16px;">
        <el-button type="success" @click="handleBatchEnable">批量启用 ({{ selectedPlatforms.length }})</el-button>
        <el-button type="warning" @click="handleBatchDisable">批量禁用 ({{ selectedPlatforms.length }})</el-button>
        <el-button type="danger" @click="handleBatchDelete">批量删除 ({{ selectedPlatforms.length }})</el-button>
      </div>
    </el-card>

    <!-- 新增/编辑平台对话框 -->
    <el-dialog v-model="platformDialogVisible" :title="platformDialogTitle" width="700px">
      <el-form :model="platformForm" :rules="platformRules" ref="platformFormRef" label-width="120px">
        <el-form-item label="平台标识" prop="key">
          <el-input v-model="platformForm.key" placeholder="例如：iqiyi" :disabled="!!editingPlatform" />
        </el-form-item>
        <el-form-item label="平台名称" prop="name">
          <el-input v-model="platformForm.name" placeholder="例如：爱奇艺" />
        </el-form-item>
        <el-form-item label="官网地址" prop="official_site">
          <el-input v-model="platformForm.official_site" placeholder="https://www.iqiyi.com" />
        </el-form-item>
        <el-form-item label="爬虫类" prop="spider">
          <el-input v-model="platformForm.spider" placeholder="spiders.iqiyi_api_spider.IQiyiAPISpider" />
        </el-form-item>
        <el-form-item label="图标" prop="icon">
          <el-input v-model="platformForm.icon" placeholder="图标URL（可选）" />
        </el-form-item>
        <el-form-item label="User-Agent">
          <el-input
            v-model="platformForm.user_agent"
            type="textarea"
            :rows="3"
            placeholder="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
          />
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="请求间隔" prop="rate_limit">
              <el-input-number v-model="platformForm.rate_limit" :min="0" :step="0.1" :precision="1" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="超时时间" prop="timeout">
              <el-input-number v-model="platformForm.timeout" :min="1" style="width: 100%;" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="排序" prop="sort_order">
              <el-input-number v-model="platformForm.sort_order" :min="0" style="width: 100%;" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="状态" prop="enabled">
              <el-switch v-model="platformForm.enabled" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="platformDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmitPlatform" :loading="platformSubmitting">确定</el-button>
      </template>
    </el-dialog>

    <!-- 平台频道管理对话框 -->
    <el-dialog v-model="channelsDialogVisible" :title="channelsDialogTitle" width="800px">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span>{{ channelsDialogTitle }}</span>
          <div class="dialog-header-actions">
            <el-button size="small" @click="downloadPlatformChannelTemplate">下载模板</el-button>
            <el-upload
              ref="platformChannelUploadRef"
              :show-file-list="false"
              :before-upload="handlePlatformChannelUpload"
              accept=".csv"
              style="display: inline-block;"
            >
              <el-button type="primary" size="small">批量导入</el-button>
            </el-upload>
            <el-button type="primary" size="small" @click="handleAddChannel">新增频道</el-button>
          </div>
        </div>
      </template>
      <el-table :data="currentPlatformChannels" stripe v-loading="channelLoading">
        <el-table-column prop="channel_key" label="频道标识" width="150" />
        <el-table-column prop="channel_name" label="频道名称" min-width="150" />
        <el-table-column prop="url" label="URL" min-width="300" show-overflow-tooltip />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.enabled ? 'success' : 'danger'">{{ row.enabled ? '启用' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEditChannel(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDeleteChannel(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 新增/编辑频道对话框 -->
      <el-dialog v-model="channelDialogVisible" :title="channelDialogTitle" width="600px">
        <el-form :model="channelForm" :rules="channelRules" ref="channelFormRef" label-width="120px">
          <el-form-item label="选择频道" prop="category_id">
            <el-select
              v-model="channelForm.category_id"
              placeholder="请选择频道"
              style="width: 100%;"
              @change="handleCategoryChange"
            >
              <el-option
                v-for="cat in categoryList"
                :key="cat.id"
                :label="cat.name"
                :value="cat.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="频道标识" prop="channel_key">
            <el-input v-model="channelForm.channel_key" placeholder="例如：tv" />
          </el-form-item>
          <el-form-item label="频道名称" prop="channel_name">
            <el-input v-model="channelForm.channel_name" placeholder="例如：电视剧" />
          </el-form-item>
          <el-form-item label="URL" prop="url">
            <el-input v-model="channelForm.url" placeholder="https://www.iqiyi.com/tv" />
          </el-form-item>
          <el-form-item label="频道ID" prop="channel_id">
            <el-input v-model="channelForm.channel_id" placeholder="可选" />
          </el-form-item>
          <el-form-item label="排序" prop="sort_order">
            <el-input-number v-model="channelForm.sort_order" :min="0" style="width: 100%;" />
          </el-form-item>
          <el-form-item label="状态" prop="enabled">
            <el-switch v-model="channelForm.enabled" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="channelDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSubmitChannel" :loading="channelSubmitting">确定</el-button>
        </template>
      </el-dialog>
    </el-dialog>

    <!-- 平台关键词管理对话框 -->
    <el-dialog v-model="keywordsDialogVisible" :title="keywordsDialogTitle" width="800px">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span>{{ keywordsDialogTitle }}</span>
          <div class="dialog-header-actions">
            <el-button type="danger" size="small" @click="handleClearKeywords">清空所有关键词</el-button>
            <el-button type="primary" size="small" @click="handleBatchAddKeywordsVisible = true">批量添加</el-button>
          </div>
        </div>
      </template>
      <div class="keywords-config">
        <div class="keyword-section">
          <div class="section-header">
            <span class="section-title">正片关键词</span>
            <div class="keyword-input">
              <el-input
                v-model="newKeywordInput"
                placeholder="输入关键词"
                @keyup.enter="addKeyword('positive')"
                style="width: 200px;"
              />
              <el-button type="primary" @click="addKeyword('positive')">添加</el-button>
              <el-button type="default" size="small" @click="copyKeywords('positive')">复制</el-button>
            </div>
          </div>
          <div class="keywords-list">
            <el-tag
              v-for="(keyword, index) in keywordsForm.positive"
              :key="index"
              closable
              @close="removeKeyword('positive', index)"
              style="margin: 4px;"
            >
              {{ keyword }}
            </el-tag>
            <div v-if="keywordsForm.positive.length === 0" style="color: #999; padding: 8px;">
              暂无关键词
            </div>
          </div>
        </div>

        <div class="keyword-section">
          <div class="section-header">
            <span class="section-title">预告关键词</span>
            <div class="keyword-input">
              <el-input
                v-model="newKeywordInput"
                placeholder="输入关键词"
                @keyup.enter="addKeyword('trailer')"
                style="width: 200px;"
              />
              <el-button type="primary" @click="addKeyword('trailer')">添加</el-button>
              <el-button type="default" size="small" @click="copyKeywords('trailer')">复制</el-button>
            </div>
          </div>
          <div class="keywords-list">
            <el-tag
              v-for="(keyword, index) in keywordsForm.trailer"
              :key="index"
              closable
              @close="removeKeyword('trailer', index)"
              style="margin: 4px;"
            >
              {{ keyword }}
            </el-tag>
            <div v-if="keywordsForm.trailer.length === 0" style="color: #999; padding: 8px;">
              暂无关键词
            </div>
          </div>
        </div>

        <div class="keyword-section">
          <div class="section-header">
            <span class="section-title">花絮关键词</span>
            <div class="keyword-input">
              <el-input
                v-model="newKeywordInput"
                placeholder="输入关键词"
                @keyup.enter="addKeyword('bts')"
                style="width: 200px;"
              />
              <el-button type="primary" @click="addKeyword('bts')">添加</el-button>
              <el-button type="default" size="small" @click="copyKeywords('bts')">复制</el-button>
            </div>
          </div>
          <div class="keywords-list">
            <el-tag
              v-for="(keyword, index) in keywordsForm.bts"
              :key="index"
              closable
              @close="removeKeyword('bts', index)"
              style="margin: 4px;"
            >
              {{ keyword }}
            </el-tag>
            <div v-if="keywordsForm.bts.length === 0" style="color: #999; padding: 8px;">
              暂无关键词
            </div>
          </div>
        </div>

        <div class="keyword-section">
          <div class="section-header">
            <span class="section-title">VIP关键词</span>
            <div class="keyword-input">
              <el-input
                v-model="newKeywordInput"
                placeholder="输入关键词"
                @keyup.enter="addKeyword('vip')"
                style="width: 200px;"
              />
              <el-button type="primary" @click="addKeyword('vip')">添加</el-button>
              <el-button type="default" size="small" @click="copyKeywords('vip')">复制</el-button>
            </div>
          </div>
          <div class="keywords-list">
            <el-tag
              v-for="(keyword, index) in keywordsForm.vip"
              :key="index"
              closable
              @close="removeKeyword('vip', index)"
              style="margin: 4px;"
            >
              {{ keyword }}
            </el-tag>
            <div v-if="keywordsForm.vip.length === 0" style="color: #999; padding: 8px;">
              暂无关键词
            </div>
          </div>
        </div>

        <div class="keyword-section">
          <div class="section-header">
            <span class="section-title">完结关键词</span>
            <div class="keyword-input">
              <el-input
                v-model="newKeywordInput"
                placeholder="输入关键词"
                @keyup.enter="addKeyword('completed')"
                style="width: 200px;"
              />
              <el-button type="primary" @click="addKeyword('completed')">添加</el-button>
              <el-button type="default" size="small" @click="copyKeywords('completed')">复制</el-button>
            </div>
          </div>
          <div class="keywords-list">
            <el-tag
              v-for="(keyword, index) in keywordsForm.completed"
              :key="index"
              closable
              @close="removeKeyword('completed', index)"
              style="margin: 4px;"
            >
              {{ keyword }}
            </el-tag>
            <div v-if="keywordsForm.completed.length === 0" style="color: #999; padding: 8px;">
              暂无关键词
            </div>
          </div>
        </div>

        <div class="keyword-section">
          <div class="section-header">
            <span class="section-title">更新中关键词</span>
            <div class="keyword-input">
              <el-input
                v-model="newKeywordInput"
                placeholder="输入关键词"
                @keyup.enter="addKeyword('ongoing')"
                style="width: 200px;"
              />
              <el-button type="primary" @click="addKeyword('ongoing')">添加</el-button>
              <el-button type="default" size="small" @click="copyKeywords('ongoing')">复制</el-button>
            </div>
          </div>
          <div class="keywords-list">
            <el-tag
              v-for="(keyword, index) in keywordsForm.ongoing"
              :key="index"
              closable
              @close="removeKeyword('ongoing', index)"
              style="margin: 4px;"
            >
              {{ keyword }}
            </el-tag>
            <div v-if="keywordsForm.ongoing.length === 0" style="color: #999; padding: 8px;">
              暂无关键词
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="keywordsDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSaveKeywords" :loading="keywordsSubmitting">保存</el-button>
      </template>
    </el-dialog>

    <!-- 批量添加关键词对话框 -->
    <el-dialog v-model="handleBatchAddKeywordsVisible" title="批量添加关键词" width="500px">
      <el-form label-width="100px">
        <el-form-item label="添加到分类">
            <el-select v-model="batchKeywordType" style="width: 100%;">
              <el-option label="正片关键词" value="positive" />
              <el-option label="预告关键词" value="trailer" />
              <el-option label="花絮关键词" value="bts" />
              <el-option label="VIP关键词" value="vip" />
              <el-option label="完结关键词" value="completed" />
              <el-option label="更新中关键词" value="ongoing" />
            </el-select>
        </el-form-item>
        <el-form-item label="关键词列表">
          <el-input
            v-model="batchKeywordsInput"
            type="textarea"
            :rows="6"
            placeholder="请输入关键词，多个关键词用英文逗号分隔，例如：正片,第1集,第2集"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="handleBatchAddKeywordsVisible = false">取消</el-button>
        <el-button type="primary" @click="handleBatchAddKeywords" :loading="batchKeywordSubmitting">添加</el-button>
      </template>
    </el-dialog>

    <!-- 平台解析源管理对话框 -->
    <el-dialog v-model="parseSourcesDialogVisible" :title="parseSourcesDialogTitle" width="800px">
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center;">
          <span>{{ parseSourcesDialogTitle }}</span>
          <div class="dialog-header-actions">
            <el-button size="small" @click="downloadParseSourceTemplate">下载模板</el-button>
            <el-upload
              ref="parseSourceUploadRef"
              :show-file-list="false"
              :before-upload="handleParseSourceUpload"
              accept=".csv"
              style="display: inline-block;"
            >
              <el-button type="primary" size="small">批量导入</el-button>
            </el-upload>
            <el-button type="primary" size="small" @click="handleAddParseSource">新增解析源</el-button>
          </div>
        </div>
      </template>
      <draggable
        v-model="currentPlatformParseSources"
        item-key="id"
        handle=".drag-handle"
        @end="handleDragEnd"
      >
        <template #item="{ element }">
          <div class="parse-source-item">
            <div class="drag-handle">
              <el-icon><Sort /></el-icon>
            </div>
            <div class="parse-source-content">
              <span class="parse-source-name">{{ element.name }}</span>
              <span class="parse-source-url">{{ element.url }}</span>
            </div>
            <div class="parse-source-actions">
              <el-tag :type="element.enabled ? 'success' : 'danger'" size="small">{{ element.enabled ? '启用' : '禁用' }}</el-tag>
              <el-button link type="primary" size="small" @click="handleEditParseSource(element)">编辑</el-button>
              <el-button link type="danger" size="small" @click="handleDeleteParseSource(element)">删除</el-button>
            </div>
          </div>
        </template>
      </draggable>

      <!-- 新增/编辑解析源对话框 -->
      <el-dialog v-model="parseSourceDialogVisible" :title="parseSourceDialogTitle" width="600px">
        <el-form :model="parseSourceForm" :rules="parseSourceRules" ref="parseSourceFormRef" label-width="100px">
          <el-form-item label="名称" prop="name">
            <el-input v-model="parseSourceForm.name" placeholder="解析源名称" />
          </el-form-item>
          <el-form-item label="解析地址" prop="url">
            <el-input v-model="parseSourceForm.url" placeholder="https://example.com/api/parse" />
          </el-form-item>
          <el-form-item label="排序" prop="sort_order">
            <el-input-number v-model="parseSourceForm.sort_order" :min="0" style="width: 100%;" />
          </el-form-item>
          <el-form-item label="状态" prop="enabled">
            <el-switch v-model="parseSourceForm.enabled" />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="parseSourceDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSubmitParseSource" :loading="parseSourceSubmitting">确定</el-button>
        </template>
      </el-dialog>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Sort } from '@element-plus/icons-vue'
import draggable from 'vuedraggable'
import request from '@/utils/api'

interface KeywordsConfig {
  positive: string[];
  trailer: string[];
  bts: string[];
  vip: string[];
  completed: string[];
  ongoing: string[];
}

interface Category {
  id: number
  key: string
  name: string
}

interface PlatformChannel {
  id: number
  platform_id: number
  category_id?: number
  channel_key: string
  channel_name: string
  url: string
  output_table: string
  channel_id?: string
  config?: any
  sort_order: number
  enabled: boolean
}

interface ParseSource {
  id: number
  platform_id: number
  name: string
  type: string
  url: string
  sort_order: number
  enabled: boolean
}

interface Platform {
  id: number
  key: string
  name: string
  spider?: string
  official_site: string
  icon?: string
  rate_limit: number
  timeout: number
  sort_order: number
  enabled: boolean
  user_agent?: string
  keywords?: any
  config?: any
  parse_sources?: ParseSource[]
  platform_channels?: PlatformChannel[]
}

const loading = ref(false)
const platformSubmitting = ref(false)
const channelSubmitting = ref(false)
const channelLoading = ref(false)
const parseSourceSubmitting = ref(false)
const parseSourceLoading = ref(false)
const platformList = ref<Platform[]>([])
const categoryList = ref<Category[]>([])
const selectedPlatforms = ref<Platform[]>([])

// 平台相关
const platformDialogVisible = ref(false)
const platformDialogTitle = computed(() => (editingPlatform ? '编辑平台' : '新增平台'))
const platformFormRef = ref()
const editingPlatform = ref<Platform | null>(null)

// 关键词相关
const keywordsDialogVisible = ref(false)
const keywordsDialogTitle = ref('')
const currentKeywordsPlatform = ref<Platform | null>(null)
const keywordsSubmitting = ref(false)
const keywordsForm = reactive({
  positive: [] as string[],
  trailer: [] as string[],
  bts: [] as string[],
  vip: [] as string[],
  completed: [] as string[],
  ongoing: [] as string[]
})
const newKeywordInput = ref('')

// 关键词批量操作相关
const handleBatchAddKeywordsVisible = ref(false)
const batchKeywordType = ref('positive')
const batchKeywordsInput = ref('')
const batchKeywordSubmitting = ref(false)

const platformForm = reactive({
  key: '',
  name: '',
  spider: '',
  official_site: '',
  icon: '',
  rate_limit: 1.0,
  timeout: 15,
  sort_order: 0,
  enabled: true,
  user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
})

const platformRules = {
  key: [{ required: true, message: '请输入平台标识', trigger: 'blur' }],
  name: [{ required: true, message: '请输入平台名称', trigger: 'blur' }]
}

// 频道相关
const channelsDialogVisible = ref(false)
const channelsDialogTitle = ref('')
const currentPlatformChannels = ref<PlatformChannel[]>([])
const currentPlatform = ref<Platform | null>(null)
const channelDialogVisible = ref(false)
const channelDialogTitle = computed(() => (editingChannel ? '编辑频道' : '新增频道'))
const channelFormRef = ref()
const editingChannel = ref<PlatformChannel | null>(null)

const channelForm = reactive({
  platform_id: 0,
  category_id: undefined as number | undefined,
  channel_key: '',
  channel_name: '',
  url: '',
  channel_id: '',
  config: null as any,
  sort_order: 0,
  enabled: true
})

const channelRules = {
  channel_key: [{ required: true, message: '请输入频道标识', trigger: 'blur' }],
  channel_name: [{ required: true, message: '请输入频道名称', trigger: 'blur' }],
  url: [{ required: true, message: '请输入URL', trigger: 'blur' }]
}

// 解析源相关
const parseSourcesDialogVisible = ref(false)
const parseSourcesDialogTitle = ref('')
const currentPlatformParseSources = ref<ParseSource[]>([])
const parseSourceDialogVisible = ref(false)
const parseSourceDialogTitle = computed(() => (editingParseSource ? '编辑解析源' : '新增解析源'))
const parseSourceFormRef = ref()
const editingParseSource = ref<ParseSource | null>(null)

const parseSourceForm = reactive({
  platform_id: 0,
  name: '',
  url: '',
  sort_order: 0,
  enabled: true
})

const parseSourceRules = {
  name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  url: [{ required: true, message: '请输入解析地址', trigger: 'blur' }]
}

const loadData = async () => {
  loading.value = true
  try {
    const [platformsRes, categoriesRes] = await Promise.all([
      request.get('/platforms-v2'),
      request.get('/categories')
    ])
    platformList.value = platformsRes.data || []
    categoryList.value = categoriesRes.data || []
  } catch (error) {
    console.error('获取数据失败:', error)
    ElMessage.error('获取数据失败')
  } finally {
    loading.value = false
  }
}

const handleSelectionChange = (selection: Platform[]) => {
  selectedPlatforms.value = selection
}

// 导出平台数据
const handleExportPlatforms = async () => {
  try {
    const response = await request.get('/platforms-v2/export', { responseType: 'blob' })
    const blob = new Blob([response], { type: 'application/json' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `platforms_${new Date().toISOString().slice(0, 10)}.json`
    link.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (error: any) {
    console.error('导出失败:', error)
    ElMessage.error(error.message || '导出失败')
  }
}

// 导入平台数据
const handleImportPlatforms = async (file: File) => {
  try {
    const text = await file.text()
    const data = JSON.parse(text)

    await ElMessageBox.confirm(
      `即将导入 ${data.platforms?.length || 0} 个平台数据，包括频道、关键词和解析源。是否继续？`,
      '导入确认',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'info' }
    )

    const result = await request.post('/platforms-v2/import', data)
    ElMessage.success(result.message || '导入成功')
    loadData()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('导入失败:', error)
      ElMessage.error(error.message || '导入失败')
    }
  }
  return false // 阻止默认上传行为
}

const handleAddPlatform = () => {
  editingPlatform.value = null
  Object.assign(platformForm, {
    key: '',
    name: '',
    spider: '',
    official_site: '',
    icon: '',
    rate_limit: 1.0,
    timeout: 15,
    sort_order: 0,
    enabled: true,
    user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
  })
  platformDialogVisible.value = true
}

const handleEditPlatform = (row: Platform) => {
  editingPlatform.value = row
  Object.assign(platformForm, {
    key: row.key,
    name: row.name,
    spider: row.spider,
    official_site: row.official_site,
    icon: row.icon || '',
    rate_limit: row.rate_limit,
    timeout: row.timeout,
    sort_order: row.sort_order,
    enabled: row.enabled,
    user_agent: row.user_agent || 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
  })
  platformDialogVisible.value = true
}

// 关键词管理
const handleManageKeywords = (row: Platform) => {
  currentKeywordsPlatform.value = row
  keywordsDialogTitle.value = `${row.name} 关键词配置`
  Object.assign(keywordsForm, {
    positive: row.keywords?.positive || [],
    trailer: row.keywords?.trailer || [],
    bts: row.keywords?.bts || [],
    vip: row.keywords?.vip || [],
    completed: row.keywords?.completed || [],
    ongoing: row.keywords?.ongoing || []
  })
  keywordsDialogVisible.value = true
}

const handleSaveKeywords = async () => {
  if (!currentKeywordsPlatform.value) return
  try {
    keywordsSubmitting.value = true
    await request.put(`/platforms-v2/${currentKeywordsPlatform.value.id}`, {
      keywords: keywordsForm
    })
    ElMessage.success('保存成功')
    keywordsDialogVisible.value = false
    await loadData()
  } catch (error: any) {
    ElMessage.error('保存失败')
  } finally {
    keywordsSubmitting.value = false
  }
}

const addKeyword = (type: keyof KeywordsConfig) => {
  const keyword = newKeywordInput.value.trim()
  if (keyword && !keywordsForm[type].includes(keyword)) {
    keywordsForm[type].push(keyword)
    newKeywordInput.value = ''
  } else if (keywordsForm[type].includes(keyword)) {
    ElMessage.warning('关键词已存在')
  }
}

const removeKeyword = (type: keyof KeywordsConfig, index: number) => {
  if (index > -1) {
    keywordsForm[type].splice(index, 1)
  }
}

const copyKeywords = async (type: keyof KeywordsConfig) => {
  const keywords = keywordsForm[type]
  if (keywords.length === 0) {
    ElMessage.warning('暂无关键词可复制')
    return
  }
  try {
    await navigator.clipboard.writeText(keywords.join(','))
    ElMessage.success('复制成功')
  } catch (e) {
    ElMessage.error('复制失败')
  }
}

// 关键词批量操作
const handleClearKeywords = async () => {
  if (!currentKeywordsPlatform.value) return
  try {
    await ElMessageBox.confirm('确定要清空该平台的所有关键词吗？此操作不可恢复！', '警告', {
      confirmButtonText: '确定清空',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await request.delete(`/platforms-v2/${currentKeywordsPlatform.value.id}/keywords`)
    ElMessage.success('清空成功')
    Object.assign(keywordsForm, {
      positive: [],
      trailer: [],
      bts: [],
      vip: [],
      completed: [],
      ongoing: []
    })
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('清空失败')
    }
  }
}

const handleBatchAddKeywords = async () => {
  if (!currentKeywordsPlatform.value) return
  if (!batchKeywordsInput.value.trim()) {
    ElMessage.warning('请输入关键词')
    return
  }
  try {
    batchKeywordSubmitting.value = true
    await request.post(`/platforms-v2/${currentKeywordsPlatform.value.id}/keywords/batch-add`, {
      type: batchKeywordType.value,
      keywords: batchKeywordsInput.value
    })
    ElMessage.success('批量添加成功')
    // 添加到本地表单
    const newKeywords = batchKeywordsInput.value.split(',').map(k => k.trim()).filter(k => k)
    newKeywords.forEach(keyword => {
      if (!keywordsForm[batchKeywordType.value as keyof KeywordsConfig].includes(keyword)) {
        keywordsForm[batchKeywordType.value as keyof KeywordsConfig].push(keyword)
      }
    })
    handleBatchAddKeywordsVisible.value = false
    batchKeywordsInput.value = ''
  } catch (error: any) {
    ElMessage.error('批量添加失败')
  } finally {
    batchKeywordSubmitting.value = false
  }
}

// 解析源批量导入和模板
const downloadParseSourceTemplate = () => {
  window.open('/admin-api/parse-sources/template', '_blank')
}

const handleParseSourceUpload = async (file: File) => {
  if (!currentPlatform.value) return false
  try {
    const formData = new FormData()
    formData.append('file', file)
    const res = await request.post('/parse-sources/batch-import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    ElMessage.success(res.message || '导入成功')
    await loadParseSources(currentPlatform.value.id)
  } catch (error: any) {
    ElMessage.error('导入失败: ' + (error.message || '未知错误'))
  }
  return false
}

// 平台频道批量导入和模板
const downloadPlatformChannelTemplate = () => {
  if (!currentPlatform.value) return
  window.open(`/admin-api/platforms-v2/${currentPlatform.value.id}/channels/template`, '_blank')
}

const handlePlatformChannelUpload = async (file: File) => {
  if (!currentPlatform.value) return false
  try {
    const formData = new FormData()
    formData.append('file', file)
    const res = await request.post(`/platforms-v2/${currentPlatform.value.id}/channels/batch-import`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    ElMessage.success(res.message || '导入成功')
    await loadChannels(currentPlatform.value.id)
  } catch (error: any) {
    ElMessage.error('导入失败: ' + (error.message || '未知错误'))
  }
  return false
}

// 解析源拖拽排序
const handleDragEnd = async () => {
  if (!currentPlatform.value) return
  try {
    // 更新所有解析源的 sort_order
    const updates = currentPlatformParseSources.value.map((item, index) => ({
      id: item.id,
      sort_order: index
    }))
    // 调用 API 批量更新排序
    await Promise.all(
      updates.map(update =>
        request.put(`/platforms-v2/${currentPlatform.value!.id}/parse-sources/${update.id}`, {
          sort_order: update.sort_order
        })
      )
    )
  } catch (error: any) {
    console.error('更新排序失败:', error)
  }
}

const handleSubmitPlatform = async () => {
  try {
    await platformFormRef.value.validate()
    platformSubmitting.value = true
    if (editingPlatform.value) {
      await request.put(`/platforms-v2/${editingPlatform.value.id}`, platformForm)
      ElMessage.success('更新成功')
    } else {
      await request.post('/platforms-v2', platformForm)
      ElMessage.success('创建成功')
    }
    platformDialogVisible.value = false
    await loadData()
  } catch (error: any) {
    if (error !== false) {
      console.error('提交失败:', error)
      ElMessage.error(error.message || '操作失败')
    }
  } finally {
    platformSubmitting.value = false
  }
}

const handleDeletePlatform = async (row: Platform) => {
  try {
    await ElMessageBox.confirm('确定要删除该平台吗？该平台下的所有频道和解析源也会被删除。', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await request.delete(`/platforms-v2/${row.id}`)
    ElMessage.success('删除成功')
    await loadData()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

const handleBatchEnable = async () => {
  try {
    await Promise.all(
      selectedPlatforms.value.map(p =>
        request.put(`/platforms-v2/${p.id}`, { enabled: true })
      )
    )
    ElMessage.success('批量启用成功')
    selectedPlatforms.value = []
    await loadData()
  } catch (error) {
    ElMessage.error('批量启用失败')
  }
}

const handleBatchDisable = async () => {
  try {
    await Promise.all(
      selectedPlatforms.value.map(p =>
        request.put(`/platforms-v2/${p.id}`, { enabled: false })
      )
    )
    ElMessage.success('批量禁用成功')
    selectedPlatforms.value = []
    await loadData()
  } catch (error) {
    ElMessage.error('批量禁用失败')
  }
}

const handleBatchDelete = async () => {
  try {
    await ElMessageBox.confirm('确定要批量删除选中的平台吗？', '警告', {
      confirmButtonText: '确定删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await Promise.all(
      selectedPlatforms.value.map(p =>
        request.delete(`/platforms-v2/${p.id}`)
      )
    )
    ElMessage.success('批量删除成功')
    selectedPlatforms.value = []
    await loadData()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('批量删除失败')
    }
  }
}

// 平台频道管理
const handleManageChannels = async (row: Platform) => {
  currentPlatform.value = row
  channelsDialogTitle.value = `${row.name} 频道管理`
  channelsDialogVisible.value = true
  await loadChannels(row.id)
}

const loadChannels = async (platformId: number) => {
  channelLoading.value = true
  try {
    const res = await request.get(`/platforms-v2/${platformId}/channels`)
    currentPlatformChannels.value = res.data || []
  } catch (error) {
    ElMessage.error('获取频道列表失败')
  } finally {
    channelLoading.value = false
  }
}

const handleAddChannel = () => {
  if (!currentPlatform.value) return
  editingChannel.value = null
  Object.assign(channelForm, {
    platform_id: currentPlatform.value.id,
    category_id: undefined,
    channel_key: '',
    channel_name: '',
    url: '',
    channel_id: '',
    config: null,
    sort_order: 0,
    enabled: true
  })
  channelDialogVisible.value = true
}

const handleEditChannel = (row: PlatformChannel) => {
  editingChannel.value = row
  Object.assign(channelForm, {
    platform_id: row.platform_id,
    category_id: row.category_id,
    channel_key: row.channel_key,
    channel_name: row.channel_name,
    url: row.url,
    channel_id: row.channel_id || '',
    config: row.config || null,
    sort_order: row.sort_order,
    enabled: row.enabled
  })
  channelDialogVisible.value = true
}

const handleSubmitChannel = async () => {
  try {
    await channelFormRef.value.validate()
    channelSubmitting.value = true
    if (editingChannel.value) {
      await request.put(`/platforms-v2/${channelForm.platform_id}/channels/${editingChannel.value.id}`, channelForm)
      ElMessage.success('更新成功')
    } else {
      await request.post(`/platforms-v2/${channelForm.platform_id}/channels`, channelForm)
      ElMessage.success('创建成功')
    }
    channelDialogVisible.value = false
    if (currentPlatform.value) {
      await loadChannels(currentPlatform.value.id)
    }
  } catch (error: any) {
    if (error !== false) {
      ElMessage.error('提交失败')
    }
  } finally {
    channelSubmitting.value = false
  }
}

const handleDeleteChannel = async (row: PlatformChannel) => {
  try {
    await ElMessageBox.confirm('确定要删除该频道吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await request.delete(`/platforms-v2/${row.platform_id}/channels/${row.id}`)
    ElMessage.success('删除成功')
    if (currentPlatform.value) {
      await loadChannels(currentPlatform.value.id)
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const handleCategoryChange = (categoryId: number) => {
  const category = categoryList.value.find(cat => cat.id === categoryId)
  if (category) {
    channelForm.channel_key = category.key
    channelForm.channel_name = category.name
  }
}

// 平台解析源管理
const handleManageParseSources = async (row: Platform) => {
  currentPlatform.value = row
  parseSourcesDialogTitle.value = `${row.name} 解析源管理`
  parseSourcesDialogVisible.value = true
  await loadParseSources(row.id)
}

const loadParseSources = async (platformId: number) => {
  parseSourceLoading.value = true
  try {
    const res = await request.get(`/platforms-v2/${platformId}/parse-sources`)
    currentPlatformParseSources.value = res.data || []
  } catch (error) {
    ElMessage.error('获取解析源列表失败')
  } finally {
    parseSourceLoading.value = false
  }
}

const handleAddParseSource = () => {
  if (!currentPlatform.value) return
  editingParseSource.value = null
  Object.assign(parseSourceForm, {
    platform_id: currentPlatform.value.id,
    name: '',
    url: '',
    sort_order: 0,
    enabled: true
  })
  parseSourceDialogVisible.value = true
}

const handleEditParseSource = (row: ParseSource) => {
  editingParseSource.value = row
  Object.assign(parseSourceForm, {
    platform_id: row.platform_id,
    name: row.name,
    url: row.url,
    sort_order: row.sort_order,
    enabled: row.enabled
  })
  parseSourceDialogVisible.value = true
}

const handleSubmitParseSource = async () => {
  try {
    await parseSourceFormRef.value.validate()
    parseSourceSubmitting.value = true
    if (editingParseSource.value) {
      await request.put(`/platforms-v2/${parseSourceForm.platform_id}/parse-sources/${editingParseSource.value.id}`, parseSourceForm)
      ElMessage.success('更新成功')
    } else {
      await request.post(`/platforms-v2/${parseSourceForm.platform_id}/parse-sources`, parseSourceForm)
      ElMessage.success('创建成功')
    }
    parseSourceDialogVisible.value = false
    if (currentPlatform.value) {
      await loadParseSources(currentPlatform.value.id)
    }
  } catch (error: any) {
    if (error !== false) {
      ElMessage.error('提交失败')
    }
  } finally {
    parseSourceSubmitting.value = false
  }
}

const handleDeleteParseSource = async (row: ParseSource) => {
  try {
    await ElMessageBox.confirm('确定要删除该解析源吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await request.delete(`/platforms-v2/${row.platform_id}/parse-sources/${row.id}`)
    ElMessage.success('删除成功')
    if (currentPlatform.value) {
      await loadParseSources(currentPlatform.value.id)
    }
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped lang="scss">
.platforms {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .header-actions {
      display: flex;
      gap: 10px;
    }
  }

  .dialog-header-actions {
    display: flex;
    gap: 10px;
    align-items: center;
  }

  .keywords-config {
    .keyword-section {
      margin-bottom: 24px;
      border: 1px solid #EBEEF5;
      border-radius: 8px;
      padding: 15px;

      .section-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;

        .section-title {
          font-size: 14px;
          font-weight: 600;
          color: #303133;
        }

        .keyword-input {
          display: flex;
          gap: 10px;
        }
      }

      .keywords-list {
        min-height: 40px;
      }
    }
  }

  .parse-source-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px;
    border: 1px solid #EBEEF5;
    border-radius: 8px;
    margin-bottom: 8px;

    &:last-child {
      margin-bottom: 0;
    }

    .drag-handle {
      cursor: grab;
      color: #909399;
      display: flex;
      align-items: center;
      padding: 4px;

      &:active {
        cursor: grabbing;
      }
    }

    .parse-source-content {
      flex: 1;
      display: flex;
      flex-direction: column;
      gap: 4px;

      .parse-source-name {
        font-size: 14px;
        font-weight: 500;
        color: #303133;
      }

      .parse-source-url {
        font-size: 12px;
        color: #909399;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }

    .parse-source-actions {
      display: flex;
      align-items: center;
      gap: 8px;
    }
  }
}
</style>
