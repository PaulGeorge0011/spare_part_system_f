<template>
  <div class="mechanical-spare-part-list">
    <div class="header">
      <h2>机械设备管理</h2>
      <div class="header-buttons">
        <template v-if="!isMobile">
          <template v-if="canEdit">
            <el-button
              type="danger"
              :disabled="selectedRows.length === 0"
              :loading="isBatchDeleting"
              @click="handleBatchDelete"
            >
              <el-icon><Delete /></el-icon>批量删除 ({{ selectedRows.length }})
            </el-button>
            <el-button type="success" @click="handleBatchImport">
              <el-icon><Upload /></el-icon>批量新增
            </el-button>
            <el-button type="warning" @click="handleBatchUpdate">
              <el-icon><Edit /></el-icon>批量更新
            </el-button>
            <el-button type="primary" @click="handleCreate">
              <el-icon><Plus /></el-icon>新增机械设备
            </el-button>
          </template>
          <el-dropdown trigger="click" @command="(cmd: string) => handleExportExcel(cmd as 'selected' | 'current' | 'all')">
            <el-button type="info" :loading="exportLoading">
              导出 Excel<el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="selected" :disabled="selectedRows.length === 0">
                  导出选中 ({{ selectedRows.length }})
                </el-dropdown-item>
                <el-dropdown-item command="current" :disabled="list.length === 0">
                  导出当前页 ({{ list.length }})
                </el-dropdown-item>
                <el-dropdown-item command="all">全部导出</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
        <template v-else>
          <el-button v-if="canEdit" type="primary" size="small" @click="handleCreate">
            <el-icon><Plus /></el-icon>新增
          </el-button>
          <el-dropdown trigger="click" :append-to="mobileDropdownAppendTo" @command="handleMobileMenuCommand">
            <el-button type="default" size="small">
              更多<el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <template v-if="canEdit">
                  <el-dropdown-item command="batch-delete" :disabled="selectedRows.length === 0">
                    批量删除 ({{ selectedRows.length }})
                  </el-dropdown-item>
                  <el-dropdown-item command="batch-import">批量新增</el-dropdown-item>
                  <el-dropdown-item command="batch-update">批量更新</el-dropdown-item>
                </template>
                <el-dropdown-item command="export-selected" :disabled="selectedRows.length === 0">导出选中</el-dropdown-item>
                <el-dropdown-item command="export-current" :disabled="list.length === 0">导出当前页</el-dropdown-item>
                <el-dropdown-item command="export-all">全部导出</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
      </div>
    </div>

    <!-- PC 端：搜索 + 筛选 -->
    <div v-if="!isMobile" class="search-and-filter">
      <div class="search-bar">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索货位号、MES编码、规格型号、图号、保管人、物料描述..."
          clearable
          @clear="handleSearch"
          @keyup.enter="handleSearch"
        >
          <template #append>
            <el-button :icon="Search" @click="handleSearch" />
          </template>
        </el-input>
      </div>
      <div class="filter-bar">
        <el-select v-model="filterBrand" placeholder="品牌" clearable filterable style="width: 120px" @change="applyFilters">
          <el-option v-for="item in filterOptions.brands" :key="item" :label="item" :value="item" />
        </el-select>
        <el-select v-model="filterApplicableModel" placeholder="适用机型" clearable filterable style="width: 130px" @change="applyFilters">
          <el-option v-for="item in filterOptions.applicable_models" :key="item" :label="item" :value="item" />
        </el-select>
        <el-select v-model="filterStorageLocation" placeholder="存放地" clearable filterable style="width: 120px" @change="applyFilters">
          <el-option v-for="item in filterOptions.storage_locations" :key="item" :label="item" :value="item" />
        </el-select>
        <el-select v-model="filterLocationPrefix" placeholder="货位号" clearable style="width: 100px" @change="applyFilters">
          <el-option v-for="item in filterOptions.location_prefixes" :key="item" :label="item" :value="item" />
        </el-select>
        <el-button v-if="hasActiveFilters" type="default" @click="clearFilters">清空筛选</el-button>
      </div>
    </div>

    <!-- 移动端：顶栏搜索由 App 统一展示，本页只保留抽屉 -->
    <template v-if="isMobile">
      <el-drawer
        v-model="mobileSearchDrawer"
        title="搜索筛选"
        direction="btt"
        size="78%"
        :append-to-body="true"
        :close-on-click-modal="true"
        :show-close="true"
        :destroy-on-close="false"
        class="mech-list-mobile-search-drawer mobile-search-drawer-unified"
        @close="mobileSearchDrawer = false"
      >
        <div class="mobile-filter-form">
          <div class="filter-group">
            <span class="filter-label">关键词</span>
            <el-input
              v-model="searchKeyword"
              placeholder="货位号、MES编码、规格型号、图号、保管人..."
              clearable
              @clear="handleSearch"
              @keyup.enter="handleSearchAndClose"
            >
              <template #append>
                <el-button :icon="Search" @click="handleSearchAndClose" />
              </template>
            </el-input>
          </div>
          <div class="filter-row-two">
            <div class="filter-group filter-group-half">
              <span class="filter-label">品牌</span>
              <el-select v-model="filterBrand" placeholder="选择品牌" clearable style="width: 100%" @change="applyFilters">
                <el-option v-for="item in filterOptions.brands" :key="item" :label="item" :value="item" />
                <template #empty>暂无数据</template>
              </el-select>
            </div>
            <div class="filter-group filter-group-half">
              <span class="filter-label">适用机型</span>
              <el-select v-model="filterApplicableModel" placeholder="选择适用机型" clearable style="width: 100%" @change="applyFilters">
                <el-option v-for="item in filterOptions.applicable_models" :key="item" :label="item" :value="item" />
                <template #empty>暂无数据</template>
              </el-select>
            </div>
          </div>
          <div class="filter-row-two">
            <div class="filter-group filter-group-half">
              <span class="filter-label">存放地</span>
              <el-select v-model="filterStorageLocation" placeholder="选择存放地" clearable style="width: 100%" @change="applyFilters">
                <el-option v-for="item in filterOptions.storage_locations" :key="item" :label="item" :value="item" />
                <template #empty>暂无数据</template>
              </el-select>
            </div>
            <div class="filter-group filter-group-half">
              <span class="filter-label">货位号前缀</span>
              <el-select v-model="filterLocationPrefix" placeholder="选择货位号前缀" clearable style="width: 100%" @change="applyFilters">
                <el-option v-for="item in filterOptions.location_prefixes" :key="item" :label="item" :value="item" />
                <template #empty>暂无数据</template>
              </el-select>
            </div>
          </div>
          <div class="filter-actions">
            <el-button v-if="hasActiveFilters" type="default" @click="clearFilters">清空</el-button>
            <el-button type="primary" :icon="Search" @click="handleSearchAndClose" style="flex:1">查询</el-button>
          </div>
        </div>
      </el-drawer>
    </template>

    <!-- 方案四：零库存/低库存横幅 + 直接查询 -->
    <div v-if="!loading && (list.length > 0 || total > 0)" class="stock-alert-banner">
      <template v-if="stockAlertFilter">
        <span class="banner-label">当前筛选：</span>
        <span>{{ stockAlertFilter === 'zero' ? '零库存' : '低库存' }} 共 {{ total }} 条</span>
        <el-button type="primary" link size="small" @click="clearStockAlertFilter">清除库存筛选</el-button>
      </template>
      <template v-else>
        <span class="banner-stat">零库存 <strong>{{ zeroCount }}</strong> 条</span>
        <span class="banner-divider">|</span>
        <span class="banner-stat">低库存 <strong>{{ lowCount }}</strong> 条</span>
        <el-button v-if="zeroCount > 0" type="danger" link size="small" @click="setStockAlertFilter('zero')">查看零库存</el-button>
        <el-button v-if="lowCount > 0" type="warning" link size="small" @click="setStockAlertFilter('low')">查看低库存</el-button>
      </template>
    </div>

    <!-- 移动端：卡片列表 -->
    <div v-if="isMobile" class="card-list-wrap">
      <div class="card-list" v-loading="loading && !loadingMore">
        <div
          v-for="row in list"
          :key="row.id"
          class="mech-card"
          :class="[{ 'card-selected': selectedRows.some(r => r.id === row.id) }, getReqCardStockClass(row)]"
          @click="toggleCardSelection(row)"
        >
          <div class="card-main">
            <el-checkbox
              :model-value="selectedRows.some(r => r.id === row.id)"
              @click.stop
              @update:model-value="(v: boolean) => v ? addSelection(row) : removeSelection(row)"
            />
            <div class="card-content">
              <div class="card-field-row">
                <span class="card-field-label">货位号</span>
                <el-tag type="info" size="small" class="location-tag">{{ row.location_code }}</el-tag>
              </div>
              <div class="card-field-row">
                <span class="card-field-label">MES编码</span>
                <span class="card-code">{{ row.mes_material_code || '—' }}</span>
              </div>
              <div v-if="row.specification_model" class="card-field-row">
                <span class="card-field-label">规格型号</span>
                <span class="card-spec">{{ row.specification_model }}</span>
              </div>
              <div class="card-field-row">
                <span class="card-field-label">物料描述</span>
                <span class="card-desc">{{ row.mes_material_desc || row.physical_material_desc || '—' }}</span>
              </div>
              <div v-if="row.storage_location || row.custodian" class="card-field-row">
                <span class="card-field-label">存放地</span>
                <div class="card-location">
                  <el-icon v-if="row.storage_location" class="location-icon"><Location /></el-icon>
                  <span>{{ row.storage_location || '' }}</span>
                  <span v-if="row.custodian" class="card-custodian">保管人：{{ row.custodian }}</span>
                </div>
              </div>
              <div v-if="row.drawing_no" class="card-field-row">
                <span class="card-field-label">图号</span>
                <span class="card-drawing">{{ row.drawing_no }}</span>
              </div>
              <div v-if="row.brand" class="card-field-row">
                <span class="card-field-label">品牌</span>
                <el-tag type="primary" size="small">{{ row.brand }}</el-tag>
              </div>
              <div v-if="row.applicable_model" class="card-field-row">
                <span class="card-field-label">适用机型</span>
                <el-tag type="warning" size="small">{{ formatApplicableModel(row.applicable_model) }}</el-tag>
              </div>
              <div class="card-field-row">
                <span class="card-field-label">库存</span>
                <div class="card-stock">
                  <el-tag :type="getStockType(row.mes_stock ?? 0, row.physical_stock ?? 0)" size="small">MES: {{ row.mes_stock ?? 0 }}</el-tag>
                  <el-tag :type="getStockType(row.physical_stock ?? 0, row.mes_stock ?? 0)" size="small" class="card-stock-tag">修附件: {{ row.physical_stock ?? 0 }}</el-tag>
                  <span class="unit-text">{{ row.unit || '个' }}</span>
                </div>
              </div>
              <div v-if="row.physical_image_url || row.physical_image_url2" class="card-field-row">
                <span class="card-field-label">图片</span>
                <div class="card-images">
                  <el-image
                    v-if="row.physical_image_url"
                    style="width: 36px; height: 36px; border-radius: 4px;"
                    :src="getImageUrlForDisplay(row.physical_image_url)"
                    :preview-src-list="[getImageUrlForDisplay(row.physical_image_url)]"
                    fit="cover"
                    preview-teleported
                  hide-on-click-modal
                  />
                  <el-image
                    v-if="row.physical_image_url2"
                    style="width: 36px; height: 36px; border-radius: 4px;"
                    :src="getImageUrlForDisplay(row.physical_image_url2)"
                    :preview-src-list="[getImageUrlForDisplay(row.physical_image_url2)]"
                    fit="cover"
                    preview-teleported
                  hide-on-click-modal
                  />
                </div>
              </div>
            </div>
          </div>
          <div v-if="canEdit" class="card-actions">
            <el-button size="small" type="primary" :icon="Edit" link @click.stop="handleEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" :icon="Delete" link @click.stop="handleDelete(row)">删除</el-button>
          </div>
        </div>
      </div>
      <div v-if="isMobile && list.length > 0" ref="loadMoreSentinel" class="load-more-sentinel">
        <div v-if="loadingMore" class="load-more-loading">加载中...</div>
        <div v-else-if="listHasMore" class="load-more-hint">下滑加载更多</div>
        <div v-else class="load-more-end">— 没有更多了 —</div>
      </div>
    </div>

    <!-- PC 端：表格 -->
    <div v-else class="table-wrapper">
      <el-table
        ref="tableRef"
        v-loading="loading"
        :data="list"
        border
        stripe
        style="width: 100%"
        row-key="id"
        highlight-current-row
        :row-class-name="getRequisitionRowClass"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" fixed="left" />
        <el-table-column prop="location_code" label="货位号" width="100" fixed="left">
          <template #default="{ row }">
            <el-tag type="info">{{ row.location_code }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="mes_material_code" label="MES编码" min-width="220" fixed="left">
          <template #default="{ row }">
            <div class="code-cell">
              <el-icon v-if="row.mes_material_code" class="copy-icon" @click="copyToClipboard(row.mes_material_code)">
                <DocumentCopy />
              </el-icon>
              <span class="code-value">{{ row.mes_material_code || '—' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="specification_model" label="规格型号" width="150" fixed="left" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="code-cell">
              <el-icon v-if="row.specification_model" class="copy-icon" @click.stop="copyToClipboard(row.specification_model)">
                <DocumentCopy />
              </el-icon>
              <span class="code-value">{{ row.specification_model || '—' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="drawing_no" label="图号" width="100" show-overflow-tooltip />
        <el-table-column label="物料描述" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            {{ row.mes_material_desc || row.physical_material_desc || '—' }}
          </template>
        </el-table-column>
        <el-table-column prop="applicable_model" label="适用机型" width="120" show-overflow-tooltip>
          <template #default="{ row }">
            <el-tag v-if="row.applicable_model" type="warning" size="small">{{ formatApplicableModel(row.applicable_model) }}</el-tag>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column prop="brand" label="品牌" width="100" show-overflow-tooltip>
          <template #default="{ row }">
            <el-tag v-if="row.brand" type="primary" size="small">{{ row.brand }}</el-tag>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column prop="mes_stock" label="MES库存" width="100">
          <template #default="{ row }">
            <div class="stock-cell">
              <el-tag :type="getStockType(row.mes_stock ?? 0, row.physical_stock ?? 0)" size="small">
                {{ row.mes_stock ?? 0 }}
              </el-tag>
              <span class="unit-text">{{ row.unit || '个' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="physical_stock" label="修附件库存" width="110">
          <template #default="{ row }">
            <div class="stock-cell">
              <el-tag :type="getStockType(row.physical_stock ?? 0, row.mes_stock ?? 0)" size="small">
                {{ row.physical_stock ?? 0 }}
              </el-tag>
              <span class="unit-text">{{ row.unit || '个' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="storage_location" label="存放地" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">
            <el-tag v-if="row.storage_location" type="success" size="small">{{ row.storage_location }}</el-tag>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column prop="custodian" label="保管人" width="90" show-overflow-tooltip>
          <template #default="{ row }">{{ row.custodian || '—' }}</template>
        </el-table-column>
        <el-table-column label="实物图片1" width="100" align="center">
          <template #default="{ row }">
            <div v-if="row.physical_image_url" class="image-cell">
              <el-image
                style="width: 40px; height: 40px; border-radius: 4px;"
                :src="getImageUrlForDisplay(row.physical_image_url)"
                :preview-src-list="[getImageUrlForDisplay(row.physical_image_url)]"
                fit="cover"
                preview-teleported
              hide-on-click-modal
              />
            </div>
            <span v-else class="empty-text">无</span>
          </template>
        </el-table-column>
        <el-table-column label="实物图片2" width="100" align="center">
          <template #default="{ row }">
            <div v-if="row.physical_image_url2" class="image-cell">
              <el-image
                style="width: 40px; height: 40px; border-radius: 4px;"
                :src="getImageUrlForDisplay(row.physical_image_url2)"
                :preview-src-list="[getImageUrlForDisplay(row.physical_image_url2)]"
                fit="cover"
                preview-teleported
              hide-on-click-modal
              />
            </div>
            <span v-else class="empty-text">无</span>
          </template>
        </el-table-column>
        <el-table-column prop="disposal_method" label="处置方式" width="100" show-overflow-tooltip>
          <template #default="{ row }">{{ row.disposal_method || '—' }}</template>
        </el-table-column>
        <el-table-column prop="source_description" label="来源说明" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.source_description || '—' }}</template>
        </el-table-column>
        <el-table-column prop="technical_appraisal" label="技术鉴定" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.technical_appraisal || '—' }}</template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="160">
          <template #default="{ row }">
            <span v-if="row.updated_at" class="time-text">{{ formatDateTime(row.updated_at) }}</span>
            <span v-else class="empty-text">—</span>
          </template>
        </el-table-column>
        <el-table-column v-if="canEdit" label="操作" width="180" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-button 
                size="small" 
                type="primary" 
                @click="handleEdit(row)"
                :icon="Edit"
                plain
              >
                编辑
              </el-button>
              <el-button 
                size="small" 
                type="danger" 
                @click="handleDelete(row)"
                :icon="Delete"
                plain
              >
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div v-if="!isMobile" class="pagination-wrap">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        layout="total, sizes, prev, pager, next"
        @size-change="loadData"
        @current-change="loadData"
      />
    </div>
    <div v-if="isMobile && !loading && list.length > 0" class="mobile-total-tip">共 {{ total }} 条</div>

    <MechanicalSparePartFormDialog
      v-model="dialogVisible"
      :form-data="currentForm"
      :mode="dialogMode"
      @success="handleDialogSuccess"
    />

    <!-- 批量导入对话框 -->
    <MechanicalBatchImportDialog
      v-model="batchImportDialogVisible"
      @success="handleBatchImportSuccess"
    />
    <!-- 批量更新 MES 库存对话框 -->
    <BatchUpdateDialog
      v-model="batchUpdateDialogVisible"
      type="mechanical"
      @success="handleBatchUpdateSuccess"
    />
  </div>
</template>

<script setup lang="ts">
// 定义组件名称，用于 keep-alive 缓存
defineOptions({
  name: 'MechanicalSparePartList'
})

import { ref, computed, onMounted, onActivated, onDeactivated, onUnmounted, watch, nextTick, inject } from 'vue'
import { useRoute } from 'vue-router'
import { Search, Plus, DocumentCopy, Edit, Delete, Location, Upload, ArrowDown } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import MechanicalSparePartFormDialog from '@/components/MechanicalSparePartFormDialog.vue'
import MechanicalBatchImportDialog from '@/components/MechanicalBatchImportDialog.vue'
import BatchUpdateDialog from '@/components/BatchUpdateDialog.vue'
import { mechanicalSparePartApi } from '@/api/mechanicalSparePart'
import type { MechanicalSparePart } from '@/types/mechanicalSparePart'
import type { MechanicalSparePartFilterOptions } from '@/types/mechanicalSparePart'
import { useIsMobile } from '@/composables/useIsMobile'
import { scrollMainToTop } from '@/composables/useScrollMainToTop'
import { useDataRefresh } from '@/composables/useDataRefresh'
import { useMechanicalSparePartDataChanged, broadcastMechanicalSparePartDataChanged } from '@/composables/useMechanicalSparePartDataChanged'
import { getImageUrlForDisplay } from '@/utils/image'
import { formatDateTime } from '@/utils/date'
import { navLog, navLogStart } from '@/utils/navLog'
import { exportToExcel, type ExportColumn } from '@/utils/exportExcel'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const canEdit = computed(() => authStore.canAccessModule('mechanical', 'editor'))

const route = useRoute()
const { isMobile } = useIsMobile()
// iframe 移动端：将「更多」下拉挂到 #iframe-mobile-scaler 内，避免 zoom 导致下拉与按钮错位
const mobileDropdownAppendTo = ref<string | undefined>(undefined)
useDataRefresh(loadData)
useMechanicalSparePartDataChanged(loadData)
const searchKeyword = ref('')
const filterBrand = ref('')
const filterApplicableModel = ref('')
const filterStorageLocation = ref('')
const filterLocationPrefix = ref('')
const filterOptions = ref<MechanicalSparePartFilterOptions>({
  brands: [],
  applicable_models: [],
  storage_locations: [],
  location_prefixes: [],
})
const hasActiveFilters = computed(() =>
  !!(filterBrand.value || filterApplicableModel.value || filterStorageLocation.value || filterLocationPrefix.value)
)
const mobileSearchDrawer = ref(false)
const openMobileSearch = inject<{ value: boolean }>('openMobileSearch')
if (openMobileSearch) {
  watch(() => openMobileSearch.value, (v) => {
    if (v && route.path === '/mechanical/parts') {
      mobileSearchDrawer.value = true
      openMobileSearch.value = false
    }
  })
}

const currentPage = ref(1)
const pageSize = ref(20)
const list = ref<MechanicalSparePart[]>([])
const total = ref(0)
const loading = ref(false)
const loadingMore = ref(false)
const loadMoreSentinel = ref<HTMLElement | null>(null)
const listHasMore = computed(
  () => list.value.length < total.value && !loadingMore.value && !loading.value
)
const stockAlertFilter = ref<'zero' | 'low' | ''>('')
const zeroCount = ref(0)
const lowCount = ref(0)
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const currentForm = ref<Partial<MechanicalSparePart>>({})
const batchImportDialogVisible = ref(false)
const batchUpdateDialogVisible = ref(false)
const selectedRows = ref<MechanicalSparePart[]>([])
const isBatchDeleting = ref(false)
const exportLoading = ref(false)
const tableRef = ref()

const skip = computed(() => (currentPage.value - 1) * pageSize.value)

async function loadFilterOptions() {
  try {
    const res = await mechanicalSparePartApi.getFilterOptions()
    if (res?.brands) filterOptions.value.brands = res.brands
    if (res?.applicable_models) filterOptions.value.applicable_models = res.applicable_models
    if (res?.storage_locations) filterOptions.value.storage_locations = res.storage_locations
    if (res?.location_prefixes) filterOptions.value.location_prefixes = res.location_prefixes
  } catch {
    // ignore
  }
}

function formatApplicableModel(v: string | null | undefined): string {
  if (!v) return '—'
  const s = String(v).trim()
  return s.length > 20 ? s.slice(0, 20) + '…' : s
}

function copyToClipboard(text: string) {
  const t = String(text || '').trim()
  if (!t) return
  navigator.clipboard.writeText(t).then(() => ElMessage.success('已复制')).catch(() => {})
}

// 与电气一致：MES/修附件库存标签颜色（零库存 danger，低库存 warning，正常 success；与对比库存差异大时 danger/warning）
function getStockType(current: number, compare: number): 'success' | 'warning' | 'danger' | 'info' {
  if (current !== 0 && !current) return 'info'
  if (compare !== undefined && compare !== null) {
    const diff = Math.abs(current - compare)
    if (diff > 10) return 'danger'
    if (diff > 5) return 'warning'
  }
  if (current === 0) return 'danger'
  if (current < 10) return 'warning'
  return 'success'
}

function totalStock(row: MechanicalSparePart): number {
  return (row.mes_stock ?? 0) + (row.physical_stock ?? 0)
}
function getRequisitionRowClass({ row }: { row: MechanicalSparePart }) {
  const t = totalStock(row)
  if (t === 0) return 'req-row-zero'
  if (t === 1) return 'req-row-low'
  return ''
}
function getReqCardStockClass(row: MechanicalSparePart): string {
  const t = totalStock(row)
  if (t === 0) return 'req-card-zero'
  if (t === 1) return 'req-card-low'
  return ''
}
function setStockAlertFilter(value: 'zero' | 'low') {
  stockAlertFilter.value = value
  currentPage.value = 1
  loadData()
}
function clearStockAlertFilter() {
  stockAlertFilter.value = ''
  currentPage.value = 1
  loadData()
}

async function loadData(append = false) {
  const t = navLogStart()
  navLog('MechanicalSparePartList loadData start', { append })
  if (append) {
    loadingMore.value = true
  } else {
    loading.value = true
  }
  try {
    const skipVal = append ? list.value.length : skip.value
    const res = await mechanicalSparePartApi.getList({
      skip: skipVal,
      limit: pageSize.value,
      keyword: searchKeyword.value || undefined,
      brand: filterBrand.value || undefined,
      applicable_model: filterApplicableModel.value || undefined,
      storage_location: filterStorageLocation.value || undefined,
      location_prefix: filterLocationPrefix.value || undefined,
      stock_alert: stockAlertFilter.value || undefined,
    }) as { items?: MechanicalSparePart[]; total?: number; zero_count?: number; low_count?: number }
    const newItems = res?.items ?? []
    const totalCount = res?.total ?? 0
    if (typeof res?.zero_count === 'number') zeroCount.value = res.zero_count
    if (typeof res?.low_count === 'number') lowCount.value = res.low_count
    if (append && newItems.length > 0) {
      const ids = new Set(list.value.map((i) => i.id))
      const toAdd = newItems.filter((i) => !ids.has(i.id))
      list.value = [...list.value, ...toAdd]
    } else {
      list.value = newItems
    }
    total.value = totalCount
  } catch {
    ElMessage.error('加载数据失败')
    if (!append) {
      list.value = []
      total.value = 0
    }
  } finally {
    loading.value = false
    loadingMore.value = false
    navLog('MechanicalSparePartList loadData end', { append }, t)
  }
}

function loadMore() {
  if (!listHasMore.value || loadingMore.value) return
  loadData(true)
}

function handleSearch() {
  currentPage.value = 1
  loadData()
}

function handleSearchAndClose() {
  handleSearch()
  mobileSearchDrawer.value = false
  scrollMainToTop()
}

function applyFilters() {
  currentPage.value = 1
  loadData()
}

function clearFilters() {
  searchKeyword.value = ''
  filterBrand.value = ''
  filterApplicableModel.value = ''
  filterStorageLocation.value = ''
  filterLocationPrefix.value = ''
  stockAlertFilter.value = ''
  zeroCount.value = 0
  lowCount.value = 0
  currentPage.value = 1
  loadData()
  mobileSearchDrawer.value = false
}

function handleCreate() {
  currentForm.value = { mes_stock: 0, physical_stock: 0, unit: '个' }
  dialogMode.value = 'create'
  dialogVisible.value = true
}

function handleEdit(row: MechanicalSparePart) {
  currentForm.value = { ...row }
  dialogMode.value = 'edit'
  dialogVisible.value = true
}

function handleSelectionChange(rows: MechanicalSparePart[]) {
  selectedRows.value = rows
}

function toggleCardSelection(row: MechanicalSparePart) {
  const idx = selectedRows.value.findIndex((r) => r.id === row.id)
  if (idx >= 0) {
    selectedRows.value = selectedRows.value.filter((r) => r.id !== row.id)
  } else {
    selectedRows.value = [...selectedRows.value, row]
  }
}

function addSelection(row: MechanicalSparePart) {
  if (!selectedRows.value.some((r) => r.id === row.id)) {
    selectedRows.value = [...selectedRows.value, row]
  }
}

function removeSelection(row: MechanicalSparePart) {
  selectedRows.value = selectedRows.value.filter((r) => r.id !== row.id)
}

async function handleBatchDelete() {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请先选择要删除的机械设备')
    return
  }
  try {
    const count = selectedRows.value.length
    const ids = selectedRows.value.map((row) => row.id)
    const mesCodes = selectedRows.value.map((row) => row.mes_material_code || row.location_code).join('、')
    await ElMessageBox.confirm(
      `确定删除选中的 ${count} 个机械设备吗？\n涉及：${mesCodes.substring(0, 100)}${mesCodes.length > 100 ? '...' : ''}\n此操作不可恢复。`,
      '确认批量删除',
      {
        type: 'warning',
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        confirmButtonClass: 'el-button--danger',
      }
    )
    isBatchDeleting.value = true
    try {
      const result = await mechanicalSparePartApi.batchDelete(ids)
      const { deleted, failed, errors } = result
      if (failed === 0) {
        ElMessage.success(`成功删除 ${deleted} 个机械设备`)
      } else {
        ElMessage.warning(`删除完成：成功 ${deleted} 个，失败 ${failed} 个`)
        if (errors?.length) console.error('批量删除错误:', errors)
      }
      tableRef.value?.clearSelection()
      selectedRows.value = []
      loadData()
      broadcastMechanicalSparePartDataChanged()
    } finally {
      isBatchDeleting.value = false
    }
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('批量删除失败')
      console.error('批量删除失败:', e)
    }
  }
}

async function handleDelete(row: MechanicalSparePart) {
  try {
    await ElMessageBox.confirm(
      `确定删除机械设备 "${row.mes_material_code || row.location_code}" 吗？此操作不可恢复。`,
      '确认删除',
      { type: 'warning', confirmButtonText: '确定', cancelButtonText: '取消' }
    )
    await mechanicalSparePartApi.delete(row.id)
    ElMessage.success('删除成功')
    loadData()
    broadcastMechanicalSparePartDataChanged()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

function handleDialogSuccess() {
  dialogVisible.value = false
  loadData()
  broadcastMechanicalSparePartDataChanged()
}

// 批量新增相关
function handleBatchImport() {
  batchImportDialogVisible.value = true
}

function handleBatchImportSuccess() {
  loadData()
  broadcastMechanicalSparePartDataChanged()
}

function handleBatchUpdate() {
  batchUpdateDialogVisible.value = true
}

function handleBatchUpdateSuccess() {
  loadData()
  broadcastMechanicalSparePartDataChanged()
}

// 导出 Excel：与表格列严格一致（排除实物图片1、实物图片2、操作）
const MECHANICAL_EXPORT_COLUMNS: ExportColumn[] = [
  { key: 'location_code', label: '货位号' },
  { key: 'mes_material_code', label: 'MES编码' },
  { key: 'specification_model', label: '规格型号' },
  { key: 'drawing_no', label: '图号' },
  {
    key: 'mes_material_desc',
    label: '物料描述',
    formatter: (r) => (r as MechanicalSparePart).mes_material_desc || (r as MechanicalSparePart).physical_material_desc || '—',
  },
  { key: 'applicable_model', label: '适用机型', formatter: (r) => formatApplicableModel((r as MechanicalSparePart).applicable_model) || '—' },
  { key: 'brand', label: '品牌' },
  { key: 'mes_stock', label: 'MES库存' },
  { key: 'physical_stock', label: '修附件库存' },
  { key: 'storage_location', label: '存放地' },
  { key: 'custodian', label: '保管人' },
  { key: 'disposal_method', label: '处置方式' },
  { key: 'source_description', label: '来源说明' },
  { key: 'technical_appraisal', label: '技术鉴定' },
  { key: 'updated_at', label: '更新时间', formatter: (r) => formatDateTime((r as MechanicalSparePart).updated_at) || '—' },
]
type ExportScope = 'selected' | 'current' | 'all'
async function handleExportExcel(scope: ExportScope) {
  exportLoading.value = true
  try {
    let items: MechanicalSparePart[] = []
    if (scope === 'selected') {
      items = selectedRows.value
      if (items.length === 0) {
        ElMessage.warning('请先勾选要导出的记录')
        return
      }
    } else if (scope === 'current') {
      items = [...list.value]
      if (items.length === 0) {
        ElMessage.warning('当前页无数据可导出')
        return
      }
    } else {
      const res = (await mechanicalSparePartApi.getList({
        skip: 0,
        limit: 1000,
        keyword: searchKeyword.value || undefined,
        brand: filterBrand.value || undefined,
        applicable_model: filterApplicableModel.value || undefined,
        storage_location: filterStorageLocation.value || undefined,
        location_prefix: filterLocationPrefix.value || undefined,
        stock_alert: stockAlertFilter.value || undefined,
      })) as { items?: MechanicalSparePart[] }
      items = res?.items ?? []
      if (items.length === 0) {
        ElMessage.warning('当前筛选条件下无数据可导出')
        return
      }
    }
    const date = new Date().toISOString().slice(0, 10)
    exportToExcel(items, MECHANICAL_EXPORT_COLUMNS, `机械修复件列表_${date}`)
    ElMessage.success(`已导出 ${items.length} 条记录`)
  } catch (e: any) {
    ElMessage.error(e?.message || '导出失败')
  } finally {
    exportLoading.value = false
  }
}

// 移动端菜单命令
function handleMobileMenuCommand(command: string) {
  if (command === 'batch-delete') handleBatchDelete()
  else if (command === 'batch-import') handleBatchImport()
  else if (command === 'batch-update') handleBatchUpdate()
  else if (command === 'export-selected') handleExportExcel('selected')
  else if (command === 'export-current') handleExportExcel('current')
  else if (command === 'export-all') handleExportExcel('all')
}

function scheduleAfterPaint(fn: () => void) {
  if (typeof requestIdleCallback !== 'undefined') requestIdleCallback(fn, { timeout: 120 })
  else setTimeout(fn, 0)
}
onMounted(() => {
  navLog('MechanicalSparePartList mounted', {})
  if (typeof document !== 'undefined' && document.documentElement.classList.contains('iframe-mobile-viewport')) {
    mobileDropdownAppendTo.value = '#iframe-mobile-scaler'
  }
  scheduleAfterPaint(() => {
    navLog('MechanicalSparePartList scheduleAfterPaint running', {})
    loadFilterOptions()
    loadData()
  })
})
onActivated(() => {
  navLog('MechanicalSparePartList activated', {})
})
onDeactivated(() => {
  mobileSearchDrawer.value = false
})

// 移动端：IntersectionObserver 监听滚动加载更多（与机械领用页一致）
let observer: IntersectionObserver | null = null
function setupLoadMoreObserver() {
  if (!isMobile.value || !loadMoreSentinel.value) return
  observer?.disconnect()
  observer = new IntersectionObserver(
    (entries) => {
      const e = entries[0]
      if (e?.isIntersecting && listHasMore.value) loadMore()
    },
    { root: null, rootMargin: '100px', threshold: 0.1 }
  )
  observer.observe(loadMoreSentinel.value)
}
watch(
  [loadMoreSentinel, () => list.value.length],
  () => {
    if (isMobile.value && list.value.length > 0) {
      nextTick(setupLoadMoreObserver)
    }
  },
  { immediate: true }
)
onUnmounted(() => {
  observer?.disconnect()
})
</script>

<style scoped>
.mechanical-spare-part-list {
  padding: 20px;
  background: #f5f7fa;
  min-height: calc(100vh - 60px);
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}
.header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

@media (max-width: 767px) {
  .mechanical-spare-part-list {
    padding: 0 0 16px;
  }
  .header {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
    margin-bottom: 16px;
  }
  .header h2 {
    font-size: 18px;
  }
  .search-and-filter {
    margin-bottom: 12px;
  }
  .card-list {
    gap: 14px;
  }
  .mech-card {
    padding: 14px 16px;
  }
  .pagination-wrap {
    margin-top: 12px;
  }
}
.search-and-filter {
  margin-bottom: 16px;
}
.search-bar {
  margin-bottom: 12px;
}
.search-bar :deep(.el-input-group__append) {
  padding: 0 8px;
}
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}
.pagination-wrap {
  margin-top: 16px;
}

.stock-alert-banner {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px 12px;
  padding: 10px 14px;
  margin-bottom: 12px;
  background: linear-gradient(to right, #fef3c7 0%, #fef9c3 100%);
  border: 1px solid #fcd34d;
  border-radius: 8px;
  font-size: 14px;
  color: #92400e;
}
.stock-alert-banner .banner-label { font-weight: 500; }
.stock-alert-banner .banner-stat strong { margin: 0 2px; }
.stock-alert-banner .banner-divider { color: #d97706; margin: 0 4px; }

.table-wrapper :deep(.el-table tr.req-row-zero) {
  background-color: #fef2f2 !important;
}
.table-wrapper :deep(.el-table tr.req-row-zero:hover > td) {
  background-color: #fee2e2 !important;
}
.table-wrapper :deep(.el-table tr.req-row-low) {
  background-color: #fffbeb !important;
}
.table-wrapper :deep(.el-table tr.req-row-low:hover > td) {
  background-color: #fef3c7 !important;
}

.mech-card.req-card-zero {
  border-left: 4px solid var(--el-color-danger);
  background: linear-gradient(to bottom, #fef2f2, #fee2e2) !important;
}
.mech-card.req-card-low {
  border-left: 4px solid var(--el-color-warning);
  background: linear-gradient(to bottom, #fffbeb, #fef3c7) !important;
}

.table-wrapper {
  overflow-x: auto;
}
.code-cell {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.code-cell .code-value {
  font-family: 'Courier New', monospace;
  font-weight: bold;
  color: #409eff;
}
.copy-icon {
  margin-left: 8px;
  cursor: pointer;
  color: #909399;
  transition: color 0.3s;
  flex-shrink: 0;
}
.copy-icon:hover {
  color: #409eff;
}
.action-buttons {
  display: flex;
  gap: 8px;
  justify-content: center;
}
.unit-text {
  margin-left: 4px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}
.stock-cell {
  display: flex;
  align-items: center;
  gap: 4px;
}
.card-stock .card-stock-tag {
  margin-left: 6px;
}

/* 移动端卡片 */
.card-list-wrap {
  margin-bottom: 16px;
}
.card-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.mech-card {
  background: linear-gradient(to bottom, #ffffff, #fafbff);
  border-radius: 12px;
  padding: 14px 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
  border: 1px solid var(--el-border-color-lighter);
  border-left: 4px solid var(--el-color-primary-light-5);
  transition: box-shadow 0.2s ease, transform 0.2s ease;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  tap-highlight-color: transparent;
  touch-action: manipulation;
  user-select: none;
}
.mech-card:active {
  transform: scale(0.99);
}
/* 与电气一致：去掉子元素点击时的蓝罩，避免短暂遮罩影响观感 */
.mech-card :deep(.el-checkbox),
.mech-card :deep(.el-checkbox__inner),
.mech-card :deep(.el-tag),
.mech-card :deep(.el-icon) {
  -webkit-tap-highlight-color: transparent;
  tap-highlight-color: transparent;
}
.mech-card.card-selected {
  border-left-color: var(--el-color-primary);
  background: linear-gradient(to bottom, var(--el-color-primary-light-9), #fff);
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.15);
}
.card-main {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.card-main .el-checkbox {
  flex-shrink: 0;
  margin-top: 2px;
}
/* 字段标签行样式 */
.card-field-row {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-bottom: 4px;
}
.card-field-label {
  flex: 0 0 56px;
  font-size: 11px;
  color: #94a3b8;
  font-weight: 500;
  padding-top: 2px;
  line-height: 1.4;
  text-align: left;
}
.card-content {
  display: flex;
  flex-direction: column;
  gap: 0;
}
.card-row-top {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.location-tag {
  flex-shrink: 0;
}
.card-code {
  font-size: 13px;
  color: #409eff;
  word-break: break-all;
  font-family: 'SF Mono', Monaco, monospace;
  font-weight: 600;
  flex: 1;
}
.card-spec {
  font-size: 13px;
  color: #334155;
  line-height: 1.4;
  word-break: break-word;
  flex: 1;
}
.card-desc {
  font-size: 13px;
  color: var(--el-text-color-regular);
  line-height: 1.4;
  word-break: break-word;
  flex: 1;
}
.card-location {
  font-size: 12px;
  color: #67c23a;
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 1;
  flex-wrap: wrap;
}
.card-location .location-icon {
  flex-shrink: 0;
}
.card-custodian {
  color: #64748b;
  margin-left: 2px;
}
.card-drawing {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  flex: 1;
}
.card-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  flex: 1;
}
.card-stock {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  flex-wrap: wrap;
}
.card-images {
  display: flex;
  gap: 8px;
  flex: 1;
}
/* 搜索抽屉两列布局 */
.filter-row-two {
  display: flex;
  gap: 12px;
  .filter-group-half { flex: 1; min-width: 0; }
}
.card-actions {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex-shrink: 0;
}
.load-more-sentinel {
  text-align: center;
  padding: 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.load-more-loading,
.load-more-hint,
.load-more-end {
  padding: 8px 0;
}
.mobile-total-tip {
  text-align: center;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  padding: 8px 0;
}

.mobile-filter-form .filter-group {
  margin-bottom: 16px;
}
.mobile-filter-form .filter-label {
  display: block;
  margin-bottom: 6px;
  font-size: 14px;
  color: var(--el-text-color-regular);
}
.mobile-filter-form .filter-actions {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
</style>
