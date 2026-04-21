import { ref, onMounted, onActivated } from 'vue'

/**
 * 页面缓存优化 composable
 * 用于 keep-alive 缓存的页面，智能处理数据刷新：
 * - 首次加载时获取数据
 * - 从缓存激活时，根据时间间隔决定是否刷新
 * - 支持强制刷新
 */
export function usePageCache(
  loadData: () => void | Promise<void>,
  options: {
    /** 数据过期时间（毫秒），超过此时间从缓存激活时会自动刷新，默认 30 秒 */
    staleTime?: number
    /** 是否在激活时总是刷新，默认 false */
    alwaysRefreshOnActivate?: boolean
  } = {}
) {
  const { staleTime = 30_000, alwaysRefreshOnActivate = false } = options
  
  // 上次数据加载时间
  const lastLoadTime = ref<number>(0)
  // 是否正在加载
  const isLoading = ref(false)
  // 是否已完成首次加载
  const hasLoaded = ref(false)
  
  async function doLoad() {
    if (isLoading.value) return
    isLoading.value = true
    try {
      await Promise.resolve(loadData())
      lastLoadTime.value = Date.now()
      hasLoaded.value = true
    } finally {
      isLoading.value = false
    }
  }
  
  // 检查数据是否过期
  function isStale(): boolean {
    if (!hasLoaded.value) return true
    return Date.now() - lastLoadTime.value > staleTime
  }
  
  // 强制刷新
  function refresh() {
    return doLoad()
  }
  
  // 首次挂载时加载数据
  onMounted(() => {
    if (!hasLoaded.value) {
      doLoad()
    }
  })
  
  // 从缓存激活时，按需刷新
  onActivated(() => {
    if (alwaysRefreshOnActivate || isStale()) {
      doLoad()
    }
  })
  
  return {
    isLoading,
    hasLoaded,
    lastLoadTime,
    isStale,
    refresh
  }
}

/**
 * 简化版：仅在激活时检查是否需要刷新
 * 适用于已有 onMounted 加载逻辑的页面
 */
export function useActivateRefresh(
  loadData: () => void | Promise<void>,
  options: {
    /** 数据过期时间（毫秒），默认 60 秒 */
    staleTime?: number
  } = {}
) {
  const { staleTime = 60_000 } = options
  const lastLoadTime = ref<number>(Date.now())
  
  // 标记数据已加载（在 loadData 调用后手动调用）
  function markLoaded() {
    lastLoadTime.value = Date.now()
  }
  
  // 从缓存激活时，如果数据过期则刷新
  onActivated(() => {
    const isStale = Date.now() - lastLoadTime.value > staleTime
    if (isStale) {
      Promise.resolve(loadData()).then(markLoaded).catch(() => {})
    }
  })
  
  return { markLoaded, lastLoadTime }
}
