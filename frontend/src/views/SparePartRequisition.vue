<template>
  <div class="requisition-page">
    <div class="page-header">
      <h2>设备领用</h2>
      <p class="page-desc">
        可按规格型号、MES编码、物料描述、适用机型、品牌查询；空查询返回全部设备。仅支持领用（扣减设备库存），不可新增、删除。
      </p>
    </div>

    <!-- 最近领用记录：每页最多 3 条，支持翻页 -->
    <el-card v-if="recentRequisitions.length > 0" class="recent-card" shadow="never">
      <template #header>
        <span>最近领用</span>
      </template>
      <div class="recent-list">
        <div
          v-for="r in recentDisplayList"
          :key="r.id"
          class="recent-item"
        >
          <div class="recent-item-info" @click="applyRecentKeyword(r.mes_material_code)">
            <span class="recent-meta">{{ r.location_code }} · {{ r.mes_material_code || '—' }}</span>
            <span class="recent-spec">{{ r.specification_model || '—' }}</span>
            <span class="recent-qty">×{{ r.quantity }}</span>
            <span class="recent-time">{{ formatRecentTime(r.requisition_at) }}</span>
          </div>
          <el-button
            v-if="canRequisition && (r.unreturned_qty ?? 0) > 0"
            size="small"
            type="warning"
            plain
            class="recent-return-btn"
            @click.stop="openReturnDialog(r)"
          >
            归还 ({{ r.unreturned_qty }})
          </el-button>
        </div>
      </div>
      <div v-if="recentTotalPages > 1" class="recent-pagination">
        <el-button text size="small" :disabled="recentPage <= 1" @click="recentPage = Math.max(1, recentPage - 1)">
          上一页
        </el-button>
        <span class="recent-page-info">{{ recentPage }} / {{ recentTotalPages }}</span>
        <el-button text size="small" :disabled="recentPage >= recentTotalPages" @click="recentPage = Math.min(recentTotalPages, recentPage + 1)">
          下一页
        </el-button>
      </div>
    </el-card>

    <!-- PC 端：筛选卡片在流式布局中 -->
    <el-card v-if="!isMobile" class="filter-card" shadow="never">
      <div class="filter-row">
        <span class="filter-label">搜索</span>
        <div class="search-input-wrap">
          <el-input
            v-model="searchKeyword"
            placeholder="规格型号、MES编码、物料描述、适用机型、品牌"
            clearable
            class="search-input"
            @clear="handleClear"
            @keyup.enter="handleSearch"
          />
          <el-button type="primary" :icon="Search" @click="handleSearch" class="search-btn">查询</el-button>
        </div>
      </div>
      <div class="filter-row filter-filters">
        <el-select v-model="filterSpecificationModel" placeholder="规格型号" clearable filterable style="width: 140px" @change="handleSearch">
          <el-option v-for="item in filterOptions.specification_models" :key="item" :label="item" :value="item" />
        </el-select>
        <el-select v-model="filterApplicableModel" placeholder="适用机型" clearable filterable style="width: 140px" @change="handleSearch">
          <el-option v-for="item in filterOptions.applicable_models" :key="item" :label="item" :value="item" />
        </el-select>
        <el-select v-model="filterBrand" placeholder="品牌" clearable filterable style="width: 120px" @change="handleSearch">
          <el-option v-for="item in filterOptions.brands" :key="item" :label="item" :value="item" />
        </el-select>
        <el-select v-model="filterStorageLocation" placeholder="存放地" clearable filterable style="width: 120px" @change="handleSearch">
          <el-option v-for="item in filterOptions.storage_locations" :key="item" :label="item" :value="item" />
        </el-select>
        <el-select v-model="filterLocationPrefix" placeholder="货位号" clearable style="width: 100px" @change="handleSearch">
          <el-option v-for="item in filterOptions.location_prefixes" :key="item" :label="item" :value="item" />
        </el-select>
        <el-button v-if="hasActiveFilters" type="info" plain size="small" @click="clearFilters">清空筛选</el-button>
      </div>
    </el-card>

    <!-- 移动端：顶栏搜索由 App 统一展示，本页只保留抽屉 -->
    <template v-if="isMobile">
      <el-drawer
        v-model="mobileSearchDrawer"
        title="搜索筛选"
        direction="btt"
        size="82%"
        :append-to-body="true"
        :close-on-click-modal="true"
        :show-close="true"
        :destroy-on-close="false"
        class="requisition-mobile-search-drawer mobile-search-drawer-unified"
        @close="mobileSearchDrawer = false"
      >
        <div class="mobile-filter-form">
          <div class="filter-group">
            <span class="filter-label">关键词搜索</span>
            <el-input
              v-model="searchKeyword"
              placeholder="规格型号、MES编码、物料描述、适用机型、品牌"
              clearable
              class="search-input"
              @clear="handleClear"
              @keyup.enter="handleSearchAndClose"
            />
          </div>
          <div class="filter-row-two">
            <div class="filter-group filter-group-half">
              <span class="filter-label">规格型号</span>
              <el-select v-model="filterSpecificationModel" placeholder="选择规格型号" clearable style="width: 100%" @change="handleSearch">
                <el-option v-for="item in filterOptions.specification_models" :key="item" :label="item" :value="item" />
                <template #empty>暂无数据</template>
              </el-select>
            </div>
            <div class="filter-group filter-group-half">
              <span class="filter-label">适用机型</span>
              <el-select v-model="filterApplicableModel" placeholder="选择适用机型" clearable style="width: 100%" @change="handleSearch">
                <el-option v-for="item in filterOptions.applicable_models" :key="item" :label="item" :value="item" />
                <template #empty>暂无数据</template>
              </el-select>
            </div>
          </div>
          <div class="filter-row-two">
            <div class="filter-group filter-group-half">
              <span class="filter-label">品牌</span>
              <el-select v-model="filterBrand" placeholder="选择品牌" clearable style="width: 100%" @change="handleSearch">
                <el-option v-for="item in filterOptions.brands" :key="item" :label="item" :value="item" />
                <template #empty>暂无数据</template>
              </el-select>
            </div>
            <div class="filter-group filter-group-half">
              <span class="filter-label">存放地</span>
              <el-select v-model="filterStorageLocation" placeholder="选择存放地" clearable style="width: 100%" @change="handleSearch">
                <el-option v-for="item in filterOptions.storage_locations" :key="item" :label="item" :value="item" />
                <template #empty>暂无数据</template>
              </el-select>
            </div>
          </div>
          <div class="filter-group">
            <span class="filter-label">货位号前缀</span>
            <el-select v-model="filterLocationPrefix" placeholder="选择货位号前缀" clearable style="width: 100%" @change="handleSearch">
              <el-option v-for="item in filterOptions.location_prefixes" :key="item" :label="item" :value="item" />
              <template #empty>暂无数据</template>
            </el-select>
          </div>
          <div class="filter-actions">
            <el-button v-if="hasActiveFilters" type="default" @click="clearFilters">清空筛选</el-button>
            <el-button type="primary" :icon="Search" @click="handleSearchAndClose" style="flex:1">查询</el-button>
          </div>
        </div>
      </el-drawer>
    </template>

    <el-card v-show="hasSearched" class="table-card" shadow="never">
      <!-- 移动端：卡片列表 + 无限滚动 -->
      <div v-if="isMobile" class="card-list-wrap">
        <div class="card-list" v-loading="loading && !loadingMore">
          <div
            v-for="row in list"
            :key="row.id"
            class="req-card"
            :class="getReqCardStockClass(row)"
          >
            <div class="req-card-row">
              <div class="req-card-field-row">
                <span class="req-field-label">货位号</span>
                <el-tag type="info" size="small" class="req-location-tag">{{ row.location_code }}</el-tag>
              </div>
              <div class="req-card-field-row">
                <span class="req-field-label">MES编码</span>
                <span class="req-code">{{ row.mes_material_code || '—' }}</span>
              </div>
            </div>
            <div class="req-card-field-row">
              <span class="req-field-label">规格型号</span>
              <span class="req-card-desc">{{ row.specification_model || row.mes_material_desc || '—' }}</span>
            </div>
            <div v-if="row.physical_material_desc" class="req-card-field-row">
              <span class="req-field-label">实物描述</span>
              <span class="req-card-physical-desc">{{ row.physical_material_desc }}</span>
            </div>
            <div v-if="row.storage_location" class="req-card-field-row">
              <span class="req-field-label">存放地</span>
              <div class="req-card-location">
                <el-icon class="location-icon"><Location /></el-icon>
                <span>{{ row.storage_location }}</span>
              </div>
            </div>
            <div v-if="row.brand" class="req-card-field-row">
              <span class="req-field-label">品牌</span>
              <el-tag type="primary" size="small">{{ row.brand }}</el-tag>
            </div>
            <div v-if="row.applicable_model" class="req-card-field-row">
              <span class="req-field-label">适用机型</span>
              <el-tag type="warning" size="small">{{ formatApplicableModel(row.applicable_model) }}</el-tag>
            </div>
            <div class="req-card-field-row">
              <span class="req-field-label">库存</span>
              <span class="req-card-stock">MES: {{ row.mes_stock ?? 0 }} | 库存: <strong :class="(row.physical_stock ?? 0) > 0 ? 'stock-ok' : 'stock-zero'">{{ row.physical_stock ?? 0 }}</strong> {{ row.unit || '个' }}</span>
            </div>
            <div v-if="row.physical_image_url || row.physical_image_url2" class="req-card-field-row">
              <span class="req-field-label">图片</span>
              <div class="req-card-images">
                <el-image
                  v-if="row.physical_image_url"
                  style="width: 48px; height: 48px; border-radius: 6px;"
                  :src="getImageUrlForDisplay(row.physical_image_url)"
                  :preview-src-list="[getImageUrlForDisplay(row.physical_image_url)]"
                  fit="cover"
                  preview-teleported
                hide-on-click-modal
                />
                <el-image
                  v-if="row.physical_image_url2"
                  style="width: 48px; height: 48px; border-radius: 6px;"
                  :src="getImageUrlForDisplay(row.physical_image_url2)"
                  :preview-src-list="[getImageUrlForDisplay(row.physical_image_url2)]"
                  fit="cover"
                  preview-teleported
                hide-on-click-modal
                />
              </div>
            </div>
            <el-button
              v-if="canRequisition"
              type="primary"
              size="small"
              :disabled="(row.physical_stock ?? 0) < 1"
              class="req-card-btn"
              @click="handleRequisition(row)"
            >
              领用
            </el-button>
          </div>
        </div>
        <!-- 移动端：滚动加载更多 -->
        <div v-if="list.length > 0" ref="loadMoreSentinel" class="load-more-sentinel">
          <div v-if="loadingMore" class="load-more-loading">加载中...</div>
          <div v-else-if="reqHasMore" class="load-more-hint">下滑加载更多</div>
          <div v-else class="load-more-end">— 没有更多了 —</div>
        </div>
      </div>
      <div v-if="isMobile && !loading && list.length > 0" class="mobile-total-tip">共 {{ total }} 条</div>
      <!-- PC 端：表格 -->
      <div v-else class="table-scroll-wrap">
      <el-table
        v-loading="loading"
        :data="list"
        border
        stripe
        style="width: 100%"
        row-key="id"
        :max-height="tableMaxHeight"
        :row-class-name="getRequisitionRowClass"
      >
      <el-table-column prop="location_code" label="货位号" width="100" fixed="left" sortable>
        <template #default="{ row }">
          <el-tag type="info">{{ row.location_code }}</el-tag>
        </template>
      </el-table-column>
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
      <el-table-column prop="applicable_model" label="适用机型" width="140" show-overflow-tooltip sortable>
        <template #default="{ row }">
          <el-tag v-if="row.applicable_model" type="warning" size="small">
            {{ formatApplicableModel(row.applicable_model) }}
          </el-tag>
          <span v-else class="empty-text">-</span>
        </template>
      </el-table-column>
      <el-table-column prop="brand" label="品牌" width="100" show-overflow-tooltip sortable>
        <template #default="{ row }">
          <el-tag v-if="row.brand" type="primary" size="small">{{ row.brand }}</el-tag>
          <span v-else class="empty-text">-</span>
        </template>
      </el-table-column>
      <el-table-column prop="mes_stock" label="MES库存" width="100" align="center" sortable>
        <template #default="{ row }">
          <span>{{ row.mes_stock ?? 0 }}</span>
          <span class="unit-text">{{ row.unit || '个' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="physical_stock" label="设备库存" width="110" align="center" sortable>
        <template #default="{ row }">
          <el-tag :type="(row.physical_stock ?? 0) > 0 ? 'success' : 'info'" size="small">
            {{ row.physical_stock ?? 0 }}
          </el-tag>
          <span class="unit-text">{{ row.unit || '个' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="storage_location" label="存放地" width="120" show-overflow-tooltip sortable>
        <template #default="{ row }">
          <el-tag v-if="row.storage_location" type="success" size="small">{{ row.storage_location }}</el-tag>
          <span v-else class="empty-text">-</span>
        </template>
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
      <el-table-column v-if="canRequisition" label="操作" width="100" fixed="right" align="center">
        <template #default="{ row }">
          <el-button
            type="primary"
            size="small"
            :disabled="(row.physical_stock ?? 0) < 1"
            @click="handleRequisition(row)"
          >
            领用
          </el-button>
        </template>
      </el-table-column>
    </el-table>
      </div>
      <div v-if="!loading && list.length === 0" class="empty-tip">暂无匹配设备</div>
      <div v-if="!loading && list.length > 0" class="total-tip">
        <span class="total-count">共 {{ total }} 条设备</span>
      </div>
      <div v-if="!isMobile && !loading && list.length > 0" class="pagination-wrap">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :layout="'total, sizes, prev, pager, next, jumper'"
          :total="total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>

    <el-card v-if="!hasSearched" class="empty-card" shadow="never">
      <el-empty :image-size="120">
        <template #description>
          <p class="empty-desc">输入关键词或选择筛选条件，或直接点击查询查看全部设备</p>
        </template>
      </el-empty>
    </el-card>

    <RequisitionDialog
      v-model="requisitionDialogVisible"
      :row="requisitionRow"
      @success="onRequisitionSuccess"
    />

    <!-- 归还弹窗 -->
    <el-dialog
      v-model="returnDialogVisible"
      title="归还备件"
      :width="isMobile ? '92%' : '400px'"
      :fullscreen="false"
      append-to-body
      @closed="returnRemark = ''; returnQty = 1"
    >
      <div v-if="returnTarget" class="return-dialog-body">
        <p class="return-dialog-info">
          <span class="return-label">备件：</span>
          <span>{{ returnTarget.location_code }} · {{ returnTarget.mes_material_code || '—' }}</span>
        </p>
        <p class="return-dialog-info">
          <span class="return-label">规格型号：</span>
          <span>{{ returnTarget.specification_model || '—' }}</span>
        </p>
        <p class="return-dialog-info">
          <span class="return-label">可归还数量：</span>
          <strong class="return-max">{{ returnTarget.unreturned_qty ?? 0 }}</strong>
        </p>
        <el-form label-width="80px" class="return-form">
          <el-form-item label="归还数量">
            <el-input-number
              v-model="returnQty"
              :min="1"
              :max="returnTarget.unreturned_qty ?? 1"
              :step="1"
              style="width: 100%"
            />
          </el-form-item>
          <el-form-item label="备注">
            <el-input v-model="returnRemark" placeholder="选填" maxlength="200" clearable />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="returnDialogVisible = false">取消</el-button>
        <el-button type="warning" :loading="returning" @click="submitReturn">确认归还</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
// 定义组件名称，用于 keep-alive 缓存
defineOptions({
  name: 'SparePartRequisition'
})

import { ref, computed, onMounted, onUnmounted, onActivated, onDeactivated, nextTick, watch, inject } from 'vue'
import { useRoute } from 'vue-router'
import { sparePartApi, type SparePartFilterOptions } from '@/api/sparePart'
import { Search, DocumentCopy, Location } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import RequisitionDialog from '@/components/RequisitionDialog.vue'
import type { SparePart } from '@/types/sparePart'
import { getImageUrlForDisplay } from '@/utils/image'
import { useDataRefresh } from '@/composables/useDataRefresh'
import { useSparePartDataChanged, broadcastSparePartDataChanged } from '@/composables/useSparePartDataChanged'
import { useIsMobile } from '@/composables/useIsMobile'
import { scrollMainToTop } from '@/composables/useScrollMainToTop'
import { useAuthStore } from '@/stores/auth'
import { navLog, navLogStart } from '@/utils/navLog'

const route = useRoute()
const { isMobile } = useIsMobile()
const authStore = useAuthStore()
const canEdit = computed(() => authStore.canAccessModule('electrical', 'editor'))
/** 领用员或有编辑权限者均可进行领用/归还操作 */
const canRequisition = computed(() => canEdit.value || authStore.isElectricalClerk)
const searchKeyword = ref('')
const filterSpecificationModel = ref('')
const filterApplicableModel = ref('')
const filterBrand = ref('')
const filterStorageLocation = ref('')
const filterLocationPrefix = ref('')
const filterOptions = ref<{
  specification_models: string[]
  applicable_models: string[]
  brands: string[]
  storage_locations: string[]
  location_prefixes: string[]
}>({
  specification_models: [],
  applicable_models: [],
  brands: [],
  storage_locations: [],
  location_prefixes: [],
})
const hasActiveFilters = computed(
  () =>
    !!(filterSpecificationModel.value || filterApplicableModel.value || filterBrand.value || filterStorageLocation.value || filterLocationPrefix.value)
)
const currentPage = ref(1)
const pageSize = ref(20)
const skip = computed(() => (currentPage.value - 1) * pageSize.value)

const list = ref<SparePart[]>([])
const total = ref(0)
const loading = ref(false)
const loadingMore = ref(false)
const hasSearched = ref(false)
const stockAlertFilter = ref<'zero' | 'low' | ''>('')
const zeroCount = ref(0)
const lowCount = ref(0)
const loadMoreSentinel = ref<HTMLElement | null>(null)

const reqHasMore = computed(
  () => list.value.length < total.value && !loadingMore.value && !loading.value
)

// PC 端表格高度：与修复件管理页一致，填满视口剩余空间
const tableMaxHeight = computed(() =>
  isMobile.value ? undefined : 'calc(100vh - 300px)'
)

const requisitionDialogVisible = ref(false)
const mobileSearchDrawer = ref(false)
const openMobileSearch = inject<{ value: boolean }>('openMobileSearch')
if (openMobileSearch) {
  watch(() => openMobileSearch.value, (v) => {
    if (v && route.path === '/electrical/requisition') {
      mobileSearchDrawer.value = true
      openMobileSearch.value = false
    }
  })
}
const requisitionRow = ref<SparePart | null>(null)
// 归还功能
type RecentItem = { id: number; requisition_at: string; quantity: number; spare_part_id: number; mes_material_code?: string; specification_model?: string; location_code?: string; unreturned_qty?: number }
const returnDialogVisible = ref(false)
const returnTarget = ref<RecentItem | null>(null)
const returnQty = ref(1)
const returnRemark = ref('')
const returning = ref(false)

function openReturnDialog(item: RecentItem) {
  returnTarget.value = item
  returnQty.value = Math.min(1, item.unreturned_qty ?? 1)
  returnRemark.value = ''
  returnDialogVisible.value = true
}

async function submitReturn() {
  if (!returnTarget.value) return
  const maxQty = returnTarget.value.unreturned_qty ?? 0
  if (returnQty.value <= 0 || returnQty.value > maxQty) {
    ElMessage.warning(`归还数量须在 1 ~ ${maxQty} 之间`)
    return
  }
  returning.value = true
  try {
    await sparePartApi.returnPart(returnTarget.value.spare_part_id, returnQty.value, returnRemark.value || undefined)
    ElMessage.success('归还成功')
    returnDialogVisible.value = false
    loadData()
    loadRecentRequisition()
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    ElMessage.error(typeof detail === 'string' ? detail : '归还失败，请重试')
  } finally {
    returning.value = false
  }
}

const RECENT_PAGE_SIZE = 3
const recentRequisitions = ref<RecentItem[]>([])
const recentPage = ref(1)
const recentDisplayList = computed(() => {
  const list = recentRequisitions.value
  const total = list.length
  if (total === 0) return []
  const start = (recentPage.value - 1) * RECENT_PAGE_SIZE
  return list.slice(start, start + RECENT_PAGE_SIZE)
})
const recentTotalPages = computed(() => Math.max(1, Math.ceil(recentRequisitions.value.length / RECENT_PAGE_SIZE)))

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

function formatApplicableModel(s: string) {
  if (!s) return ''
  const parts = s.split(',').map((x) => x.trim())
  return parts.length > 2 ? `${parts[0]}等${parts.length}个` : s
}

function formatRecentTime(iso: string) {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    const now = new Date()
    const diff = (now.getTime() - d.getTime()) / 60000
    if (diff < 1) return '刚刚'
    if (diff < 60) return `${Math.floor(diff)}分钟前`
    if (diff < 1440) return `${Math.floor(diff / 60)}小时前`
    return `${d.getMonth() + 1}/${d.getDate()}`
  } catch {
    return iso.slice(0, 16)
  }
}

function applyRecentKeyword(mesCode: string | undefined) {
  if (mesCode) {
    searchKeyword.value = mesCode
    currentPage.value = 1
    loadData()
  }
}

async function loadRecentRequisition() {
  try {
    const res = await sparePartApi.getRecentRequisition(10)
    recentRequisitions.value = res?.items ?? []
    recentPage.value = 1
  } catch {
    recentRequisitions.value = []
    recentPage.value = 1
  }
}

async function loadFilterOptions() {
  try {
    const res = await sparePartApi.getFilterOptions() as SparePartFilterOptions
    if (res?.brands) filterOptions.value.brands = res.brands
    if (res?.applicable_models) filterOptions.value.applicable_models = res.applicable_models
    if (res?.specification_models) filterOptions.value.specification_models = res.specification_models ?? []
    if (res?.storage_locations) filterOptions.value.storage_locations = res.storage_locations ?? []
    if (res?.location_prefixes) filterOptions.value.location_prefixes = res.location_prefixes ?? []
  } catch {
    /* ignore */
  }
}

/** 总库存 = MES库存 + 设备库存 */
function totalStock(row: SparePart): number {
  return (row.mes_stock ?? 0) + (row.physical_stock ?? 0)
}
function getRequisitionRowClass({ row }: { row: SparePart }) {
  const t = totalStock(row)
  if (t === 0) return 'req-row-zero'
  if (t === 1) return 'req-row-low'
  return ''
}
function getReqCardStockClass(row: SparePart): string {
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
  navLog('SparePartRequisition loadData start', { append })
  const kw = searchKeyword.value?.trim() ?? ''

  if (append) {
    loadingMore.value = true
  } else {
    loading.value = true
  }
  hasSearched.value = true
  try {
    const skipVal = append ? list.value.length : skip.value
    const res = await sparePartApi.requisitionSearch({
      keyword: kw || undefined,
      skip: skipVal,
      limit: pageSize.value,
      brand: filterBrand.value || undefined,
      applicable_model: filterApplicableModel.value || undefined,
      specification_model: filterSpecificationModel.value || undefined,
      storage_location: filterStorageLocation.value || undefined,
      location_prefix: filterLocationPrefix.value || undefined,
      stock_alert: stockAlertFilter.value || undefined,
    }) as { items?: SparePart[]; total?: number; zero_count?: number; low_count?: number }
    const newItems = Array.isArray(res?.items) ? res.items : []
    const totalCount = typeof res?.total === 'number' ? res.total : newItems.length
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
    navLog('SparePartRequisition loadData end', { append }, t)
  }
}

async function loadMore() {
  if (!reqHasMore.value || loadingMore.value) return
  await loadData(true)
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

function clearFilters() {
  filterSpecificationModel.value = ''
  filterApplicableModel.value = ''
  filterBrand.value = ''
  filterStorageLocation.value = ''
  filterLocationPrefix.value = ''
  searchKeyword.value = ''
  stockAlertFilter.value = ''
  zeroCount.value = 0
  lowCount.value = 0
  currentPage.value = 1
  loadData()
}

function handleClear() {
  searchKeyword.value = ''
  currentPage.value = 1
  loadData()
}

function handleSizeChange() {
  currentPage.value = 1
  loadData()
}

function handleCurrentChange() {
  loadData()
}

function handleRequisition(row: SparePart) {
  requisitionRow.value = row
  requisitionDialogVisible.value = true
}

function onRequisitionSuccess() {
  loadData()
  loadRecentRequisition()
}

function doRefresh() {
  if (hasSearched.value) {
    loadData()
  }
}

// 轮询 + 标签页可见时刷新（仅在有搜索结果时）
useDataRefresh(doRefresh)
// 跨标签页/窗口：修复件管理页增删改后，本页若有搜索结果则立即刷新
useSparePartDataChanged(doRefresh)

function scheduleAfterPaint(fn: () => void) {
  if (typeof requestIdleCallback !== 'undefined') requestIdleCallback(fn, { timeout: 120 })
  else setTimeout(fn, 0)
}
onMounted(() => {
  navLog('SparePartRequisition mounted', {})
  scheduleAfterPaint(async () => {
    navLog('SparePartRequisition scheduleAfterPaint loadFilterOptions', {})
    await loadFilterOptions()
    loadRecentRequisition()
    // 领用员、管理员、以及各模块管理员进入后自动加载数据
    if (authStore.isElectricalClerk || authStore.canManageSystem || authStore.canAccessModule('electrical', 'admin')) handleSearch()
  })
})
onActivated(() => {
  navLog('SparePartRequisition activated', {})
  loadRecentRequisition()
})
onDeactivated(() => {
  mobileSearchDrawer.value = false
})

// 移动端：IntersectionObserver 监听滚动加载更多
let observer: IntersectionObserver | null = null
function setupLoadMoreObserver() {
  if (!isMobile.value || !loadMoreSentinel.value) return
  observer?.disconnect()
  observer = new IntersectionObserver(
    (entries) => {
      const e = entries[0]
      if (e?.isIntersecting && reqHasMore.value) loadMore()
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

<style scoped lang="scss">
.requisition-page {
  padding: 0 24px 24px;
  min-height: calc(100vh - 60px);
  background: linear-gradient(to bottom, #f8fafc 0%, #fff 120px);
}

.page-header {
  margin-bottom: 24px;
  padding: 20px 0 8px;

  h2 {
    margin: 0 0 10px;
    font-size: 22px;
    font-weight: 600;
    color: #1e293b;
    letter-spacing: 0.02em;
  }

  .page-desc {
    margin: 0;
    font-size: 14px;
    color: #64748b;
    line-height: 1.6;
    max-width: 680px;
  }
}

.filter-card {
  margin-bottom: 16px;
  border-radius: 12px;
  border: 1px solid var(--el-border-color-lighter);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}
.recent-card {
  margin-bottom: 16px;
  border-radius: 12px;
  border: 1px solid var(--el-border-color-lighter);
}

.table-scroll-wrap :deep(.el-table tr.req-row-zero) {
  background-color: #fef2f2 !important;
}
.table-scroll-wrap :deep(.el-table tr.req-row-zero:hover > td) {
  background-color: #fee2e2 !important;
}
.table-scroll-wrap :deep(.el-table tr.req-row-low) {
  background-color: #fffbeb !important;
}
.table-scroll-wrap :deep(.el-table tr.req-row-low:hover > td) {
  background-color: #fef3c7 !important;
}
.req-card.req-card-zero {
  border-left: 4px solid var(--el-color-danger);
  background: linear-gradient(to bottom, #fef2f2, #fee2e2);
}
.req-card.req-card-low {
  border-left: 4px solid var(--el-color-warning);
  background: linear-gradient(to bottom, #fffbeb, #fef3c7);
}

.recent-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.recent-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 8px 0 4px;
  margin-top: 4px;
  border-top: 1px solid var(--el-border-color-lighter);
}
.recent-page-info {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  min-width: 48px;
  text-align: center;
}
.recent-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  transition: background 0.15s;
}
.recent-item:hover {
  background: var(--el-fill-color-light);
}
.recent-item-info {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
  cursor: pointer;
}
.recent-return-btn {
  flex-shrink: 0;
}
.recent-meta {
  font-size: 13px;
  color: var(--el-text-color-primary);
  font-family: 'SF Mono', Monaco, monospace;
}
.recent-spec {
  font-size: 12px;
  color: var(--el-text-color-regular);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.recent-qty {
  font-size: 12px;
  color: var(--el-color-primary);
}
.recent-time {
  font-size: 11px;
  color: var(--el-text-color-secondary);

  :deep(.el-card__body) {
    padding: 20px 24px;
    background: linear-gradient(to bottom, #fff, #fafbfc);
    border-radius: 12px;
  }
}

.filter-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;

  &:last-child {
    margin-bottom: 0;
  }

  .filter-label {
    font-size: 14px;
    font-weight: 500;
    color: #475569;
    white-space: nowrap;
  }

  .search-input-wrap {
    display: flex;
    align-items: center;
    gap: 0;
    max-width: 400px;
    flex: 0 1 auto;
    min-width: 0;
  }

  .search-input {
    flex: 1;
    min-width: 0;

    :deep(.el-input__wrapper) {
      border-radius: 8px 0 0 8px;
      box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
    }
  }

  .search-btn {
    flex-shrink: 0;
    border-radius: 0 8px 8px 0;
    margin-left: -1px;
  }
}

.filter-filters {
  margin-top: 8px;
  padding-top: 12px;
  border-top: 1px dashed var(--el-border-color-lighter);

  .el-select :deep(.el-input__wrapper) {
    border-radius: 6px;
  }

  .clear-filters-btn {
    margin-left: 4px;
  }
}

.table-card {
  position: relative;
  border-radius: 12px;
  border: 1px solid var(--el-border-color-lighter);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  overflow: hidden;

  :deep(.el-card__body) {
    padding: 20px 24px;
    background: #fff;
  }

  :deep(.el-table) {
    --el-table-border-color: var(--el-border-color-lighter);
    --el-table-header-bg-color: #f8fafc;
  }

  :deep(.el-table th.el-table__cell) {
    font-weight: 600;
    color: #475569;
  }
}

.empty-tip {
  text-align: center;
  padding: 48px 16px;
  font-size: 14px;
  color: #94a3b8;
  background: linear-gradient(to bottom, #fafbfc, #fff);
}

.total-tip {
  text-align: center;
  padding: 14px 16px;
  font-size: 14px;
  color: #64748b;
  font-weight: 500;
  background: #f8fafc;
  border-radius: 8px;
  margin-top: 12px;
}

.pagination-wrap {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--el-border-color-lighter);
  display: flex;
  justify-content: flex-end;
}

.empty-card {
  margin-top: 20px;
  border-radius: 12px;
  border: 1px dashed var(--el-border-color-lighter);
  background: linear-gradient(to bottom, #fafbfc, #fff);

  :deep(.el-card__body) {
    padding: 56px 24px;
  }

  :deep(.el-empty__description) {
    margin-top: 12px;
  }
}

.empty-desc {
  margin: 0;
  font-size: 14px;
  color: #94a3b8;
  line-height: 1.7;
}

.unit-text {
  margin-left: 4px;
  font-size: 12px;
  color: #909399;
}

.empty-text {
  color: #c0c4cc;
  font-style: italic;
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
    transition: color 0.2s;

    &:hover {
      color: #409eff;
    }
  }
}

.image-cell {
  display: inline-flex;
  align-items: center;
  justify-content: center;

  .el-image {
    border-radius: 6px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  }
}

.table-scroll-wrap {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  border-radius: 8px;
}

/* 归还弹窗（PC端） */
.return-dialog-body {
  padding: 4px 0;
}
.return-dialog-info {
  margin: 0 0 10px;
  font-size: 14px;
  color: #334155;
  display: flex;
  align-items: baseline;
  gap: 4px;
  .return-label { color: #94a3b8; font-size: 13px; white-space: nowrap; }
  .return-max { color: #e6a23c; font-size: 16px; font-weight: 600; }
}
.return-form { margin-top: 12px; }

/* 移动端 */
@media (max-width: 767px) {
  .requisition-page {
    padding: 0 0 20px;
    background: #f1f5f9;
  }

  .page-header {
    margin-bottom: 20px;
    padding: 16px 0 8px;

    h2 {
      font-size: 20px;
      font-weight: 600;
      color: #1e293b;
      letter-spacing: 0.02em;
    }

    .page-desc {
      font-size: 14px;
      line-height: 1.55;
      color: #64748b;
    }
  }

  .mobile-filter-form {
    .filter-group {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-bottom: 20px;

      &:last-of-type {
        margin-bottom: 0;
      }
    }

    .filter-label {
      font-size: 15px;
      font-weight: 600;
      color: #334155;
      line-height: 1.4;
    }

    .filter-actions {
      margin-top: 24px;
      padding-top: 20px;
      border-top: 1px solid var(--el-border-color-lighter);
      display: flex;
      gap: 12px;

      .el-button:not([block]) {
        flex: 1;
      }
    }

    .search-input {
      width: 100%;
    }

    .el-input__wrapper,
    .el-select .el-select__wrapper {
      min-height: 44px;
      padding: 8px 14px;
      font-size: 16px;
      border-radius: 10px;
    }

    .el-button {
      font-size: 15px;
      min-height: 44px;
      border-radius: 10px;
    }
  }


  .filter-row .search-input-wrap {
    max-width: none;
    width: 100%;
    flex: 1 1 100%;
  }

  .filter-filters {
    flex-direction: column;
    align-items: stretch;
    padding-top: 12px;
  }

  .filter-filters .el-select {
    width: 100% !important;
    max-width: none;
  }

  /* 移动端：避免 overflow:hidden 在 iframe 内裁切卡片边框，改由 body 做圆角裁剪 */
  .table-card {
    overflow: visible;
    :deep(.el-card__body) {
      padding: 0;
      overflow: hidden;
      border-radius: 12px;
    }
  }

  .card-list-wrap {
    /* 留出安全区，避免卡片边框/阴影贴边被裁切（尤其 iframe 嵌入时） */
    padding: 0 2px;
  }

  .req-card-list {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .card-list {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .req-card {
    background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
    border-radius: 14px;
    padding: 16px 18px;
    border: 1px solid rgba(0, 0, 0, 0.06);
    border-left: 4px solid var(--el-color-success);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    display: flex;
    flex-direction: column;
    gap: 8px;

    &:active {
      transform: scale(0.99);
    }
  }

  /* 卡片字段标签行 */
  .req-card-field-row {
    display: flex;
    align-items: flex-start;
    gap: 6px;
  }

  .req-field-label {
    flex: 0 0 60px;
    font-size: 12px;
    color: #94a3b8;
    font-weight: 500;
    padding-top: 2px;
    line-height: 1.4;
    text-align: left;
  }

  .req-card-row {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .req-code {
    font-family: 'SF Mono', 'Monaco', 'Courier New', monospace;
    font-size: 14px;
    color: #409eff;
    font-weight: 600;
    flex: 1;
  }

  .req-card-desc {
    font-size: 14px;
    color: #334155;
    line-height: 1.5;
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
  }

  .req-card-physical-desc {
    font-size: 13px;
    color: #64748b;
    line-height: 1.45;
    flex: 1;
  }

  .req-card-location {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 13px;
    color: #67c23a;

    .location-icon {
      font-size: 14px;
      flex-shrink: 0;
    }
  }

  .req-card-tags-row .req-card-meta {
    flex-wrap: wrap;
  }

  .req-card-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    flex: 1;
  }

  .req-card-stock {
    font-size: 13px;
    color: #64748b;
    flex: 1;

    .stock-ok { color: #67c23a; font-weight: 600; }
    .stock-zero { color: #f56c6c; font-weight: 600; }
  }

  .req-card-images {
    display: flex;
    gap: 8px;

    :deep(.el-image) {
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }
  }

  .req-card-btn {
    width: 100%;
    font-weight: 600;
    font-size: 15px;
    padding: 12px 16px;
    min-height: 44px;
    border-radius: 10px;
    margin-top: 4px;
  }

  /* 搜索抽屉两列布局 */
  .filter-row-two {
    display: flex;
    gap: 12px;
    margin-bottom: 0;

    .filter-group-half {
      flex: 1;
      min-width: 0;
    }
  }

  /* 归还弹窗 */
  .return-dialog-body {
    padding: 4px 0;
  }

  .return-dialog-info {
    margin: 0 0 10px;
    font-size: 14px;
    color: #334155;
    display: flex;
    align-items: baseline;
    gap: 4px;

    .return-label {
      color: #94a3b8;
      font-size: 13px;
      white-space: nowrap;
    }
    .return-max {
      color: #e6a23c;
      font-size: 16px;
    }
  }

  .return-form {
    margin-top: 12px;
  }

  .card-list-wrap {
    margin-bottom: 16px;
  }

  .mobile-total-tip {
    text-align: center;
    padding: 14px 16px;
    font-size: 14px;
    line-height: 1.5;
    color: #64748b;
    font-weight: 500;
    background: linear-gradient(to bottom, #f8fafc, #fff);
    border-radius: 10px;
    margin-top: 16px;
  }

  .empty-card {
    :deep(.el-card__body) {
      padding: 40px 20px;
    }
  }

  .load-more-sentinel {
    min-height: 52px;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 18px 16px;
    font-size: 14px;
    line-height: 1.5;
    color: #64748b;
  }

  .load-more-loading {
    color: var(--el-color-primary);
  }

  .load-more-end {
    color: #94a3b8;
  }
}
</style>
