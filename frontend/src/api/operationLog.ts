import request from '@/utils/request'

export interface OperationLog {
  id: number
  created_at: string
  user_id: number | null
  username: string | null
  real_name: string | null
  module: string
  action: string
  entity_type: string | null
  entity_id: number | null
  summary: string | null
  detail: string | null
}

export type TimeRange = 'today' | '7d' | '30d' | '6m' | '1y' | 'custom'

export type MaterialScope = 'electrical' | 'mechanical'

export interface OperationLogQuery {
  scope: MaterialScope
  time_range?: TimeRange
  start_date?: string
  end_date?: string
  username?: string
  module?: string
  action?: string
  keyword?: string
  limit?: number
  skip?: number
}

/** 分页列表接口返回 */
export interface OperationLogListResult {
  data: OperationLog[]
  total: number
}

export function getOperationLogs(params: OperationLogQuery) {
  const query: Record<string, string | number> = { scope: params.scope }
  if (params.time_range) query.time_range = params.time_range
  if (params.start_date) query.start_date = params.start_date
  if (params.end_date) query.end_date = params.end_date
  if (params.username) query.username = params.username
  if (params.module) query.module = params.module
  if (params.action) query.action = params.action
  if (params.keyword) query.keyword = params.keyword
  if (params.limit != null) query.limit = params.limit
  if (params.skip != null) query.skip = params.skip
  return request.get<OperationLogListResult>('/operation-logs', { params: query })
}

/** 操作人选项（用于下拉筛选） */
export interface OperationLogOperatorOption {
  username: string
  real_name: string | null
  display: string
}

/** 获取操作日志中已出现的操作人列表，按 scope 仅电气或仅机械 */
export function getOperationLogOperatorOptions(scope: MaterialScope) {
  return request.get<OperationLogOperatorOption[]>('/operation-logs/operator-options', { params: { scope } })
}

