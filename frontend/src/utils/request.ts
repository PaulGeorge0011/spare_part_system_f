// frontend/src/utils/request.ts
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { config as appConfig, getEffectiveApiBaseURL } from '@/utils/config'

const apiBaseURL = appConfig.api.baseURL
const request = axios.create({
  baseURL: apiBaseURL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

function genRequestId(): string {
  // 优先使用浏览器原生 UUID
  const c: any = typeof crypto !== 'undefined' ? crypto : undefined
  if (c?.randomUUID) return c.randomUUID()
  // fallback：时间戳 + 随机
  return `req_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`
}

// 请求拦截器
request.interceptors.request.use(
  (config) => {
    // 二级目录下使用运行时 API 前缀，保证上传/删除等请求走代理
    if (typeof window !== 'undefined') {
      config.baseURL = getEffectiveApiBaseURL()
    }
    // 对于 FormData 请求，让浏览器自动设置 Content-Type
    if (config.data instanceof FormData) {
      ;(config.headers as any)?.['Content-Type'] && delete (config.headers as any)['Content-Type']
    }
    
    // 可以在这里添加token等
    const token = localStorage.getItem('access_token')
    if (token) {
      ;(config.headers as any) = (config.headers as any) ?? {}
      ;(config.headers as any).Authorization = `Bearer ${token}`
    }

    // 给每次请求附带 requestId，便于后端日志定位（不影响后端逻辑）
    const requestId = genRequestId()
    ;(config.headers as any) = (config.headers as any) ?? {}
    ;(config.headers as any)['X-Request-Id'] = requestId
    ;(config as any).__requestId = requestId
    
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  (response) => {
    // 对于 FormData 请求，响应可能是字符串，需要手动解析
    if (response.config.data instanceof FormData) {
      // 检查响应是否是字符串
      if (typeof response.data === 'string') {
        try {
          // 尝试解析为 JSON
          return JSON.parse(response.data)
        } catch (e) {
          console.error('解析 FormData 响应失败:', e)
          // 返回原始字符串
          return response.data
        }
      }
    }
    return response.data
  },
  async (error) => {
    const isWechatOptional = error.config?.url?.includes?.('/wechat/')
    const isSsoOptional = error.config?.url?.includes?.('/auth/sso-')
    if (!isWechatOptional && !isSsoOptional) {
      console.error('API请求错误:', error)
    }

    if (error.response) {
      const status = error.response.status
      const data = error.response.data
      const isLoginRequest = error.config?.url?.includes?.('/auth/login')
      const requestId = error.config?.__requestId

      let message = '请求失败'
      if (data && data.detail) {
        message = data.detail
      } else if (data && data.message) {
        message = data.message
      } else if (typeof data === 'string') {
        message = data
      }

      if (!isLoginRequest && !isWechatOptional && !isSsoOptional) {
        const suffix = requestId ? ` | 请求ID: ${requestId}` : ''
        ElMessage.error(`${message} (${status})${suffix}`)
      }

      if (status === 401 && !isLoginRequest) {
        if (!isWechatOptional && !isSsoOptional) {
          try {
            const { useAuthStore } = await import('@/stores/auth')
            useAuthStore().clearAuth()
          } catch {}
          const loginPath = (appConfig.baseURL.replace(/\/+$/, '') || '') + '/login'
          if (!window.location.pathname.startsWith(loginPath) && !window.location.pathname.endsWith('/login')) {
            window.location.href = loginPath
          }
        }
      }
    } else if (error.request) {
      ElMessage.error('网络错误，请检查网络连接')
    } else {
      ElMessage.error('请求配置错误')
    }

    return Promise.reject(error)
  }
)


// 创建专门用于上传的实例（不设置baseURL）
const uploadRequest = axios.create({
  timeout: 60000, // 上传需要更长时间
  headers: {
    'Content-Type': 'multipart/form-data'
  }
})

// 配置请求拦截器
uploadRequest.interceptors.request.use(
  (config) => {
    // 对于上传请求，使用与 config 一致的 base；二级目录下用运行时 API 前缀
    if (!config.url?.startsWith('http')) {
      config.baseURL = typeof window !== 'undefined' ? getEffectiveApiBaseURL() : apiBaseURL
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

export { request, uploadRequest }

export default request




