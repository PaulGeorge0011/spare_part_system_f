<template>
  <div class="oplog-page">
    <h2>记录查询</h2>
    <p class="page-desc">查看系统中对数据执行的关键操作记录（修复件新增/修改/删除、领用、批量导入、用户管理权限变更等）。</p>

    <!-- PC 端：筛选卡片 -->
    <el-card v-if="!isMobile" class="filter-card">
      <div class="filter-row">
        <span class="filter-label">时间范围：</span>
        <el-radio-group v-model="timeRange" @change="onTimeRangeChange">
          <el-radio-button value="today">固定日期</el-radio-button>
          <el-radio-button value="7d">7天内</el-radio-button>
          <el-radio-button value="30d">30天内</el-radio-button>
          <el-radio-button value="6m">半年内</el-radio-button>
          <el-radio-button value="1y">一年内</el-radio-button>
          <el-radio-button value="custom">自定义</el-radio-button>
        </el-radio-group>
      </div>
      <div v-if="timeRange === 'today'" class="filter-row date-row">
        <span class="filter-label">选择日期：</span>
        <el-date-picker v-model="singleDate" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" style="width: 200px" />
      </div>
      <div v-if="timeRange === 'custom'" class="filter-row date-row">
        <span class="filter-label">开始日期：</span>
        <el-date-picker v-model="customStart" type="date" placeholder="开始日期" value-format="YYYY-MM-DD" style="width: 200px" />
        <span class="filter-label" style="margin-left: 16px">结束日期：</span>
        <el-date-picker v-model="customEnd" type="date" placeholder="结束日期" value-format="YYYY-MM-DD" style="width: 200px" />
      </div>
      <div class="filter-row">
        <span class="filter-label">操作人：</span>
        <el-select v-model="username" placeholder="选择操作人" clearable filterable style="width: 160px" @change="onSearch">
          <el-option
            v-for="item in operatorOptions"
            :key="item.username"
            :label="item.display"
            :value="item.username"
          />
          <template #empty>暂无操作人数据</template>
        </el-select>
        <span class="filter-label">模块：</span>
        <el-select v-model="module" placeholder="全部" clearable style="width: 160px">
          <el-option v-for="opt in moduleOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
        </el-select>
        <span class="filter-label">操作类型：</span>
        <el-select v-model="action" placeholder="全部" clearable style="width: 160px">
          <el-option label="创建" value="create" />
          <el-option label="更新" value="update" />
          <el-option label="删除" value="delete" />
          <el-option label="批量新增" value="batch_create" />
          <el-option label="批量删除" value="batch_delete" />
          <el-option label="领用" value="requisition" />
          <el-option label="修改角色" value="update_role" />
          <el-option label="审批通过" value="approve" />
          <el-option label="审批拒绝" value="reject" />
        </el-select>
      </div>
      <div class="filter-row">
        <span class="filter-label">每页条数：</span>
        <el-select v-model="pageSize" placeholder="条数" style="width: 100px" @change="onPageSizeChange">
          <el-option label="20 行" :value="20" />
          <el-option label="50 行" :value="50" />
          <el-option label="100 行" :value="100" />
        </el-select>
        <span class="filter-label">关键字：</span>
        <el-input v-model="keyword" placeholder="搜索摘要..." clearable style="width: 260px" @keyup.enter="fetchLogs" />
        <el-button type="primary" :loading="loading" @click="onSearch">查询</el-button>
        <el-dropdown trigger="click" @command="(cmd: string) => handleExportExcel(cmd as 'selected' | 'current' | 'all')">
          <el-button type="info" :disabled="logs.length === 0 && selectedLogs.length === 0">
            导出 Excel<el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="selected" :disabled="selectedLogs.length === 0">导出选中 ({{ selectedLogs.length }})</el-dropdown-item>
              <el-dropdown-item command="current" :disabled="logs.length === 0">导出当前页 ({{ logs.length }})</el-dropdown-item>
              <el-dropdown-item command="all">全部导出 ({{ totalCount }})</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-dropdown trigger="click" @command="(cmd: string) => handleExportCSV(cmd as 'selected' | 'current' | 'all')">
          <el-button type="info" :disabled="logs.length === 0 && selectedLogs.length === 0">
            导出 CSV<el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="selected" :disabled="selectedLogs.length === 0">导出选中 ({{ selectedLogs.length }})</el-dropdown-item>
              <el-dropdown-item command="current" :disabled="logs.length === 0">导出当前页 ({{ logs.length }})</el-dropdown-item>
              <el-dropdown-item command="all">全部导出 ({{ totalCount }})</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-card>

    <!-- 移动端：顶栏搜索由 App 统一展示，本页只保留抽屉 -->
    <template v-if="isMobile">
      <el-drawer
        v-model="mobileSearchDrawer"
        title="记录查询"
        direction="rtl"
        size="88%"
        :append-to-body="true"
        :close-on-click-modal="true"
        :show-close="true"
        :destroy-on-close="false"
        class="oplog-mobile-search-drawer mobile-search-drawer-unified"
        @close="mobileSearchDrawer = false"
      >
        <div class="mobile-filter-form">
          <div class="filter-group">
            <span class="filter-label">时间范围</span>
            <el-radio-group v-model="timeRange" @change="onTimeRangeChange" style="width: 100%; flex-wrap: wrap">
              <el-radio-button value="today">固定日期</el-radio-button>
              <el-radio-button value="7d">7天内</el-radio-button>
              <el-radio-button value="30d">30天内</el-radio-button>
              <el-radio-button value="6m">半年内</el-radio-button>
              <el-radio-button value="1y">一年内</el-radio-button>
              <el-radio-button value="custom">自定义</el-radio-button>
            </el-radio-group>
          </div>
          <div v-if="timeRange === 'today'" class="filter-group">
            <el-date-picker v-model="singleDate" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" style="width: 100%" />
          </div>
          <div v-if="timeRange === 'custom'" class="filter-group">
            <el-date-picker v-model="customStart" type="date" placeholder="开始日期" value-format="YYYY-MM-DD" style="width: 100%" />
            <el-date-picker v-model="customEnd" type="date" placeholder="结束日期" value-format="YYYY-MM-DD" style="width: 100%" />
          </div>
          <div class="filter-group">
            <span class="filter-label">操作人</span>
            <el-select v-model="username" placeholder="选择操作人" clearable style="width: 100%" @change="fetchLogs">
              <el-option
                v-for="item in operatorOptions"
                :key="item.username"
                :label="item.display"
                :value="item.username"
              />
              <template #empty>暂无操作人数据</template>
            </el-select>
          </div>
          <div class="filter-group">
            <span class="filter-label">模块</span>
            <el-select v-model="module" placeholder="选择模块" clearable style="width: 100%" @change="fetchLogs">
              <el-option v-for="opt in moduleOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
            </el-select>
          </div>
          <div class="filter-group">
            <span class="filter-label">操作类型</span>
            <el-select v-model="action" placeholder="选择操作类型" clearable style="width: 100%" @change="fetchLogs">
              <el-option label="创建" value="create" />
              <el-option label="更新" value="update" />
              <el-option label="删除" value="delete" />
              <el-option label="批量新增" value="batch_create" />
              <el-option label="批量删除" value="batch_delete" />
              <el-option label="领用" value="requisition" />
              <el-option label="修改角色" value="update_role" />
              <el-option label="审批通过" value="approve" />
              <el-option label="审批拒绝" value="reject" />
            </el-select>
          </div>
          <div class="filter-group">
            <span class="filter-label">每页条数</span>
            <el-select v-model="pageSize" placeholder="条数" style="width: 100%" @change="onPageSizeChange">
              <el-option label="20 行" :value="20" />
              <el-option label="50 行" :value="50" />
              <el-option label="100 行" :value="100" />
            </el-select>
          </div>
          <div class="filter-group">
            <span class="filter-label">关键字</span>
            <el-input v-model="keyword" placeholder="搜索摘要" clearable style="width: 100%" @keyup.enter="fetchLogsAndClose" />
          </div>
          <div class="filter-actions">
            <el-button type="primary" :loading="loading" @click="fetchLogsAndClose" block>查询</el-button>
            <el-dropdown trigger="click" @command="(cmd: string) => handleExportExcel(cmd as 'selected' | 'current' | 'all')" style="width: 100%">
              <el-button type="info" :disabled="logs.length === 0 && selectedLogs.length === 0" block>
                导出 Excel<el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="selected" :disabled="selectedLogs.length === 0">导出选中</el-dropdown-item>
                  <el-dropdown-item command="current" :disabled="logs.length === 0">导出当前页</el-dropdown-item>
                  <el-dropdown-item command="all">全部导出</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-dropdown trigger="click" @command="(cmd: string) => handleExportCSV(cmd as 'selected' | 'current' | 'all')" style="width: 100%">
              <el-button type="info" :disabled="logs.length === 0 && selectedLogs.length === 0" block>
                导出 CSV<el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="selected" :disabled="selectedLogs.length === 0">导出选中</el-dropdown-item>
                  <el-dropdown-item command="current" :disabled="logs.length === 0">导出当前页</el-dropdown-item>
                  <el-dropdown-item command="all">全部导出</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </el-drawer>
    </template>

    <el-card class="table-card">
      <!-- 移动端：卡片列表 -->
      <div v-if="isMobile" class="oplog-card-list" v-loading="loading">
        <div v-for="row in logs" :key="row.id" class="oplog-card">
          <div class="oplog-card-header">
            <el-tag size="small">{{ moduleLabel(row.module) }}</el-tag>
            <el-tag size="small" type="info">{{ actionLabel(row.action) }}</el-tag>
            <span class="oplog-card-time">{{ formatDateTime(row.created_at) }}</span>
          </div>
          <div class="oplog-card-row">
            <span class="oplog-label">操作人</span>
            <span class="oplog-value">{{ row.real_name || row.username || '—' }}</span>
          </div>
          <div v-if="row.summary" class="oplog-card-summary">{{ formatSummary(row.summary) }}</div>
        </div>
        <div v-if="!loading && totalCount > 0" class="pagination-row mobile-pagination">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="[20, 50, 100]"
            :total="totalCount"
            layout="total, sizes, prev, pager, next"
            @size-change="onPageSizeChange"
            @current-change="onPageChange"
          />
        </div>
      </div>
      <!-- PC 端：表格 -->
      <div v-else class="table-scroll-wrap">
      <el-table
        v-loading="loading"
        :data="logs"
        border
        stripe
        style="width: 100%"
        max-height="560"
        row-key="id"
        @selection-change="onSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="created_at" label="操作时间" width="180" align="center" sortable>
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="real_name" label="操作人" width="120" align="center" sortable>
          <template #default="{ row }">
            {{ row.real_name || row.username || '—' }}
          </template>
        </el-table-column>
        <el-table-column prop="module" label="模块" width="120" align="center" sortable>
          <template #default="{ row }">
            <el-tag size="small">
              {{ moduleLabel(row.module) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="action" label="操作类型" width="110" align="center" sortable>
          <template #default="{ row }">
            <el-tag size="small" type="info">
              {{ actionLabel(row.action) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="summary" label="摘要" min-width="320" align="left" sortable>
          <template #default="{ row }">
            <div v-if="row.summary" class="summary-cell" :title="row.summary">
              {{ formatSummary(row.summary) }}
            </div>
            <span v-else class="empty-cell">—</span>
          </template>
        </el-table-column>
      </el-table>
      </div>
      <div v-if="!loading && logs.length === 0" class="empty-tip">暂无记录</div>
      <div v-else-if="!loading && totalCount > 0" class="pagination-row">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[20, 50, 100]"
          :total="totalCount"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="onPageSizeChange"
          @current-change="onPageChange"
        />
        <span class="total-tip">共 {{ totalCount }} 条</span>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
// 定义组件名称，用于 keep-alive 缓存
defineOptions({
  name: 'OperationLogs'
})

import { ref, computed, onMounted, onDeactivated, watch, inject } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getOperationLogs, getOperationLogOperatorOptions, type OperationLog, type OperationLogOperatorOption, type TimeRange, type MaterialScope } from '@/api/operationLog'
import { ArrowDown } from '@element-plus/icons-vue'
import { useIsMobile } from '@/composables/useIsMobile'
import { scrollMainToTop } from '@/composables/useScrollMainToTop'
import { formatDateTime } from '@/utils/date'

const route = useRoute()
const materialScope = computed<MaterialScope>(() =>
  route.path.startsWith('/electrical') ? 'electrical' : 'mechanical'
)
const { isMobile } = useIsMobile()
const mobileSearchDrawer = ref(false)
const openMobileSearch = inject<{ value: boolean }>('openMobileSearch')
if (openMobileSearch) {
  watch(() => openMobileSearch.value, (v) => {
    if (v && (route.path === '/electrical/operation-logs' || route.path === '/mechanical/operation-logs')) {
      mobileSearchDrawer.value = true
      openMobileSearch.value = false
    }
  })
}
const operatorOptions = ref<OperationLogOperatorOption[]>([])

const moduleOptions = computed(() =>
  materialScope.value === 'electrical'
    ? [{ label: '修复件管理', value: 'spare_part' }]
    : [{ label: '机械修复件', value: 'mechanical_spare_part' }]
)

async function loadOperatorOptions() {
  try {
    const res = await getOperationLogOperatorOptions(materialScope.value)
    operatorOptions.value = Array.isArray(res) ? res : []
  } catch {
    operatorOptions.value = []
  }
}
import { exportToExcel, exportToCSV, type ExportColumn } from '@/utils/exportExcel'

const timeRange = ref<TimeRange>('30d')
const singleDate = ref<string>('')
const customStart = ref<string>('')
const customEnd = ref<string>('')
const username = ref<string>('')
const module = ref<string>('')
const action = ref<string>('')
const keyword = ref<string>('')
/** 每页条数，默认 20 */
const pageSize = ref(20)
/** 当前页码，从 1 开始 */
const currentPage = ref(1)
/** 符合条件的总条数（由接口返回） */
const totalCount = ref(0)

const loading = ref(false)
const logs = ref<OperationLog[]>([])
const selectedLogs = ref<OperationLog[]>([])
function onSelectionChange(rows: OperationLog[]) {
  selectedLogs.value = rows
}

function formatDate(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function onTimeRangeChange() {
  if (timeRange.value === 'custom' && !customStart.value && !customEnd.value) {
    const d = new Date()
    const s = new Date(d)
    s.setDate(s.getDate() - 30)
    customStart.value = formatDate(s)
    customEnd.value = formatDate(d)
  }
}

function moduleLabel(m: string | null | undefined): string {
  if (!m) return '—'
  if (m === 'spare_part') return '修复件管理'
  if (m === 'mechanical_spare_part') return '机械修复件'
  if (m === 'requisition') return '修复件领用'
  if (m === 'inventory') return '库存管理'
  if (m === 'user') return '用户管理'
  return m
}

function actionLabel(a: string | null | undefined): string {
  if (!a) return '—'
  if (a === 'create') return '创建'
  if (a === 'update') return '更新'
  if (a === 'delete') return '删除'
  if (a === 'batch_create') return '批量新增'
  if (a === 'batch_delete') return '批量删除'
  if (a === 'requisition') return '领用'
  if (a === 'update_role') return '修改角色'
  if (a === 'approve') return '审批通过'
  if (a === 'reject') return '审批拒绝'
  return a
}

/** 将摘要中的分号换行显示，便于阅读变更前/变更后等结构 */
function formatSummary(summary: string | null | undefined): string {
  if (!summary) return ''
  return summary.replace(/；/g, '；\n').trim()
}

// 导出：与表格列严格一致
const OPERATION_LOG_EXPORT_COLUMNS: ExportColumn[] = [
  { key: 'created_at', label: '操作时间', formatter: (r) => formatDateTime(r.created_at) || '—' },
  { key: 'real_name', label: '操作人', formatter: (r) => (r as OperationLog).real_name || (r as OperationLog).username || '—' },
  { key: 'module', label: '模块', formatter: (r) => moduleLabel(r.module) },
  { key: 'action', label: '操作类型', formatter: (r) => actionLabel(r.action) },
  { key: 'summary', label: '摘要', formatter: (r) => r.summary || '—' },
]

type ExportScope = 'selected' | 'current' | 'all'

function getExportAllParams() {
  let start: string | undefined
  let end: string | undefined
  let range: TimeRange = timeRange.value
  if (timeRange.value === 'today' && singleDate.value) {
    start = singleDate.value
    end = singleDate.value
    range = 'custom'
  } else if (timeRange.value === 'custom') {
    start = customStart.value
    end = customEnd.value
  }
  return {
    scope: materialScope.value,
    time_range: range,
    start_date: start,
    end_date: end,
    username: username.value || undefined,
    module: module.value || undefined,
    action: action.value || undefined,
    keyword: keyword.value || undefined,
    limit: 500,
    skip: 0,
  }
}

async function handleExportExcel(scope: ExportScope) {
  let data: OperationLog[] = []
  if (scope === 'all') {
    try {
      const res = await getOperationLogs(getExportAllParams())
      const result = res as { data?: OperationLog[] }
      data = Array.isArray(result?.data) ? result.data : (res as any)?.data ?? []
    } catch (e: any) {
      ElMessage.error(e?.message || '获取数据失败')
      return
    }
  } else {
    data = scope === 'selected' ? selectedLogs.value : logs.value
    if (data.length === 0) {
      ElMessage.warning(scope === 'selected' ? '请先勾选要导出的记录' : '当前页无数据可导出')
      return
    }
  }
  if (data.length === 0) {
    ElMessage.warning('无数据可导出')
    return
  }
  const date = new Date().toISOString().slice(0, 10)
  exportToExcel(data, OPERATION_LOG_EXPORT_COLUMNS, `记录查询_${date}`)
  ElMessage.success(`已导出 ${data.length} 条记录`)
}

async function handleExportCSV(scope: ExportScope) {
  let data: OperationLog[] = []
  if (scope === 'all') {
    try {
      const res = await getOperationLogs(getExportAllParams())
      const result = res as { data?: OperationLog[] }
      data = Array.isArray(result?.data) ? result.data : (res as any)?.data ?? []
    } catch (e: any) {
      ElMessage.error(e?.message || '获取数据失败')
      return
    }
  } else {
    data = scope === 'selected' ? selectedLogs.value : logs.value
    if (data.length === 0) {
      ElMessage.warning(scope === 'selected' ? '请先勾选要导出的记录' : '当前页无数据可导出')
      return
    }
  }
  if (data.length === 0) {
    ElMessage.warning('无数据可导出')
    return
  }
  const date = new Date().toISOString().slice(0, 10)
  exportToCSV(data, OPERATION_LOG_EXPORT_COLUMNS, `记录查询_${date}`)
  ElMessage.success(`已导出 ${data.length} 条记录`)
}

async function fetchLogs() {
  if (timeRange.value === 'custom' && (!customStart.value || !customEnd.value)) {
    ElMessage.warning('请选择自定义的开始和结束日期')
    return
  }
  loading.value = true
  try {
    let start: string | undefined
    let end: string | undefined
    let range: TimeRange = timeRange.value
    if (timeRange.value === 'today' && singleDate.value) {
      start = singleDate.value
      end = singleDate.value
      range = 'custom'
    } else if (timeRange.value === 'custom') {
      start = customStart.value
      end = customEnd.value
    }
    const skip = (currentPage.value - 1) * pageSize.value
    const res = await getOperationLogs({
      scope: materialScope.value,
      time_range: range,
      start_date: start,
      end_date: end,
      username: username.value || undefined,
      module: module.value || undefined,
      action: action.value || undefined,
      keyword: keyword.value || undefined,
      limit: pageSize.value,
      skip,
    })
    const result = res as { data?: OperationLog[]; total?: number }
    logs.value = Array.isArray(result?.data) ? result.data : (res as any)?.data ?? []
    totalCount.value = typeof result?.total === 'number' ? result.total : logs.value.length
  } catch (e: any) {
    ElMessage.error(e?.message || '查询操作记录失败')
    logs.value = []
    totalCount.value = 0
  } finally {
    loading.value = false
  }
}

function onPageSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1
  fetchLogs()
}

function onPageChange(page: number) {
  currentPage.value = page
  fetchLogs()
}

function onSearch() {
  currentPage.value = 1
  fetchLogs()
}

function fetchLogsAndClose() {
  currentPage.value = 1
  fetchLogs()
  mobileSearchDrawer.value = false
  scrollMainToTop()
}

onMounted(() => {
  singleDate.value = formatDate(new Date())
  onTimeRangeChange()
  loadOperatorOptions()
  fetchLogs()
})
onDeactivated(() => {
  mobileSearchDrawer.value = false
})

// 监听系统切换（电气/机械），重新加载数据
watch(materialScope, () => {
  currentPage.value = 1
  loadOperatorOptions()
  fetchLogs()
})
</script>

<style scoped lang="scss">
.oplog-page {
  padding: 0 20px 20px;
}
h2 {
  margin: 0 0 8px;
  font-size: 20px;
  color: #303133;
}
.page-desc {
  margin: 0 0 20px;
  font-size: 14px;
  color: #606266;
}
.filter-card {
  margin-bottom: 20px;
}
.filter-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
  &:last-of-type {
    margin-bottom: 0;
  }
}
.filter-label {
  font-size: 14px;
  color: #606266;
  white-space: nowrap;
}
.date-row {
  margin-left: 0;
}
.table-card {
  position: relative;
}

.table-scroll-wrap {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}
.empty-tip,
.total-tip {
  text-align: center;
  padding: 16px;
  font-size: 14px;
  color: #909399;
}
.total-tip {
  color: #606266;
}
.pagination-row {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 16px;
  padding: 12px 0 8px;
  flex-wrap: wrap;
}
.pagination-row .total-tip {
  padding: 0;
  margin-left: 8px;
}
.pagination-row.mobile-pagination {
  padding: 16px 0;
  justify-content: center;
}
.pagination-row.mobile-pagination :deep(.el-pagination) {
  flex-wrap: wrap;
  justify-content: center;
}
.empty-cell {
  color: #c0c4cc;
  font-size: 14px;
}
.summary-cell {
  font-size: 13px;
  line-height: 1.5;
  color: #303133;
  white-space: pre-wrap;
  word-break: break-word;
  padding: 6px 0;
}

/* 移动端卡片 */
.oplog-card-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.oplog-card {
  padding: 16px;
  background: linear-gradient(to bottom, #ffffff, #fafbff);
  border-radius: 12px;
  border: 1px solid var(--el-border-color-lighter);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
  border-left: 4px solid var(--el-color-info-light-5);
}

.oplog-card-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.oplog-card-time {
  font-size: 12px;
  color: #909399;
  margin-left: auto;
}

.oplog-card-row {
  display: flex;
  margin-bottom: 6px;
  font-size: 14px;
}

.oplog-label {
  flex: 0 0 56px;
  color: #909399;
}

.oplog-value {
  flex: 1;
  min-width: 0;
}

.oplog-card-summary {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed var(--el-border-color-lighter);
  font-size: 13px;
  line-height: 1.5;
  color: #303133;
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 767px) {
  .oplog-page {
    padding: 0 0 16px;
  }
  .oplog-page h2 {
    font-size: 18px;
  }
  .oplog-page .page-desc {
    font-size: 13px;
    margin-bottom: 16px;
  }
  .table-card {
    border-radius: 8px;
    overflow: hidden;
  }

  .mobile-filter-form {
    .filter-row {
      flex-direction: column;
      align-items: stretch;
      margin-bottom: 12px;
    }

    .filter-actions {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-top: 12px;
    }
  }

  .filter-row {
    flex-direction: column;
    align-items: stretch;
  }

  .filter-row .el-radio-group {
    flex-wrap: wrap;
  }

  .filter-row .el-input,
  .filter-row .el-select {
    width: 100% !important;
    max-width: none;
  }
}
</style>

