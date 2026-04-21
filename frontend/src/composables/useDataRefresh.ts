import { onMounted, onUnmounted, onActivated, onDeactivated, ref } from 'vue'
import { navLog, navLogStart } from '@/utils/navLog'

const DEFAULT_POLL_INTERVAL_MS = 30_000
const DEFAULT_STALE_TIME_MS = 60_000

/**
 * 当后端数据可能发生变化时自动刷新列表。
 * 刷新节点：
 * - 轮询（仅在前台）
 * - 标签页重新可见时
 * - keep-alive 缓存激活时（如果数据过期）
 *
 * @param refresh 执行刷新的函数（如 loadData）
 * @param options.pollIntervalMs 轮询间隔毫秒数，默认 30s；0 表示不轮询
 * @param options.staleTimeMs 数据过期时间毫秒数，默认 60s；从缓存激活时超过此时间会刷新
 */
export function useDataRefresh(
  refresh: () => void | Promise<void>,
  options: { pollIntervalMs?: number; staleTimeMs?: number } = {}
) {
  const pollIntervalMs = options.pollIntervalMs ?? DEFAULT_POLL_INTERVAL_MS
  const staleTimeMs = options.staleTimeMs ?? DEFAULT_STALE_TIME_MS
  
  let timer: ReturnType<typeof setInterval> | null = null
  const lastRefreshTime = ref<number>(Date.now())
  const isActive = ref(true)

  function runRefresh() {
    const t = navLogStart()
    navLog('useDataRefresh runRefresh start', {})
    void Promise.resolve(refresh()).catch(() => {}).finally(() => {
      lastRefreshTime.value = Date.now()
      navLog('useDataRefresh runRefresh end', {}, t)
    })
  }

  function startPolling() {
    if (pollIntervalMs <= 0 || timer) return
    timer = setInterval(() => {
      if (typeof document !== 'undefined' && document.visibilityState === 'visible' && isActive.value) {
        runRefresh()
      }
    }, pollIntervalMs)
  }

  function stopPolling() {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  function onVisibilityChange() {
    if (document.visibilityState === 'visible' && isActive.value) {
      runRefresh()
      startPolling()
    } else {
      stopPolling()
    }
  }

  onMounted(() => {
    if (typeof document === 'undefined') return
    document.addEventListener('visibilitychange', onVisibilityChange)
    if (document.visibilityState === 'visible') {
      startPolling()
    }
    // 首次挂载时标记时间
    lastRefreshTime.value = Date.now()
  })

  // keep-alive 激活时：先让页面切过去，再在空闲时检查过期并刷新，避免切换卡顿
  function scheduleIdle(fn: () => void, timeoutMs = 150) {
    if (typeof requestIdleCallback !== 'undefined') {
      requestIdleCallback(fn, { timeout: timeoutMs })
    } else {
      setTimeout(fn, 0)
    }
  }

  onActivated(() => {
    isActive.value = true
    const isStale = Date.now() - lastRefreshTime.value > staleTimeMs
    if (isStale) {
      navLog('useDataRefresh onActivated stale, scheduleIdle refresh', { staleTimeMs })
      scheduleIdle(() => runRefresh())
    }
    if (typeof document !== 'undefined' && document.visibilityState === 'visible') {
      scheduleIdle(() => startPolling())
    }
  })

  // keep-alive 停用时：暂停轮询
  onDeactivated(() => {
    isActive.value = false
    stopPolling()
  })

  onUnmounted(() => {
    if (typeof document !== 'undefined') {
      document.removeEventListener('visibilitychange', onVisibilityChange)
    }
    stopPolling()
  })

  return { runRefresh, startPolling, stopPolling, lastRefreshTime }
}
