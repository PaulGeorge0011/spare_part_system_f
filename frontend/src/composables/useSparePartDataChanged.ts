import { onMounted, onUnmounted } from 'vue'
import { getEffectiveApiBaseURL } from '@/utils/config'

const CHANNEL_NAME = 'spare-part-data-changed'
const STORAGE_KEY = 'spare-part-data-changed'
const DEBOUNCE_MS = 400
const WS_EVENT_TYPE = 'spare-part-changed'
const WS_RECONNECT_DELAY_MS = 5000
const WS_PING_INTERVAL_MS = 25000
const WS_MAX_RECONNECT_ATTEMPTS = 3

let channel: BroadcastChannel | null = null

function getChannel(): BroadcastChannel | null {
  if (typeof window === 'undefined') return null
  try {
    if (!channel) channel = new BroadcastChannel(CHANNEL_NAME)
    return channel
  } catch {
    return null
  }
}

function getSparePartEventsWsUrl(): string {
  const base = getEffectiveApiBaseURL()
  let href: string
  if (base.startsWith('http://') || base.startsWith('https://')) {
    href = base
  } else {
    const path = base.startsWith('/') ? base : `/${base}`
    href = `${window.location.origin}${path}`
  }
  const u = new URL(href)
  const wsProto = u.protocol === 'https:' ? 'wss:' : 'ws:'
  const path = u.pathname.replace(/\/$/, '') + '/ws/spare-part-events'
  return `${wsProto}//${u.host}${path}`
}

/**
 * 广播「修复件数据已变更」。
 * 在领用、修复件增/删/改成功后调用，同浏览器其他标签页/窗口会收到并刷新列表。
 * 跨浏览器、跨终端依赖服务端 WebSocket 推送，无需在此额外请求。
 * 同时写入 localStorage，供 storage 事件备用（部分环境 BC 不可用）。
 */
export function broadcastSparePartDataChanged(): void {
  const timestamp = Date.now()
  console.log('[广播] 发送修复件数据变更通知', { timestamp })
  try {
    const ch = getChannel()
    if (ch) {
      ch.postMessage({ type: CHANNEL_NAME, at: timestamp })
      console.log('[广播] BroadcastChannel 消息已发送')
    } else {
      console.warn('[广播] BroadcastChannel 不可用')
    }
  } catch (e) {
    console.error('[广播] BroadcastChannel 发送失败', e)
  }
  try {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, String(timestamp))
      console.log('[广播] localStorage 已更新')
    }
  } catch (e) {
    console.error('[广播] localStorage 更新失败', e)
  }
}

/**
 * 监听「修复件数据已变更」广播，收到时执行 refresh。
 * - 同浏览器多标签页：BroadcastChannel + localStorage storage。
 * - 跨浏览器、跨终端：WebSocket 服务端推送。
 * 支持 bfcache 恢复时刷新。
 */
export function useSparePartDataChanged(refresh: () => void | Promise<void>): void {
  let lastRun = 0
  let ws: WebSocket | null = null
  let wsPingTimer: ReturnType<typeof setInterval> | null = null
  let wsReconnectTimer: ReturnType<typeof setTimeout> | null = null
  let wsReconnectAttempts = 0
  let mounted = true

  function runRefresh() {
    const now = Date.now()
    if (now - lastRun < DEBOUNCE_MS) {
      console.log('[监听] 刷新被防抖跳过', { now, lastRun, diff: now - lastRun })
      return
    }
    lastRun = now
    console.log('[监听] 触发刷新', { now })
    void Promise.resolve(refresh()).catch((e) => {
      console.error('[监听] 刷新执行失败', e)
    })
  }

  function handleMessage(e: MessageEvent) {
    console.log('[监听] 收到 BroadcastChannel 消息', e?.data)
    if (e?.data?.type !== CHANNEL_NAME) return
    runRefresh()
  }

  function handleStorage(e: StorageEvent) {
    console.log('[监听] 收到 storage 事件', { key: e?.key, newValue: e?.newValue })
    if (e?.key !== STORAGE_KEY) return
    runRefresh()
  }

  function handlePageShow(e: PageTransitionEvent) {
    if (e.persisted) runRefresh()
  }

  function handleWsMessage(ev: MessageEvent) {
    try {
      const data = typeof ev.data === 'string' ? JSON.parse(ev.data) : ev.data
      if (data?.type === WS_EVENT_TYPE) {
        console.log('[监听] 收到 WebSocket 修复件变更推送', data)
        runRefresh()
      }
    } catch {
      // ignore
    }
  }

  function connectWs() {
    if (typeof window === 'undefined' || !mounted) return
    if (wsReconnectAttempts >= WS_MAX_RECONNECT_ATTEMPTS) return
    const url = getSparePartEventsWsUrl()
    try {
      const s = new WebSocket(url)
      s.addEventListener('open', () => {
        wsReconnectAttempts = 0
        wsPingTimer = window.setInterval(() => {
          if (s.readyState === WebSocket.OPEN) s.send('ping')
        }, WS_PING_INTERVAL_MS)
      })
      s.addEventListener('message', handleWsMessage)
      s.addEventListener('close', () => {
        if (wsPingTimer) {
          clearInterval(wsPingTimer)
          wsPingTimer = null
        }
        ws = null
        if (!mounted) return
        wsReconnectAttempts += 1
        if (wsReconnectAttempts <= WS_MAX_RECONNECT_ATTEMPTS) {
          wsReconnectTimer = window.setTimeout(connectWs, WS_RECONNECT_DELAY_MS)
        }
      })
      s.addEventListener('error', () => {
        // 关闭时会触发 close，不在此重复打日志
      })
      ws = s
    } catch {
      wsReconnectAttempts += 1
      if (mounted && wsReconnectAttempts <= WS_MAX_RECONNECT_ATTEMPTS) {
        wsReconnectTimer = window.setTimeout(connectWs, WS_RECONNECT_DELAY_MS)
      }
    }
  }

  function disconnectWs() {
    mounted = false
    if (wsReconnectTimer) {
      clearTimeout(wsReconnectTimer)
      wsReconnectTimer = null
    }
    if (wsPingTimer) {
      clearInterval(wsPingTimer)
      wsPingTimer = null
    }
    if (ws) {
      try {
        ws.close(1000, 'Component unmount')
      } catch {
        // ignore
      }
      ws = null
    }
    wsReconnectAttempts = WS_MAX_RECONNECT_ATTEMPTS
  }

  onMounted(() => {
    if (typeof window === 'undefined') return
    mounted = true
    wsReconnectAttempts = 0
    const ch = getChannel()
    if (ch) {
      ch.addEventListener('message', handleMessage)
      console.log('[监听] BroadcastChannel 监听器已注册')
    } else {
      console.warn('[监听] BroadcastChannel 不可用，仅使用 localStorage')
    }
    window.addEventListener('storage', handleStorage)
    window.addEventListener('pageshow', handlePageShow)
    connectWs()
  })

  onUnmounted(() => {
    if (typeof window === 'undefined') return
    disconnectWs()
    const ch = getChannel()
    if (ch) ch.removeEventListener('message', handleMessage)
    window.removeEventListener('storage', handleStorage)
    window.removeEventListener('pageshow', handlePageShow)
  })
}
