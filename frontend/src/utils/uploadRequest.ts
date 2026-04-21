// frontend/src/utils/uploadRequest.ts
import axios from 'axios'
import { config, getEffectiveApiBaseURL } from '@/utils/config'

// 与 request 一致，请求时使用 getEffectiveApiBaseURL()，二级目录下为 /zs2sbgl/api/v1
const uploadRequest = axios.create({
  baseURL: config.api.baseURL,
  timeout: 30000, // 上传需要更长时间
})

// 请求拦截器
uploadRequest.interceptors.request.use(
  (config) => {
    if (typeof window !== 'undefined') {
      config.baseURL = getEffectiveApiBaseURL()
    }
    // 对于 FormData，不设置 Content-Type，让浏览器自动设置
    if (config.data instanceof FormData) {
      delete config.headers['Content-Type']
    }
    
    // 添加认证 token
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器 - 直接返回完整的响应
uploadRequest.interceptors.response.use(
  (response) => {
    // 直接返回完整响应，让调用方处理
    return response
  },
  (error) => {
    console.error('上传请求错误:', error)
    
    if (error.response) {
      const status = error.response.status
      const data = error.response.data
      
      let message = '上传失败'
      if (data && data.detail) {
        message = data.detail
      } else if (data && data.message) {
        message = data.message
      } else if (typeof data === 'string') {
        message = data
      }
      
      throw new Error(`${message} (${status})`)
    } else if (error.request) {
      throw new Error('网络错误，请检查网络连接')
    } else {
      throw error
    }
  }
)

export default uploadRequest