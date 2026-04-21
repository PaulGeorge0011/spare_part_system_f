import request from '@/utils/request'

export interface InventoryRecord {
  id: number
  event_type: string
  inbound_time: string | null
  outbound_time: string | null
  requisitioner_name: string | null
  operator_name: string | null
  spare_part_id: number
  location_code: string | null
  mes_material_code: string | null
  specification_model: string | null
  unit: string | null
  physical_image_url: string | null
  physical_image_url2: string | null
  quantity: number
  physical_stock_before: number | null
  physical_stock_after: number | null
  remark: string | null
  requisition_reason: string | null
  usage_location: string | null
  storage_location: string | null
}

export type TimeRange = 'today' | '7d' | '30d' | '6m' | '1y' | 'custom'

export type MaterialScope = 'electrical' | 'mechanical'

/**
 * 查询库存记录，仅返回指定 scope（电气或机械）数据
 * @param scope 物资范围：electrical 仅电气，mechanical 仅机械
 */
export function getInventoryRecords(
  scope: MaterialScope,
  time_range: TimeRange = '30d',
  start_date?: string,
  end_date?: string,
  event_type?: string,
  requisitioner?: string
) {
  const params: Record<string, string> = { scope, time_range }
  if (start_date) params.start_date = start_date
  if (end_date) params.end_date = end_date
  if (event_type?.trim()) params.event_type = event_type.trim()
  if (requisitioner?.trim()) params.requisitioner = requisitioner.trim()
  return request.get<InventoryRecord[]>('/inventory/records', { params })
}

/** 获取库存记录中已出现的操作人列表，按 scope 仅电气或仅机械 */
export function getInventoryOperatorOptions(scope: MaterialScope) {
  return request.get<string[]>('/inventory/operator-options', { params: { scope } })
}
