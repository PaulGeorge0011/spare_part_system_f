import { shallowRef, onMounted, onUnmounted } from 'vue'

/** 移动端断点（小于此宽度视为移动端） */
export const MOBILE_BREAKPOINT = 768

/** 是否在 iframe 内（跨域时可能抛错，返回 false） */
function inIframe(): boolean {
  try {
    return typeof window !== 'undefined' && window.self !== window.top
  } catch {
    return true
  }
}

/** 根据 User-Agent 判断是否为移动设备（用于 iframe 内无法依赖视口宽度时） */
function isMobileUserAgent(): boolean {
  if (typeof navigator === 'undefined' || !navigator.userAgent) return false
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini|Mobile|mobile/i.test(navigator.userAgent)
}

function debounce(fn: () => void, delay: number) {
  let timer: ReturnType<typeof setTimeout> | null = null
  return () => {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      fn()
      timer = null
    }, delay)
  }
}

function computeIsMobile(): boolean {
  if (typeof window === 'undefined') return false
  const byViewport = window.innerWidth < MOBILE_BREAKPOINT
  if (inIframe()) {
    return byViewport || isMobileUserAgent()
  }
  return byViewport
}

export function useIsMobile() {
  const isMobile = shallowRef(typeof window !== 'undefined' ? computeIsMobile() : false)

  onMounted(() => {
    const update = () => {
      isMobile.value = computeIsMobile()
    }
    const handler = debounce(update, 150)
    update()
    window.addEventListener('resize', handler)
    onUnmounted(() => {
      window.removeEventListener('resize', handler)
    })
  })

  return { isMobile }
}
