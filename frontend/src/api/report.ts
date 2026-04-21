import request from '@/utils/request'

export interface BrandStatItem {
  brand: string
  inbound: number
  outbound: number
}

export interface ApplicableModelStatItem {
  applicable_model: string
  inbound: number
  outbound: number
}

export type TimeRange = 'today' | '7d' | '30d' | '6m' | '1y' | 'custom'

export type MaterialScope = 'electrical' | 'mechanical'

/**
 * 按品牌获取入库/出库统计，仅统计指定 scope 数据
 */
export function getReportByBrand(
  scope: MaterialScope,
  time_range: TimeRange = '30d',
  start_date?: string,
  end_date?: string
) {
  const params: Record<string, string> = { scope, time_range }
  if (start_date) params.start_date = start_date
  if (end_date) params.end_date = end_date
  return request.get<BrandStatItem[]>('/reports/statistics/by-brand', { params })
}

/**
 * 按适用机型获取入库/出库统计，仅统计指定 scope 数据
 */
export function getReportByApplicableModel(
  scope: MaterialScope,
  time_range: TimeRange = '30d',
  start_date?: string,
  end_date?: string
) {
  const params: Record<string, string> = { scope, time_range }
  if (start_date) params.start_date = start_date
  if (end_date) params.end_date = end_date
  return request.get<ApplicableModelStatItem[]>('/reports/statistics/by-applicable-model', { params })
}
