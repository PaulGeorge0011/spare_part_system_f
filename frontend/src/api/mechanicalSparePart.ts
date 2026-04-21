import request from '@/utils/request'
import type {
  MechanicalSparePart,
  MechanicalSparePartCreate,
  MechanicalSparePartUpdate,
  MechanicalSparePartQueryParams,
  MechanicalSparePartFilterOptions,
} from '@/types/mechanicalSparePart'

export const mechanicalSparePartApi = {
  getList(params?: MechanicalSparePartQueryParams) {
    return request.get<{ items: MechanicalSparePart[]; total: number; zero_count?: number; low_count?: number }>('/mechanical-spare-parts', { params })
  },

  getFilterOptions() {
    return request.get<MechanicalSparePartFilterOptions>('/mechanical-spare-parts-filter-options')
  },

  getDetail(id: number) {
    return request.get<MechanicalSparePart>(`/mechanical-spare-parts/${id}`)
  },

  getDetailWithImages(id: number) {
    return request.get<MechanicalSparePart & { images?: Array<{ id: number; filename?: string; url?: string; is_temp?: boolean; size?: number; uploaded_at?: string }> }>(
      `/mechanical-spare-parts/${id}/with-images`
    )
  },

  create(data: MechanicalSparePartCreate, params?: { allow_overwrite?: boolean }) {
    return request.post<MechanicalSparePart>('/mechanical-spare-parts', data, { params })
  },

  update(id: number, data: MechanicalSparePartUpdate) {
    return request.put<MechanicalSparePart>(`/mechanical-spare-parts/${id}`, data)
  },

  delete(id: number) {
    return request.delete(`/mechanical-spare-parts/${id}`)
  },

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
    return request.get<{ items: MechanicalSparePart[]; total: number; zero_count?: number; low_count?: number }>('/mechanical-requisition-search', { params })
  },

  /** 当前用户的最近领用记录（机械） */
  getRecentRequisition(limit = 10) {
    return request.get<{ items: Array<{ id: number; requisition_at: string; quantity: number; mechanical_spare_part_id: number; mes_material_code?: string; specification_model?: string; location_code?: string; unreturned_qty?: number }> }>('/mechanical-requisition-recent', { params: { limit } })
  },

  requisition(id: number, quantity: number, requisition_reason: string, usage_location: string, remark?: string) {
    const body: Record<string, unknown> = {
      quantity,
      requisition_reason: (requisition_reason || '').trim(),
      usage_location: (usage_location || '').trim(),
    }
    if (remark != null && String(remark).trim() !== '') {
      body.remark = String(remark).trim()
    }
    return request.post<{ success: boolean; message: string; spare_part_id: number; quantity: number; physical_stock_before: number; physical_stock_after: number }>(
      `/mechanical-spare-parts/${id}/requisition`,
      body
    )
  },

  /** 机械备件归还：增加库存，不能超过当前用户的未归还余量。 */
  returnPart(id: number, quantity: number, remark?: string) {
    return request.post<{ success: boolean; message: string; spare_part_id: number; quantity: number; physical_stock_before: number; physical_stock_after: number }>(
      `/mechanical-spare-parts/${id}/return`,
      { quantity, remark: remark ?? undefined }
    )
  },

  batchCreate(dataList: MechanicalSparePartCreate[]) {
    return request.post<{ success: boolean; message: string; totalCount: number; successCount: number; failedCount: number; skippedCount: number; errors?: Array<{ row: number; message: string }> }>(
      '/mechanical-spare-parts/batch',
      { items: dataList }
    )
  },

  batchDelete(ids: number[]) {
    return request.post<{ success: boolean; message: string; deleted: number; failed: number; errors?: Array<{ id: number; message: string }> }>(
      '/mechanical-spare-parts/batch-delete',
      { ids }
    )
  },

  /**
   * 按 MES 编码批量更新 MES 库存
   */
  batchUpdateMesStock(items: Array<{ mes_material_code: string; mes_stock: number }>) {
    return request.post<{ updated: number; skipped: number; errors: Array<{ row: number; message: string }> }>(
      '/mechanical-spare-parts/batch-update-mes',
      { items }
    )
  },
}

export async function createMechanicalSparePartWithImages(
  data: MechanicalSparePartCreate,
  tempImageIds: string[] = [],
  options?: { allowOverwrite?: boolean }
): Promise<MechanicalSparePart> {
  const payload = { ...data, image_upload_ids: tempImageIds.length ? tempImageIds : data.image_upload_ids }
  const res = await mechanicalSparePartApi.create(payload, options?.allowOverwrite ? { allow_overwrite: true } : undefined)
  if (tempImageIds.length) {
    try {
      await request.post(`/mechanical-spare-parts/${(res as any).id}/sync-images`)
    } catch (_) {}
  }
  const updated = await mechanicalSparePartApi.getDetail((res as any).id)
  return updated as MechanicalSparePart
}

export async function updateMechanicalSparePartWithImages(
  id: number,
  data: MechanicalSparePartUpdate,
  tempImageIds: string[] = [],
  imageIdsToDelete: number[] = []
): Promise<MechanicalSparePart> {
  const payload = { ...data, image_ids_to_delete: imageIdsToDelete.length ? imageIdsToDelete : data.image_ids_to_delete, image_upload_ids: tempImageIds.length ? tempImageIds : data.image_upload_ids }
  await mechanicalSparePartApi.update(id, payload)
  if (tempImageIds.length || (imageIdsToDelete && imageIdsToDelete.length)) {
    try {
      await request.post(`/mechanical-spare-parts/${id}/sync-images`)
    } catch (_) {}
  }
  const updated = await mechanicalSparePartApi.getDetail(id)
  return updated as MechanicalSparePart
}

export default mechanicalSparePartApi
