/**
 * 机械修复件类型：与电气修复件字段一致，另增图号、保管人、来源说明、技术鉴定、处置方式。
 */
export interface MechanicalSparePart {
  id: number
  location_code: string
  mes_material_code?: string | null
  mes_material_desc?: string | null
  physical_material_desc?: string | null
  specification_model?: string | null
  applicable_model?: string | null
  brand?: string | null
  mes_stock?: number
  physical_stock?: number
  unit?: string | null
  storage_location?: string | null
  physical_image_url?: string | null
  physical_image_url2?: string | null
  remarks?: string | null
  drawing_no?: string | null
  custodian?: string | null
  source_description?: string | null
  technical_appraisal?: string | null
  disposal_method?: string | null
  created_at?: string
  updated_at?: string | null
  is_active?: boolean
}

export interface MechanicalSparePartCreate {
  location_code: string
  mes_material_code?: string
  mes_material_desc?: string
  physical_material_desc?: string
  specification_model?: string
  applicable_model?: string
  brand?: string
  mes_stock?: number
  physical_stock?: number
  unit?: string
  storage_location?: string
  physical_image_url?: string
  physical_image_url2?: string
  remarks?: string
  drawing_no?: string
  custodian?: string
  source_description?: string
  technical_appraisal?: string
  disposal_method?: string
  image_upload_ids?: string[]
}

export interface MechanicalSparePartUpdate {
  location_code?: string
  mes_material_code?: string
  mes_material_desc?: string
  physical_material_desc?: string
  specification_model?: string
  applicable_model?: string
  brand?: string
  mes_stock?: number
  physical_stock?: number
  unit?: string
  storage_location?: string
  physical_image_url?: string
  physical_image_url2?: string
  remarks?: string
  drawing_no?: string
  custodian?: string
  source_description?: string
  technical_appraisal?: string
  disposal_method?: string
  image_upload_ids?: string[]
  image_ids_to_delete?: number[]
}

export interface MechanicalSparePartQueryParams {
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

export interface MechanicalSparePartFilterOptions {
  brands: string[]
  applicable_models: string[]
  storage_locations: string[]
  specification_models?: string[]
  location_prefixes: string[]
}
