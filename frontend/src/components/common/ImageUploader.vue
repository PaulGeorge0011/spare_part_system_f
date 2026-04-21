<!-- src/components/common/ImageUploader.vue -->
<template>
  <div class="image-uploader">
    <!-- 如果已经有图片，显示图片 -->
    <div v-if="imageUrl && !imageLoadError" class="image-preview">
      <img 
        ref="imageElement"
        :src="displayUrl" 
        :alt="imageName || '图片预览'"
        class="preview-image"
        @load="handleImageLoad"
        @error="handleImageError"
      />
      <div class="image-actions">
        <el-button
          type="primary"
          size="small"
          :icon="View"
          circle
          @click="previewImage"
        />
        <el-button
          type="danger"
          size="small"
          :icon="Delete"
          circle
          @click="removeImage"
        />
      </div>
    </div>
    
    <!-- 图片加载失败或没有图片时显示上传按钮 -->
    <div v-else class="upload-container">
      <!-- 使用自定义上传按钮 -->
      <div class="upload-button">
        <el-button 
          type="primary" 
          :icon="Upload"
          :loading="uploading"
          :disabled="!materialCode || uploading"
          @click="handleSelectFile"
        >
          {{ buttonText }}
        </el-button>
        <input
          ref="fileInput"
          type="file"
          accept="image/*"
          style="display: none"
          @change="handleFileChange"
        />
      </div>
      
      <!-- 物料编码提示 -->
      <div v-if="!materialCode" class="material-code-tip">
        <el-alert
          title="请先输入物料编码"
          type="warning"
          :closable="false"
          show-icon
          class="warning-alert"
        />
      </div>
      
      <!-- 加载失败提示 -->
      <div v-else-if="imageLoadError" class="image-error-tip">
        <el-alert
          title="图片加载失败"
          type="error"
          :closable="false"
          show-icon
          class="error-alert"
        >
          <template #default>
            <div style="font-size: 12px;">
              <p>图片无法加载</p>
              <el-button type="text" size="small" @click="retryLoadImage">
                重试加载
              </el-button>
            </div>
          </template>
        </el-alert>
      </div>
    </div>
    
    <!-- 上传进度 -->
    <div v-if="uploadProgress > 0 && uploadProgress < 100" class="upload-progress">
      <el-progress 
        :percentage="uploadProgress" 
        :status="uploadStatus"
        :stroke-width="8"
      />
    </div>
    
    <!-- 图片信息 -->
    <div v-if="imageUrl && imageName" class="image-info">
      <span class="image-name">{{ imageName }}</span>
      <span v-if="imageSize" class="image-size">{{ formatFileSize(imageSize) }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload, View, Delete } from '@element-plus/icons-vue'
import { 
  uploadTempImage, 
  validateImageFile, 
  convertMinioUrlToAccessible,
  getTempImage,
  type TempUploadResponse 
} from '@/utils/imageUpload'
import { getImageUrlForDisplay } from '@/utils/image'

// 定义Props
interface Props {
  modelValue?: string
  uploadId?: string
  materialCode?: string
  sparePartId?: number
  imageType?: 'primary' | 'secondary'
  maxSizeMb?: number
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: '',
  materialCode: '',
  uploadId: '',
  imageType: 'primary',
  maxSizeMb: 10,
})

// 定义Emits
const emit = defineEmits<{
  'update:modelValue': [value: string]
  'update:upload-id': [uploadId: string]
  'uploaded': [response: TempUploadResponse]
  'removed': []
}>()

// 响应式数据
const imageUrl = ref<string>(props.modelValue || '')
const processedImageUrl = ref<string>('')
const uploadProgress = ref<number>(0)
const uploadStatus = ref<'success' | 'exception' | 'warning' | undefined>()
const currentUploadId = ref<string>('')
const imageName = ref<string>('')
const imageSize = ref<number>(0)
const imageLoadError = ref<boolean>(false)
const imageElement = ref<HTMLImageElement | null>(null)
const retryCount = ref<number>(0)
const maxRetryCount = 3
const fileInput = ref<HTMLInputElement | null>(null)
const uploading = ref<boolean>(false)

// 计算属性
const buttonText = computed(() => {
  if (uploading.value) return '上传中...'
  return props.imageType === 'primary' ? '上传主图' : '上传副图'
})

// 实时计算可访问的图片 URL（用于显示与预览），避免首次打开时因 watch 未及时更新而用错地址
const displayUrl = computed(() => {
  const raw = imageUrl.value || props.modelValue || ''
  if (!raw) return ''
  return getImageUrlForDisplay(raw) || convertMinioUrlToAccessible(raw) || raw
})

// 方法

// 修改 loadTempImage 方法，添加重试机制
const loadTempImage = async (uploadId: string, maxRetries = 2): Promise<boolean> => {
  if (!uploadId) return false
  
  let attempts = 0
  while (attempts < maxRetries) {
    try {
      console.log(`第${attempts + 1}次尝试获取临时图片，uploadId:`, uploadId)
      
      const response = await getTempImage(uploadId)
      console.log('获取临时图片响应:', response)
      
      if (response && response.temp_url) {
        const accessibleUrl = getImageUrlForDisplay(response.temp_url) || convertMinioUrlToAccessible(response.temp_url)
        imageUrl.value = accessibleUrl
        processedImageUrl.value = accessibleUrl
        currentUploadId.value = uploadId
        
        // 更新父组件
        emit('update:modelValue', accessibleUrl)
        
        console.log('临时图片加载成功:', accessibleUrl)
        return true
      }
    } catch (error: any) {
      console.error(`第${attempts + 1}次获取临时图片失败:`, error)
      if (attempts === maxRetries - 1) {
        // 最后一次尝试也失败，显示错误
        imageLoadError.value = true
      }
    }
    
    attempts++
    if (attempts < maxRetries) {
      // 等待一段时间后重试
      await new Promise(resolve => setTimeout(resolve, 1000 * attempts))
    }
  }
  
  return false
}

// 修改 uploadFile 方法，优化URL处理
const uploadFile = async (file: File) => {
  if (!props.materialCode) {
    ElMessage.error('请先输入物料编码')
    return
  }
  
  try {
    uploading.value = true
    uploadProgress.value = 10
    
    console.log('开始上传图片...')
    
    const response = await uploadTempImage(
      file,
      props.materialCode,
      (progress) => {
        console.log('上传进度回调:', progress)
        uploadProgress.value = progress
      }
    )
    
    console.log('图片上传成功响应:', response)
    
    // 确保响应有效
    if (!response || !response.upload_id || !response.temp_url) {
      throw new Error('上传响应无效')
    }
    
    const accessibleUrl = getImageUrlForDisplay(response.temp_url) || convertMinioUrlToAccessible(response.temp_url)
    console.log('temp_url 转换后:', accessibleUrl)

    // 更新状态
    currentUploadId.value = response.upload_id
    imageUrl.value = accessibleUrl
    processedImageUrl.value = accessibleUrl
    
    // 更新父组件
    emit('update:modelValue', accessibleUrl)
    emit('update:upload-id', response.upload_id)
    emit('uploaded', response)
    
    uploadProgress.value = 100
    uploadStatus.value = 'success'
    
    setTimeout(() => {
      uploadProgress.value = 0
      uploadStatus.value = undefined
    }, 3000)
    
    ElMessage.success('图片上传成功')
    
  } catch (error: any) {
    console.error('上传失败:', error)
    uploadProgress.value = 0
    uploadStatus.value = 'exception'
    ElMessage.error(`上传失败: ${error.message}`)
  } finally {
    uploading.value = false
  }
}

const formatFileSize = (bytes: number): string => {
  if (!bytes || bytes === 0) return '0 B'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const handleImageLoad = () => {
  imageLoadError.value = false
  retryCount.value = 0
  imageLoadError.value = false
  retryCount.value = 0
}

// 修改 handleImageError 方法，添加对临时图片的重试逻辑
// 修改 handleImageError 方法，添加更智能的重试逻辑
const handleImageError = async (event: any) => {
  console.error('图片加载失败:', event)
  
  const imgElement = event.target as HTMLImageElement
  
  // 如果已经有重试次数限制，并且达到了最大重试次数
  if (retryCount.value >= maxRetryCount) {
    imageLoadError.value = true
    console.error('图片加载失败，已达到最大重试次数')
    return
  }
  
  retryCount.value++
  console.log(`第${retryCount.value}次重试加载图片，当前URL:`, imgElement.src)
  
  // 尝试不同的解决方案：
  
  // 方案1：如果有 currentUploadId，尝试重新获取临时图片URL
  if (currentUploadId.value && retryCount.value === 1) {
    console.log('尝试通过 uploadId 重新获取临时图片')
    const success = await loadTempImage(currentUploadId.value)
    if (success) {
      console.log('通过 uploadId 重新获取临时图片成功')
      return
    }
  }
  
  // 方案2：添加时间戳避免缓存（延迟执行）
  setTimeout(() => {
    const url = displayUrl.value
    if (imageElement.value && url) {
      if (url.includes('X-Amz-Date=')) {
        const timestamp = Date.now()
        const newUrl = url.replace(
          /X-Amz-Date=[^&]+/,
          `X-Amz-Date=${new Date(timestamp).toISOString().replace(/[:-]/g, '').split('.')[0]}Z`
        )
        imageElement.value.src = newUrl + `&_retry=${retryCount.value}`
      } else {
        const separator = url.includes('?') ? '&' : '?'
        imageElement.value.src = url + separator + `_t=${Date.now()}&_retry=${retryCount.value}`
      }
    }
  }, 1000 * retryCount.value)
}

const retryLoadImage = () => {
  imageLoadError.value = false
  retryCount.value = 0
  const url = displayUrl.value
  if (imageElement.value && url) {
    const separator = url.includes('?') ? '&' : '?'
    imageElement.value.src = url + separator + `_t=${Date.now()}`
  }
}

const handleSelectFile = () => {
  if (!props.materialCode) {
    ElMessage.error('请先输入物料编码')
    return
  }
  
  // 触发文件选择
  if (fileInput.value) {
    fileInput.value.click()
  }
}

const handleFileChange = async (event: Event) => {
  const input = event.target as HTMLInputElement
  if (!input.files || input.files.length === 0) {
    return
  }
  
  const file = input.files[0]
  
  // 验证图片文件
  const validation = validateImageFile(file)
  if (!validation.valid) {
    ElMessage.error(validation.message)
    // 清空文件输入
    input.value = ''
    return
  }
  
  imageName.value = file.name
  imageSize.value = file.size
  
  // 开始上传
  await uploadFile(file)
  
  // 清空文件输入
  input.value = ''
}



const previewImage = () => {
  const url = displayUrl.value
  if (url && !imageLoadError.value) {
    window.open(url, '_blank')
  }
}

const removeImage = async () => {
  try {
    await ElMessageBox.confirm(
      '确定要删除这张图片吗？',
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    // 如果有currentUploadId，尝试删除临时图片
    if (currentUploadId.value) {
      try {
        console.log('删除临时图片，uploadId:', currentUploadId.value)
        // 如果需要删除后端临时图片，可以在这里调用API
        // await deleteTempImage(currentUploadId.value)
      } catch (error) {
        console.error('删除临时图片失败:', error)
      }
    }
    
    // 清空图片
    imageUrl.value = ''
    processedImageUrl.value = ''
    currentUploadId.value = ''
    imageName.value = ''
    imageSize.value = 0
    uploadProgress.value = 0
    uploadStatus.value = undefined
    imageLoadError.value = false
    retryCount.value = 0
    
    // 更新父组件
    emit('update:modelValue', '')
    emit('update:upload-id', '')
    emit('removed')
    
    ElMessage.success('图片已删除')
  } catch {
    // 用户取消删除
  }
}

const clear = () => {
  imageUrl.value = ''
  processedImageUrl.value = ''
  currentUploadId.value = ''
  imageName.value = ''
  imageSize.value = 0
  uploadProgress.value = 0
  uploadStatus.value = undefined
  imageLoadError.value = false
  retryCount.value = 0
  uploading.value = false
}

// 修改 watch，添加对 uploadId 的监听
watch(
  () => props.uploadId,
  async (newUploadId) => {
    if (newUploadId && newUploadId !== currentUploadId.value) {
      console.log('uploadId 变化，加载临时图片:', newUploadId)
      await loadTempImage(newUploadId)
    }
  },
  { immediate: true }
)

// 监听modelValue变化（编辑模式下加载的图片 URL 需转换，移动端 localhost -> 当前 host）
watch(
  () => props.modelValue,
  (newValue) => {
    if (newValue !== imageUrl.value) {
      const raw = newValue || ''
      const accessible = raw ? (getImageUrlForDisplay(raw) || convertMinioUrlToAccessible(raw)) : ''
      imageUrl.value = accessible || raw
      if (raw) {
        processedImageUrl.value = accessible || raw
        imageLoadError.value = false
        retryCount.value = 0
      }
    }
  },
  { immediate: true }
)

// 监听materialCode变化
watch(
  () => props.materialCode,
  () => {
    if (!props.materialCode) {
      clear()
    }
  }
)



// 暴露方法给父组件
defineExpose({
  clear
})
</script>

<style scoped>
.image-uploader {
  width: 100%;
}

.image-preview {
  position: relative;
  width: 100%;
  height: 120px;
  border: 1px dashed #dcdfe6;
  border-radius: 6px;
  overflow: hidden;
  background-color: #f5f7fa;
}

.preview-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-actions {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.3s;
}

.image-preview:hover .image-actions {
  opacity: 1;
}

.upload-container {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.upload-button {
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 120px;
  border: 1px dashed #dcdfe6;
  border-radius: 6px;
  background-color: #f5f7fa;
}

.material-code-tip {
  width: 100%;
}

.warning-alert {
  margin-top: 8px;
}

.image-error-tip {
  width: 100%;
}

.error-alert {
  margin-top: 8px;
}

.upload-progress {
  margin-top: 8px;
}

.image-info {
  margin-top: 8px;
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #909399;
}

.image-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 70%;
}

.image-size {
  font-weight: bold;
}
</style>