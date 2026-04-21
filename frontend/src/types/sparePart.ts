import request from '@/utils/request'
import type {
  SparePart,
  SparePartCreate,
  SparePartUpdate,
  SparePartQueryParams,
} from '@/types/sparePart'

/**
 * 修复件管理API
 */
export const sparePartApi = {
  /**
   * 获取修复件列表
   * @param params 查询参数
   */
  getList(params?: SparePartQueryParams) {
    return request.get<SparePart[]>('/spare-parts', { params })
  },

  /**
   * 获取单个修复件详情
   * @param id 修复件ID
   */
  getDetail(id: number) {
    return request.get<SparePart>(`/spare-parts/${id}`)
  },

  /**
   * 创建新修复件
   * @param data 修复件数据
   */
  create(data: SparePartCreate) {
    return request.post<SparePart>('/spare-parts', data)
  },

  /**
   * 创建修复件并确认临时图片
   * @param data 修复件数据
   * @param tempImageIds 临时图片ID数组
   */
  async createWithImages(data: SparePartCreate, tempImageIds: string[] = []): Promise<SparePart> {
    try {
      // 1. 先创建修复件
      const sparePart = await request.post<SparePart>('/spare-parts', data)
      
      if (!sparePart.data || !sparePart.data.id) {
        throw new Error('创建修复件失败：未返回有效ID')
      }
      
      const sparePartId = sparePart.data.id
      
      // 2. 如果有临时图片，批量确认并关联到修复件
      if (tempImageIds.length > 0) {
        console.log('开始确认临时图片，修复件ID:', sparePartId, '图片数量:', tempImageIds.length)
        
        try {
          // 使用批量确认接口
          const confirmResponse = await request.post('/images/bulk-confirm', {
            upload_ids: tempImageIds,
            spare_part_id: sparePartId,
            material_code: data.mes_material_code
          })
          
          console.log('批量确认图片结果:', confirmResponse.data)
          
          if (confirmResponse.data.success === false && confirmResponse.data.failed && confirmResponse.data.failed.length > 0) {
            console.warn('部分图片确认失败:', confirmResponse.data.failed)
            // 不抛出错误，继续流程，只记录警告
          }
          
        } catch (confirmError: any) {
          console.error('批量确认图片失败:', confirmError)
          // 备用方案：逐个确认
          console.log('尝试逐个确认图片...')
          
          for (const uploadId of tempImageIds) {
            try {
              const formData = new FormData()
              formData.append('upload_id', uploadId)
              formData.append('material_code', data.mes_material_code)
              formData.append('spare_part_id', sparePartId.toString())
              
              await request.post('/images/confirm', formData)
              console.log(`图片 ${uploadId} 确认成功`)
            } catch (singleError) {
              console.error(`确认图片 ${uploadId} 失败:`, singleError)
            }
          }
        }
      }
      
      // 3. 重新获取完整的修复件信息（包含图片）
      const fullDetail = await request.get<SparePart>(`/spare-parts/${sparePartId}/with-images`)
      return fullDetail.data
      
    } catch (error: any) {
      console.error('创建修复件（包含图片）失败:', error)
      throw error
    }
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
   * 更新修复件并处理图片
   * @param id 修复件ID
   * @param data 更新数据
   * @param tempImageIds 临时图片ID数组
   * @param imageIdsToDelete 要删除的图片ID数组
   */
  async updateWithImages(
    id: number, 
    data: SparePartUpdate, 
    tempImageIds: string[] = [], 
    imageIdsToDelete: number[] = []
  ): Promise<SparePart> {
    try {
      // 1. 先删除标记为删除的图片
      if (imageIdsToDelete.length > 0) {
        console.log('删除标记的图片，ID列表:', imageIdsToDelete)
        try {
          await request.delete('/images/bulk', {
            data: { image_ids: imageIdsToDelete }
          })
          console.log('图片删除成功')
        } catch (deleteError: any) {
          console.error('删除图片失败:', deleteError)
          // 不阻止后续操作，继续更新修复件
        }
      }
      
      // 2. 更新修复件基本信息
      const sparePart = await request.put<SparePart>(`/spare-parts/${id}`, data)
      
      // 3. 确认临时图片
      if (tempImageIds.length > 0) {
        console.log('确认临时图片，修复件ID:', id, '图片数量:', tempImageIds.length)
        
        try {
          // 使用批量确认接口
          const confirmResponse = await request.post('/images/bulk-confirm', {
            upload_ids: tempImageIds,
            spare_part_id: id,
            material_code: data.mes_material_code || ''
          })
          
          console.log('批量确认图片结果:', confirmResponse.data)
          
          if (confirmResponse.data.success === false && confirmResponse.data.failed && confirmResponse.data.failed.length > 0) {
            console.warn('部分图片确认失败:', confirmResponse.data.failed)
          }
          
        } catch (confirmError: any) {
          console.error('批量确认图片失败:', confirmError)
          // 备用方案：逐个确认
          console.log('尝试逐个确认图片...')
          
          for (const uploadId of tempImageIds) {
            try {
              const formData = new FormData()
              formData.append('upload_id', uploadId)
              formData.append('material_code', data.mes_material_code || '')
              formData.append('spare_part_id', id.toString())
              
              await request.post('/images/confirm', formData)
              console.log(`图片 ${uploadId} 确认成功`)
            } catch (singleError) {
              console.error(`确认图片 ${uploadId} 失败:`, singleError)
            }
          }
        }
      }
      
      // 4. 重新获取完整的修复件信息
      const fullDetail = await request.get<SparePart>(`/spare-parts/${id}/with-images`)
      return fullDetail.data
      
    } catch (error: any) {
      console.error('更新修复件（包含图片处理）失败:', error)
      throw error
    }
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
   */
  checkExists(mesCode: string) {
    // 通过查询列表来实现检查
    return request.get<SparePart[]>('/spare-parts', {
      params: { keyword: mesCode, limit: 1 },
    })
  },

  /**
   * 获取修复件图片
   * @param sparePartId 修复件ID
   */
  getImages(sparePartId: number) {
    return request.get(`/images/by-spare-part/${sparePartId}`)
  },
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

// 新增：获取临时图片信息
export async function getTempImageApi(uploadId: string) {
  return request.get(`/images/temp/${uploadId}`)
}

// 新增：批量获取临时图片
export async function getTempImagesBatchApi(uploadIds: string[]) {
  return request.post('/images/temp/batch', uploadIds)
}

/**
 * 创建修复件并确认临时图片
 */
export async function createSparePartWithImages(data: SparePartCreate, tempImageIds: string[] = []): Promise<SparePart> {
  try {
    console.log('开始创建修复件...')
    
    // 1. 先创建修复件
    const response = await sparePartApi.create(data)
    
    if (!response) {
      throw new Error('创建修复件失败：未返回响应')
    }
    
    const sparePartId = response.id
    
    if (!sparePartId) {
      throw new Error('创建修复件失败：未返回有效ID')
    }
    
    console.log('修复件创建成功，ID:', sparePartId)
    
    // 2. 如果有临时图片，批量确认并关联到修复件
    if (tempImageIds.length > 0) {
      console.log('开始确认临时图片，修复件ID:', sparePartId, '图片数量:', tempImageIds.length)
      
      try {
        // 使用批量确认接口
        const confirmResponse = await request.post('/images/bulk-confirm', {
          upload_ids: tempImageIds,
          spare_part_id: sparePartId,
          material_code: data.mes_material_code
        })
        
        console.log('批量确认图片结果:', confirmResponse.data)
        
        if (confirmResponse.data.success === false) {
          console.warn('部分图片确认失败:', confirmResponse.data.failed)
        }
        
      } catch (confirmError: any) {
        console.error('批量确认图片失败:', confirmError)
        // 备用方案：逐个确认
        console.log('尝试逐个确认图片...')
        
        for (const uploadId of tempImageIds) {
          try {
            const formData = new FormData()
            formData.append('upload_id', uploadId)
            formData.append('material_code', data.mes_material_code)
            formData.append('spare_part_id', sparePartId.toString())
            
            await request.post('/images/confirm', formData)
            console.log(`图片 ${uploadId} 确认成功`)
          } catch (singleError) {
            console.error(`确认图片 ${uploadId} 失败:`, singleError)
          }
        }
      }
    }
    
    return response
    
  } catch (error: any) {
    console.error('创建修复件（包含图片）失败:', error)
    throw error
  }
}
