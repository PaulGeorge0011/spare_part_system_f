// src/utils/date.ts
/**
 * 日期时间格式化工具
 * 所有展示时间统一使用北京时间（Asia/Shanghai, UTC+8）
 */

const BEIJING_TZ = 'Asia/Shanghai'

const dtf = new Intl.DateTimeFormat('en-CA', {
  timeZone: BEIJING_TZ,
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
})

function getBeijingParts(d: Date): Record<string, string> {
  const parts = dtf.formatToParts(d)
  const map: Record<string, string> = {}
  for (const p of parts) {
    if (p.type !== 'literal') map[p.type] = p.value
  }
  return map
}

/**
 * 将 API 返回的日期字符串解析为 Date（无 Z 时按 UTC 处理，避免比北京时间晚 8 小时）
 */
function parseApiDate(date: string | Date): Date {
  if (date instanceof Date) return date
  const s = String(date).trim()
  if (!s) return new Date(NaN)
  // 后端返回带 Z 或 +00:00 的 UTC 时间；无时区时按 UTC 解析，再在前端按北京时间展示
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(s) && !/Z|[+-]\d{2}:?\d{2}$/.test(s)) {
    return new Date(s + 'Z')
  }
  return new Date(s)
}

/**
 * 格式化日期时间（北京时间）
 * @param date 日期字符串或 Date 对象（API 返回的 ISO 时间会按 UTC 解析后以北京时间展示）
 * @param format 格式，默认：YYYY-MM-DD HH:mm:ss
 */
export const formatDateTime = (
  date: string | Date | null | undefined,
  format: string = 'YYYY-MM-DD HH:mm:ss'
): string => {
  if (date == null) return ''

  const d = typeof date === 'string' ? parseApiDate(date) : date
  if (!(d instanceof Date) || isNaN(d.getTime())) return ''

  const p = getBeijingParts(d)
  const year = p.year ?? ''
  const month = (p.month ?? '').padStart(2, '0')
  const day = (p.day ?? '').padStart(2, '0')
  const hours = (p.hour ?? '').padStart(2, '0')
  const minutes = (p.minute ?? '').padStart(2, '0')
  const seconds = (p.second ?? '').padStart(2, '0')

  return format
    .replace('YYYY', year)
    .replace('MM', month)
    .replace('DD', day)
    .replace('HH', hours)
    .replace('mm', minutes)
    .replace('ss', seconds)
}

/**
 * 格式化日期（不带时间，北京时间）
 */
export const formatDate = (date: string | Date | null | undefined): string => {
  return formatDateTime(date, 'YYYY-MM-DD')
}

/**
 * 相对时间显示（比较为 UTC 时刻，落款日期用北京时间）
 */
export const formatRelativeTime = (date: string | Date | null | undefined): string => {
  if (date == null) return ''

  const d = typeof date === 'string' ? parseApiDate(date) : date
  if (!(d instanceof Date) || isNaN(d.getTime())) return ''

  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMins = Math.floor(diffMs / (1000 * 60))
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffMins < 1) return '刚刚'
  if (diffMins < 60) return `${diffMins}分钟前`
  if (diffHours < 24) return `${diffHours}小时前`
  if (diffDays < 7) return `${diffDays}天前`

  return formatDate(d)
}