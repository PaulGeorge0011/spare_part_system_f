<template>
  <el-dialog
    v-model="dialogVisible"
    :title="title"
    :width="isMobile ? '95%' : '720px'"
    :close-on-click-modal="false"
    @close="handleClose"
    class="batch-update-dialog"
  >
    <el-steps :active="currentStep" finish-status="success" style="margin-bottom: 20px">
      <el-step title="上传Excel" />
      <el-step title="字段映射" />
      <el-step title="数据预览" />
      <el-step title="更新结果" />
    </el-steps>

    <!-- 步骤1: 上传Excel -->
    <div v-if="currentStep === 0" class="step-content">
      <el-alert type="info" :closable="false" style="margin-bottom: 16px">
        请上传包含 <strong>MES编码</strong> 与 <strong>MES库存</strong> 的 Excel 文件，系统将按 MES 编码匹配并更新对应修复件的 MES 库存。
      </el-alert>
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
        <div class="el-upload__text">将 Excel 拖到此处，或<em>点击上传</em></div>
        <template #tip>
          <div class="el-upload__tip">仅支持 .xlsx 或 .xls</div>
        </template>
      </el-upload>
      <div v-if="isParsing" class="parsing-progress">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span class="progress-text">{{ parsingStatus }}</span>
        <el-progress :percentage="parsingProgress" :stroke-width="8" />
      </div>
      <div v-if="excelColumns.length > 0 && !isParsing" class="columns-preview">
        <h4>检测到的列：</h4>
        <el-tag v-for="col in excelColumns" :key="col" style="margin: 4px">{{ col }}</el-tag>
      </div>
    </div>

    <!-- 步骤2: 字段映射 -->
    <div v-if="currentStep === 1" class="step-content">
      <el-alert type="info" :closable="false" style="margin-bottom: 16px">
        请为 <strong>MES编码</strong> 和 <strong>MES库存</strong> 选择对应的 Excel 列（均为必选）。
      </el-alert>
      <el-table :data="fieldMapping" border style="width: 100%">
        <el-table-column prop="fieldLabel" label="字段" width="140" />
        <el-table-column label="对应 Excel 列" min-width="280">
          <template #default="{ row }">
            <el-select
              v-model="row.excelColumn"
              placeholder="请选择列"
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
      </el-table>
    </div>

    <!-- 步骤3: 数据预览 -->
    <div v-if="currentStep === 2" class="step-content">
      <div v-if="isSubmitting" class="import-overlay">
        <div class="import-progress-box">
          <el-icon class="is-loading"><Loading /></el-icon>
          <div class="import-status">正在提交更新...</div>
        </div>
      </div>
      <el-alert type="warning" :closable="false" style="margin-bottom: 16px">
        共 {{ previewData.length }} 条，将按 MES 编码更新现有记录的 MES 库存；未匹配到的行将跳过。
      </el-alert>
      <div class="table-scroll-wrap">
        <el-table :data="previewData" border max-height="360" style="width: 100%">
          <el-table-column prop="mes_material_code" label="MES编码" min-width="140" show-overflow-tooltip />
          <el-table-column prop="mes_stock" label="MES库存" width="100" align="right" />
        </el-table>
      </div>
    </div>

    <!-- 步骤4: 更新结果 -->
    <div v-if="currentStep === 3" class="step-content">
      <el-result
        :icon="updateResult.success ? 'success' : 'warning'"
        :title="updateResult.title"
        :sub-title="updateResult.subTitle"
      >
        <template #extra>
          <div v-if="updateResult.details" class="import-details">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="已更新">{{ updateResult.details.updated ?? 0 }} 条</el-descriptions-item>
              <el-descriptions-item label="已跳过">{{ updateResult.details.skipped ?? 0 }} 条</el-descriptions-item>
            </el-descriptions>
            <div v-if="updateResult.details.errors && updateResult.details.errors.length > 0" style="margin-top: 16px">
              <h4>跳过/错误详情：</h4>
              <el-table :data="updateResult.details.errors" border max-height="200" style="width: 100%">
                <el-table-column prop="row" label="行号" width="80" />
                <el-table-column prop="message" label="说明" show-overflow-tooltip />
              </el-table>
            </div>
          </div>
        </template>
      </el-result>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button :disabled="isSubmitting" @click="handleClose">取消</el-button>
        <el-button v-if="currentStep > 0 && !isSubmitting" @click="handlePrev">上一步</el-button>
        <el-button
          v-if="currentStep < 3"
          type="primary"
          :disabled="!canNext || isSubmitting"
          :loading="isSubmitting && currentStep === 2"
          @click="handleNext"
        >
          {{ currentStep === 2 ? '开始更新' : '下一步' }}
        </el-button>
        <el-button v-if="currentStep === 3" type="primary" @click="handleClose">完成</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useIsMobile } from '@/composables/useIsMobile'
import { UploadFilled, Loading } from '@element-plus/icons-vue'
import * as XLSX from 'xlsx'
import { sparePartApi } from '@/api/sparePart'
import { mechanicalSparePartApi } from '@/api/mechanicalSparePart'

const props = withDefaults(
  defineProps<{
    modelValue: boolean
    /** electrical=电气修复件, mechanical=机械修复件 */
    type?: 'electrical' | 'mechanical'
  }>(),
  { type: 'electrical' }
)

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  success: []
}>()

const title = computed(() =>
  props.type === 'mechanical' ? '批量更新 MES 库存（机械修复件）' : '批量更新 MES 库存（电气修复件）'
)

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val),
})

const { isMobile } = useIsMobile()
const currentStep = ref(0)
const uploadRef = ref()
const excelColumns = ref<string[]>([])
const excelData = ref<any[][]>([])
const fieldMapping = ref<Array<{ fieldName: string; fieldLabel: string; excelColumn: string }>>([
  { fieldName: 'mes_material_code', fieldLabel: 'MES编码', excelColumn: '' },
  { fieldName: 'mes_stock', fieldLabel: 'MES库存', excelColumn: '' },
])
const previewData = ref<Array<{ mes_material_code: string; mes_stock: number }>>([])
const updateResult = ref<{
  success: boolean
  title: string
  subTitle: string
  details: { updated: number; skipped: number; errors: Array<{ row: number; message: string }> } | null
}>({ success: false, title: '', subTitle: '', details: null })

const isParsing = ref(false)
const parsingProgress = ref(0)
const parsingStatus = ref('')
const isSubmitting = ref(false)

const canNext = computed(() => {
  if (currentStep.value === 0) return excelColumns.value.length > 0 && !isParsing.value
  if (currentStep.value === 1) {
    return fieldMapping.value.every((f) => f.excelColumn)
  }
  if (currentStep.value === 2) return previewData.value.length > 0
  return true
})

function getOptimizedRange(worksheet: XLSX.WorkSheet): string | null {
  try {
    const ref = worksheet['!ref']
    if (!ref) return null
    const range = XLSX.utils.decode_range(ref)
    const totalCells = (range.e.r - range.s.r + 1) * (range.e.c - range.s.c + 1)
    if (totalCells < 1000000) return null
    let minR = Infinity, maxR = -1, minC = Infinity, maxC = -1
    const re = /^([A-Z]+)(\d+)$/
    for (const key of Object.keys(worksheet)) {
      if (key.startsWith('!')) continue
      const m = key.match(re)
      if (!m) continue
      const cell = worksheet[key]
      if (!cell || (cell.v !== 0 && !cell.v)) continue
      const d = XLSX.utils.decode_cell(key)
      minR = Math.min(minR, d.r)
      maxR = Math.max(maxR, d.r)
      minC = Math.min(minC, d.c)
      maxC = Math.max(maxC, d.c)
    }
    if (maxR < 0 || maxC < 0) return null
    return XLSX.utils.encode_range({ s: { r: minR, c: minC }, e: { r: maxR, c: maxC } })
  } catch {
    return null
  }
}

function handleFileChange(file: any) {
  if (!file?.raw) return
  isParsing.value = true
  parsingProgress.value = 0
  parsingStatus.value = '正在读取...'
  excelColumns.value = []
  excelData.value = []

  const reader = new FileReader()
  reader.onload = (e) => {
    const arrayBuffer = e.target?.result as ArrayBuffer
    parsingProgress.value = 40
    parsingStatus.value = '解析工作表...'
    const workbook = XLSX.read(new Uint8Array(arrayBuffer), { type: 'array' })
    const sheetName = workbook.SheetNames[0]
    const worksheet = workbook.Sheets[sheetName]
    const optimizedRange = getOptimizedRange(worksheet)
    const jsonData = XLSX.utils.sheet_to_json(worksheet, {
      header: 1,
      defval: '',
      range: optimizedRange || undefined,
    }) as any[][]
    parsingProgress.value = 90
    if (jsonData.length === 0) {
      isParsing.value = false
      ElMessage.error('Excel 为空')
      return
    }
    const headers = (jsonData[0] || []) as string[]
    excelColumns.value = headers.filter((h) => h != null && String(h).trim())
    excelData.value = jsonData.slice(1)
    parsingProgress.value = 100
    parsingStatus.value = '解析完成'
    isParsing.value = false
    fieldMapping.value = [
      { fieldName: 'mes_material_code', fieldLabel: 'MES编码', excelColumn: '' },
      { fieldName: 'mes_stock', fieldLabel: 'MES库存', excelColumn: '' },
    ]
  }
  reader.readAsArrayBuffer(file.raw)
}

function buildPreviewRows(): Array<{ mes_material_code: string; mes_stock: number }> {
  const mesCol = fieldMapping.value.find((f) => f.fieldName === 'mes_material_code')?.excelColumn
  const stockCol = fieldMapping.value.find((f) => f.fieldName === 'mes_stock')?.excelColumn
  if (!mesCol || !stockCol) return []
  const mesIdx = excelColumns.value.indexOf(mesCol)
  const stockIdx = excelColumns.value.indexOf(stockCol)
  if (mesIdx < 0 || stockIdx < 0) return []
  const out: Array<{ mes_material_code: string; mes_stock: number }> = []
  for (const row of excelData.value as any[][]) {
    const code = row && row[mesIdx] != null ? String(row[mesIdx]).trim() : ''
    const raw = row && row[stockIdx] != null ? row[stockIdx] : ''
    if (raw === '' || raw == null) continue
    let stock: number
    if (typeof raw === 'number' && !Number.isNaN(raw)) stock = Math.max(0, Math.round(raw))
    else {
      const n = Number(raw)
      if (Number.isNaN(n)) continue
      stock = Math.max(0, Math.round(n))
    }
    if (!code) continue
    out.push({ mes_material_code: code, mes_stock: stock })
  }
  return out
}

watch(
  () => currentStep.value,
  (step) => {
    if (step === 2) {
      previewData.value = buildPreviewRows()
    }
  }
)

function handlePrev() {
  if (currentStep.value > 0) currentStep.value--
}

async function handleNext() {
  if (currentStep.value === 2) {
    const payload = [...previewData.value]
    if (payload.length === 0) {
      ElMessage.warning('没有可更新的数据')
      return
    }
    isSubmitting.value = true
    try {
      const api = props.type === 'mechanical' ? mechanicalSparePartApi : sparePartApi
      const res = await api.batchUpdateMesStock(payload)
      updateResult.value = {
        success: (res.updated ?? 0) > 0 || (res.skipped ?? 0) === payload.length,
        title: '更新完成',
        subTitle: `已更新 ${res.updated ?? 0} 条，跳过 ${res.skipped ?? 0} 条`,
        details: {
          updated: res.updated ?? 0,
          skipped: res.skipped ?? 0,
          errors: res.errors ?? [],
        },
      }
      currentStep.value = 3
      if ((res.updated ?? 0) > 0) {
        ElMessage.success(`已更新 ${res.updated} 条 MES 库存`)
        emit('success')
      }
    } catch (e: any) {
      ElMessage.error(e?.message || '批量更新失败')
      updateResult.value = {
        success: false,
        title: '更新失败',
        subTitle: e?.message || '请求异常',
        details: null,
      }
      currentStep.value = 3
    } finally {
      isSubmitting.value = false
    }
    return
  }
  if (currentStep.value < 3) currentStep.value++
}

function handleClose() {
  currentStep.value = 0
  excelColumns.value = []
  excelData.value = []
  previewData.value = []
  fieldMapping.value = [
    { fieldName: 'mes_material_code', fieldLabel: 'MES编码', excelColumn: '' },
    { fieldName: 'mes_stock', fieldLabel: 'MES库存', excelColumn: '' },
  ]
  updateResult.value = { success: false, title: '', subTitle: '', details: null }
  dialogVisible.value = false
}

watch(
  () => props.modelValue,
  (v) => {
    if (v) {
      currentStep.value = 0
      excelColumns.value = []
      excelData.value = []
      previewData.value = []
    }
  }
)
</script>

<style scoped>
.batch-update-dialog .step-content {
  min-height: 200px;
}
.columns-preview {
  margin-top: 16px;
}
.columns-preview h4 {
  margin-bottom: 8px;
  font-size: 14px;
}
.parsing-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
}
.progress-text {
  font-size: 14px;
}
.table-scroll-wrap {
  overflow-x: auto;
}
.import-overlay {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
}
.import-progress-box {
  text-align: center;
}
.import-status {
  margin-top: 8px;
  font-size: 14px;
}
.import-details {
  text-align: left;
  max-width: 560px;
}
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
