// frontend/src/utils/imageUpload.ts
import uploadRequest from './uploadRequest'  // 使用专门的上传实例
import request from './request'  // 普通请求还是用原来的
import type { AxiosProgressEvent } from 'axios'
import { ElMessage } from 'element-plus'
import { smartConvertMinioUrl } from './config'

let _httpx503Warned = false
let _formulaOr400Warned = false

export interface TempUploadResponse {
  success: boolean
  message: string
  upload_id: string
  temp_url: string
  filename: string
  material_code: string
  size: number
  uploaded_at: string
}

export interface ImageConfirmResponse {
  success: boolean
  message: string
  upload_id: string
  object_name: string
  permanent_url: string
  filename: string
  material_code: string
  spare_part_id?: number
  confirmed_at: string
}

export interface SparePartImage {
  id: number
  filename: string
  url: string
  object_name: string
  is_temp: number
  size?: number
  uploaded_at: string
  confirmed_at?: string
  original_filename?: string
  content_type?: string
  material_code?: string
}

/**
 * 从 Blob 临时上传图片（用于批量导入中的 Excel 嵌入图片）
 */
export async function uploadTempImageFromBlob(
  blob: Blob,
  filename: string,
  materialCode: string
): Promise<TempUploadResponse> {
  const ext = (filename.split('.').pop() || 'png').toLowerCase()
  const fallback = ext === 'jpg' || ext === 'jpeg' ? 'image/jpeg' : ext === 'gif' ? 'image/gif' : 'image/png'
  const mime = /^image\/(jpeg|png|gif|webp)$/i.test(blob.type) ? blob.type : fallback
  const file = new File([blob], filename, { type: mime })
  return uploadTempImage(file, materialCode)
}

/**
 * 临时上传图片（表单提交前）
 */
export async function uploadTempImage(
  file: File,
  materialCode: string,
  onProgress?: (progress: number) => void
): Promise<TempUploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('material_code', materialCode)

  console.log('上传图片参数:', {
    fileName: file.name,
    fileSize: file.size,
    fileType: file.type,
    materialCode: materialCode,
    hasFile: true
  })

  try {
    console.log('开始发送上传请求...')
    
    // 使用专门的上传实例
    const response = await uploadRequest.post('/images/temp-upload', formData, {
      onUploadProgress: (progressEvent: AxiosProgressEvent) => {
        console.log('上传进度事件:', progressEvent)
        if (onProgress && progressEvent.total && progressEvent.total > 0) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          console.log('上传进度:', progress)
          onProgress(progress)
        }
      }
    })

    console.log('上传响应:', response)
    
    // 现在 response 是完整的响应对象，需要通过 response.data 获取数据
    const responseData = response.data
    
    console.log('上传响应数据:', responseData)
    
    if (!responseData) {
      throw new Error('服务器返回空响应')
    }
    
    // 确保返回的数据结构正确
    if (responseData.success === false) {
      throw new Error(responseData.message || '上传失败')
    }
    
    return responseData
    
  } catch (error: any) {
    console.error('上传图片失败:', error)
    throw error
  }
}

/**
 * 确认图片（表单提交后）
 */
export async function confirmImage(
  uploadId: string,
  materialCode: string,
  sparePartId?: number
): Promise<ImageConfirmResponse> {
  const formData = new FormData()
  formData.append('upload_id', uploadId)
  formData.append('material_code', materialCode)
  if (sparePartId) {
    formData.append('spare_part_id', sparePartId.toString())
  }

  // 这里也用上传实例
  const response = await uploadRequest.post('/images/confirm', formData)
  return response.data
}

/**
 * 批量确认图片
 */
/**
 * 批量确认图片 - 修复版本
 */
export async function bulkConfirmImages(
  uploadIds: string[],
  sparePartId?: number,
  materialCode?: string
): Promise<any> {
  try {
    console.log('批量确认图片参数:', { uploadIds, sparePartId, materialCode })
    
    // 注意：根据后端API，可能不需要传递material_code
    const requestData: any = {
      upload_ids: uploadIds
    }
    
    if (sparePartId !== undefined) {
      requestData.spare_part_id = sparePartId
    }
    
    // 根据后端API决定是否需要material_code
    // 如果后端需要，则添加
    if (materialCode) {
      requestData.material_code = materialCode
    }
    
    const response = await request.post('/images/bulk-confirm', requestData)
    console.log('批量确认图片响应:', response)
    return response
    
  } catch (error: any) {
    console.error('批量确认图片失败:', error)
    
    // 如果批量确认失败，返回一个可以处理的结果结构
    return {
      data: {
        success: false,
        message: error.message,
        failed: uploadIds.map(id => ({ upload_id: id, error: error.message }))
      }
    }
  }
}

/**
 * 删除临时图片
 */
export async function deleteTempImage(uploadId: string): Promise<void> {
  // 这里用普通请求实例
  await request.delete(`/images/temp/${uploadId}`)
}

/**
 * 删除永久图片
 */
export async function deletePermanentImage(imageId: number): Promise<void> {
  // 这里用普通请求实例
  await request.delete(`/images/permanent/${imageId}`)
}

/**
 * 获取修复件的所有图片
 */
/**
 * 根据物料编码获取图片
 */
export async function getImagesByMaterial(materialCode: string): Promise<any[]> {
  try {
    // 这里用普通请求实例
    const response = await request.get(`/images/by-material/${materialCode}`)
    
    if (response && Array.isArray(response.images)) {
      return response.images
    }
    
    return []
  } catch (error: any) {
    console.error('获取物料图片失败:', error)
    return []
  }
}

/**
 * 直接上传图片（兼容旧接口）
 */
export async function uploadImage(
  file: File,
  materialCode: string,
  sparePartId?: number,
  options: any = {}
): Promise<any> {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('material_code', materialCode)
  
  if (sparePartId) {
    formData.append('spare_part_id', sparePartId.toString())
  }
  
  // 使用上传实例
  const response = await uploadRequest.post('/images/upload', formData, {
    onUploadProgress: (progressEvent: AxiosProgressEvent) => {
      if (progressEvent.total && options.onProgress) {
        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        options.onProgress(progress)
      }
    }
  })
  
  return response.data
}

/**
 * 批量删除图片
 */
export async function bulkDeleteImages(imageIds: number[]): Promise<any> {
  // 这里用普通请求实例
  const response = await request.delete('/images/bulk', {
    data: { image_ids: imageIds }
  })
  
  return response
}

/**
 * 转换MinIO容器内部URL为可访问的URL
 * 直接使用后端API提供的URL，不进行复杂的转换
 */
export function convertMinioUrlToAccessible(url: string): string {
  return smartConvertMinioUrl(url)
}

// frontend/src/utils/imageUpload.ts
// 添加以下函数

/**
 * 获取临时图片信息
 */
export async function getTempImage(uploadId: string): Promise<TempUploadResponse> {
  try {
    const response = await request.get(`/images/temp/${uploadId}`)
    return response
  } catch (error: any) {
    console.error('获取临时图片失败:', error)
    throw error
  }
}

/**
 * 批量获取临时图片
 */
export async function getTempImagesBatch(uploadIds: string[]): Promise<{images: TempUploadResponse[]}> {
  try {
    const response = await request.post('/images/temp/batch', uploadIds)
    return response
  } catch (error: any) {
    console.error('批量获取临时图片失败:', error)
    throw error
  }
}

/**
 * 从URL下载图片并上传到临时存储（用于批量导入）。
 * 公式（=DISPIMG）、503、400 时跳过并返回 upload_id=null，不抛错，批量导入继续。
 */
export async function downloadAndUploadImageFromUrl(
  imageUrl: string,
  materialCode: string
): Promise<TempUploadResponse & { upload_id?: string | null }> {
  const t = String(imageUrl ?? '').trim()
  if (!t || t.startsWith('=') || /^=DISPIMG\s*\(/i.test(t)) {
    if (!_formulaOr400Warned) {
      _formulaOr400Warned = true
      ElMessage.warning('检测到 Excel 公式(=DISPIMG)，已跳过；请将实物图片映射为「本行嵌入图片1/2」以导入表内图片。')
    }
    return { upload_id: null } as any
  }
  try {
    const formData = new FormData()
    formData.append('image_url', t)
    formData.append('material_code', materialCode)
    const response = await uploadRequest.post('/images/download-and-upload', formData)
    return response.data
  } catch (error: any) {
    const status = error?.response?.status
    const msg = String(error?.message || '')
    const is503 = status === 503 || /\(503\)/.test(msg)
    if (is503) {
      if (!_httpx503Warned) {
        _httpx503Warned = true
        ElMessage.warning('图片导入需要服务器安装 httpx，已跳过图片；修复件数据将正常导入。')
      }
      return { upload_id: null } as any
    }
    const is400 = status === 400 || /\(400\)/.test(msg)
    if (is400) {
      if (!_formulaOr400Warned) {
        _formulaOr400Warned = true
        ElMessage.warning('部分图片地址无效或无法下载，已跳过；请用「本行嵌入图片」导入表内图片。')
      }
      return { upload_id: null } as any
    }
    console.warn('从URL下载并上传图片失败:', error?.message || error)
    throw error
  }
}

/**
 * 获取修复件图片列表（/images/by-spare-part）。
 * 若接口 404 或失败，静默返回 []，不抛错。
 */
export async function getSparePartImages(sparePartId: number): Promise<SparePartImage[]> {
  try {
    const response = await request.get(`/images/by-spare-part/${sparePartId}`)
    
    if (response && (response as any).images && Array.isArray((response as any).images)) {
      return (response as any).images.map((img: any) => ({
        id: img.id,
        filename: img.filename || img.object_name?.split('/').pop() || '未知文件',
        url: img.url || '',
        object_name: img.object_name,
        is_temp: img.is_temp || 0,
        size: img.size,
        uploaded_at: img.uploaded_at,
        confirmed_at: img.confirmed_at,
        original_filename: img.original_filename,
        content_type: img.content_type,
        material_code: img.material_code
      }))
    }
    
    return []
  } catch (e: any) {
    if (e?.response?.status === 404) return []
    console.warn('获取修复件图片失败:', e?.message || e)
    return []
  }
}


/**
 * 获取图片URL - 简化版本
 */
export function getImageUrl(
  urlOrPathOrObject: string | { object_name?: string; filename?: string; url?: string },
  options: {
    width?: number
    height?: number
    quality?: number
    format?: 'webp' | 'jpeg' | 'png'
  } = {}
): string {
  // 如果是对象，提取相关信息
  let urlOrPath: string = ''
  
  if (typeof urlOrPathOrObject === 'string') {
    urlOrPath = urlOrPathOrObject
  } else if (urlOrPathOrObject && typeof urlOrPathOrObject === 'object') {
    // 优先使用url，其次object_name，最后filename
    urlOrPath = urlOrPathOrObject.url || urlOrPathOrObject.object_name || urlOrPathOrObject.filename || ''
  }
  
  console.log('getImageUrl输入:', urlOrPathOrObject, '提取的URL:', urlOrPath)
  
  if (!urlOrPath) {
    console.warn('getImageUrl: 没有有效的URL或路径')
    return ''
  }
  
  // 1. 如果是完整URL（http://...），直接转换
  if (urlOrPath.startsWith('http://') || urlOrPath.startsWith('https://')) {
    const convertedUrl = convertMinioUrlToAccessible(urlOrPath)
    console.log('完整URL转换结果:', convertedUrl)
    return convertedUrl
  }
  
  // 2. 如果是对象路径（如 spare-parts/xxx/xxx.jpg）
  if (urlOrPath.includes('spare-parts/') || urlOrPath.includes('spareparts/')) {
    // 对于对象路径，我们无法直接访问，需要后端API
    console.warn('对象路径需要后端API访问:', urlOrPath)
    return ''
  }
  
  console.warn('无法识别的图片URL格式:', urlOrPath)
  return ''
}

/**
 * 获取优化的图片URL
 */
export function getOptimizedUrl(
  url: string,
  options: {
    width?: number
    height?: number
    quality?: number
    format?: 'webp' | 'jpeg' | 'png'
  } = {}
): string {
  if (!url) return ''
  
  // 先转换可能存在的容器内部地址
  const accessibleUrl = convertMinioUrlToAccessible(url)
  
  return accessibleUrl
}

/**
 * 验证图片文件
 */
export function validateImageFile(file: File): { valid: boolean; message?: string } {
  // 检查文件类型
  const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp']
  if (!allowedTypes.includes(file.type)) {
    return {
      valid: false,
      message: `不支持的文件类型: ${file.type}。请选择 JPEG、PNG、GIF、WebP 或 BMP 格式的图片`
    }
  }
  
  // 检查文件大小（10MB），与后端配置保持一致
  const maxSize = 10 * 1024 * 1024
  if (file.size > maxSize) {
    return {
      valid: false,
      message: `文件大小超过限制 (${(file.size / 1024 / 1024).toFixed(2)}MB > 10MB)`
    }
  }
  
  // 检查文件扩展名
  const allowedExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
  const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase()
  if (!fileExtension || !allowedExtensions.includes(fileExtension)) {
    return {
      valid: false,
      message: `不支持的文件扩展名: ${fileExtension}`
    }
  }
  
  return { valid: true }
}

/**
 * 测试URL可访问性 - 简化版本
 */
export async function testUrlAccessibility(url: string, timeout: number = 5000): Promise<boolean> {
  if (!url) return false
  
  // 对于临时图片URL，直接返回true，让用户创建表单时确认
  if (url.includes('/temp/')) {
    console.log('临时图片URL，跳过测试')
    return true
  }
  
  try {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), timeout)
    
    const response = await fetch(url, {
      method: 'HEAD',
      mode: 'cors',
      signal: controller.signal,
      headers: {
        'Accept': 'image/*',
        'Cache-Control': 'no-cache'
      }
    })
    
    clearTimeout(timeoutId)
    
    if (response.ok) {
      console.log(`URL可访问: ${url} - ${response.status}`)
      return true
    } else {
      console.warn(`URL不可访问: ${url} - ${response.status} ${response.statusText}`)
      return false
    }
  } catch (error: any) {
    console.warn(`URL访问测试失败: ${url}`, error.message)
    return false
  }
}