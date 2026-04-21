<template>
  <el-dialog
    v-model="dialogVisible"
    title="批量新增修复件"
    :width="isMobile ? '95%' : '90%'"
    :close-on-click-modal="false"
    @close="handleClose"
    class="batch-import-dialog"
  >
    <el-steps :active="currentStep" finish-status="success" style="margin-bottom: 20px">
      <el-step title="上传Excel" />
      <el-step title="字段映射" />
      <el-step title="数据预览" />
      <el-step title="导入结果" />
    </el-steps>

    <!-- 步骤1: 上传Excel -->
    <div v-if="currentStep === 0" class="step-content">
      <div class="batch-mode-row">
        <span class="mode-label">批量上传模式：</span>
        <el-radio-group v-model="batchMode" class="batch-mode-group">
          <el-radio-button value="full">
            <span class="mode-title">模式一：全部读取</span>
            <span class="mode-desc">不做数据验证，按行读取文件中全部数据并导入</span>
          </el-radio-button>
          <el-radio-button value="validate">
            <span class="mode-title">模式二：数据验证</span>
            <span class="mode-desc">仅导入必填字段完整的行，其余行不参与导入</span>
          </el-radio-button>
        </el-radio-group>
      </div>
      <el-upload
        ref="uploadRef"
        :auto-upload="false"
        :on-change="handleFileChange"
        :limit="1"
        accept=".xlsx,.xls"
        :disabled="isParsing"
        drag
      >
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">
          将Excel文件拖到此处，或<em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">仅支持 .xlsx 或 .xls。.xlsx 表内嵌入图片会自动提取（含 Excel 浮动图片与 WPS 嵌入单元格图片 =DISPIMG("ID_xxx",1)），可映射为「本行嵌入图片1」「本行嵌入图片2」。</div>
        </template>
      </el-upload>
      
      <!-- 解析进度 -->
      <div v-if="isParsing" class="parsing-progress">
        <div class="progress-header">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span class="progress-text">{{ parsingStatus }}</span>
        </div>
        <el-progress
          :percentage="parsingProgress"
          :status="parsingProgress === 100 ? 'success' : undefined"
          :stroke-width="8"
          :show-text="true"
        />
        <div v-if="parsingDetail" class="progress-detail">{{ parsingDetail }}</div>
      </div>
      
      <div v-if="excelColumns.length > 0 && !isParsing" class="columns-preview">
        <h4>检测到的列：</h4>
        <el-tag v-for="col in excelColumns" :key="col" style="margin: 4px">{{ col }}</el-tag>
      </div>
    </div>

    <!-- 步骤2: 字段映射 -->
    <div v-if="currentStep === 1" class="step-content">
      <el-alert
        type="info"
        :closable="false"
        style="margin-bottom: 20px"
      >
        <template #title>
          <div>请为每个必填字段选择对应的Excel列（带<span style="color: red">*</span>的为必填）</div>
        </template>
      </el-alert>
      <div class="table-scroll-wrap">
      <el-table :data="fieldMapping" border style="width: 100%">
        <el-table-column prop="fieldLabel" label="修复件字段" width="200" sortable>
          <template #default="{ row }">
            <span v-if="row.required" style="color: red">*</span>
            {{ row.fieldLabel }}
          </template>
        </el-table-column>
        <el-table-column prop="fieldName" label="字段名" width="150" sortable />
        <el-table-column label="对应Excel列" min-width="300">
          <template #default="{ row }">
            <el-select
              v-model="row.excelColumn"
              placeholder="请选择Excel列"
              clearable
              style="width: 100%"
            >
              <el-option
                v-for="col in excelColumns"
                :key="col"
                :label="col"
                :value="col"
              />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="默认值" width="200">
          <template #default="{ row }">
            <el-input
              v-if="!row.required"
              v-model="row.defaultValue"
              :placeholder="row.defaultValuePlaceholder"
              size="small"
            />
            <span v-else style="color: #909399">-</span>
          </template>
        </el-table-column>
      </el-table>
      </div>
    </div>

    <!-- 步骤3: 数据预览 -->
    <div v-if="currentStep === 2" class="step-content step-preview-wrap">
      <div v-if="isImporting" class="import-overlay">
        <div class="import-progress-box">
          <el-icon class="is-loading"><Loading /></el-icon>
          <div class="import-status">{{ importStatus }}</div>
          <el-progress
            :percentage="importProgress"
            :stroke-width="8"
            style="max-width: 360px; margin: 16px auto 0;"
          />
        </div>
      </div>
      <el-alert
        type="warning"
        :closable="false"
        style="margin-bottom: 12px"
      >
        <template #title>
          <div>
            共 {{ totalPreviewRows }} 条数据，请检查预览数据是否正确
            <span class="mode-hint">（{{ batchMode === 'full' ? '模式一：全部读取，未做行级验证' : '模式二：数据验证，仅含必填完整的行' }}）</span>
          </div>
        </template>
      </el-alert>
      <div v-if="totalPreviewRows > 0" class="range-row">
        <span class="range-label">本次导入行范围：</span>
        <el-input-number
          v-model="importRangeStart"
          :min="1"
          :max="totalPreviewRows"
          :step="1"
          size="small"
        />
        <span class="range-separator">至</span>
        <el-input-number
          v-model="importRangeEnd"
          :min="1"
          :max="totalPreviewRows"
          :step="1"
          size="small"
        />
        <span class="range-hint">（共 {{ totalPreviewRows }} 行，实际将导入 {{ effectivePreviewData.length }} 行）</span>
      </div>
      <div class="table-scroll-wrap">
      <el-table :data="effectivePreviewData" border max-height="400" style="width: 100%">
        <template v-for="field in visibleFields" :key="field.fieldName">
          <el-table-column
            v-if="field.type === 'image'"
            :prop="field.fieldName"
            :label="field.fieldLabel"
            :min-width="field.minWidth || 120"
            align="center"
            sortable
          >
            <template #default="{ row }">
              <div v-if="row[field.fieldName]" class="image-preview-cell">
                <el-image
                  :src="previewImageSrc(row[field.fieldName])"
                  style="width: 60px; height: 60px; border-radius: 4px;"
                  fit="cover"
                  :preview-src-list="[previewImageSrc(row[field.fieldName])]"
                  preview-teleported
                  hide-on-click-modal
                />
              </div>
              <span v-else class="empty-text">-</span>
            </template>
          </el-table-column>
          <el-table-column
            v-else
            :prop="field.fieldName"
            :label="field.fieldLabel"
            :min-width="field.minWidth || 120"
            show-overflow-tooltip
            sortable
          />
        </template>
      </el-table>
      </div>
    </div>

    <!-- 步骤4: 导入结果 -->
    <div v-if="currentStep === 3" class="step-content">
      <el-result
        :icon="importResult.success ? 'success' : 'error'"
        :title="importResult.title"
        :sub-title="importResult.subTitle"
      >
        <template #extra>
          <div v-if="importResult.details" class="import-details">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="成功">{{ importResult.details.success || 0 }} 条</el-descriptions-item>
              <el-descriptions-item label="失败">{{ importResult.details.failed || 0 }} 条</el-descriptions-item>
              <el-descriptions-item label="跳过">{{ importResult.details.skipped || 0 }} 条</el-descriptions-item>
              <el-descriptions-item label="总计">{{ importResult.details.total || 0 }} 条</el-descriptions-item>
            </el-descriptions>
            <div v-if="importResult.details.errors && importResult.details.errors.length > 0" style="margin-top: 20px">
              <h4>错误详情：</h4>
              <el-table :data="importResult.details.errors" border max-height="200">
                <el-table-column prop="row" label="行号" width="80" sortable />
                <el-table-column prop="message" label="错误信息" sortable />
              </el-table>
            </div>
          </div>
        </template>
      </el-result>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button :disabled="isImporting" @click="handleClose">取消</el-button>
        <el-button v-if="currentStep > 0 && !isImporting" @click="handlePrev">上一步</el-button>
        <el-button
          v-if="currentStep < 3"
          type="primary"
          :disabled="!canNext || isImporting"
          :loading="isImporting && currentStep === 2"
          @click="handleNext"
        >
          {{ currentStep === 2 ? '开始导入' : '下一步' }}
        </el-button>
        <el-button
          v-if="currentStep === 3"
          type="primary"
          @click="handleClose"
        >
          完成
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useIsMobile } from '@/composables/useIsMobile'

const { isMobile } = useIsMobile()
import { UploadFilled, Loading } from '@element-plus/icons-vue'
import * as XLSX from 'xlsx'
import { createSparePartWithImages } from '@/api/sparePart'
import type { SparePartCreate } from '@/types/sparePart'
import { downloadAndUploadImageFromUrl, uploadTempImageFromBlob } from '@/utils/imageUpload'
import { extractEmbeddedImagesFromXlsx, getOrderedAnchorsWithBlobs, pickTwoDistinctBlobsPerRow } from '@/utils/excelEmbeddedImages'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'success': []
}>()

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const currentStep = ref(0)
/** 模式一 full：全部读取不做验证；模式二 validate：仅导入必填字段完整的行 */
const batchMode = ref<'full' | 'validate'>('validate')
const uploadRef = ref()
const excelFile = ref<File | null>(null)
const excelColumns = ref<string[]>([])
const excelData = ref<any[]>([])
const fieldMapping = ref<FieldMappingItem[]>([])
// 所有通过字段映射与验证后的行（完整列表）
const previewAllRows = ref<any[]>([])
// 当前要导入的行范围（基于预览列表的 1-based 索引）
const importRangeStart = ref(1)
const importRangeEnd = ref(0)
const importResult = ref<ImportResult>({
  success: false,
  title: '',
  subTitle: '',
  details: null
})

// 解析进度相关
const isParsing = ref(false)
const parsingProgress = ref(0)
const parsingStatus = ref('准备解析...')
const parsingDetail = ref('')

// 导入进度相关
const isImporting = ref(false)
const importProgress = ref(0)
const importStatus = ref('')

// 字段定义
const fieldDefinitions: FieldDefinition[] = [
  { fieldName: 'location_code', fieldLabel: '货位号', required: true, minWidth: 100 },
  { fieldName: 'mes_material_code', fieldLabel: 'MES物料编码', required: false, minWidth: 150 },
  { fieldName: 'specification_model', fieldLabel: '规格型号', required: true, minWidth: 150 },
  { fieldName: 'mes_material_desc', fieldLabel: 'MES物料描述', required: false, minWidth: 200 },
  { fieldName: 'physical_material_desc', fieldLabel: '实物物料描述', required: false, minWidth: 200 },
  { fieldName: 'applicable_model', fieldLabel: '适用机型', required: false, minWidth: 150 },
  { fieldName: 'brand', fieldLabel: '品牌', required: false, minWidth: 100 },
  { fieldName: 'mes_stock', fieldLabel: 'MES库存', required: false, minWidth: 100, type: 'number' },
  { fieldName: 'physical_stock', fieldLabel: '实物库存', required: false, minWidth: 100, type: 'number' },
  { fieldName: 'unit', fieldLabel: '单位', required: false, minWidth: 80, defaultValue: '个' },
  { fieldName: 'remarks', fieldLabel: '备注', required: false, minWidth: 200 },
  { fieldName: 'storage_location', fieldLabel: '存放地', required: false, minWidth: 150 },
  { fieldName: 'image_url_1', fieldLabel: '实物图片1 (URL)', required: false, minWidth: 200, type: 'image' },
  { fieldName: 'image_url_2', fieldLabel: '实物图片2 (URL)', required: false, minWidth: 200, type: 'image' },
]

interface FieldDefinition {
  fieldName: string
  fieldLabel: string
  required: boolean
  minWidth?: number
  type?: 'string' | 'number' | 'image'
  defaultValue?: string
}

interface FieldMappingItem {
  fieldName: string
  fieldLabel: string
  required: boolean
  excelColumn: string | null
  defaultValue: string
  defaultValuePlaceholder?: string
  type?: 'string' | 'number' | 'image'
}

interface ImportResult {
  success: boolean
  title: string
  subTitle: string
  details: {
    success: number
    failed: number
    skipped: number
    total: number
    errors?: Array<{ row: number; message: string }>
  } | null
}

const visibleFields = computed(() => {
  return fieldMapping.value.filter(f => f.excelColumn || f.defaultValue)
})

// 总预览条数
const totalPreviewRows = computed(() => previewAllRows.value.length)

// 按用户选择的起止行裁剪后的实际导入数据
const effectivePreviewData = computed(() => {
  const all = previewAllRows.value
  if (!all.length) return []
  const total = all.length
  const start = Math.min(Math.max(1, Number(importRangeStart.value || 1)), total)
  const end = Math.min(
    total,
    Math.max(start, Number(importRangeEnd.value || total)),
  )
  return all.slice(start - 1, end)
})

const canNext = computed(() => {
  if (currentStep.value === 0) {
    return excelColumns.value.length > 0
  }
  if (currentStep.value === 1) {
    // 检查必填字段是否都已映射
    return fieldMapping.value
      .filter(f => f.required)
      .every(f => f.excelColumn)
  }
  if (currentStep.value === 2) {
    return effectivePreviewData.value.length > 0
  }
  return true
})

const embedPreviewUrls = new Set<string>()
function previewImageSrc(val: any): string {
  if (val instanceof Blob) {
    const u = URL.createObjectURL(val)
    embedPreviewUrls.add(u)
    return u
  }
  return String(val || '')
}

function revokeEmbedPreviewUrls() {
  embedPreviewUrls.forEach(u => URL.revokeObjectURL(u))
  embedPreviewUrls.clear()
}

function yieldToMain() {
  return new Promise<void>(resolve => {
    if (typeof requestAnimationFrame !== 'undefined') {
      requestAnimationFrame(() => setTimeout(resolve, 0))
    } else {
      setTimeout(resolve, 0)
    }
  })
}

/**
 * 优化工作表范围，避免处理大量空白区域
 * 某些Excel文件的 !ref 可能被错误设置为整个工作表范围（如 A1:XFD1048576）
 * 这会导致 sheet_to_json 遍历数百万个空单元格而卡住
 */
function getOptimizedRange(worksheet: XLSX.WorkSheet): string | null {
  try {
    const ref = worksheet['!ref']
    if (!ref) return null
    
    const range = XLSX.utils.decode_range(ref)
    const totalCells = (range.e.r - range.s.r + 1) * (range.e.c - range.s.c + 1)
    
    // 如果单元格数量合理（小于100万），不需要优化
    if (totalCells < 1000000) {
      console.log(`[BatchImport] 工作表范围正常: ${ref}, 单元格数: ${totalCells}`)
      return null
    }
    
    console.warn(`[BatchImport] 工作表范围过大: ${ref}, 单元格数: ${totalCells}, 开始优化...`)
    
    // 使用更高效的方式：直接遍历worksheet的键找到实际存在的单元格
    let minRow = Infinity, maxRow = -1
    let minCol = Infinity, maxCol = -1
    
    // worksheet 的键包含单元格地址（如 "A1", "B2"）和特殊属性（如 "!ref", "!cols"）
    const cellAddressRegex = /^([A-Z]+)(\d+)$/
    
    for (const key of Object.keys(worksheet)) {
      if (key.startsWith('!')) continue // 跳过特殊属性
      
      const match = key.match(cellAddressRegex)
      if (!match) continue
      
      const cell = worksheet[key]
      if (!cell || cell.v === undefined || cell.v === null || cell.v === '') continue
      
      // 解析单元格地址
      const decoded = XLSX.utils.decode_cell(key)
      minRow = Math.min(minRow, decoded.r)
      maxRow = Math.max(maxRow, decoded.r)
      minCol = Math.min(minCol, decoded.c)
      maxCol = Math.max(maxCol, decoded.c)
    }
    
    // 如果没找到数据，返回null（让sheet_to_json自己处理）
    if (maxRow === -1 || maxCol === -1) {
      console.warn('[BatchImport] 未找到有效数据，使用原始范围')
      return null
    }
    
    // 构建优化后的范围
    const newRange = XLSX.utils.encode_range({
      s: { r: minRow, c: minCol },
      e: { r: maxRow, c: maxCol }
    })
    
    const newTotalCells = (maxRow - minRow + 1) * (maxCol - minCol + 1)
    console.log(`[BatchImport] 优化后范围: ${newRange}, 单元格数: ${newTotalCells}`)
    
    return newRange
  } catch (e) {
    console.warn('[BatchImport] 优化范围失败:', e)
    return null
  }
}

function handleFileChange(file: any) {
  const raw = file?.raw
  if (!raw) {
    ElMessage.error('未获取到文件内容，请重新选择文件')
    return
  }
  // 部分浏览器/上传组件会重复复用同一个 Blob，构造一个新的 File 更稳定
  const f = raw instanceof File ? raw : new File([raw], file.name || raw.name || 'import.xlsx', { type: raw.type || file.raw?.type || '' })
  excelFile.value = f
  parseExcel(f)
}

function parseExcel(file: File) {
  // 重置状态
  isParsing.value = true
  parsingProgress.value = 0
  parsingStatus.value = '正在读取文件...'
  parsingDetail.value = ''
  excelColumns.value = []
  excelData.value = []
  
  const reader = new FileReader()
  
  reader.onprogress = (e) => {
    if (e.lengthComputable) {
      const progress = Math.round((e.loaded / e.total) * 30) // 读取文件占30%
      parsingProgress.value = progress
      parsingDetail.value = `已读取 ${(e.loaded / 1024 / 1024).toFixed(2)} MB / ${(e.total / 1024 / 1024).toFixed(2)} MB`
    }
  }
  
  reader.onload = async (e) => {
    try {
      parsingProgress.value = 30
      parsingStatus.value = '正在解析Excel结构...'
      parsingDetail.value = ''
      
      // 先让 UI 渲染「解析中」再执行耗时逻辑
      await yieldToMain()
      
      const arrayBuffer = e.target?.result as ArrayBuffer
      const data = new Uint8Array(arrayBuffer)
      parsingProgress.value = 50
      parsingStatus.value = '正在解析工作表...'
      await yieldToMain()
      
      const workbook = XLSX.read(data, { type: 'array' })
      const firstSheetName = workbook.SheetNames[0]
      parsingProgress.value = 60
      parsingDetail.value = `工作表: ${firstSheetName}`
      await yieldToMain()
      
      const worksheet = workbook.Sheets[firstSheetName]
      parsingProgress.value = 70
      parsingStatus.value = '正在转换数据...'
      await yieldToMain()
      
      // 优化：检测并限制工作表范围，避免处理大量空白区域
      const optimizedRange = getOptimizedRange(worksheet)
      if (optimizedRange) {
        parsingDetail.value = `优化范围: ${optimizedRange}`
        await yieldToMain()
      }
      
      const jsonData = XLSX.utils.sheet_to_json(worksheet, { 
        header: 1, 
        defval: '',
        range: optimizedRange || undefined
      })
      parsingProgress.value = 80
      
      if (jsonData.length === 0) {
        isParsing.value = false
        parsingProgress.value = 0
        ElMessage.error('Excel文件为空')
        return
      }
      
      parsingStatus.value = '正在处理数据...'
      parsingDetail.value = `共 ${jsonData.length - 1} 行数据`
      
      const headers = jsonData[0] as string[]
      excelColumns.value = headers.filter(h => h && String(h).trim())
      parsingProgress.value = 85
      await yieldToMain()
      
      const rows = jsonData.slice(1) as any[][]
      const totalRows = rows.length
      const CHUNK = Math.max(1, Math.floor(totalRows / 20) || 1)
      const result: any[] = []
      let embeddedMap = new Map<number, { blob: Blob; col: number; row: number }[]>()
      
      if (file.name.toLowerCase().endsWith('.xlsx')) {
        try {
          parsingStatus.value = '正在提取表格内嵌入图片...'
          await yieldToMain()
          embeddedMap = await extractEmbeddedImagesFromXlsx(arrayBuffer)
        } catch (ex) {
          console.warn('提取嵌入图片失败，将仅使用URL列:', ex)
        }
      }
      
      for (let i = 0; i < rows.length; i++) {
        const row = rows[i]
        const obj: any = { _rowIndex: i + 2 }
        headers.forEach((header, colIndex) => {
          if (header && String(header).trim()) {
            obj[String(header).trim()] = row[colIndex] ?? ''
          }
        })
        result.push(obj)
        if ((i + 1) % CHUNK === 0 || i === rows.length - 1) {
          parsingProgress.value = 85 + Math.round(((i + 1) / totalRows) * 10)
          await yieldToMain()
        }
      }
      
      let hasEmbedded = false
      if (file.name.toLowerCase().endsWith('.xlsx')) {
        const ordered = await getOrderedAnchorsWithBlobs(arrayBuffer)
        if (ordered.length > 0) {
          // 补齐 result：sheet_to_json 可能跳过末尾空行，导致有图的行没有对应 result，先按最大 dataRowIndex 补足行
          const maxDataRowIndex = Math.max(...ordered.map((o) => o.dataRowIndex))
          while (result.length <= maxDataRowIndex) {
            const emptyRow: any = { _rowIndex: result.length + 2 }
            headers.forEach((header) => {
              if (header && String(header).trim()) emptyRow[String(header).trim()] = ''
            })
            result.push(emptyRow)
          }
          const byRow = new Map<number, Array<{ col: number; blob: Blob; source?: 'drawing' | 'dispimg' }>>()
          for (const { dataRowIndex, col, blob, source } of ordered) {
            if (dataRowIndex < 0) continue
            const arr = byRow.get(dataRowIndex) ?? []
            arr.push({ col, blob, source })
            byRow.set(dataRowIndex, arr)
          }
          for (const [dataRowIndex, arr] of byRow) {
            const [b1, b2] = pickTwoDistinctBlobsPerRow(arr)
            if (dataRowIndex < 0 || dataRowIndex >= result.length) continue
            const rowObj = result[dataRowIndex]
            if (b1) rowObj['本行嵌入图片1'] = b1
            if (b2) rowObj['本行嵌入图片2'] = b2
            hasEmbedded = true
          }
        } else {
          for (let j = 0; j < result.length; j++) {
            const rowObj = result[j]
            const imgs = embeddedMap.get(j) ?? []
            if (imgs.length > 0) {
              const [b1, b2] = pickTwoDistinctBlobsPerRow(imgs.map((i) => ({ col: i.col, blob: i.blob })))
              if (b1) rowObj['本行嵌入图片1'] = b1
              if (b2) rowObj['本行嵌入图片2'] = b2
              hasEmbedded = true
            }
          }
        }
      }
      excelData.value = result
      if (hasEmbedded) {
        const baseCols = [...excelColumns.value]
        if (!baseCols.includes('本行嵌入图片1')) baseCols.push('本行嵌入图片1')
        if (!baseCols.includes('本行嵌入图片2')) baseCols.push('本行嵌入图片2')
        excelColumns.value = baseCols
      }
      parsingProgress.value = 95
      parsingStatus.value = '正在初始化字段映射...'
      await yieldToMain()
      
      initFieldMapping()
      
      parsingProgress.value = 100
      parsingStatus.value = '解析完成！'
      parsingDetail.value = `成功解析 ${excelData.value.length} 行数据，${excelColumns.value.length} 个列`
      await yieldToMain()
      
      await new Promise(r => setTimeout(r, 400))
      isParsing.value = false
      parsingProgress.value = 0
      ElMessage.success(`成功解析Excel，共 ${excelData.value.length} 行数据`)
      
    } catch (error) {
      isParsing.value = false
      parsingProgress.value = 0
      console.error('解析Excel失败:', error)
      ElMessage.error('解析Excel文件失败，请检查文件格式')
    }
  }
  
  reader.onerror = () => {
    isParsing.value = false
    parsingProgress.value = 0
    ElMessage.error('文件读取失败')
  }
  
  reader.readAsArrayBuffer(file)
}

function initFieldMapping() {
  fieldMapping.value = fieldDefinitions.map(def => ({
    fieldName: def.fieldName,
    fieldLabel: def.fieldLabel,
    required: def.required,
    excelColumn: null,
    defaultValue: def.defaultValue || '',
    defaultValuePlaceholder: def.defaultValue ? `默认: ${def.defaultValue}` : '',
    type: def.type || 'string'
  }))
  
  const hasEmbedded1 = excelColumns.value.includes('本行嵌入图片1')
  const hasEmbedded2 = excelColumns.value.includes('本行嵌入图片2')
  fieldMapping.value.forEach(mapping => {
    const fieldName = mapping.fieldName.toLowerCase()
    let matched: string | undefined
    if (fieldName === 'image_url_1') {
      if (hasEmbedded1) matched = '本行嵌入图片1'
      else matched = excelColumns.value.find(col => {
        const c = String(col).toLowerCase()
        return c.includes('图片1') || c.includes('图片') || c.includes('image') || c.includes('photo')
      })
    } else if (fieldName === 'image_url_2') {
      if (hasEmbedded2) matched = '本行嵌入图片2'
      else matched = excelColumns.value.find(col => {
        const c = String(col).toLowerCase()
        return c.includes('图片2') || c.includes('image2') || c.includes('photo2')
      })
    } else {
      matched = excelColumns.value.find(col => {
        const colLower = String(col).toLowerCase()
        return colLower.includes(fieldName) || fieldName.includes(colLower) ||
          (fieldName === 'mes_material_code' && (colLower.includes('mes') || colLower.includes('编码'))) ||
          (fieldName === 'location_code' && (colLower.includes('货位') || colLower.includes('位置'))) ||
          (fieldName === 'specification_model' && (colLower.includes('规格') || colLower.includes('型号')))
      })
    }
    if (matched) mapping.excelColumn = matched
  })
}

async function handleNext() {
  if (currentStep.value === 1) {
    generatePreview()
    currentStep.value++
    return
  }
  if (currentStep.value === 2) {
    await startImport()
    currentStep.value = 3
    return
  }
  if (currentStep.value < 3) {
    currentStep.value++
  }
}

function handlePrev() {
  if (currentStep.value > 0) {
    currentStep.value--
  }
}

function generatePreview() {
  revokeEmbedPreviewUrls()
  const mappedList = excelData.value.map((row) => {
    const mapped: any = { _rowIndex: row._rowIndex ?? 0 }
    fieldMapping.value.forEach(mapping => {
      let value: any = null
      if (mapping.excelColumn && row[mapping.excelColumn] !== undefined) {
        value = row[mapping.excelColumn]
      } else if (mapping.defaultValue) {
        value = mapping.defaultValue
      }
      
      // 类型转换
      if (value !== null && value !== '') {
        if (mapping.type === 'number') {
          value = parseFloat(String(value)) || 0
        } else         if (mapping.type === 'image') {
          if (value instanceof Blob) {
            // 保持 Blob
          } else {
            const s = String(value).trim()
            const isFormula = !s || s.startsWith('=') || /^=DISPIMG\s*\(/i.test(s)
            if (isFormula && mapping.fieldName === 'image_url_1' && row['本行嵌入图片1'] instanceof Blob) {
              value = row['本行嵌入图片1']
            } else if (isFormula && mapping.fieldName === 'image_url_2' && row['本行嵌入图片2'] instanceof Blob) {
              value = row['本行嵌入图片2']
            } else if (isFormula) {
              value = null
            } else {
              value = s
            }
          }
        } else {
          value = String(value).trim()
        }
      }
      
      mapped[mapping.fieldName] = value
    })
    return mapped
  })
  // 模式二（数据验证）：仅保留必填字段完整的行；模式一（全部读取）：不做过滤，全部保留
  const filtered = batchMode.value === 'validate'
    ? mappedList.filter(item =>
        fieldMapping.value
          .filter(f => f.required)
          .every(f => item[f.fieldName])
      )
    : mappedList
  const sorted = filtered.sort((a, b) => (a._rowIndex ?? 0) - (b._rowIndex ?? 0))
  previewAllRows.value = sorted
  // 默认导入全部行，用户可在预览界面调整
  importRangeStart.value = sorted.length > 0 ? 1 : 0
  importRangeEnd.value = sorted.length
}

async function startImport() {
  isImporting.value = true
  importProgress.value = 0
  importStatus.value = '正在处理图片...'

  try {
    const rowsToImport = effectivePreviewData.value
    const totalItems = rowsToImport.length

    const processedData = await processImagesForImport(rowsToImport, (current, total) => {
      const pct = total ? Math.round((current / total) * 50) : 0
      importProgress.value = pct
      importStatus.value = `图片处理进度: ${current}/${total}`
    })
    const sorted = [...processedData].sort((a: any, b: any) => (a._rowIndex ?? 0) - (b._rowIndex ?? 0))

    importProgress.value = 50
    importStatus.value = '正在创建修复件...'
    await yieldToMain()

    // 参照批量导入图片的成功流程：逐条调用 createSparePartWithImages（先创建修复件，再 /images/confirm + sync），与前者一致
    let successCount = 0
    let failedCount = 0
    let skippedCount = 0
    const errors: Array<{ row: number; message: string }> = []

    for (let idx = 0; idx < sorted.length; idx++) {
      const item = sorted[idx]
      const { _rowIndex, image_upload_ids, ...rest } = item
      const rowNum = _rowIndex ?? idx + 1
      const body = { ...rest } as SparePartCreate & { _rowIndex?: number }
      delete (body as any)._rowIndex
      const ids: string[] = image_upload_ids || []

      // 与批量导入图片一致：material_code 需符合后端要求（3–50 位字母数字下划线短横线），否则用 row_N
      const code = materialCodeForUpload(body.mes_material_code, idx)
      if (!body.mes_material_code || !MATERIAL_CODE_PATTERN.test(String(body.mes_material_code).trim())) {
        body.mes_material_code = code
      }

      // 后端 SparePartCreate 要求 mes_stock、physical_stock 为数字，空字符串会校验失败，需规范为数字
      const numFields = ['mes_stock', 'physical_stock'] as const
      for (const f of numFields) {
        const v = (body as any)[f]
        if (v === '' || v === undefined || v === null) {
          (body as any)[f] = 0
        } else if (typeof v === 'string') {
          const n = parseFloat(v)
          ;(body as any)[f] = Number.isFinite(n) && n >= 0 ? n : 0
        }
      }

      try {
        await createSparePartWithImages(body, ids, { allowOverwrite: batchMode.value === 'full' })
        successCount++
      } catch (e: any) {
        const msg = e?.message || e?.detail || String(e)
        if (msg.includes('已存在') || msg.includes('重复') || msg.includes('跳过')) {
          skippedCount++
          errors.push({ row: rowNum, message: msg })
        } else {
          failedCount++
          errors.push({ row: rowNum, message: msg })
        }
      }

      const pct = 50 + Math.round(((idx + 1) / sorted.length) * 50)
      importProgress.value = pct
      importStatus.value = `正在创建修复件: ${idx + 1}/${sorted.length}`
      await yieldToMain()
    }

    importProgress.value = 100
    importStatus.value = '导入完成'

    const allSuccess = failedCount === 0
    importResult.value = {
      success: allSuccess,
      title: allSuccess ? '导入成功' : '导入完成（部分失败）',
      subTitle: `成功 ${successCount} 条，失败 ${failedCount} 条，跳过 ${skippedCount} 条`,
      details: {
        success: successCount,
        failed: failedCount,
        skipped: skippedCount,
        total: sorted.length,
        errors: errors.slice(0, 50)
      }
    }
    if (successCount > 0) {
      emit('success')
    }
  } catch (error: any) {
    console.error('批量导入失败:', error)
    ElMessage.error(error?.message || '批量导入失败')
    importResult.value = {
      success: false,
      title: '导入失败',
      subTitle: error?.message || '未知错误',
      details: null
    }
  } finally {
    isImporting.value = false
    importProgress.value = 0
    importStatus.value = ''
  }
}

/** 后端要求：物料编码仅允许字母、数字、下划线、短横线，长度 3–50 */
const MATERIAL_CODE_PATTERN = /^[a-zA-Z0-9_-]{3,50}$/

function materialCodeForUpload(mesMaterialCode: any, rowIndex: number): string {
  const s = mesMaterialCode != null ? String(mesMaterialCode).trim() : ''
  if (s && MATERIAL_CODE_PATTERN.test(s)) return s
  return `row_${rowIndex + 1}`
}

/**
 * 处理图片：URL 下载上传 或 本行嵌入 Blob 直接上传，获取 upload_id
 */
async function processImagesForImport(
  data: any[],
  onProgress?: (current: number, total: number) => void
): Promise<any[]> {
  const processed: any[] = []
  const total = data.length
  
  for (let idx = 0; idx < data.length; idx++) {
    const item = data[idx]
    const processedItem = { ...item }
    const imageUploadIds: string[] = []
    const code = materialCodeForUpload(item.mes_material_code, idx)
    
    const uploadOne = async (val: any, slot: 1 | 2): Promise<string | null> => {
      if (!val) return null
      if (val instanceof Blob) {
        try {
          const res = await uploadTempImageFromBlob(val, `embed_${code}_${slot}.png`, code)
          return res?.upload_id ?? null
        } catch (e: any) {
          console.warn(`本行嵌入图片${slot} 上传失败 (${code}):`, e)
          return null
        }
      }
      if (typeof val === 'string' && val.trim()) {
        return downloadAndUploadImage(val.trim(), code)
      }
      return null
    }
    
    const u1 = await uploadOne(item.image_url_1, 1)
    if (u1) imageUploadIds.push(u1)
    const u2 = await uploadOne(item.image_url_2, 2)
    if (u2) imageUploadIds.push(u2)
    
    delete processedItem.image_url_1
    delete processedItem.image_url_2
    if (imageUploadIds.length > 0) {
      processedItem.image_upload_ids = imageUploadIds
    }
    
    processed.push(processedItem)
    if (onProgress) onProgress(idx + 1, total)
  }
  
  return processed
}

/**
 * 从URL下载图片并上传到临时存储（通过后端API）
 */
async function downloadAndUploadImage(imageUrl: string, materialCode: string): Promise<string | null> {
  if (!imageUrl || !materialCode) return null
  
  try {
    // 清理URL（去除前后空格）
    const cleanUrl = String(imageUrl).trim()
    if (!cleanUrl) return null
    
    // 如果是相对路径，尝试转换为完整URL
    let finalUrl = cleanUrl
    if (!cleanUrl.startsWith('http://') && !cleanUrl.startsWith('https://')) {
      // 相对路径，使用当前域名
      finalUrl = new URL(cleanUrl, window.location.origin).href
    }
    
    // 通过后端API下载并上传
    const uploadResult = await downloadAndUploadImageFromUrl(finalUrl, materialCode)
    
    return uploadResult.upload_id
  } catch (error: any) {
    console.error(`下载并上传图片失败 (${imageUrl}):`, error)
    // 不抛出错误，返回null，让调用者决定是否继续
    return null
  }
}

function handleClose() {
  // 重置状态
  currentStep.value = 0
  batchMode.value = 'validate'
  excelFile.value = null
  excelColumns.value = []
  excelData.value = []
  fieldMapping.value = []
  previewAllRows.value = []
  importRangeStart.value = 1
  importRangeEnd.value = 0
  importResult.value = {
    success: false,
    title: '',
    subTitle: '',
    details: null
  }
  isParsing.value = false
  parsingProgress.value = 0
  parsingStatus.value = '准备解析...'
  parsingDetail.value = ''
  isImporting.value = false
  importProgress.value = 0
  importStatus.value = ''
  revokeEmbedPreviewUrls()
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
  dialogVisible.value = false
}

watch(() => props.modelValue, (val) => {
  if (val) {
    currentStep.value = 0
  }
})
</script>

<style scoped lang="scss">
.step-content {
  min-height: 400px;
  padding: 20px 0;
}

.batch-mode-row {
  margin-bottom: 20px;
  .mode-label {
    display: block;
    font-size: 14px;
    color: #606266;
    margin-bottom: 8px;
  }
  .batch-mode-group {
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    :deep(.el-radio-button) {
      flex: 1;
      min-width: 260px;
      .el-radio-button__inner {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
        text-align: left;
        padding: 12px 16px;
        white-space: normal;
      }
    }
  }
  .mode-title {
    font-weight: 500;
    color: #303133;
  }
  .mode-desc {
    font-size: 12px;
    color: #909399;
    margin-top: 4px;
  }
}

.columns-preview {
  margin-top: 20px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 4px;
  
  h4 {
    margin: 0 0 12px;
    font-size: 14px;
    color: #606266;
  }
}

.import-details {
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
}

.image-preview-cell {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.empty-text {
  color: #c0c4cc;
  font-style: italic;
}

.mode-hint {
  font-size: 12px;
  color: #909399;
  font-weight: normal;
}

.parsing-progress {
  margin-top: 24px;
  padding: 24px;
  background: #f5f7fa;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
}

.progress-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  font-size: 16px;
  font-weight: 500;
  color: #303133;
  
  .el-icon {
    font-size: 18px;
    color: #409eff;
  }
  
  .progress-text {
    flex: 1;
  }
}

.progress-detail {
  margin-top: 12px;
  font-size: 14px;
  color: #606266;
  text-align: center;
}

.step-preview-wrap {
  position: relative;
}

.import-overlay {
  position: absolute;
  inset: 0;
  z-index: 10;
  background: rgba(255, 255, 255, 0.85);
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
}

.import-progress-box {
  text-align: center;
  padding: 24px 32px;
  min-width: 320px;
}

.import-progress-box .el-icon {
  font-size: 32px;
  color: #409eff;
}

.import-status {
  margin-top: 12px;
  font-size: 15px;
  color: #303133;
  font-weight: 500;
}

.range-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
  font-size: 13px;
  color: #606266;
  .range-label {
    font-weight: 500;
  }
  .range-separator {
    margin: 0 4px;
  }
  .range-hint {
    font-size: 12px;
    color: #909399;
  }
}

@media (max-width: 767px) {
  .batch-import-dialog :deep(.el-dialog__body) {
    padding: 12px;
    max-height: 70vh;
    overflow-y: auto;
  }
  .batch-import-dialog .step-content {
    min-height: 280px;
    padding: 12px 0;
  }
  .batch-import-dialog .batch-mode-row .batch-mode-group :deep(.el-radio-button) {
    min-width: 0;
  }
  .batch-import-dialog :deep(.el-table) {
    font-size: 12px;
  }
  .batch-import-dialog :deep(.el-steps) {
    flex-wrap: wrap;
  }
  .batch-import-dialog .table-scroll-wrap {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }
}
</style>
