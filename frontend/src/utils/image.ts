import { smartConvertMinioUrl } from './config'

/**
 * 图片展示用 URL 处理（完整 URL 经 MinIO 转换后返回，相对路径等按 baseURL 拼接）
 * 移动端需将 localhost:9000 转为当前主机 IP，否则无法访问
 */
export function getImageUrlForDisplay(url: string): string {
  if (!url) return ''
  // 完整 URL 或相对路径 /minio/、/zs2sbgl/minio/ 都走 MinIO 转换（工厂二级目录下会改为当前 origin + /zs2sbgl/minio/）
  if (
    url.startsWith('http://') ||
    url.startsWith('https://') ||
    url.startsWith('/minio/') ||
    url.startsWith('/zs2sbgl/minio/')
  ) {
    return smartConvertMinioUrl(url)
  }
  const baseUrl = import.meta.env.VITE_API_BASE_URL || window.location.origin
  if (url.startsWith('/api/v1/')) {
    const path = url.substring(7).replace(/^\//, '')
    const base = baseUrl.replace(/\/$/, '')
    return `${base}/${path}`
  }
  return url
}
