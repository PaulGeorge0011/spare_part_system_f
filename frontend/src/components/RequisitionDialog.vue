<template>
  <el-dialog
    v-model="visible"
    title="设备领用"
    :width="isMobile ? undefined : '420px'"
    :fullscreen="isMobile"
    :before-close="handleClose"
    append-to-body
    destroy-on-close
    class="requisition-dialog"
    :class="{ 'requisition-dialog--mobile': isMobile }"
  >
    <div :class="{ 'requisition-dialog__scroll': isMobile }">
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        :label-width="isMobile ? 'auto' : '90px'"
        :label-position="isMobile ? 'top' : 'right'"
        :class="{ 'requisition-form--mobile': isMobile }"
      >
        <el-form-item label="设备">
          <span class="requisition-part-label">{{ partLabel }}</span>
        </el-form-item>
        <el-form-item v-if="row?.physical_material_desc" label="实物物料描述">
          <span class="requisition-physical-desc">{{ row.physical_material_desc }}</span>
        </el-form-item>
        <el-form-item label="当前库存">
          <el-tag type="info">{{ (row?.physical_stock ?? 0) }} {{ row?.unit || '个' }}</el-tag>
        </el-form-item>
        <el-form-item label="领用人">
          <el-input
            :model-value="requisitionerDisplay"
            readonly
            placeholder="—"
            size="large"
          />
          <span v-if="!requisitionerDisplay" class="requisition-tip">您尚未设置真实姓名，请先完善个人信息</span>
        </el-form-item>
        <el-form-item label="领用数量" prop="quantity">
          <el-input-number
            v-model="form.quantity"
            :min="1"
            :max="Math.max(0, (row?.physical_stock ?? 0))"
            :precision="0"
            controls-position="right"
            :size="isMobile ? 'large' : 'default'"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="领用原因" prop="requisition_reason">
          <el-input
            v-model="form.requisition_reason"
            :size="isMobile ? 'large' : 'default'"
            placeholder="请输入领用原因（必填）"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="使用地点" prop="usage_location">
          <el-input
            v-model="form.usage_location"
            :size="isMobile ? 'large' : 'default'"
            placeholder="请输入使用地点（必填）"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>
        <el-form-item label="备注">
          <el-input
            v-model="form.remark"
            type="textarea"
            :rows="isMobile ? 3 : 2"
            placeholder="选填"
            maxlength="500"
            show-word-limit
          />
        </el-form-item>
      </el-form>
    </div>
    <template #footer>
      <div :class="{ 'requisition-dialog__footer--mobile': isMobile }">
        <el-button v-if="isMobile" size="large" @click="handleClose">取消</el-button>
        <el-button v-else @click="handleClose">取消</el-button>
        <el-button
          v-if="isMobile"
          type="primary"
          size="large"
          :loading="submitting"
          @click="handleSubmit"
        >
          确认领用
        </el-button>
        <el-button v-else type="primary" :loading="submitting" @click="handleSubmit">确认领用</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, watch, computed } from 'vue'
import { useIsMobile } from '@/composables/useIsMobile'
import { useAuthStore } from '@/stores/auth'

const { isMobile } = useIsMobile()
const authStore = useAuthStore()
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import type { SparePart } from '@/types/sparePart'
import { sparePartApi } from '@/api/sparePart'
import { broadcastSparePartDataChanged } from '@/composables/useSparePartDataChanged'

const props = defineProps<{
  modelValue: boolean
  row: SparePart | null
}>()
const emit = defineEmits<{
  'update:modelValue': [v: boolean]
  'success': []
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const formRef = ref<FormInstance>()
const submitting = ref(false)
const form = reactive({ quantity: 1, requisition_reason: '', usage_location: '', remark: '' })

// 领用人 = 当前用户真实姓名，无则回退用户名；由后端自动确定，前端只读展示
const requisitionerDisplay = computed(() => {
  const u = authStore.user
  if (!u) return ''
  return (u.real_name || u.username || '').trim() || ''
})

const rules: FormRules = {
  quantity: [
    { required: true, message: '请输入领用数量', trigger: 'blur' },
    { type: 'number', min: 1, message: '领用数量至少为 1', trigger: 'blur' },
  ],
  requisition_reason: [
    { required: true, message: '请输入领用原因', trigger: 'blur' },
  ],
  usage_location: [
    { required: true, message: '请输入使用地点', trigger: 'blur' },
  ],
}

const partLabel = computed(() => {
  const r = props.row
  if (!r) return '-'
  return [r.mes_material_code, r.specification_model].filter(Boolean).join(' · ') || r.location_code || '-'
})

watch(
  () => props.row,
  (r) => {
    const max = Math.max(0, r?.physical_stock ?? 0)
    form.quantity = max > 0 ? 1 : 0
    form.requisition_reason = ''
    form.usage_location = ''
    form.remark = ''
  },
  { immediate: true }
)

watch(visible, (v) => {
  if (v && props.row) {
    const max = Math.max(0, props.row.physical_stock ?? 0)
    form.quantity = max > 0 ? 1 : 0
    form.requisition_reason = ''
    form.usage_location = ''
    form.remark = ''
  }
})

const handleClose = () => {
  if (!submitting.value) visible.value = false
}

const handleSubmit = async () => {
  if (!formRef.value || !props.row) return
  if (!requisitionerDisplay.value) {
    ElMessage.warning('领用人信息缺失，请重新登录或联系管理员完善真实姓名')
    return
  }
  try {
    await formRef.value.validate()
    const max = Math.max(0, props.row.physical_stock ?? 0)
    if (form.quantity < 1 || form.quantity > max) {
      ElMessage.warning('领用数量需在 1 与当前设备库存之间')
      return
    }
    submitting.value = true
    await sparePartApi.requisition(props.row.id, form.quantity, form.requisition_reason, form.usage_location, form.remark || undefined)
    broadcastSparePartDataChanged()
    ElMessage.success('领用成功')
    visible.value = false
    emit('success')
  } catch (e: any) {
    if (e?.message) ElMessage.error(e.message)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.requisition-part-label {
  font-size: 14px;
  color: var(--el-text-color-regular);
}

.requisition-tip {
  font-size: 12px;
  color: var(--el-color-warning);
  margin-top: 4px;
  display: block;
}

/* 移动端：全屏弹窗，内容可滚动，底部按钮固定 */
.requisition-dialog--mobile :deep(.el-dialog) {
  display: flex;
  flex-direction: column;
  height: 100%;
  max-height: 100%;
  margin: 0 !important;
  border-radius: 0;
}
.requisition-dialog--mobile :deep(.el-dialog__body) {
  padding: 16px;
  padding-bottom: 24px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}
.requisition-dialog__scroll {
  min-height: 0;
}
.requisition-form--mobile :deep(.el-form-item) {
  margin-bottom: 20px;
}
.requisition-form--mobile :deep(.el-form-item__label) {
  font-weight: 500;
  margin-bottom: 6px;
}
.requisition-dialog__footer--mobile {
  display: flex;
  gap: 12px;
  padding: 12px 16px;
  padding-bottom: calc(12px + env(safe-area-inset-bottom, 0));
  background: var(--el-bg-color);
  border-top: 1px solid var(--el-border-color-lighter);
}
.requisition-dialog__footer--mobile .el-button {
  flex: 1;
}

@media (max-width: 767px) {
  .requisition-dialog:not(.requisition-dialog--mobile) :deep(.el-dialog__body) {
    padding: 12px;
  }
  .requisition-dialog:not(.requisition-dialog--mobile) :deep(.el-form-item) {
    margin-bottom: 16px;
  }
}
</style>
