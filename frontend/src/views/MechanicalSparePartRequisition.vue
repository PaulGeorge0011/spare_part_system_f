<template>
  <div class="mechanical-requisition-page">
    <div class="page-header">
      <h2>机械设备领用</h2>
      <p class="page-desc">
        可按规格型号、MES编码、物料描述、适用机型、品牌、图号、保管人查询；空查询返回全部设备。仅支持领用（扣减设备库存），不可新增、删除。
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

    <!-- PC 端：筛选（与电气一致） -->
    <el-card v-if="!isMobile" class="filter-card" shadow="never">
      <div class="filter-row">
        <span class="filter-label">搜索</span>
        <div class="search-input-wrap">
          <el-input
            v-model="searchKeyword"
            placeholder="规格型号、MES编码、物料描述、图号、保管人..."
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
        class="mech-requisition-mobile-search-drawer mobile-search-drawer-unified"
        @close="mobileSearchDrawer = false"
      >
        <div class="mobile-filter-form">
          <div class="filter-group">
            <span class="filter-label">关键词搜索</span>
            <el-input
              v-model="searchKeyword"
              placeholder="规格型号、MES编码、图号、保管人..."
              clearable
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
      <!-- 移动端：卡片列表 -->
      <template v-if="isMobile">
        <div class="card-list-wrap">
          <div class="card-list" v-loading="loading && !loadingMore">
            <div v-for="row in list" :key="row.id" class="req-card" :class="getReqCardStockClass(row)">
              <div class="req-card-field-row">
                <span class="req-field-label">货位号</span>
                <el-tag type="info" size="small" class="req-location-tag">{{ row.location_code }}</el-tag>
              </div>
              <div class="req-card-field-row">
                <span class="req-field-label">MES编码</span>
                <span class="req-code">{{ row.mes_material_code || '—' }}</span>
              </div>
              <div v-if="row.specification_model" class="req-card-field-row">
                <span class="req-field-label">规格型号</span>
                <span class="req-card-spec">{{ row.specification_model }}</span>
              </div>
              <div class="req-card-field-row">
                <span class="req-field-label">物料描述</span>
                <span class="req-card-desc">{{ row.mes_material_desc || row.physical_material_desc || '—' }}</span>
              </div>
              <div v-if="row.storage_location || row.custodian" class="req-card-field-row">
                <span class="req-field-label">存放地</span>
                <div class="req-card-location">
                  <el-icon v-if="row.storage_location" class="location-icon"><Location /></el-icon>
                  <span>{{ row.storage_location || '' }}</span>
                  <span v-if="row.custodian" class="req-custodian">保管人：{{ row.custodian }}</span>
                </div>
              </div>
              <div v-if="row.drawing_no" class="req-card-field-row">
                <span class="req-field-label">图号</span>
                <span class="req-card-drawing">{{ row.drawing_no }}</span>
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
                <div class="req-card-stock-row">
                  <el-tag :type="getStockType(row.mes_stock ?? 0, row.physical_stock ?? 0)" size="small">MES: {{ row.mes_stock ?? 0 }}</el-tag>
                  <el-tag :type="getStockType(row.physical_stock ?? 0, row.mes_stock ?? 0)" size="small">库存: {{ row.physical_stock ?? 0 }}</el-tag>
                  <span class="unit-text">{{ row.unit || '个' }}</span>
                </div>
              </div>
              <div v-if="row.physical_image_url || row.physical_image_url2" class="req-card-field-row req-card-images-row">
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
          <div v-if="list.length > 0" ref="loadMoreSentinel" class="load-more-sentinel">
            <div v-if="loadingMore" class="load-more-loading">加载中...</div>
            <div v-else-if="reqHasMore" class="load-more-hint">下滑加载更多</div>
            <div v-else class="load-more-end">— 没有更多了 —</div>
          </div>
        </div>
        <div v-if="!loading && list.length > 0" class="mobile-total-tip">共 {{ total }} 条</div>
        <div v-if="!loading && list.length === 0" class="empty-tip">暂无匹配设备</div>
      </template>

      <!-- PC 端：表格 -->
      <template v-else>
        <div class="table-scroll-wrap">
          <el-table
            v-loading="loading"
            :data="list"
            border
            stripe
            style="width: 100%"
            row-key="id"
            :row-class-name="getRequisitionRowClass"
          >
            <el-table-column prop="location_code" label="货位号" width="100" fixed="left">
            <template #default="{ row }">
              <el-tag type="info">{{ row.location_code }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="mes_material_code" label="MES编码" min-width="120" show-overflow-tooltip>
            <template #default="{ row }">
              <div class="code-cell">
                <el-icon v-if="row.mes_material_code" class="copy-icon" @click="copyToClipboard(row.mes_material_code)">
                  <DocumentCopy />
                </el-icon>
                <span class="code-value">{{ row.mes_material_code || '—' }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="specification_model" label="规格型号" min-width="120" show-overflow-tooltip>
            <template #default="{ row }">
              <div class="code-cell">
                <el-icon v-if="row.specification_model" class="copy-icon" @click="copyToClipboard(row.specification_model)">
                  <DocumentCopy />
                </el-icon>
                <span class="code-value">{{ row.specification_model || '—' }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="drawing_no" label="图号" width="100" show-overflow-tooltip />
          <el-table-column label="物料描述" min-width="160" show-overflow-tooltip>
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
              <span v-else class="empty-text">—</span>
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
              <span v-else class="empty-text">—</span>
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
          <el-table-column prop="storage_location" label="存放地" width="120" show-overflow-tooltip>
            <template #default="{ row }">
              <el-tag v-if="row.storage_location" type="success" size="small">{{ row.storage_location }}</el-tag>
              <span v-else>—</span>
            </template>
          </el-table-column>
          <el-table-column prop="custodian" label="保管人" width="90" show-overflow-tooltip>
            <template #default="{ row }">{{ row.custodian || '—' }}</template>
          </el-table-column>
          <el-table-column v-if="canRequisition" label="操作" width="100" fixed="right">
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
        <div v-if="!loading && list.length > 0" class="pagination-wrap">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="total"
          layout="total, sizes, prev, pager, next"
          @size-change="loadData"
          @current-change="loadData"
        />
        </div>
      </template>
    </el-card>

    <el-card v-if="!hasSearched" class="empty-card" shadow="never">
      <el-empty :image-size="120">
        <template #description>
          <p class="empty-desc">输入关键词或选择筛选条件，或直接点击查询查看全部设备</p>
        </template>
      </el-empty>
    </el-card>

    <MechanicalRequisitionDialog
      v-model="requisitionDialogVisible"
      :row="requisitionRow"
      @success="onRequisitionSuccess"
    />

    <!-- 归还弹窗 -->
    <el-dialog
      v-model="returnDialogVisible"
      title="归还备件"
      :width="isMobile ? '92%' : '400px'"
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
  name: 'MechanicalSparePartRequisition'
})

import { ref, computed, onMounted, onActivated, onDeactivated, watch, inject, nextTick, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { Search, DocumentCopy, Location } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import MechanicalRequisitionDialog from '@/components/MechanicalRequisitionDialog.vue'
import { mechanicalSparePartApi } from '@/api/mechanicalSparePart'
import type { MechanicalSparePart, MechanicalSparePartFilterOptions } from '@/types/mechanicalSparePart'
import { useIsMobile } from '@/composables/useIsMobile'
import { scrollMainToTop } from '@/composables/useScrollMainToTop'
import { useDataRefresh } from '@/composables/useDataRefresh'
import { useMechanicalSparePartDataChanged } from '@/composables/useMechanicalSparePartDataChanged'
import { getImageUrlForDisplay } from '@/utils/image'
import { useAuthStore } from '@/stores/auth'
import { navLog, navLogStart } from '@/utils/navLog'

const route = useRoute()
const { isMobile } = useIsMobile()
const authStore = useAuthStore()
const canEdit = computed(() => authStore.canAccessModule('mechanical', 'editor'))
/** 领用员或有编辑权限者均可进行领用/归还操作 */
const canRequisition = computed(() => canEdit.value || authStore.isMechanicalClerk)
useDataRefresh(loadData)
useMechanicalSparePartDataChanged(loadData)
const mobileSearchDrawer = ref(false)
const openMobileSearch = inject<{ value: boolean }>('openMobileSearch')
if (openMobileSearch) {
  watch(() => openMobileSearch.value, (v) => {
    if (v && route.path === '/mechanical/requisition') {
      mobileSearchDrawer.value = true
      openMobileSearch.value = false
    }
  })
}
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
const list = ref<MechanicalSparePart[]>([])
const total = ref(0)
const loading = ref(false)
const loadingMore = ref(false)
const loadMoreSentinel = ref<HTMLElement | null>(null)
const hasSearched = ref(false)
const reqHasMore = computed(
  () => list.value.length < total.value && !loadingMore.value && !loading.value
)
const stockAlertFilter = ref<'zero' | 'low' | ''>('')
const zeroCount = ref(0)
const lowCount = ref(0)
const requisitionDialogVisible = ref(false)
const requisitionRow = ref<MechanicalSparePart | null>(null)

// 归还功能
type RecentItem = { id: number; requisition_at: string; quantity: number; mechanical_spare_part_id: number; mes_material_code?: string; specification_model?: string; location_code?: string; unreturned_qty?: number }
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
    await mechanicalSparePartApi.returnPart(returnTarget.value.mechanical_spare_part_id, returnQty.value, returnRemark.value || undefined)
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

const skip = computed(() => (currentPage.value - 1) * pageSize.value)

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

async function loadFilterOptions() {
  try {
    const res = await mechanicalSparePartApi.getFilterOptions() as MechanicalSparePartFilterOptions
    if (res?.brands) filterOptions.value.brands = res.brands
    if (res?.applicable_models) filterOptions.value.applicable_models = res.applicable_models
    if (res?.specification_models) filterOptions.value.specification_models = res.specification_models ?? []
    if (res?.storage_locations) filterOptions.value.storage_locations = res.storage_locations ?? []
    if (res?.location_prefixes) filterOptions.value.location_prefixes = res.location_prefixes ?? []
  } catch {
    /* ignore */
  }
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
    const res = await mechanicalSparePartApi.getRecentRequisition(10)
    recentRequisitions.value = res?.items ?? []
    recentPage.value = 1
  } catch {
    recentRequisitions.value = []
    recentPage.value = 1
  }
}

// 与电气一致：MES/修附件库存标签颜色
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

/** 总库存 = MES库存 + 修附件库存 */
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
  navLog('MechanicalSparePartRequisition loadData start', { append })
  if (append) {
    loadingMore.value = true
  } else {
    loading.value = true
  }
  hasSearched.value = true
  try {
    const skipVal = append ? list.value.length : skip.value
    const res = (await mechanicalSparePartApi.requisitionSearch({
      keyword: searchKeyword.value?.trim() || undefined,
      skip: skipVal,
      limit: pageSize.value,
      brand: filterBrand.value || undefined,
      applicable_model: filterApplicableModel.value || undefined,
      specification_model: filterSpecificationModel.value || undefined,
      storage_location: filterStorageLocation.value || undefined,
      location_prefix: filterLocationPrefix.value || undefined,
      stock_alert: stockAlertFilter.value || undefined,
    })) as { items?: MechanicalSparePart[]; total?: number; zero_count?: number; low_count?: number }
    const newItems = res?.items ?? []
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
      zeroCount.value = 0
      lowCount.value = 0
    }
  } finally {
    loading.value = false
    loadingMore.value = false
    navLog('MechanicalSparePartRequisition loadData end', { append }, t)
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

function handleRequisition(row: MechanicalSparePart) {
  requisitionRow.value = row
  requisitionDialogVisible.value = true
}

function onRequisitionSuccess() {
  loadData()
  loadRecentRequisition()
}

function scheduleAfterPaint(fn: () => void) {
  if (typeof requestIdleCallback !== 'undefined') requestIdleCallback(fn, { timeout: 120 })
  else setTimeout(fn, 0)
}
onMounted(() => {
  navLog('MechanicalSparePartRequisition mounted', {})
  scheduleAfterPaint(async () => {
    await loadFilterOptions()
    loadRecentRequisition()
    if (authStore.isMechanicalClerk || authStore.isElectricalClerk || authStore.canManageSystem || authStore.canAccessModule('mechanical', 'admin')) handleSearch()
  })
})
onActivated(() => {
  navLog('MechanicalSparePartRequisition activated', {})
  loadRecentRequisition()
})
onDeactivated(() => {
  mobileSearchDrawer.value = false
})

// 移动端：IntersectionObserver 监听滚动加载更多（与电气领用/电气修复件一致）
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

<style scoped>
.mechanical-requisition-page {
  padding: 20px;
  background: #f5f7fa;
  min-height: calc(100vh - 60px);
}
.page-header {
  margin-bottom: 20px;
}
.page-header h2 {
  margin: 0 0 8px;
  font-size: 24px;
  font-weight: 600;
}
.page-desc {
  margin: 0;
  font-size: 14px;
  color: #606266;
}
.filter-card {
  margin-bottom: 16px;
  border-radius: 12px;
  border: 1px solid var(--el-border-color-lighter);
}
.filter-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.filter-row.filter-filters {
  margin-top: 12px;
  flex-wrap: wrap;
}
.filter-label {
  font-size: 14px;
  color: #606266;
  white-space: nowrap;
}
.search-input-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  max-width: 400px;
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
  background: linear-gradient(to bottom, #fef2f2, #fee2e2) !important;
}
.req-card.req-card-low {
  border-left: 4px solid var(--el-color-warning);
  background: linear-gradient(to bottom, #fffbeb, #fef3c7) !important;
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

/* 归还弹窗 */
.return-dialog-body { padding: 4px 0; }
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
}
.empty-card {
  margin-top: 16px;
  border-radius: 12px;
  border: 1px dashed var(--el-border-color-lighter);
  background: linear-gradient(to bottom, #fafbfc, #fff);
}
.empty-desc {
  margin: 0;
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

@media (max-width: 767px) {
  .mechanical-requisition-page {
    padding: 0 0 16px;
  }
  .page-header {
    margin-bottom: 16px;
  }
  .page-header h2 {
    font-size: 18px;
  }
  .page-desc {
    font-size: 13px;
  }
  .search-input-wrap {
    max-width: none;
    width: 100%;
  }
  .req-card-list {
    gap: 14px;
  }
  /* 移动端：避免 iframe 内裁切卡片边框，改由 body 做圆角裁剪 */
  .table-card {
    overflow: visible;
    :deep(.el-card__body) {
      padding: 0;
      overflow: hidden;
      border-radius: 12px;
    }
  }
}
.search-input {
  flex: 1;
}
.pagination-wrap {
  margin-top: 16px;
}
.table-scroll-wrap {
  overflow-x: auto;
}
.code-cell {
  display: flex;
  align-items: center;
  gap: 6px;
}
.code-cell .code-value {
  flex: 1;
  min-width: 0;
}
.copy-icon {
  cursor: pointer;
  color: var(--el-color-primary);
}
.unit-text {
  margin-left: 4px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.stock-cell {
  display: flex;
  align-items: center;
  gap: 4px;
}
.image-cell {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.image-cell :deep(.el-image) {
  border-radius: 4px;
  overflow: hidden;
}
.empty-text {
  font-size: 13px;
  color: var(--el-text-color-placeholder);
}
.req-card-stock .req-stock-tag {
  margin-left: 6px;
}
.empty-tip {
  text-align: center;
  padding: 24px;
  color: var(--el-text-color-secondary);
}

/* 移动端卡片 */
.card-list-wrap {
  margin-bottom: 12px;
  /* 留出安全区，避免卡片边框在 iframe 内被裁切 */
  padding: 0 2px;
}
.card-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.req-card {
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
  border-radius: 14px;
  padding: 18px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-left: 4px solid var(--el-color-success);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.req-card:active {
  transform: scale(0.99);
}
/* 字段标签行样式 */
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
.req-location-tag {
  flex-shrink: 0;
}
.req-code {
  font-family: 'SF Mono', 'Monaco', 'Courier New', monospace;
  font-size: 14px;
  color: #409eff;
  font-weight: 600;
  word-break: break-all;
  flex: 1;
}
.req-card-spec {
  font-size: 13px;
  color: #334155;
  line-height: 1.4;
  word-break: break-word;
  flex: 1;
}
.req-card-desc {
  font-size: 14px;
  color: #303133;
  line-height: 1.45;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  flex: 1;
}
.req-card-location {
  font-size: 12px;
  color: #67c23a;
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 1;
  flex-wrap: wrap;
}
.req-card-location .location-icon {
  font-size: 14px;
  flex-shrink: 0;
}
.req-custodian {
  color: #64748b;
  margin-left: 4px;
}
.req-card-drawing {
  font-size: 13px;
  color: #64748b;
  flex: 1;
}
.req-card-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  flex: 1;
}
.req-card-stock-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  flex-wrap: wrap;
}
.req-card-images {
  display: flex;
  gap: 8px;
  flex: 1;
  :deep(.el-image) {
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }
}
.req-drawing { font-size: 12px; color: var(--el-text-color-secondary); }
/* 搜索抽屉两列布局 */
.filter-row-two {
  display: flex;
  gap: 12px;
  .filter-group-half { flex: 1; min-width: 0; }
}
.req-card-physical-image {
  width: 48px;
  height: 48px;
  border-radius: 6px;
  overflow: hidden;
  flex-shrink: 0;
}
.req-card-physical-image :deep(.el-image) {
  border-radius: 6px;
}
.req-card-physical-image-empty {
  font-size: 13px;
  color: var(--el-text-color-placeholder);
}
.req-card-stock {
  font-size: 12px;
  color: #909399;
  margin-bottom: 10px;
}
.req-card-btn {
  width: 100%;
  font-weight: 600;
  padding: 10px 16px;
  border-radius: 8px;
}
.load-more-sentinel {
  min-height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
.load-more-loading {
  color: var(--el-color-primary);
}
.load-more-end {
  color: var(--el-text-color-placeholder);
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
}
</style>
