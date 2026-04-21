/**
 * 导出 Excel / CSV 工具
 * 使用 xlsx 库生成文件并触发浏览器下载
 */
import * as XLSX from 'xlsx'

/** iframe 移动端：由 main.ts 在 iframe+移动端时给 html 加的 class，用于仅在此环境下改用 blob+锚点下载，避免跳转系统浏览器 */
function isIframeMobileViewport(): boolean {
  return typeof document !== 'undefined' && document.documentElement.classList.contains('iframe-mobile-viewport')
}

export interface ExportColumn {
  /** 数据字段名 */
  key: string
  /** 表头显示名 */
  label: string
  /** 可选：自定义取值 */
  formatter?: (row: Record<string, unknown>) => string | number
}

/**
 * 将数据按列配置转为二维数组 [表头行, ...数据行]
 */
function toSheetData<T extends Record<string, unknown>>(
  rows: T[],
  columns: ExportColumn[]
): (string | number)[][] {
  const header = columns.map((c) => c.label)
  const data = rows.map((row) =>
    columns.map((col) => {
      if (col.formatter) {
        return col.formatter(row as Record<string, unknown>)
      }
      const v = row[col.key]
      if (v === null || v === undefined) return ''
      return v as string | number
    })
  )
  return [header, ...data]
}

/**
 * 导出为 Excel (.xlsx)
 * @param rows 数据行
 * @param columns 列配置
 * @param filename 文件名（不含扩展名则自动加 .xlsx）
 */
export function exportToExcel<T extends Record<string, unknown>>(
  rows: T[],
  columns: ExportColumn[],
  filename: string
): void {
  const sheetData = toSheetData(rows, columns)
  const ws = XLSX.utils.aoa_to_sheet(sheetData)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, 'Sheet1')
  const name = filename.endsWith('.xlsx') ? filename : `${filename}.xlsx`

  if (isIframeMobileViewport()) {
    const array = XLSX.write(wb, { bookType: 'xlsx', type: 'array' }) as Uint8Array
    const a = document.createElement('a')
    a.download = name
    a.rel = 'noopener'
    a.style.cssText = 'position:fixed;left:-9999px;opacity:0;pointer-events:none'
    document.body.appendChild(a)

    const maxDataUrlBytes = 1.2e6
    if (array.byteLength <= maxDataUrlBytes) {
      const base64 = XLSX.write(wb, { bookType: 'xlsx', type: 'base64' })
      a.href = `data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,${base64}`
    } else {
      const blob = new Blob([array.slice(0)], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      })
      const url = URL.createObjectURL(blob)
      a.href = url
      setTimeout(() => URL.revokeObjectURL(url), 10000)
    }
    a.click()
    setTimeout(() => document.body.removeChild(a), 500)
  } else {
    XLSX.writeFile(wb, name)
  }
}

/**
 * 导出为 CSV
 * @param rows 数据行
 * @param columns 列配置
 * @param filename 文件名（不含扩展名则自动加 .csv）
 */
export function exportToCSV<T extends Record<string, unknown>>(
  rows: T[],
  columns: ExportColumn[],
  filename: string
): void {
  const sheetData = toSheetData(rows, columns)
  const ws = XLSX.utils.aoa_to_sheet(sheetData)
  const csv = '\uFEFF' + XLSX.utils.sheet_to_csv(ws)
  const name = filename.endsWith('.csv') ? filename : `${filename}.csv`

  if (isIframeMobileViewport()) {
    const a = document.createElement('a')
    a.download = name
    a.rel = 'noopener'
    a.style.cssText = 'position:fixed;left:-9999px;opacity:0;pointer-events:none'
    a.href = 'data:text/csv;charset=utf-8,' + encodeURIComponent(csv)
    document.body.appendChild(a)
    a.click()
    setTimeout(() => document.body.removeChild(a), 500)
  } else {
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = name
    a.click()
    URL.revokeObjectURL(url)
  }
}
