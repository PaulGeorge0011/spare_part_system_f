import { onMounted, onUnmounted } from 'vue'
import { getEffectiveApiBaseURL } from '@/utils/config'

const CHANNEL_NAME = 'mechanical-spare-part-data-changed'
const STORAGE_KEY = 'mechanical-spare-part-data-changed'
const DEBOUNCE_MS = 400
const WS_EVENT_TYPE = 'mechanical-spare-part-changed'
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

function getMechanicalSparePartEventsWsUrl(): string {
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
  const path = u.pathname.replace(/\/$/, '') + '/ws/mechanical-spare-part-events'
  return `${wsProto}//${u.host}${path}`
}

/**
 * 广播「机械修复件数据已变更」。
 * 在领用、机械修复件增/删/改成功后调用，同浏览器其他标签页/窗口会收到并刷新列表。
 */
export function broadcastMechanicalSparePartDataChanged(): void {
  const timestamp = Date.now()
  try {
    const ch = getChannel()
    if (ch) {
      ch.postMessage({ type: CHANNEL_NAME, at: timestamp })
    }
  } catch (e) {
    console.error('[机械广播] BroadcastChannel 发送失败', e)
  }
  try {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(STORAGE_KEY, String(timestamp))
    }
  } catch (e) {
    console.error('[机械广播] localStorage 更新失败', e)
  }
}

/**
 * 监听「机械修复件数据已变更」广播，收到时执行 refresh。
 * 同电气：同浏览器多标签页 BroadcastChannel + localStorage；跨终端可选 WebSocket。
 */
export function useMechanicalSparePartDataChanged(refresh: () => void | Promise<void>): void {
  let lastRun = 0
  let ws: WebSocket | null = null
  let wsPingTimer: ReturnType<typeof setInterval> | null = null
  let wsReconnectTimer: ReturnType<typeof setTimeout> | null = null
  let wsReconnectAttempts = 0
  let mounted = true

  function runRefresh() {
    const now = Date.now()
    if (now - lastRun < DEBOUNCE_MS) return
    lastRun = now
    void Promise.resolve(refresh()).catch((e) => {
      console.error('[机械监听] 刷新执行失败', e)
    })
  }

  function handleMessage(e: MessageEvent) {
    if (e?.data?.type !== CHANNEL_NAME) return
    runRefresh()
  }

  function handleStorage(e: StorageEvent) {
    if (e?.key !== STORAGE_KEY) return
    runRefresh()
  }

  function handlePageShow(e: PageTransitionEvent) {
    if (e.persisted) runRefresh()
  }

  function handleWsMessage(ev: MessageEvent) {
    try {
      const data = typeof ev.data === 'string' ? JSON.parse(ev.data) : ev.data
      if (data?.type === WS_EVENT_TYPE) runRefresh()
    } catch {
      // ignore
    }
  }

  function connectWs() {
    if (typeof window === 'undefined' || !mounted) return
    if (wsReconnectAttempts >= WS_MAX_RECONNECT_ATTEMPTS) return
    const url = getMechanicalSparePartEventsWsUrl()
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
      s.addEventListener('error', () => {})
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
    }
    window.addEventListener('storage', handleStorage)
    window.addEventListener('pageshow', handlePageShow)
    // 启用 WebSocket 连接，实现跨浏览器、跨终端数据同步
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
