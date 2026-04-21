import request from '@/utils/request'
import type {
  SparePart,
  SparePartCreate,
  SparePartUpdate,
} from '@/types/sparePart'

/** 修复件列表查询参数（含筛选） */
export interface SparePartQueryParams {
  skip?: number
  limit?: number
  keyword?: string
  brand?: string
  applicable_model?: string
  storage_location?: string
  location_prefix?: string
  updated_since?: string
  /** 库存提醒筛选：zero=仅零库存，low=仅低库存(总库存=1) */
  stock_alert?: 'zero' | 'low'
}

/** 筛选下拉选项 */
export interface SparePartFilterOptions {
  brands: string[]
  applicable_models: string[]
  storage_locations: string[]
  specification_models?: string[]
  location_prefixes: string[]
}

/**
 * 修复件管理API
 */
export const sparePartApi = {
  /**
   * 获取修复件列表（分页），支持关键词及品牌/适用机型/存放地/货位号前缀/更新时间段筛选
   * @param params 查询参数
   * @returns { items, total }
   */
  getList(params?: SparePartQueryParams) {
    return request.get<{ items: SparePart[]; total: number; zero_count?: number; low_count?: number }>('/spare-parts', { params })
  },

  /**
   * 获取修复件筛选下拉选项（品牌、适用机型、存放地、货位号首字符）
   */
  getFilterOptions() {
    return request.get<SparePartFilterOptions>('/spare-parts-filter-options')
  },

  /**
   * 获取单个修复件详情
   * @param id 修复件ID
   */
  getDetail(id: number) {
    return request.get<SparePart>(`/spare-parts/${id}`)
  },

  /**
   * 获取修复件详情（含图片列表），用于编辑表单加载已有图片
   * @param id 修复件ID
   * @returns { ...sparePart, images: Array<{id, filename, url, ...}> }
   */
  getDetailWithImages(id: number) {
    return request.get<SparePart & { images?: Array<{ id: number; filename?: string; url?: string; is_temp?: boolean; size?: number; uploaded_at?: string }> }>(
      `/spare-parts/${id}/with-images`
    )
  },

  /**
   * 创建新修复件
   * @param data 修复件数据
   * @param params allow_overwrite 模式一批量导入时 true：货位号+规格型号已存在则覆盖更新
   */
  create(data: SparePartCreate, params?: { allow_overwrite?: boolean }) {
    return request.post<SparePart>('/spare-parts', data, { params })
  },

  /**
   * 更新修复件信息
   * @param id 修复件ID
   * @param data 更新数据
   */
  update(id: number, data: SparePartUpdate) {
    return request.put<SparePart>(`/spare-parts/${id}`, data)
  },

  /**
   * 删除修复件
   * @param id 修复件ID
   */
  delete(id: number) {
    return request.delete(`/spare-parts/${id}`)
  },

  /**
   * 根据MES编码检查修复件是否存在
   * @param mesCode MES物料编码
   * @returns 匹配的修复件列表（最多 1 条）
   */
  async checkExists(mesCode: string) {
    const res = await request.get<{ items: SparePart[]; total: number }>('/spare-parts', {
      params: { keyword: mesCode, limit: 1 },
    })
    return res?.items ?? []
  },

  /**
   * 修复件领用查询：关键词搜规格型号、MES编码、物料描述、适用机型、品牌；
   * 过滤器：规格型号、适用机型、品牌、货位号前缀。
   */
  requisitionSearch(params: {
    keyword?: string
    skip: number
    limit: number
    brand?: string
    applicable_model?: string
    specification_model?: string
    storage_location?: string
    location_prefix?: string
    stock_alert?: 'zero' | 'low'
  }) {
    return request.get<{ items: SparePart[]; total: number; zero_count?: number; low_count?: number }>('/requisition-search', { params })
  },

  /**
   * 当前用户的最近领用记录（电气），用于领用页「最近领用」展示。
   */
  getRecentRequisition(limit = 10) {
    return request.get<{ items: Array<{ id: number; requisition_at: string; quantity: number; spare_part_id: number; mes_material_code?: string; specification_model?: string; location_code?: string; unreturned_qty?: number }> }>('/requisition-recent', { params: { limit } })
  },

  /**
   * 修复件领用：扣减修复件库存。领用人由后端根据当前登录用户的真实姓名自动确定。
   */
  requisition(id: number, quantity: number, requisition_reason: string, usage_location: string, remark?: string) {
    const body: Record<string, unknown> = {
      quantity,
      requisition_reason: (requisition_reason || '').trim(),
      usage_location: (usage_location || '').trim(),
    }
    if (remark != null && String(remark).trim() !== '') {
      body.remark = String(remark).trim()
    }
    return request.post<RequisitionResponse>(`/spare-parts/${id}/requisition`, body)
  },

  /**
   * 修复件归还：增加修复件库存，不能超过当前用户的未归还余量。
   */
  returnPart(id: number, quantity: number, remark?: string) {
    return request.post<RequisitionResponse>(`/spare-parts/${id}/return`, {
      quantity,
      remark: remark ?? undefined,
    })
  },

  /**
   * 批量创建修复件
   * @param dataList 修复件数据数组
   */
  batchCreate(dataList: SparePartCreate[]) {
    return request.post<BatchCreateResponse>('/spare-parts/batch', { items: dataList })
  },

  /**
   * 批量删除修复件
   * @param ids 修复件 ID 数组
   */
  batchDelete(ids: number[]) {
    return request.post<BatchDeleteResponse>('/spare-parts/batch-delete', { ids })
  },

  /**
   * 按 MES 编码批量更新 MES 库存
   * @param items 每项含 mes_material_code、mes_stock
   */
  batchUpdateMesStock(items: Array<{ mes_material_code: string; mes_stock: number }>) {
    return request.post<{ updated: number; skipped: number; errors: Array<{ row: number; message: string }> }>(
      '/spare-parts/batch-update-mes',
      { items }
    )
  },
}

export interface RequisitionResponse {
  success: boolean
  message: string
  spare_part_id: number
  quantity: number
  physical_stock_before: number
  physical_stock_after: number
}

// 批量创建响应类型
export interface BatchCreateResponse {
  success: boolean
  message: string
  totalCount: number
  successCount: number
  failedCount: number
  skippedCount: number
  errors?: Array<{ row: number; message: string }>
}

// 批量删除响应类型
export interface BatchDeleteResponse {
  success: boolean
  message: string
  deleted: number
  failed: number
  errors?: Array<{ id: number; message: string }>
}

/**
 * 创建修复件并确认临时图片
 */
// frontend/src/api/sparePart.ts

/**
 * 创建修复件并确认临时图片 - 修复版本
 */

/**
 * 更新修复件并处理图片 - 修复版本
 */
// frontend/src/api/sparePart.ts

/**
 * 创建修复件并确认临时图片 - 修复版本（确保传递image_index）
 */
/**
 * 创建修复件并确认临时图片 - 修复版本（确保传递image_index）
 */

// frontend/src/api/sparePart.ts

/**
 * 创建修复件并确认临时图片 - 修复版本
 */

/**
 * 批量确认图片（独立的函数）
 */

/**
 * 更新修复件并处理图片 - 修复版本
 */

/**
 * 更新修复件并处理图片
 */

/**
 * 获取修复件图片
 */
// frontend/src/api/sparePart.ts

/**
 * 创建修复件并确认临时图片 - 最终版本
 */
export async function createSparePartWithImages(
  data: SparePartCreate,
  tempImageIds: string[] = [],
  options?: { allowOverwrite?: boolean }
): Promise<SparePart> {
  try {
    console.log('开始创建修复件...')
    console.log('修复件数据:', data)
    console.log('临时图片ID:', tempImageIds)
    
    // 1. 先创建修复件（模式一时 allow_overwrite 使已存在则覆盖）
    const response = await sparePartApi.create(data, options?.allowOverwrite ? { allow_overwrite: true } : undefined)
    
    if (!response) {
      throw new Error('创建修复件失败：未返回响应')
    }
    
    const sparePartId = response.id
    
    if (!sparePartId) {
      throw new Error('创建修复件失败：未返回有效ID')
    }
    
    console.log('修复件创建成功，ID:', sparePartId)
    
    // 2. 如果有临时图片，逐个确认
    if (tempImageIds.length > 0) {
      console.log('开始确认临时图片，修复件ID:', sparePartId, '图片数量:', tempImageIds.length)
      
      // 逐个确认图片，传递正确的image_index
      const successIds: string[] = []
      const failedIds: string[] = []
      
      for (let index = 0; index < tempImageIds.length; index++) {
        const uploadId = tempImageIds[index]
        try {
          const formData = new FormData()
          formData.append('upload_id', uploadId)
          formData.append('material_code', data.mes_material_code)
          formData.append('spare_part_id', sparePartId.toString())
          formData.append('image_index', index.toString())  // 传递图片索引
          
          await request.post('/images/confirm', formData)
          console.log(`图片 ${uploadId} 确认成功，索引: ${index}`)
          successIds.push(uploadId)
          
        } catch (singleError) {
          console.error(`确认图片 ${uploadId} 失败:`, singleError)
          failedIds.push(uploadId)
        }
      }
      
      console.log('图片确认结果:', {
        成功: successIds.length,
        失败: failedIds.length,
        失败列表: failedIds
      })
      
      if (failedIds.length > 0) {
        console.warn('部分图片确认失败:', failedIds)
        // 不抛出错误，继续流程
      }
    }
    
    // 3. 关键步骤：调用同步接口，确保spare_parts表的图片URL字段被更新
    try {
      console.log('调用图片同步接口...')
      const syncResponse = await syncSparePartImages(sparePartId)
      console.log('图片同步结果:', syncResponse)
    } catch (syncError) {
      console.error('图片同步失败:', syncError)
      // 不抛出错误，继续流程
    }
    
    // 4. 重新获取修复件信息（request 返回 body，无 .data）
    const updated = await sparePartApi.getDetail(sparePartId)
    return updated as SparePart
    
  } catch (error: any) {
    console.error('创建修复件（包含图片）失败:', error)
    throw error
  }
}

/**
 * 更新修复件并处理图片 - 最终版本
 */
export async function updateSparePartWithImages(
  id: number, 
  data: SparePartUpdate, 
  tempImageIds: string[] = [], 
  imageIdsToDelete: number[] = []
): Promise<SparePart> {
  try {
    // 1. 更新修复件（含 image_ids_to_delete），由后端统一删图 + 更新
    const updatePayload: SparePartUpdate & { image_ids_to_delete?: number[] } = { ...data }
    if (imageIdsToDelete.length > 0) {
      updatePayload.image_ids_to_delete = imageIdsToDelete
      console.log('更新修复件并删除图片，ID列表:', imageIdsToDelete)
    }
    const sparePart = await sparePartApi.update(id, updatePayload)
    const mesCode = (sparePart as any)?.mes_material_code ?? (data as any)?.mes_material_code
    console.log('修复件更新成功，ID:', id)
    
    // 2. 确认临时图片
    if (tempImageIds.length > 0) {
      console.log('确认临时图片，修复件ID:', id, '图片数量:', tempImageIds.length)
      for (let index = 0; index < tempImageIds.length; index++) {
        const uploadId = tempImageIds[index]
        try {
          const formData = new FormData()
          formData.append('upload_id', uploadId)
          formData.append('material_code', mesCode || '')
          formData.append('spare_part_id', id.toString())
          formData.append('image_index', index.toString())
          await request.post('/images/confirm', formData)
          console.log(`图片 ${uploadId} 确认成功，索引: ${index}`)
        } catch (singleError) {
          console.error(`确认图片 ${uploadId} 失败:`, singleError)
        }
      }
    }
    
    // 3. 同步 spare_parts 表图片 URL
    try {
      console.log('调用图片同步接口...')
      await syncSparePartImages(id)
    } catch (syncError) {
      console.error('图片同步失败:', syncError)
    }
    
    // 4. 重新拉取详情返回（request 返回 body，无 .data）
    const updated = await sparePartApi.getDetail(id)
    return updated as SparePart
  } catch (error: any) {
    console.error('更新修复件（包含图片处理）失败:', error)
    throw error
  }
}

/**
 * 同步修复件的图片数据到spare_parts表的字段
 */
export async function syncSparePartImages(sparePartId: number): Promise<any> {
  try {
    console.log(`同步修复件 ${sparePartId} 的图片数据...`)
    // 与 backend 路由 POST /{part_id}/sync-images 对应（挂载在 /api/v1 下）
    const res = await request.post(`/${sparePartId}/sync-images`)
    console.log('同步响应:', res)
    return res
  } catch (error) {
    console.error('同步图片数据失败:', error)
    throw error
  }
}

/**
 * 获取修复件图片列表 - 修复版本
 */
export async function getSparePartImages(sparePartId: number): Promise<any[]> {
  try {
    const res = await request.get(`/images/by-spare-part/${sparePartId}`)
    if (res && (res as any).images) return (res as any).images
    if (Array.isArray(res)) return res
    return []
  } catch (error) {
    console.error('获取修复件图片失败:', error)
    return []
  }
}
// 兼容性导出
export default sparePartApi

// 创建修复件（兼容旧接口）
export async function createSparePart(data: SparePartCreate): Promise<SparePart> {
  const response = await request.post<SparePart>('/spare-parts', data)
  return response.data
}

// 更新修复件（兼容旧接口）
export async function updateSparePart(id: number, data: SparePartUpdate): Promise<SparePart> {
  const response = await request.put<SparePart>(`/spare-parts/${id}`, data)
  return response.data
}

/**
 * 同步修复件图片数据
 */
