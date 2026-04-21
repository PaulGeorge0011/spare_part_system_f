// 部署基础路径（白码同域时为 /spare/，独立部署为 /）；保证末尾有且仅有一个 /
const rawBase = (import.meta.env.BASE_URL || '/').replace(/\/+$/, '')
const BASE_URL = rawBase ? rawBase + '/' : '/'

// 环境配置
export const config = {
  // 是否是开发环境
  isDev: import.meta.env.DEV,

  // 部署基础路径（用于 API、MinIO 等同域前缀）
  baseURL: BASE_URL,

  // MinIO配置
  minio: {
    // 开发环境下的URL转换
    endpoint: import.meta.env.VITE_MINIO_ENDPOINT || 'localhost:9000',
    internalEndpoint: 'minio:9000',

    // 是否需要URL转换
    needsUrlConversion: import.meta.env.DEV
  },

  // API配置（同域部署时自动带 base，如 /spare/api/v1）
  api: {
    baseURL: import.meta.env.VITE_API_BASE_URL || `${BASE_URL}api/v1`
  }
}

/** 工厂新媒体二级目录（API/WebSocket 路径需带此前缀，否则代理 404） */
const ZS2SBGL_API_PREFIX = '/zs2sbgl/api/v1'

/**
 * 当前页面对应的 API base（运行时判断）
 * 若从 /zs2sbgl 进入且 config.api.baseURL 未带 /zs2sbgl，则返回 /zs2sbgl/api/v1，保证 WebSocket 等请求走代理
 */
export function getEffectiveApiBaseURL(): string {
  if (typeof window === 'undefined') return config.api.baseURL
  if (window.location.pathname.startsWith('/zs2sbgl') && !config.api.baseURL.includes('/zs2sbgl')) {
    return ZS2SBGL_API_PREFIX
  }
  return config.api.baseURL
}

/** 工厂新媒体二级目录，与 nginx 的 location /zs2sbgl/minio/ 一致 */
const ZS2SBGL_MINIO_PREFIX = '/zs2sbgl/minio/'

/**
 * 获取当前环境下 MinIO 代理路径前缀（运行时判断，不依赖构建时 base）
 * 若当前页面在 /zs2sbgl 下，必须用 /zs2sbgl/minio/，否则工厂代理会 403
 */
function getEffectiveMinioPrefix(): string {
  if (typeof window === 'undefined') return `${config.baseURL}minio/`
  const pathname = window.location.pathname
  if (pathname.startsWith('/zs2sbgl')) return ZS2SBGL_MINIO_PREFIX
  return `${config.baseURL}minio/`
}

/**
 * 获取 MinIO 代理的完整基础 URL（origin + 路径前缀）
 */
function getMinioProxyBase(): string {
  const prefix = getEffectiveMinioPrefix()
  if (typeof window === 'undefined') return prefix
  return `${window.location.origin}${prefix.replace(/\/+$/, '')}/`
}

/**
 * 智能URL转换
 * 将所有 MinIO 直连 URL（minio:9000 / localhost:9000 / 127.0.0.1:9000 / IP:9000）
 * 统一转换为通过 Nginx /minio/ 代理的路径，避免客户端直连 9000 端口
 * 
 * 例如：
 *   http://localhost:9000/spareparts/xxx.png -> http://host:8080/minio/spareparts/xxx.png
 *   http://minio:9000/spareparts/xxx.png    -> http://host:8080/minio/spareparts/xxx.png
 *   /minio/spareparts/xxx.png               -> http://host:8080/minio/spareparts/xxx.png
 */
export function smartConvertMinioUrl(url: string): string {
  if (!url) return ''

  const proxyBase = getMinioProxyBase()
  const minioPrefix = getEffectiveMinioPrefix() // 如 /zs2sbgl/minio/ 或 /minio/

  // 相对路径 /zs2sbgl/minio/...：补全为当前 origin，确保工厂代理下图片可访问
  if (url.startsWith('/zs2sbgl/minio/')) {
    if (typeof window !== 'undefined') {
      return `${window.location.origin}${url}`
    }
    return url
  }

  // 相对路径 /minio/...：补全为 origin + 当前有效的 minio 前缀（运行时判断是否在 /zs2sbgl 下）
  if (url.startsWith('/minio/')) {
    return `${proxyBase}${url.substring(7)}`
  }

  // 完整 URL：路径为 /zs2sbgl/minio/ 或 /minio/ 时，统一为当前 origin + 路径，避免内网 host 导致前端无法访问
  if (url.startsWith('http://') || url.startsWith('https://')) {
    try {
      const u = new URL(url)
      const path = u.pathname
      if (path.startsWith('/zs2sbgl/minio/')) {
        if (typeof window !== 'undefined') {
          return `${window.location.origin}${path}`
        }
        return url
      }
      if (path.startsWith('/minio/')) {
        const suffix = path.substring(6) // 去掉 '/minio/'
        const newPath = `${minioPrefix.replace(/\/+$/, '')}/${suffix}`
        if (typeof window !== 'undefined') {
          return `${window.location.origin}${newPath}`
        }
        u.pathname = newPath
        return u.toString()
      }
    } catch {
      // 解析失败则 fallback 到 proxyBase 拼接
    }
  }

  // 直连 MinIO 的 URL：http(s)://host:9000/路径
  const minioDirectPattern = /^https?:\/\/[^/]+:9000\/(.+)$/
  const match = url.match(minioDirectPattern)
  if (match) {
    return `${proxyBase}${match[1]}`
  }

  // Docker 内网 minio:9000
  if (typeof window !== 'undefined' && url.includes('minio:9000')) {
    const pathPart = minioPrefix.replace(/\/+$/, '')
    return url.replace(/minio:9000[^/]*/, `${window.location.host}${pathPart}`)
  }

  return url
}