import { defineStore } from 'pinia'
import { sparePartApi, type SparePartQueryParams } from '@/api/sparePart'
import type {
  SparePart,
  SparePartCreate,
  SparePartUpdate,
} from '@/types/sparePart'

interface SparePartState {
  list: SparePart[]
  current: SparePart | null
  loading: boolean
  loadingMore: boolean
  total: number
  queryParams: SparePartQueryParams
  error: string | null
  /** 当前筛选条件下的零库存条数（总库存=0） */
  zeroCount: number
  /** 当前筛选条件下的低库存条数（总库存=1） */
  lowCount: number
}

export const useSparePartStore = defineStore('sparePart', {
  state: (): SparePartState => ({
    list: [],
    current: null,
    loading: false,
    loadingMore: false,
    total: 0,
    queryParams: {
      skip: 0,
      limit: 20,
      keyword: '',
    },
    error: null,
    zeroCount: 0,
    lowCount: 0,
  }),


  

  getters: {
    /**
     * 获取库存紧张的修复件（实物库存低于MES库存的80%）
     */
    lowStockItems: (state) => {
      return state.list.filter(
        (item) => item.physical_stock < item.mes_stock * 0.8
      )
    },

    /**
     * 按货位号分组
     */
    groupedByLocation: (state) => {
      const groups: Record<string, SparePart[]> = {}
      state.list.forEach((item) => {
        const location = item.location_code.split('-')[0] // 按区域分组，如A区
        if (!groups[location]) {
          groups[location] = []
        }
        groups[location].push(item)
      })
      return groups
    },

    /**
     * 是否有数据
     */
    hasData: (state) => state.list.length > 0,
  },

  actions: {
    /**
     * 获取修复件列表
     * @param params 查询参数
     * @param append 为 true 时追加到现有列表（用于移动端下拉加载更多）
     */
    async fetchList(params?: Partial<SparePartQueryParams>, append = false) {
      if (append) {
        this.loadingMore = true
      } else {
        this.loading = true
      }
      this.error = null

      try {
        const baseParams = append
          ? { ...this.queryParams, ...params, skip: this.list.length, _t: Date.now() }
          : { ...this.queryParams, ...params, _t: Date.now() }
        const query = { ...baseParams }
        const response = await sparePartApi.getList(query)

        const newList = Array.isArray(response?.items) ? response.items : []
        const totalCount = typeof response?.total === 'number' ? response.total : newList.length
        if (typeof (response as any)?.zero_count === 'number') this.zeroCount = (response as any).zero_count
        if (typeof (response as any)?.low_count === 'number') this.lowCount = (response as any).low_count

        if (append && newList.length > 0) {
          const ids = new Set(this.list.map((i) => i.id))
          const toAdd = newList.filter((i) => !ids.has(i.id))
          this.list = [...this.list, ...toAdd]
        } else {
          this.list = newList
        }
        this.total = totalCount

        if (params && !append) {
          this.queryParams = { ...this.queryParams, ...params }
        }

        return this.list
      } catch (error: any) {
        this.error = error.message || '获取修复件列表失败'
        console.error('获取修复件列表失败:', error)
        throw error
      } finally {
        if (append) {
          this.loadingMore = false
        } else {
          this.loading = false
        }
      }
    },

    /**
     * 获取单个修复件详情
     */
    async fetchDetail(id: number) {
      this.loading = true
      this.error = null
      
      try {
        const response = await sparePartApi.getDetail(id)
        this.current = response
        return this.current
      } catch (error: any) {
        this.error = error.message || '获取修复件详情失败'
        console.error('获取修复件详情失败:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * 创建新修复件
     */
    async createSparePart(data: SparePartCreate) {
      this.loading = true
      this.error = null
      
      try {
        const response = await sparePartApi.create(data)
        
        // 添加到列表开头
        this.list.unshift(response)
        this.total += 1
        
        return response
      } catch (error: any) {
        this.error = error.message || '创建修复件失败'
        console.error('创建修复件失败:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * 更新修复件
     */
    async updateSparePart(id: number, data: SparePartUpdate) {
      this.loading = true
      this.error = null
      
      try {
        const response = await sparePartApi.update(id, data)
        
        // 更新列表中的对应项
        const index = this.list.findIndex((item) => item.id === id)
        if (index !== -1) {
          this.list[index] = { ...this.list[index], ...response }
        }
        
        // 如果当前正在编辑此项，也更新
        if (this.current?.id === id) {
          this.current = { ...this.current, ...response }
        }
        
        return response
      } catch (error: any) {
        this.error = error.message || '更新修复件失败'
        console.error('更新修复件失败:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * 删除修复件
     */
    async deleteSparePart(id: number) {
      this.loading = true
      this.error = null
      
      try {
        await sparePartApi.delete(id)
        
        // 从列表中移除
        this.list = this.list.filter((item) => item.id !== id)
        this.total -= 1
        
        // 如果删除的是当前选中的，清空当前
        if (this.current?.id === id) {
          this.current = null
        }
        
        return true
      } catch (error: any) {
        this.error = error.message || '删除修复件失败'
        console.error('删除修复件失败:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * 批量删除修复件
     * @returns 接口返回的 { deleted, failed, errors }
     */
    async batchDeleteSpareParts(ids: number[]) {
      this.loading = true
      this.error = null
      try {
        const res = await sparePartApi.batchDelete(ids)
        return res as { deleted: number; failed: number; errors?: Array<{ id: number; message: string }> }
      } catch (error: any) {
        this.error = error.message || '批量删除修复件失败'
        console.error('批量删除修复件失败:', error)
        throw error
      } finally {
        this.loading = false
      }
    },

    /**
     * 清空当前选中的修复件
     */
    clearCurrent() {
      this.current = null
    },

    /**
     * 清空错误信息
     */
    clearError() {
      this.error = null
    },

    /**
     * 重置查询参数
     */
    resetQueryParams() {
      this.queryParams = {
        skip: 0,
        limit: 20,
        keyword: '',
      }
    },
  },
})

