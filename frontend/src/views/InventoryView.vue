<template>
  <div class="inventory-page">
    <h2>库存管理</h2>
    <p class="page-desc">按时间范围查询库存记录，包括入库/出库时间、事件类型（入库、领用、管理出库等）、操作人等。</p>

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
        <span class="filter-label">事件类型：</span>
        <el-select v-model="filterEventType" placeholder="全部" clearable style="width: 120px" @change="fetchRecords">
          <el-option label="全部" value="" />
          <el-option label="领用" value="领用" />
          <el-option label="归还" value="归还" />
          <el-option label="入库" value="入库" />
          <el-option label="管理出库" value="管理出库" />
        </el-select>
        <span class="filter-label">操作人：</span>
        <el-select v-model="filterRequisitioner" placeholder="选择操作人" clearable filterable style="width: 160px" @change="fetchRecords">
          <el-option v-for="item in operatorOptions" :key="item" :label="item" :value="item" />
          <template #empty>暂无操作人数据</template>
        </el-select>
      </div>
      <div class="filter-row">
        <el-button type="primary" :loading="loading" @click="fetchRecords">查询</el-button>
        <el-dropdown trigger="click" @command="(cmd: string) => handleExportExcel(cmd as 'selected' | 'current' | 'all')">
          <el-button type="info" :disabled="records.length === 0 && selectedRecords.length === 0">
            导出 Excel<el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="selected" :disabled="selectedRecords.length === 0">导出选中 ({{ selectedRecords.length }})</el-dropdown-item>
              <el-dropdown-item command="current" :disabled="displayRecords.length === 0">导出当前页 ({{ displayRecords.length }})</el-dropdown-item>
              <el-dropdown-item command="all" :disabled="records.length === 0">全部导出 ({{ records.length }})</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-dropdown trigger="click" @command="(cmd: string) => handleExportCSV(cmd as 'selected' | 'current' | 'all')">
          <el-button type="info" :disabled="records.length === 0 && selectedRecords.length === 0">
            导出 CSV<el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="selected" :disabled="selectedRecords.length === 0">导出选中 ({{ selectedRecords.length }})</el-dropdown-item>
              <el-dropdown-item command="current" :disabled="displayRecords.length === 0">导出当前页 ({{ displayRecords.length }})</el-dropdown-item>
              <el-dropdown-item command="all" :disabled="records.length === 0">全部导出 ({{ records.length }})</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-card>

    <!-- 移动端：顶栏搜索由 App 统一展示，本页只保留抽屉 -->
    <template v-if="isMobile">
      <el-drawer
        v-model="mobileSearchDrawer"
        title="库存查询"
        direction="rtl"
        size="88%"
        :append-to-body="true"
        :close-on-click-modal="true"
        :show-close="true"
        :destroy-on-close="false"
        class="inventory-mobile-search-drawer mobile-search-drawer-unified"
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
            <span class="filter-label">事件类型</span>
            <el-select v-model="filterEventType" placeholder="选择事件类型" clearable style="width: 100%" @change="fetchRecords">
              <el-option label="全部" value="" />
              <el-option label="领用" value="领用" />
              <el-option label="归还" value="归还" />
              <el-option label="入库" value="入库" />
              <el-option label="管理出库" value="管理出库" />
            </el-select>
          </div>
          <div class="filter-group">
            <span class="filter-label">操作人</span>
            <el-select v-model="filterRequisitioner" placeholder="选择操作人" clearable style="width: 100%" @change="fetchRecords">
              <el-option v-for="item in operatorOptions" :key="item" :label="item" :value="item" />
              <template #empty>暂无操作人数据</template>
            </el-select>
          </div>
          <div class="filter-actions">
            <el-button type="primary" :loading="loading" @click="fetchRecordsAndClose" block>查询</el-button>
            <el-dropdown trigger="click" @command="(cmd: string) => handleExportExcel(cmd as 'selected' | 'current' | 'all')" style="width: 100%">
              <el-button type="info" :disabled="records.length === 0 && selectedRecords.length === 0" block>
                导出 Excel<el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="selected" :disabled="selectedRecords.length === 0">导出选中</el-dropdown-item>
                  <el-dropdown-item command="current" :disabled="displayRecords.length === 0">导出当前页</el-dropdown-item>
                  <el-dropdown-item command="all" :disabled="records.length === 0">全部导出</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
            <el-dropdown trigger="click" @command="(cmd: string) => handleExportCSV(cmd as 'selected' | 'current' | 'all')" style="width: 100%">
              <el-button type="info" :disabled="records.length === 0 && selectedRecords.length === 0" block>
                导出 CSV<el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="selected" :disabled="selectedRecords.length === 0">导出选中</el-dropdown-item>
                  <el-dropdown-item command="current" :disabled="displayRecords.length === 0">导出当前页</el-dropdown-item>
                  <el-dropdown-item command="all" :disabled="records.length === 0">全部导出</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </el-drawer>
    </template>

    <el-card class="table-card">
      <!-- 移动端：卡片列表 -->
      <div v-if="isMobile" class="inv-card-list" v-loading="loading">
        <div v-for="row in displayRecords" :key="row.id" class="inv-card">
          <div class="inv-card-header">
            <el-tag size="small" :type="row.event_type === '领用' ? 'danger' : row.event_type === '归还' ? 'primary' : row.event_type === '入库' ? 'success' : 'warning'">{{ row.event_type }}</el-tag>
            <span class="inv-card-time">{{ formatDateTime(row.inbound_time || row.outbound_time) || '—' }}</span>
          </div>
          <div class="inv-card-row">
            <span class="inv-label">货位号</span>
            <span class="inv-value">{{ row.location_code || '—' }}</span>
          </div>
          <div v-if="row.storage_location" class="inv-card-row inv-card-location">
            <span class="inv-label">存放地</span>
            <span class="inv-value inv-location-value">{{ row.storage_location }}</span>
          </div>
          <div class="inv-card-row">
            <span class="inv-label">MES编码</span>
            <div class="inv-code-cell">
              <el-icon
                v-if="row.mes_material_code"
                class="inv-copy-icon"
                @click.stop="copyToClipboard(row.mes_material_code)"
              >
                <DocumentCopy />
              </el-icon>
              <span class="inv-value inv-code">{{ row.mes_material_code || '—' }}</span>
            </div>
          </div>
          <div class="inv-card-row">
            <span class="inv-label">规格型号</span>
            <div class="inv-code-cell">
              <el-icon
                v-if="row.specification_model"
                class="inv-copy-icon"
                @click.stop="copyToClipboard(row.specification_model)"
              >
                <DocumentCopy />
              </el-icon>
              <span class="inv-value inv-code">{{ row.specification_model || '—' }}</span>
            </div>
          </div>
          <div class="inv-card-row">
            <span class="inv-label">数量</span>
            <span class="inv-value">{{ row.quantity }} {{ row.unit || '个' }}</span>
          </div>
          <div class="inv-card-row">
            <span class="inv-label">库存变化</span>
            <span class="inv-value">{{ row.physical_stock_before ?? '—' }} → {{ row.physical_stock_after ?? '—' }}</span>
          </div>
          <div class="inv-card-row">
            <span class="inv-label">操作人</span>
            <span class="inv-value">{{ row.requisitioner_name || '—' }}</span>
          </div>
          <div class="inv-card-row">
            <span class="inv-label">用户名</span>
            <span class="inv-value">{{ row.operator_name || '—' }}</span>
          </div>
          <div v-if="row.requisition_reason" class="inv-card-row">
            <span class="inv-label">领用原因</span>
            <span class="inv-value">{{ row.requisition_reason }}</span>
          </div>
          <div v-if="row.usage_location" class="inv-card-row">
            <span class="inv-label">使用地点</span>
            <span class="inv-value">{{ row.usage_location }}</span>
          </div>
          <div v-if="row.physical_image_url || row.physical_image_url2" class="inv-card-images">
            <el-image
              v-if="row.physical_image_url"
              :src="getImageUrlForDisplay(row.physical_image_url)"
              style="width: 48px; height: 48px; border-radius: 6px;"
              fit="cover"
              :preview-src-list="[getImageUrlForDisplay(row.physical_image_url)]"
              preview-teleported
            hide-on-click-modal
            />
            <el-image
              v-if="row.physical_image_url2"
              :src="getImageUrlForDisplay(row.physical_image_url2)"
              style="width: 48px; height: 48px; border-radius: 6px;"
              fit="cover"
              :preview-src-list="[getImageUrlForDisplay(row.physical_image_url2)]"
              preview-teleported
            hide-on-click-modal
            />
          </div>
          <div v-if="row.remark" class="inv-card-remark">{{ row.remark }}</div>
        </div>
        <div v-if="!loading && records.length > 0" class="pagination-row mobile-pagination">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :page-sizes="pageSizeOptions"
            :total="records.length"
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
        :data="displayRecords"
        border
        stripe
        style="width: 100%"
        max-height="560"
        row-key="id"
        @selection-change="onInvSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="inbound_time" label="入库时间" width="170" align="center" sortable>
          <template #default="{ row }">
            {{ formatDateTime(row.inbound_time) || '—' }}
          </template>
        </el-table-column>
        <el-table-column prop="outbound_time" label="出库时间" width="170" align="center" sortable>
          <template #default="{ row }">
            {{ formatDateTime(row.outbound_time) || '—' }}
          </template>
        </el-table-column>
        <el-table-column prop="event_type" label="事件类型" width="110" align="center" sortable>
          <template #default="{ row }">
            <el-tag size="small" :type="row.event_type === '领用' ? 'danger' : row.event_type === '归还' ? 'primary' : row.event_type === '入库' ? 'success' : 'warning'">{{ row.event_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="requisitioner_name" label="操作人" width="100" align="center" sortable>
          <template #default="{ row }">
            {{ row.requisitioner_name || '—' }}
          </template>
        </el-table-column>
        <el-table-column prop="operator_name" label="用户名" width="100" align="center" sortable>
          <template #default="{ row }">
            {{ row.operator_name || '—' }}
          </template>
        </el-table-column>
        <el-table-column prop="location_code" label="货位号" width="110" show-overflow-tooltip sortable />
        <el-table-column prop="mes_material_code" label="MES编码" min-width="220" sortable>
          <template #default="{ row }">
            <div class="code-cell">
              <el-icon 
                v-if="row.mes_material_code"
                class="copy-icon"
                @click.stop="copyToClipboard(row.mes_material_code)"
              >
                <DocumentCopy />
              </el-icon>
              <span class="code-value">{{ row.mes_material_code || '—' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="specification_model" label="规格型号" min-width="140" show-overflow-tooltip sortable>
          <template #default="{ row }">
            <div class="code-cell">
              <el-icon 
                v-if="row.specification_model"
                class="copy-icon"
                @click.stop="copyToClipboard(row.specification_model)"
              >
                <DocumentCopy />
              </el-icon>
              <span class="code-value">{{ row.specification_model || '—' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="实物图片1" width="100" align="center">
          <template #default="{ row }">
            <el-image
              v-if="row.physical_image_url"
              :src="getImageUrlForDisplay(row.physical_image_url)"
              style="width: 56px; height: 56px; border-radius: 4px;"
              fit="cover"
              :preview-src-list="[getImageUrlForDisplay(row.physical_image_url)]"
              preview-teleported
            hide-on-click-modal
            />
            <span v-else class="empty-cell">—</span>
          </template>
        </el-table-column>
        <el-table-column label="实物图片2" width="100" align="center">
          <template #default="{ row }">
            <el-image
              v-if="row.physical_image_url2"
              :src="getImageUrlForDisplay(row.physical_image_url2)"
              style="width: 56px; height: 56px; border-radius: 4px;"
              fit="cover"
              :preview-src-list="[getImageUrlForDisplay(row.physical_image_url2)]"
              preview-teleported
            hide-on-click-modal
            />
            <span v-else class="empty-cell">—</span>
          </template>
        </el-table-column>
        <el-table-column prop="quantity" label="数量" width="80" align="center" sortable>
          <template #default="{ row }">
            {{ row.quantity }} {{ row.unit || '个' }}
          </template>
        </el-table-column>
        <el-table-column prop="physical_stock_before" label="库存变化" width="120" align="center" sortable>
          <template #default="{ row }">
            {{ row.physical_stock_before ?? '—' }} → {{ row.physical_stock_after ?? '—' }}
          </template>
        </el-table-column>
        <el-table-column prop="requisition_reason" label="领用原因" min-width="140" show-overflow-tooltip sortable>
          <template #default="{ row }">
            {{ row.requisition_reason || '—' }}
          </template>
        </el-table-column>
        <el-table-column prop="usage_location" label="使用地点" min-width="120" show-overflow-tooltip sortable>
          <template #default="{ row }">
            {{ row.usage_location || '—' }}
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="120" show-overflow-tooltip sortable>
          <template #default="{ row }">
            {{ row.remark || '—' }}
          </template>
        </el-table-column>
      </el-table>
      </div>
      <div v-if="!loading && records.length === 0" class="empty-tip">暂无记录</div>
      <div v-else-if="!loading && records.length > 0" class="pagination-row">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="pageSizeOptions"
          :total="records.length"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="onPageSizeChange"
          @current-change="onPageChange"
        />
        <span class="total-tip">共 {{ records.length }} 条</span>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
// 定义组件名称，用于 keep-alive 缓存
defineOptions({
  name: 'Inventory'
})

import { ref, computed, onMounted, onDeactivated, watch, inject } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { DocumentCopy, ArrowDown } from '@element-plus/icons-vue'
import { getInventoryRecords, getInventoryOperatorOptions, type InventoryRecord, type TimeRange, type MaterialScope } from '@/api/inventory'
import { formatDateTime } from '@/utils/date'
import { exportToExcel, exportToCSV, type ExportColumn } from '@/utils/exportExcel'
import { useIsMobile } from '@/composables/useIsMobile'
import { getImageUrlForDisplay } from '@/utils/image'
import { scrollMainToTop } from '@/composables/useScrollMainToTop'
const route = useRoute()
const materialScope = computed<MaterialScope>(() =>
  route.path.startsWith('/electrical') ? 'electrical' : 'mechanical'
)
const { isMobile } = useIsMobile()
const mobileSearchDrawer = ref(false)
const openMobileSearch = inject<{ value: boolean }>('openMobileSearch')
if (openMobileSearch) {
  watch(() => openMobileSearch.value, (v) => {
    if (v && (route.path === '/electrical/inventory' || route.path === '/mechanical/inventory')) {
      mobileSearchDrawer.value = true
      openMobileSearch.value = false
    }
  })
}

function copyToClipboard(text: string) {
  const t = String(text || '').trim()
  if (!t) return
  navigator.clipboard.writeText(t)
    .then(() => ElMessage.success('已复制到剪贴板'))
    .catch(() => {
      const ta = document.createElement('textarea')
      ta.value = t
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
      ElMessage.success('已复制到剪贴板')
    })
}

const timeRange = ref<TimeRange>('30d')
const singleDate = ref<string>('')
const customStart = ref<string>('')
const customEnd = ref<string>('')
const filterEventType = ref<string>('')
const filterRequisitioner = ref<string>('')
const operatorOptions = ref<string[]>([])
const loading = ref(false)

async function loadOperatorOptions() {
  try {
    const res = await getInventoryOperatorOptions(materialScope.value)
    operatorOptions.value = Array.isArray(res) ? res : []
  } catch {
    operatorOptions.value = []
  }
}
const records = ref<InventoryRecord[]>([])
/** 每页条数选项与默认值 */
const pageSizeOptions = [20, 50, 100]
const pageSize = ref(20)
const currentPage = ref(1)
/** 当前页用于展示的数据（表格/卡片只渲染此切片） */
const displayRecords = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return records.value.slice(start, start + pageSize.value)
})
const selectedRecords = ref<InventoryRecord[]>([])
function onInvSelectionChange(rows: InventoryRecord[]) {
  selectedRecords.value = rows
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

function formatDate(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

async function fetchRecords() {
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
    const res = await getInventoryRecords(
      materialScope.value,
      range,
      start,
      end,
      filterEventType.value || undefined,
      filterRequisitioner.value || undefined
    )
    records.value = Array.isArray(res) ? res : (res as any)?.data ?? []
    currentPage.value = 1
  } catch (e: any) {
    ElMessage.error(e?.message || '查询库存记录失败')
    records.value = []
  } finally {
    loading.value = false
  }
}

function onPageSizeChange(size: number) {
  pageSize.value = size
  currentPage.value = 1
}
function onPageChange(page: number) {
  currentPage.value = page
}

function fetchRecordsAndClose() {
  fetchRecords()
  mobileSearchDrawer.value = false
  scrollMainToTop()
}

// 导出：与表格列严格一致（排除实物图片1、实物图片2）
const INVENTORY_EXPORT_COLUMNS: ExportColumn[] = [
  { key: 'inbound_time', label: '入库时间', formatter: (r) => formatDateTime(r.inbound_time) || '—' },
  { key: 'outbound_time', label: '出库时间', formatter: (r) => formatDateTime(r.outbound_time) || '—' },
  { key: 'event_type', label: '事件类型' },
  { key: 'requisitioner_name', label: '操作人', formatter: (r) => r.requisitioner_name || '—' },
  { key: 'operator_name', label: '用户名', formatter: (r) => r.operator_name || '—' },
  { key: 'location_code', label: '货位号' },
  { key: 'mes_material_code', label: 'MES编码' },
  { key: 'specification_model', label: '规格型号' },
  {
    key: 'quantity',
    label: '数量',
    formatter: (r) => `${r.quantity ?? '—'} ${r.unit || '个'}`.trim(),
  },
  {
    key: 'physical_stock_before',
    label: '库存变化',
    formatter: (r) => `${r.physical_stock_before ?? '—'} → ${r.physical_stock_after ?? '—'}`,
  },
  { key: 'requisition_reason', label: '领用原因', formatter: (r) => r.requisition_reason || '—' },
  { key: 'usage_location', label: '使用地点', formatter: (r) => r.usage_location || '—' },
  { key: 'remark', label: '备注', formatter: (r) => r.remark || '—' },
]

type ExportScope = 'selected' | 'current' | 'all'
function getExportData(scope: ExportScope): InventoryRecord[] {
  if (scope === 'selected') return selectedRecords.value
  if (scope === 'current') return displayRecords.value
  return records.value
}
function handleExportExcel(scope: ExportScope) {
  const data = getExportData(scope)
  if (data.length === 0) {
    ElMessage.warning(scope === 'selected' ? '请先勾选要导出的记录' : '无数据可导出')
    return
  }
  const date = new Date().toISOString().slice(0, 10)
  exportToExcel(data, INVENTORY_EXPORT_COLUMNS, `库存记录_${date}`)
  ElMessage.success(`已导出 ${data.length} 条记录`)
}

function handleExportCSV(scope: ExportScope) {
  const data = getExportData(scope)
  if (data.length === 0) {
    ElMessage.warning(scope === 'selected' ? '请先勾选要导出的记录' : '无数据可导出')
    return
  }
  const date = new Date().toISOString().slice(0, 10)
  exportToCSV(data, INVENTORY_EXPORT_COLUMNS, `库存记录_${date}`)
  ElMessage.success(`已导出 ${data.length} 条记录`)
}

onMounted(() => {
  singleDate.value = formatDate(new Date())
  onTimeRangeChange()
  loadOperatorOptions()
  fetchRecords()
})
onDeactivated(() => {
  mobileSearchDrawer.value = false
})

// 监听系统切换（电气/机械），重新加载数据
watch(materialScope, () => {
  loadOperatorOptions()
  fetchRecords()
})
</script>

<style scoped lang="scss">
.inventory-page {
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
.code-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  .code-value {
    flex: 1;
    min-width: 0;
  }
  .copy-icon {
    flex-shrink: 0;
    cursor: pointer;
    color: #909399;
    font-size: 14px;
    &:hover {
      color: #409eff;
    }
  }
}

/* 移动端卡片 */
.inv-card-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.inv-card {
  padding: 16px;
  background: linear-gradient(to bottom, #ffffff, #fafbff);
  border-radius: 12px;
  border: 1px solid var(--el-border-color-lighter);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
  border-left: 4px solid var(--el-color-info-light-5);
}

.inv-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.inv-card-time {
  font-size: 12px;
  color: #909399;
}

.inv-card-row {
  display: flex;
  margin-bottom: 6px;
  font-size: 14px;
}

.inv-card-location .inv-location-value {
  color: #67c23a;
}

.inv-label {
  flex: 0 0 72px;
  color: #909399;
  font-size: 13px;
}

.inv-value {
  flex: 1;
  min-width: 0;
  word-break: break-all;
}

.inv-code-cell {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  min-width: 0;
}
.inv-code-cell .inv-copy-icon {
  flex-shrink: 0;
  cursor: pointer;
  color: #909399;
  font-size: 14px;
}
.inv-code-cell .inv-copy-icon:hover {
  color: #409eff;
}
.inv-code {
  font-family: 'SF Mono', 'Monaco', 'Courier New', monospace;
  color: #409eff;
}

.inv-card-images {
  display: flex;
  gap: 8px;
  margin-top: 10px;

  :deep(.el-image) {
    border-radius: 6px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }
}

.inv-card-remark {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--el-border-color-lighter);
  font-size: 13px;
  color: #606266;
  line-height: 1.4;
}

@media (max-width: 767px) {
  .inventory-page {
    padding: 0 0 16px;
  }
  .inventory-page h2 {
    font-size: 18px;
  }
  .inventory-page .page-desc {
    font-size: 13px;
    margin-bottom: 16px;
  }
  .table-card {
    border-radius: 8px;
    overflow: hidden;
  }
  .inv-card-list {
    gap: 12px;
  }
  .inv-card {
    padding: 14px;
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

  .filter-row .el-date-picker,
  .filter-row .el-input,
  .filter-row .el-select {
    width: 100% !important;
    max-width: none;
  }
}
</style>
