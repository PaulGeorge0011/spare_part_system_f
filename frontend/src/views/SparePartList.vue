<template>
  <div class="spare-part-list">
    <div class="header">
      <h2>制丝二设备管理</h2>
      <div class="header-buttons">
        <!-- PC 端：全部按钮 -->
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
            <el-button type="warning" @click="handleBatchImageImport">
              <el-icon><Picture /></el-icon>批量导入图片
            </el-button>
            <el-button type="primary" @click="handleCreate">
              <el-icon><Plus /></el-icon>新增设备
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
                <el-dropdown-item command="current" :disabled="store.list.length === 0">
                  导出当前页 ({{ store.list.length }})
                </el-dropdown-item>
                <el-dropdown-item command="all">全部导出</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
        <!-- 移动端：主要操作 + 下拉更多 -->
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
                  <el-dropdown-item command="batch-image">批量导入图片</el-dropdown-item>
                </template>
                <el-dropdown-item command="export-selected" :disabled="selectedRows.length === 0">导出选中</el-dropdown-item>
                <el-dropdown-item command="export-current" :disabled="store.list.length === 0">导出当前页</el-dropdown-item>
                <el-dropdown-item command="export-all">全部导出</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
      </div>
    </div>

    <!-- PC 端：搜索栏 + 过滤器 -->
    <div v-if="!isMobile" class="search-and-filter">
      <div class="search-bar">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索货位号、MES编码、物料描述、规格型号、品牌..."
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
        <el-select v-model="filterUpdatedSince" placeholder="更新时间" clearable style="width: 110px" @change="applyFilters">
          <el-option label="1 天" value="1d" />
          <el-option label="7 天" value="7d" />
          <el-option label="30 天" value="30d" />
          <el-option label="半年" value="6m" />
          <el-option label="一年" value="1y" />
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
        size="80%"
        :append-to-body="true"
        :close-on-click-modal="true"
        :show-close="true"
        :destroy-on-close="false"
        class="spare-part-list-mobile-search-drawer mobile-search-drawer-unified"
        @close="mobileSearchDrawer = false"
      >
        <div class="mobile-filter-form">
          <div class="filter-group">
            <span class="filter-label">关键词</span>
            <el-input
              v-model="searchKeyword"
              placeholder="搜索货位号、MES编码、物料描述、规格型号、品牌..."
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
              <span class="filter-label">更新时间</span>
              <el-select v-model="filterUpdatedSince" placeholder="选择更新时间" clearable style="width: 100%" @change="applyFilters">
                <el-option label="1 天" value="1d" />
                <el-option label="7 天" value="7d" />
                <el-option label="30 天" value="30d" />
                <el-option label="半年" value="6m" />
                <el-option label="一年" value="1y" />
              </el-select>
            </div>
          </div>
          <div class="filter-group">
            <span class="filter-label">货位号前缀</span>
            <el-select v-model="filterLocationPrefix" placeholder="选择货位号前缀" clearable style="width: 100%" @change="applyFilters">
              <el-option v-for="item in filterOptions.location_prefixes" :key="item" :label="item" :value="item" />
              <template #empty>暂无数据</template>
            </el-select>
          </div>
          <div class="filter-actions">
            <el-button v-if="hasActiveFilters" type="default" @click="clearFilters">清空</el-button>
            <el-button type="primary" :icon="Search" @click="handleSearchAndClose" style="flex:1">查询</el-button>
          </div>
        </div>
      </el-drawer>
    </template>

    <!-- 方案四：零库存/低库存横幅 + 直接查询 -->
    <div v-if="!store.loading && (store.list.length > 0 || store.total > 0)" class="stock-alert-banner">
      <template v-if="stockAlertFilter">
        <span class="banner-label">当前筛选：</span>
        <span>{{ stockAlertFilter === 'zero' ? '零库存' : '低库存' }} 共 {{ store.total }} 条</span>
        <el-button type="primary" link size="small" @click="clearStockAlertFilter">清除库存筛选</el-button>
      </template>
      <template v-else>
        <span class="banner-stat">零库存 <strong>{{ store.zeroCount }}</strong> 条</span>
        <span class="banner-divider">|</span>
        <span class="banner-stat">低库存 <strong>{{ store.lowCount }}</strong> 条</span>
        <el-button v-if="store.zeroCount > 0" type="danger" link size="small" @click="setStockAlertFilter('zero')">查看零库存</el-button>
        <el-button v-if="store.lowCount > 0" type="warning" link size="small" @click="setStockAlertFilter('low')">查看低库存</el-button>
      </template>
    </div>

    <!-- 移动端：卡片列表 + 无限滚动 -->
    <div v-if="isMobile" class="card-list-wrap">
      <div class="card-list" v-loading="store.loading && !store.loadingMore">
        <div
          v-for="row in store.list"
          :key="row.id"
          class="spare-card"
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
            <div class="card-field-row">
              <span class="card-field-label">物料描述</span>
              <span class="card-desc">{{ row.mes_material_desc || row.physical_material_desc || '—' }}</span>
            </div>
            <div v-if="row.storage_location" class="card-field-row">
              <span class="card-field-label">存放地</span>
              <div class="card-location">
                <el-icon class="location-icon"><Location /></el-icon>
                <span>{{ row.storage_location }}</span>
              </div>
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
              <span class="stock-info">MES: {{ row.mes_stock ?? 0 }} / 库存: <strong :class="(row.physical_stock ?? 0) > 0 ? 'stock-ok' : 'stock-zero'">{{ row.physical_stock ?? 0 }}</strong> {{ row.unit || '个' }}</span>
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
      <!-- 移动端：滚动加载更多 -->
      <div
        v-if="isMobile && store.list.length > 0"
        ref="loadMoreSentinel"
        class="load-more-sentinel"
      >
        <div v-if="store.loadingMore" class="load-more-loading">加载中...</div>
        <div v-else-if="hasMore" class="load-more-hint">下滑加载更多</div>
        <div v-else class="load-more-end">— 没有更多了 —</div>
      </div>
    </div>

    <!-- PC 端：数据表格（带横向滚动容器） -->
    <div v-else class="table-wrapper">
    <el-table
      ref="tableRef"
      v-loading="store.loading"
      :data="store.list"
      border
      stripe
      style="width: 100%"
      row-key="id"
      highlight-current-row
      :row-class-name="getRequisitionRowClass"
      @selection-change="handleSelectionChange"
    >
      <!-- 选择列 -->
      <el-table-column type="selection" width="55" fixed="left" />

      <!-- 1. 货位号 -->
      <el-table-column 
        prop="location_code" 
        label="货位号" 
        width="100"
        fixed="left"
        sortable
      >
        <template #default="{ row }">
          <el-tag type="info">{{ row.location_code }}</el-tag>
        </template>
      </el-table-column>

      <!-- 2. MES物料编码 -->
      <el-table-column 
        prop="mes_material_code" 
        label="MES物料编码" 
        min-width="220"
        fixed="left"
        sortable
      >
        <template #default="{ row }">
          <div class="code-cell">
            <el-icon 
              v-if="row.mes_material_code"
              class="copy-icon"
              @click="copyToClipboard(row.mes_material_code)"
            >
              <DocumentCopy />
            </el-icon>
            <span class="code-value">{{ row.mes_material_code }}</span>
          </div>
        </template>
      </el-table-column>

      <!-- 3. 规格型号（固定列，紧接 MES 编码） -->
      <el-table-column 
        prop="specification_model" 
        label="规格型号" 
        width="150"
        fixed="left"
        show-overflow-tooltip
        sortable
      >
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

      <!-- 4. MES物料描述 -->
      <el-table-column 
        prop="mes_material_desc" 
        label="MES物料描述" 
        min-width="200"
        show-overflow-tooltip
        sortable
      />

      <!-- 5. 实物物料描述 -->
      <el-table-column 
        prop="physical_material_desc" 
        label="实物物料描述" 
        min-width="250"
        show-overflow-tooltip
        sortable
      />

      <!-- 6. 适用机型 -->
      <el-table-column 
        prop="applicable_model" 
        label="适用机型" 
        width="150"
        show-overflow-tooltip
        sortable
      >
        <template #default="{ row }">
          <el-tag v-if="row.applicable_model" type="warning" size="small">
            {{ formatApplicableModel(row.applicable_model) }}
          </el-tag>
        </template>
      </el-table-column>

      <!-- 7. 品牌 -->
      <el-table-column 
        prop="brand" 
        label="品牌" 
        width="120"
        show-overflow-tooltip
        sortable
      >
        <template #default="{ row }">
          <el-tag v-if="row.brand" type="primary" size="small">
            {{ row.brand }}
          </el-tag>
        </template>
      </el-table-column>

      <!-- 8. MES库存 -->
      <el-table-column prop="mes_stock" label="MES库存" width="120" sortable>
        <template #default="{ row }">
          <div class="stock-cell">
            <el-tag 
              :type="getStockType(row.mes_stock, row.physical_stock)"
              size="small"
            >
              {{ row.mes_stock || 0 }}
            </el-tag>
            <span class="unit-text">{{ row.unit || '个' }}</span>
          </div>
        </template>
      </el-table-column>

      <!-- 9. 实物库存 -->
      <el-table-column prop="physical_stock" label="设备库存" width="120" sortable>
        <template #default="{ row }">
          <div class="stock-cell">
            <el-tag 
              :type="getStockType(row.physical_stock, row.mes_stock)"
              size="small"
            >
              {{ row.physical_stock || 0 }}
            </el-tag>
            <span class="unit-text">{{ row.unit || '个' }}</span>
          </div>
        </template>
      </el-table-column>

      <!-- 10. 单位 -->
      <el-table-column prop="unit" label="单位" width="80" sortable>
        <template #default="{ row }">
          <span class="unit-text">{{ row.unit || '个' }}</span>
        </template>
      </el-table-column>

      <!-- 11. 存放地 -->
      <el-table-column 
        prop="storage_location" 
        label="存放地" 
        width="150"
        show-overflow-tooltip
        sortable
      >
        <template #default="{ row }">
          <el-tag v-if="row.storage_location" type="success" size="small">
            {{ row.storage_location }}
          </el-tag>
          <span v-else class="empty-text">未指定</span>
        </template>
      </el-table-column>

      <!-- 12. 实物图片1 -->
      <el-table-column label="实物图片1" width="120" align="center">
        <template #default="{ row }">
          <div v-if="row.physical_image_url" class="image-cell">
            <el-image
              style="width: 40px; height: 40px; border-radius: 4px;"
              :src="getImageUrlForDisplay(row.physical_image_url)"
              :preview-src-list="[getImageUrlForDisplay(row.physical_image_url)]"
              :zoom-rate="1.2"
              :max-scale="7"
              :min-scale="0.2"
              preview-teleported
              fit="cover"
              :hide-on-click-modal="true"
            />
          </div>
          <span v-else class="empty-text">无</span>
        </template>
      </el-table-column>

            <!-- 12. 实物图片2 -->
      <el-table-column label="实物图片2" width="120" align="center">
        <template #default="{ row }">
          <div v-if="row.physical_image_url2" class="image-cell">
            <el-image
              style="width: 40px; height: 40px; border-radius: 4px;"
              :src="getImageUrlForDisplay(row.physical_image_url2)"
              :preview-src-list="[getImageUrlForDisplay(row.physical_image_url2)]"
              :zoom-rate="1.2"
              :max-scale="7"
              :min-scale="0.2"
              preview-teleported
              fit="cover"
              :hide-on-click-modal="true"
            />
          </div>
          <span v-else class="empty-text">无</span>
        </template>
      </el-table-column>


      <!-- 13. 备注（可选显示） -->
      <el-table-column 
        prop="remarks" 
        label="备注" 
        width="150"
        show-overflow-tooltip
        sortable
      >
        <template #default="{ row }">
          <span v-if="row.remarks" class="remarks-text">{{ row.remarks }}</span>
          <span v-else class="empty-text">-</span>
        </template>
      </el-table-column>

      <!-- 14. 更新时间 -->
      <el-table-column prop="updated_at" label="更新时间" width="160" sortable>
        <template #default="{ row }">
          <span v-if="row.updated_at" class="time-text">
            {{ formatDateTime(row.updated_at) }}
          </span>
          <span v-else class="empty-text">-</span>
        </template>
      </el-table-column>

      <!-- 操作列 -->
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

    <!-- 分页（移动端隐藏「显示全部」与分页器，改用无限滚动） -->
    <div v-if="!isMobile" class="pagination-wrap">
      <div class="pagination-extra">
        <el-link type="primary" :disabled="store.loading" @click="handleShowAll">
          显示全部
        </el-link>
        <span class="pagination-tip">（最多 {{ PAGE_SIZE_ALL }} 条/页）</span>
      </div>
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="pageSizeOptions"
        :layout="'total, sizes, prev, pager, next, jumper'"
        :total="store.total"
        @size-change="handleSizeChange"
        @current-change="handleCurrentChange"
      />
    </div>
    <div v-if="isMobile && store.list.length > 0" class="mobile-total-tip">共 {{ store.total }} 条</div>

    <!-- 表单对话框 -->
    <spare-part-form-dialog
      v-model="dialogVisible"
      :form-data="currentForm"
      :mode="dialogMode"
      @success="handleDialogSuccess"
    />

    <!-- 批量导入对话框 -->
    <BatchImportDialog
      v-model="batchImportDialogVisible"
      @success="handleBatchImportSuccess"
    />
    <!-- 批量更新 MES 库存对话框 -->
    <BatchUpdateDialog
      v-model="batchUpdateDialogVisible"
      type="electrical"
      @success="handleBatchUpdateSuccess"
    />
    <!-- 批量导入图片对话框 -->
    <BatchImageImportDialog
      v-model="batchImageImportDialogVisible"
      :current-page-list="store.list"
      :selected-rows="selectedRows"
      @success="handleBatchImageImportSuccess"
    />
  </div>
</template>

<script setup lang="ts">
// 定义组件名称，用于 keep-alive 缓存
defineOptions({
  name: 'SparePartList'
})

import { ref, onMounted, onUnmounted, onActivated, onDeactivated, nextTick, computed, watch, inject } from 'vue';
import { useRoute } from 'vue-router';
import { Search, Plus, DocumentCopy, Edit, Delete, Upload, Picture, ArrowDown, Location } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import { useSparePartStore } from '@/stores/sparePart';
import { useDataRefresh } from '@/composables/useDataRefresh';
import { useSparePartDataChanged, broadcastSparePartDataChanged } from '@/composables/useSparePartDataChanged';
import SparePartFormDialog from '@/components/SparePartFormDialog.vue';
import BatchImportDialog from '@/components/BatchImportDialog.vue';
import BatchUpdateDialog from '@/components/BatchUpdateDialog.vue';
import BatchImageImportDialog from '@/components/BatchImageImportDialog.vue';
import type { SparePart } from '@/types/sparePart';
import { formatDateTime } from '@/utils/date';
import SparePartImages from '@/components/sparePart/SparePartImages.vue'; // 请确认实际路径
import { deleteImage } from '@/utils/imageUpload';
import { uploadImage } from '@/utils/imageUpload';
import { exportToExcel, type ExportColumn } from '@/utils/exportExcel';
import { sparePartApi, type SparePartFilterOptions } from '@/api/sparePart';
import { useIsMobile } from '@/composables/useIsMobile';
import { scrollMainToTop } from '@/composables/useScrollMainToTop';
import { getImageUrlForDisplay } from '@/utils/image';
import { navLog, navLogStart } from '@/utils/navLog';
import { useAuthStore } from '@/stores/auth';

const route = useRoute();
const authStore = useAuthStore();
const canEdit = computed(() => authStore.canAccessModule('electrical', 'editor'));
const store = useSparePartStore();
const { isMobile } = useIsMobile();

// iframe 移动端：将「更多」下拉挂到 #iframe-mobile-scaler 内，避免 zoom 导致下拉与按钮错位
const mobileDropdownAppendTo = ref<string | undefined>(undefined);

// 搜索相关
const searchKeyword = ref('');

// 过滤器
const filterBrand = ref<string>('');
const filterApplicableModel = ref<string>('');
const filterStorageLocation = ref<string>('');
const filterLocationPrefix = ref<string>('');
const filterUpdatedSince = ref<string>('');
const filterOptions = ref<SparePartFilterOptions>({
  brands: [],
  applicable_models: [],
  storage_locations: [],
  location_prefixes: [],
});

const hasActiveFilters = computed(() =>
  !!(filterBrand.value || filterApplicableModel.value || filterStorageLocation.value || filterLocationPrefix.value || filterUpdatedSince.value)
);

/** 库存提醒筛选：空=全部，zero=仅零库存，low=仅低库存(总库存=1) */
const stockAlertFilter = ref<'zero' | 'low' | ''>('');

async function loadFilterOptions() {
  try {
    const res = await sparePartApi.getFilterOptions();
    if (res?.brands) filterOptions.value.brands = res.brands;
    if (res?.applicable_models) filterOptions.value.applicable_models = res.applicable_models;
    if (res?.storage_locations) filterOptions.value.storage_locations = res.storage_locations;
    if (res?.location_prefixes) filterOptions.value.location_prefixes = res.location_prefixes;
  } catch {
    // 忽略，下拉留空
  }
}

function applyFilters() {
  currentPage.value = 1;
  loadData();
}

function clearFilters() {
  filterBrand.value = '';
  filterApplicableModel.value = '';
  filterStorageLocation.value = '';
  filterLocationPrefix.value = '';
  filterUpdatedSince.value = '';
  stockAlertFilter.value = '';
  currentPage.value = 1;
  loadData();
}

// 分页相关（与后端 limit 上限一致，用于「显示全部」）
const PAGE_SIZE_ALL = 1000;
const pageSizeOptions = [10, 20, 50, 100, PAGE_SIZE_ALL];
const currentPage = ref(1);
const pageSize = ref(20);

// 移动端：搜索抽屉
const mobileSearchDrawer = ref(false);
const openMobileSearch = inject<{ value: boolean }>('openMobileSearch');
if (openMobileSearch) {
  watch(() => openMobileSearch.value, (v) => {
    if (v && route.path === '/electrical/parts') {
      mobileSearchDrawer.value = true;
      openMobileSearch.value = false;
    }
  });
}

// 对话框相关
const dialogVisible = ref(false);
const dialogMode = ref<'create' | 'edit'>('create');
const currentForm = ref<Partial<SparePart>>({});
const batchImportDialogVisible = ref(false);
const batchUpdateDialogVisible = ref(false);
const batchImageImportDialogVisible = ref(false);

// 表格选择相关
const tableRef = ref();
const selectedRows = ref<SparePart[]>([]);
const isBatchDeleting = ref(false);
const exportLoading = ref(false);

// 计算跳过的记录数
const skip = computed(() => (currentPage.value - 1) * pageSize.value);

// 移动端：是否有更多数据可加载
const hasMore = computed(
  () => store.list.length < store.total && !store.loadingMore && !store.loading
);

const loadMoreSentinel = ref<HTMLElement | null>(null);

// 加载数据（必须在 composable 之前定义，供其使用）
const loadData = async () => {
  const t = navLogStart()
  navLog('SparePartList loadData start', {})
  try {
    await store.fetchList({
      skip: skip.value,
      limit: pageSize.value,
      keyword: searchKeyword.value || undefined,
      brand: filterBrand.value || undefined,
      applicable_model: filterApplicableModel.value || undefined,
      storage_location: filterStorageLocation.value || undefined,
      location_prefix: filterLocationPrefix.value || undefined,
      updated_since: filterUpdatedSince.value || undefined,
      stock_alert: stockAlertFilter.value || undefined,
    });
  } catch (error) {
    ElMessage.error('加载数据失败');
    console.error('[修复件管理] 加载数据失败:', error);
  } finally {
    navLog('SparePartList loadData end', {}, t);
  }
};

/** 总库存 = MES库存 + 修复件库存 */
function totalStock(row: SparePart): number {
  return (row.mes_stock ?? 0) + (row.physical_stock ?? 0);
}
/** 方案一：表格行样式 — 零库存红色、低库存黄色 */
function getRequisitionRowClass({ row }: { row: SparePart }) {
  const t = totalStock(row);
  if (t === 0) return 'req-row-zero';
  if (t === 1) return 'req-row-low';
  return '';
}
/** 方案一：卡片样式 — 零库存/低库存高亮 */
function getReqCardStockClass(row: SparePart): string {
  const t = totalStock(row);
  if (t === 0) return 'req-card-zero';
  if (t === 1) return 'req-card-low';
  return '';
}
function setStockAlertFilter(value: 'zero' | 'low') {
  stockAlertFilter.value = value;
  currentPage.value = 1;
  loadData();
}
function clearStockAlertFilter() {
  stockAlertFilter.value = '';
  currentPage.value = 1;
  loadData();
}

// 移动端：加载更多（追加）
const loadMore = async () => {
  if (!hasMore.value || store.loadingMore) return;
  await store.fetchList(undefined, true);
};

// 必须在 setup 顶层调用，否则 onMounted 内注册的监听器可能不生效（页面一收不到页面二广播）
useDataRefresh(loadData);
useSparePartDataChanged(loadData);

// 首帧后再加载数据，避免页面切换时阻塞渲染导致卡顿
function scheduleAfterPaint(fn: () => void) {
  if (typeof requestIdleCallback !== 'undefined') {
    requestIdleCallback(fn, { timeout: 120 });
  } else {
    setTimeout(fn, 0);
  }
}
onMounted(() => {
  navLog('SparePartList mounted', {});
  if (typeof document !== 'undefined' && document.documentElement.classList.contains('iframe-mobile-viewport')) {
    mobileDropdownAppendTo.value = '#iframe-mobile-scaler';
  }
  scheduleAfterPaint(() => {
    navLog('SparePartList scheduleAfterPaint running', {});
    loadFilterOptions();
    loadData();
  });
});
onActivated(() => {
  navLog('SparePartList activated', {});
});
onDeactivated(() => {
  mobileSearchDrawer.value = false;
});

// 移动端：IntersectionObserver 监听滚动加载更多
let observer: IntersectionObserver | null = null;
function setupLoadMoreObserver() {
  if (!isMobile.value || !loadMoreSentinel.value) return;
  observer?.disconnect();
  observer = new IntersectionObserver(
    (entries) => {
      const e = entries[0];
      if (e?.isIntersecting && hasMore.value) loadMore();
    },
    { root: null, rootMargin: '100px', threshold: 0.1 }
  );
  observer.observe(loadMoreSentinel.value);
}
watch(
  [loadMoreSentinel, () => store.list.length],
  () => {
    if (isMobile.value && store.list.length > 0) {
      nextTick(setupLoadMoreObserver);
    }
  },
  { immediate: true }
);
onUnmounted(() => {
  observer?.disconnect();
});

// 导出 Excel：与表格列严格一致（排除实物图片1、实物图片2、操作）
const SPARE_PART_EXPORT_COLUMNS: ExportColumn[] = [
  { key: 'location_code', label: '货位号' },
  { key: 'mes_material_code', label: 'MES物料编码' },
  { key: 'specification_model', label: '规格型号' },
  { key: 'mes_material_desc', label: 'MES物料描述' },
  { key: 'physical_material_desc', label: '实物物料描述' },
  { key: 'applicable_model', label: '适用机型', formatter: (r) => formatApplicableModel((r as SparePart).applicable_model || '') },
  { key: 'brand', label: '品牌' },
  { key: 'mes_stock', label: 'MES库存' },
  { key: 'physical_stock', label: '设备库存' },
  { key: 'unit', label: '单位', formatter: (r) => (r as SparePart).unit || '个' },
  { key: 'storage_location', label: '存放地' },
  { key: 'remarks', label: '备注' },
  { key: 'updated_at', label: '更新时间', formatter: (r) => formatDateTime((r as SparePart).updated_at) || '—' },
];
type ExportScope = 'selected' | 'current' | 'all';
const handleExportExcel = async (scope: ExportScope = 'all') => {
  exportLoading.value = true;
  try {
    let items: SparePart[] = [];
    if (scope === 'selected') {
      items = selectedRows.value;
      if (items.length === 0) {
        ElMessage.warning('请先勾选要导出的记录');
        return;
      }
    } else if (scope === 'current') {
      items = [...store.list];
      if (items.length === 0) {
        ElMessage.warning('当前页无数据可导出');
        return;
      }
    } else {
      const res = await sparePartApi.getList({
        keyword: searchKeyword.value || undefined,
        skip: 0,
        limit: 1000,
        brand: filterBrand.value || undefined,
        applicable_model: filterApplicableModel.value || undefined,
        storage_location: filterStorageLocation.value || undefined,
        location_prefix: filterLocationPrefix.value || undefined,
        updated_since: filterUpdatedSince.value || undefined,
        stock_alert: stockAlertFilter.value || undefined,
      });
      items = Array.isArray((res as any)?.items) ? (res as any).items : (Array.isArray(res) ? res : []);
      if (items.length === 0) {
        ElMessage.warning('当前筛选条件下无数据可导出');
        return;
      }
    }
    const date = new Date().toISOString().slice(0, 10);
    exportToExcel(items, SPARE_PART_EXPORT_COLUMNS, `设备列表_${date}`);
    ElMessage.success(`已导出 ${items.length} 条记录`);
  } catch (e: any) {
    ElMessage.error(e?.message || '导出失败');
  } finally {
    exportLoading.value = false;
  }
};

// 搜索处理
const handleSearch = () => {
  currentPage.value = 1;
  loadData();
};

// 移动端：搜索后关闭抽屉
const handleSearchAndClose = () => {
  handleSearch();
  mobileSearchDrawer.value = false;
  scrollMainToTop();
};

// 分页处理
const handleSizeChange = (val: number) => {
  pageSize.value = val;
  currentPage.value = 1; // 切换每页条数后回到第一页
  loadData();
};

// 显示全部：单页最多 PAGE_SIZE_ALL 条
const handleShowAll = () => {
  pageSize.value = PAGE_SIZE_ALL;
  currentPage.value = 1;
  loadData();
};

const handleCurrentChange = (val: number) => {
  currentPage.value = val;
  loadData();
};

// 新增设备
const handleCreate = () => {
  currentForm.value = {
    mes_stock: 0,
    physical_stock: 0,
    unit: '个',
  };
  dialogMode.value = 'create';
  dialogVisible.value = true;
};

const handleBatchImport = () => {
  batchImportDialogVisible.value = true;
};

const handleBatchImportSuccess = () => {
  loadData();
  broadcastSparePartDataChanged();
};

const handleBatchUpdate = () => {
  batchUpdateDialogVisible.value = true;
};

const handleBatchUpdateSuccess = () => {
  loadData();
  broadcastSparePartDataChanged();
};

const handleBatchImageImport = () => {
  batchImageImportDialogVisible.value = true;
};

const handleBatchImageImportSuccess = () => {
  loadData();
  broadcastSparePartDataChanged();
};

// 编辑设备
const handleEdit = (row: SparePart) => {
  currentForm.value = { ...row };
  dialogMode.value = 'edit';
  dialogVisible.value = true;
};

// 表格选择变化
const handleSelectionChange = (rows: SparePart[]) => {
  selectedRows.value = rows;
};

// 移动端卡片选择
function toggleCardSelection(row: SparePart) {
  const idx = selectedRows.value.findIndex((r) => r.id === row.id);
  if (idx >= 0) {
    selectedRows.value = selectedRows.value.filter((r) => r.id !== row.id);
  } else {
    selectedRows.value = [...selectedRows.value, row];
  }
}
function addSelection(row: SparePart) {
  if (!selectedRows.value.some((r) => r.id === row.id)) {
    selectedRows.value = [...selectedRows.value, row];
  }
}
function removeSelection(row: SparePart) {
  selectedRows.value = selectedRows.value.filter((r) => r.id !== row.id);
}

// 移动端下拉菜单命令
function handleMobileMenuCommand(cmd: string) {
  if (cmd === 'batch-delete') handleBatchDelete();
  else if (cmd === 'batch-import') handleBatchImport();
  else if (cmd === 'batch-update') handleBatchUpdate();
  else if (cmd === 'batch-image') handleBatchImageImport();
  else if (cmd === 'export-selected') handleExportExcel('selected');
  else if (cmd === 'export-current') handleExportExcel('current');
  else if (cmd === 'export-all') handleExportExcel('all');
}

// 批量删除设备
const handleBatchDelete = async () => {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请先选择要删除的设备');
    return;
  }
  
  try {
    const count = selectedRows.value.length;
    const ids = selectedRows.value.map(row => row.id);
    const mesCodes = selectedRows.value.map(row => row.mes_material_code).join('、');
    
    await ElMessageBox.confirm(
      `确定删除选中的 ${count} 个设备吗？\n涉及：${mesCodes.substring(0, 100)}${mesCodes.length > 100 ? '...' : ''}\n此操作不可恢复。`,
      '确认批量删除',
      {
        type: 'warning',
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        confirmButtonClass: 'el-button--danger',
        dangerouslyUseHTMLString: false,
      }
    );
    
    isBatchDeleting.value = true;
    try {
      const result = await store.batchDeleteSpareParts(ids);
      const { deleted, failed, errors } = result;
      
      if (failed === 0) {
        ElMessage.success(`成功删除 ${deleted} 个设备`);
      } else {
        ElMessage.warning(`删除完成：成功 ${deleted} 个，失败 ${failed} 个`);
        if (errors && errors.length > 0) {
          console.error('批量删除错误:', errors);
        }
      }
      
      // 清空选择
      tableRef.value?.clearSelection();
      selectedRows.value = [];
      
      // 刷新数据
      loadData();
      broadcastSparePartDataChanged();
    } finally {
      isBatchDeleting.value = false;
    }
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('批量删除失败');
      console.error('批量删除失败:', error);
    }
  }
};

// 删除设备
const handleDelete = async (row: SparePart) => {
  try {
    await ElMessageBox.confirm(
      `确定删除设备 "${row.mes_material_code}" 吗？此操作不可恢复。`,
      '确认删除',
      {
        type: 'warning',
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        confirmButtonClass: 'el-button--danger',
      }
    );
    
    await store.deleteSparePart(row.id);
    ElMessage.success('删除成功');
    loadData();
    broadcastSparePartDataChanged();
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败');
    }
  }
};

// 对话框成功回调：表单内已通过 createSparePartWithImages / updateSparePartWithImages 完成 API 调用，此处仅刷新列表
const handleDialogSuccess = (_result?: { mode?: string; data?: any; id?: number }) => {
  dialogVisible.value = false;
  loadData();
  broadcastSparePartDataChanged();
};

// 复制到剪贴板
const copyToClipboard = (text: string) => {
  navigator.clipboard.writeText(text)
    .then(() => {
      ElMessage.success('已复制到剪贴板');
    })
    .catch(() => {
      // 降级方案
      const textArea = document.createElement('textarea');
      textArea.value = text;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
      ElMessage.success('已复制到剪贴板');
    });
};

// 格式化适用机型（如果是逗号分隔的字符串）
const formatApplicableModel = (modelString: string) => {
  if (!modelString) return '';
  const models = modelString.split(',').map(m => m.trim());
  return models.length > 2 ? `${models[0]}等${models.length}个` : modelString;
};

// 获取库存标签类型
const getStockType = (current: number, compare: number) => {
  if (!current && current !== 0) return 'info';
  
  // 如果有对比库存，显示差异
  if (compare !== undefined && compare !== null) {
    const diff = Math.abs(current - compare);
    if (diff > 10) return 'danger'; // 差异较大
    if (diff > 5) return 'warning'; // 有差异
  }
  
  // 根据库存数量显示handleDialogSuccess
  if (current === 0) return 'danger'; // 零库存
  if (current < 10) return 'warning'; // 低库存
  return 'success'; // 正常库存
};
</script>

<style scoped lang="scss">
.spare-part-list {
  padding: 20px;
  background: #f5f7fa;
  min-height: calc(100vh - 60px);
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;

  .header-buttons {
    display: flex;
    gap: 12px;
  }
  
  h2 {
    margin: 0;
    color: #303133;
    font-size: 24px;
    font-weight: 600;
  }
}

.search-and-filter {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.search-bar {
  flex: 0 0 auto;
  min-width: 280px;
  max-width: 400px;
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.filter-bar .el-select {
  flex-shrink: 0;
}

.code-cell {
  display: flex;
  align-items: center;
  justify-content: space-between;
  
  .code-value {
    font-family: 'Courier New', monospace;
    font-weight: bold;
    color: #409eff;
  }
  
  .copy-icon {
    margin-left: 8px;
    cursor: pointer;
    color: #909399;
    transition: color 0.3s;
    
    &:hover {
      color: #409eff;
    }
  }
}

.stock-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  
  .unit-text {
    color: #909399;
    font-size: 12px;
  }
}


.image-group {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
}

.image-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  
  .el-image {
    cursor: pointer;
    transition: transform 0.3s;
    
    &:hover {
      transform: scale(1.1);
    }
  }
  
  .image-label {
    font-size: 10px;
    color: #909399;
    margin-top: 2px;
  }
}

.table-image-cell {
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-text {
  color: #c0c4cc;
  font-style: italic;
}

.remarks-text {
  font-size: 12px;
  color: #666;
  line-height: 1.4;
}

.time-text {
  font-size: 12px;
  color: #909399;
}

.empty-text {
  color: #c0c4cc;
  font-style: italic;
}

.action-buttons {
  display: flex;
  gap: 8px;
  justify-content: center;
}

.pagination-wrap {
  margin-top: 24px;
  padding: 16px;
  background: white;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 12px;
}

.pagination-extra {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pagination-tip {
  font-size: 12px;
  color: #909399;
}

// 方案一+方案四：库存提醒横幅与行/卡片高亮
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

  .banner-label { font-weight: 500; }
  .banner-stat strong { margin: 0 2px; }
  .banner-divider { color: #d97706; margin: 0 4px; }
}

.table-wrapper :deep(.el-table tr.req-row-zero) {
  --el-table-tr-bg-color: #fef2f2;
  background-color: #fef2f2 !important;
}
.table-wrapper :deep(.el-table tr.req-row-zero:hover > td) {
  background-color: #fee2e2 !important;
}
.table-wrapper :deep(.el-table tr.req-row-low) {
  --el-table-tr-bg-color: #fffbeb;
  background-color: #fffbeb !important;
}
.table-wrapper :deep(.el-table tr.req-row-low:hover > td) {
  background-color: #fef3c7 !important;
}

.spare-card.req-card-zero {
  border-left-color: var(--el-color-danger);
  background: linear-gradient(to bottom, #fef2f2, #fee2e2);
}
.spare-card.req-card-low {
  border-left-color: var(--el-color-warning);
  background: linear-gradient(to bottom, #fffbeb, #fef3c7);
}

// 表格横向滚动容器（小屏时）
.table-wrapper {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

// 移动端卡片列表
.card-list-wrap {
  margin-bottom: 16px;
}

.card-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.load-more-sentinel {
  min-height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  font-size: 13px;
  color: #909399;
}

.load-more-loading {
  color: var(--el-color-primary);
}

.load-more-end {
  color: #c0c4cc;
}

.mobile-total-tip {
  text-align: center;
  padding: 12px;
  font-size: 13px;
  color: #909399;
}

.spare-card {
  background: linear-gradient(to bottom, #ffffff, #fafbff);
  border-radius: 12px;
  padding: 14px 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04);
  border: 1px solid var(--el-border-color-lighter);
  border-left: 4px solid var(--el-color-primary-light-5);
  transition: box-shadow 0.2s ease, transform 0.2s ease;

  &:active {
    transform: scale(0.99);
  }

  &.card-selected {
    border-left-color: var(--el-color-primary);
    background: linear-gradient(to bottom, var(--el-color-primary-light-9), #fff);
    box-shadow: 0 2px 12px rgba(64, 158, 255, 0.15);
  }
}

.card-main {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.card-content {
  flex: 1;
  min-width: 0;
}

/* 字段标签行样式 */
.card-field-row {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-bottom: 5px;
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

.card-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.card-row-top {
  margin-bottom: 6px;
}

.card-code {
  font-family: 'SF Mono', 'Monaco', 'Courier New', monospace;
  font-size: 14px;
  color: #409eff;
  font-weight: 600;
  flex: 1;
  word-break: break-all;
}

.card-location {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #67c23a;
  flex: 1;

  .location-icon {
    font-size: 14px;
    flex-shrink: 0;
  }
}

.card-desc {
  font-size: 13px;
  color: #606266;
  line-height: 1.45;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  flex: 1;
}

.card-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  flex: 1;
}

.stock-info {
  font-size: 12px;
  color: #909399;
  flex: 1;

  .stock-ok { color: #67c23a; font-weight: 600; }
  .stock-zero { color: #f56c6c; font-weight: 600; }
}

.card-images {
  display: flex;
  gap: 8px;
  flex: 1;

  :deep(.el-image) {
    border-radius: 6px;
    overflow: hidden;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }
}

/* 搜索抽屉两列布局 */
.filter-row-two {
  display: flex;
  gap: 12px;
  margin-bottom: 0;
  .filter-group-half { flex: 1; min-width: 0; }
}

.card-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed var(--el-border-color-lighter);
}

// 响应式调整
@media (max-width: 1200px) {
  .spare-part-list {
    padding: 16px;
  }

  .header h2 {
    font-size: 20px;
  }
}

@media (max-width: 767px) {
  .spare-part-list {
    padding: 0 0 16px;
  }

  .header {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;

    h2 {
      font-size: 18px;
      margin: 0;
    }

    .header-buttons {
      justify-content: flex-start;
    }
  }

  .search-and-filter {
    flex-direction: column;
    align-items: stretch;
  }

  .mobile-filter-form .filter-actions {
    display: flex;
    gap: 12px;
    margin-top: 8px;
  }

  .search-bar {
    min-width: 0;
    max-width: none;
  }

  .filter-bar {
    flex-direction: column;
  }

  .filter-bar :deep(.el-select),
  .filter-bar .el-button {
    width: 100% !important;
    max-width: none;
  }

  .pagination-wrap {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>