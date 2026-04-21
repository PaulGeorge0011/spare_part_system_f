/**
 * 从 .xlsx 中提取嵌入图片，按行+列索引关联。
 * 支持 Excel 浮动图片（drawing）与 WPS 嵌入单元格图片（DISPIMG 公式）。
 */

import JSZip from 'jszip'

const LOG_PREFIX = '[Excel图片]'
function log(step: string, detail?: unknown) {
  if (detail !== undefined) console.log(LOG_PREFIX, step, detail)
  else console.log(LOG_PREFIX, step)
}

export interface EmbeddedImage {
  blob: Blob
  col: number
  row: number
}

function parseRelsXml(xmlText: string): Map<string, string> {
  const map = new Map<string, string>()
  const parser = new DOMParser()
  const doc = parser.parseFromString(xmlText, 'text/xml')
  const relationships = doc.getElementsByTagName('Relationship')
  for (let i = 0; i < relationships.length; i++) {
    const r = relationships.item(i)
    if (!r) continue
    const id = r.getAttribute('Id') ?? r.getAttribute('id')
    const target = r.getAttribute('Target')
    if (id && target) map.set(id, target)
  }
  return map
}

/** 最大解析锚点数量，防止超大 drawing XML 导致卡死 */
const MAX_DRAWING_ANCHORS = 10000

/** 从 drawing XML 按顺序逐块提取 row, col, rId（避免整表大正则回溯导致卡死） */
function parseDrawingAnchors(xmlText: string): Array<{ row: number; col: number; rId: string }> {
  log('parseDrawingAnchors 开始', { xmlLen: xmlText.length })
  const out: Array<{ row: number; col: number; rId: string }> = []
  const oneTag = '<xdr:oneCellAnchor'
  const oneClose = '</xdr:oneCellAnchor>'
  const twoTag = '<xdr:twoCellAnchor'
  const twoClose = '</xdr:twoCellAnchor>'
  let pos = 0
  while (out.length < MAX_DRAWING_ANCHORS) {
    const iOne = xmlText.indexOf(oneTag, pos)
    const iTwo = xmlText.indexOf(twoTag, pos)
    let start: number
    let closeTag: string
    if (iOne === -1 && iTwo === -1) break
    if (iOne === -1) {
      start = iTwo
      closeTag = twoClose
    } else if (iTwo === -1) {
      start = iOne
      closeTag = oneClose
    } else if (iOne <= iTwo) {
      start = iOne
      closeTag = oneClose
    } else {
      start = iTwo
      closeTag = twoClose
    }
    const end = xmlText.indexOf(closeTag, start)
    if (end === -1) break
    const block = xmlText.slice(start, end + closeTag.length)
    pos = end + closeTag.length
    const colM = block.match(/<xdr:col[^>]*>(\d+)<\/xdr:col>/i) || block.match(/<[^:]*:col[^>]*>(\d+)<\/[^:]*:col>/i)
    const rowM = block.match(/<xdr:row[^>]*>(\d+)<\/xdr:row>/i) || block.match(/<[^:]*:row[^>]*>(\d+)<\/[^:]*:row>/i)
    const embedM = block.match(/r:embed=["']([^"']+)["']/i) || block.match(/embed=["']([^"']+)["']/i)
    if (!colM?.[1] || !rowM?.[1] || !embedM?.[1]) continue
    const col = parseInt(colM[1], 10)
    const row = parseInt(rowM[1], 10)
    out.push({ row, col, rId: embedM[1] })
  }
  log('parseDrawingAnchors 结束', { anchors: out.length })
  return out
}

/** WPS 嵌入单元格图片：从 cellimages.xml 解析 imageId -> rId，从 cellimages.xml.rels 解析 rId -> 路径，再从 zip 读取得到 imageId -> Blob */
async function getWpsCellImageBlobs(zip: JSZip): Promise<Map<string, Blob>> {
  log('getWpsCellImageBlobs 开始')
  const idToBlob = new Map<string, Blob>()
  const cellimagesXml = await zip.file('xl/cellimages.xml')?.async('string')
  if (!cellimagesXml) {
    log('getWpsCellImageBlobs 无 cellimages.xml，跳过')
    return idToBlob
  }
  const idToRid = new Map<string, string>()
  const cellImageBlocks = cellimagesXml.match(/<[^>]*:cellImage[^>]*>[\s\S]*?<\/[^>]*:cellImage>/gi) || []
  if (cellImageBlocks.length > 0) {
    for (const block of cellImageBlocks) {
      const nameM = block.match(/name=["']([^"']+)["']/i)
      const embedM = block.match(/r:embed=["']([^"']+)["']/i) || block.match(/embed=["']([^"']+)["']/i)
      if (nameM?.[1] && embedM?.[1]) idToRid.set(nameM[1], embedM[1])
    }
  }
  if (idToRid.size === 0) {
    log('getWpsCellImageBlobs idToRid 为空，跳过')
    return idToBlob
  }
  const relsText = await zip.file('xl/_rels/cellimages.xml.rels')?.async('string')
  if (!relsText) {
    log('getWpsCellImageBlobs 无 cellimages.xml.rels，跳过')
    return idToBlob
  }
  const ridToTarget = parseRelsXml(relsText)
  const mediaFiles = Object.keys(zip.files).filter((p) => p.startsWith('xl/media/') && !p.includes('_rels'))
  const tasks: Array<{ imageId: string; path: string }> = []
  for (const [imageId, rId] of idToRid) {
    const target = ridToTarget.get(rId)
    if (!target) continue
    const mediaName = target.replace(/^\.\.\/media\//, '').split('/').pop()!
    let mediaPath = 'xl/media/' + mediaName
    if (!zip.file(mediaPath)) {
      const found = mediaFiles.find((p) => p.endsWith(mediaName) || p.includes(mediaName))
      if (found) mediaPath = found
      else continue
    }
    if (zip.file(mediaPath)) tasks.push({ imageId, path: mediaPath })
  }
  const results = await Promise.all(
    tasks.map(async ({ imageId, path }) => {
      const file = zip.file(path)
      if (!file) return null
      const buf = await file.async('arraybuffer')
      const ext = (path.split('.').pop() || 'png').toLowerCase()
      const mime =
        ext === 'jpg' || ext === 'jpeg' ? 'image/jpeg' : ext === 'gif' ? 'image/gif' : ext === 'webp' ? 'image/webp' : ext === 'bmp' ? 'image/bmp' : 'image/png'
      return { imageId, blob: new Blob([buf], { type: mime }) }
    })
  )
  for (const r of results) {
    if (r) idToBlob.set(r.imageId, r.blob)
  }
  log('getWpsCellImageBlobs 结束', { blobs: idToBlob.size })
  return idToBlob
}

/** 最大扫描单元格数，防止含大量空白行的表导致主线程长时间阻塞 */
const MAX_DISPIMG_CELLS = 80000
/** 每扫描多少单元格让出主线程一次（0 表示不让出） */
const DISPIMG_YIELD_EVERY = 5000
/** 超过此长度的 sheet 用「先找 DISPIMG 再反查单元格」方式解析，避免逐格扫描卡死 */
const BIG_SHEET_DISPIMG_THRESHOLD = 5 * 1024 * 1024

/** 从工作表 XML 中解析包含 =DISPIMG("ID_xxx",1) 的单元格，返回 (dataRowIndex, col, imageId) 列表。表头为第 1 行，dataRowIndex 0 对应 Excel 第 2 行。超大 sheet 时先正则找所有 DISPIMG 再反查 <c，避免逐格扫描。 */
async function parseSheetForDispimgFormulas(sheetXml: string): Promise<Array<{ dataRowIndex: number; col: number; imageId: string }>> {
  log('parseSheetForDispimgFormulas 开始', { sheetLen: sheetXml.length })
  if (sheetXml.indexOf('DISPIMG') === -1) {
    log('parseSheetForDispimgFormulas 无 DISPIMG，快速返回')
    return []
  }
  const out: Array<{ dataRowIndex: number; col: number; imageId: string }> = []

  // 支持 XML 转义引号：sheet 里公式常为 DISPIMG(&quot;ID&quot;,1) 而非 DISPIMG("ID",1)
  const normalizedXml = sheetXml.replace(/&quot;/g, '"').replace(/&apos;/g, "'")

  if (sheetXml.length > BIG_SHEET_DISPIMG_THRESHOLD) {
    // 超大 sheet：先找所有 DISPIMG 再反查所在单元格，复杂度与 DISPIMG 数量相关
    const dispimgRegex = /DISPIMG\s*\(\s*["']([^"']+)["']\s*,\s*\d+\s*\)/gi
    let m: RegExpExecArray | null
    let matchCount = 0
    while ((m = dispimgRegex.exec(normalizedXml)) !== null) {
      const imageId = m[1]
      if (!imageId) continue
      const cellStart = normalizedXml.lastIndexOf('<c ', m.index)
      if (cellStart === -1) continue
      const frag = normalizedXml.slice(cellStart, m.index + 300)
      const refM = frag.match(/r=["']([A-Za-z0-9]+)["']/i)
      const cellRef = refM?.[1]
      if (!cellRef) continue
      const decoded = decodeCellRef(cellRef)
      if (decoded == null || decoded.r < 1) continue
      out.push({ dataRowIndex: decoded.r - 1, col: decoded.c, imageId })
      matchCount++
      if (matchCount % 100 === 0) await new Promise((r) => setTimeout(r, 0))
    }
    if (out.length === 0) {
      const first = normalizedXml.indexOf('DISPIMG')
      if (first !== -1) {
        const snippet = normalizedXml.slice(Math.max(0, first - 20), first + 120)
        log('parseSheetForDispimgFormulas DISPIMG 存在但未匹配，片段', snippet)
      }
    }
    log('parseSheetForDispimgFormulas 结束 (DISPIMG 先查)', { dispimgFound: out.length })
    return out
  }

  const dispimgRegex = /DISPIMG\s*\(\s*["']([^"']+)["']\s*,\s*\d+\s*\)/gi
  let pos = 0
  let cellCount = 0
  for (;;) {
    if (cellCount >= MAX_DISPIMG_CELLS) {
      log('parseSheetForDispimgFormulas 达到单元格上限', { MAX_DISPIMG_CELLS, found: out.length })
      break
    }
    const start = normalizedXml.indexOf('<c ', pos)
    if (start === -1) break
    const end = normalizedXml.indexOf('</c>', start)
    if (end === -1) break
    cellCount++
    if (DISPIMG_YIELD_EVERY > 0 && cellCount % DISPIMG_YIELD_EVERY === 0) {
      log('parseSheetForDispimgFormulas 让出主线程', { cellCount })
      await new Promise((r) => setTimeout(r, 0))
    }
    const cellBlock = normalizedXml.slice(start, end + 4)
    pos = end + 4
    const refM = cellBlock.match(/r=["']([A-Za-z0-9]+)["']/i)
    const cellRef = refM?.[1]
    if (!cellRef) continue
    const formulaM = cellBlock.match(/<[^:]*:?f>([\s\S]*?)<\/[^:]*:?f>/i)
    const formula = formulaM?.[1]
    if (!formula) continue
    dispimgRegex.lastIndex = 0
    const idM = dispimgRegex.exec(formula)
    if (!idM?.[1]) continue
    const imageId = idM[1]
    const decoded = decodeCellRef(cellRef)
    if (decoded == null || decoded.r < 1) continue
    const dataRowIndex = decoded.r - 1
    out.push({ dataRowIndex, col: decoded.c, imageId })
  }
  log('parseSheetForDispimgFormulas 结束', { cellsScanned: cellCount, dispimgFound: out.length })
  return out
}

function decodeCellRef(ref: string): { r: number; c: number } | null {
  const match = ref.match(/^([A-Za-z]+)(\d+)$/)
  if (!match?.[1] || !match?.[2]) return null
  const colLetters = match[1].toUpperCase()
  let c = 0
  for (let i = 0; i < colLetters.length; i++) {
    c = c * 26 + (colLetters.charCodeAt(i) - 64)
  }
  const r = parseInt(match[2], 10) - 1
  return { r, c: c - 1 }
}

/** WPS 嵌入单元格图片（DISPIMG 公式）：从 cellimages 与 sheet 公式解析，合并到 map */
async function extractDispImgImagesIntoMap(
  zip: JSZip,
  sheetXml: string,
  map: Map<number, EmbeddedImage[]>
): Promise<void> {
  log('extractDispImgImagesIntoMap 开始')
  const idToBlob = await getWpsCellImageBlobs(zip)
  if (idToBlob.size === 0) {
    log('extractDispImgImagesIntoMap 无 WPS 图片，跳过')
    return
  }
  const dispimgCells = await parseSheetForDispimgFormulas(sheetXml)
  log('extractDispImgImagesIntoMap 解析 DISPIMG 单元格数', dispimgCells.length)
  for (const { dataRowIndex, col, imageId } of dispimgCells) {
    const blob = idToBlob.get(imageId)
    if (!blob) continue
    const arr = map.get(dataRowIndex) ?? []
    arr.push({ blob, col, row: dataRowIndex + 1 })
    map.set(dataRowIndex, arr)
  }
  log('extractDispImgImagesIntoMap 结束')
}

/**
 * 从 xlsx buffer 提取嵌入图片。
 * 返回 Map<dataRowIndex, EmbeddedImage[]>，按 col 排序。
 * dataRowIndex：0 = 第一条数据行（Excel 第 2 行，表头为第 1 行）。
 * 支持 Excel 浮动图片与 WPS 嵌入单元格图片（=DISPIMG("ID_xxx",1)）。
 */
export async function extractEmbeddedImagesFromXlsx(
  arrayBuffer: ArrayBuffer
): Promise<Map<number, EmbeddedImage[]>> {
  log('extractEmbeddedImagesFromXlsx 开始')
  const map = new Map<number, EmbeddedImage[]>()
  let zip: JSZip
  try {
    zip = await JSZip.loadAsync(arrayBuffer)
    log('extractEmbeddedImagesFromXlsx zip 加载完成')
  } catch (e) {
    log('extractEmbeddedImagesFromXlsx zip 加载失败', e)
    return map
  }
  if (!zip.folder('xl')) {
    log('extractEmbeddedImagesFromXlsx 无 xl 目录')
    return map
  }

  try {
    const wbRels = await zip.file('xl/_rels/workbook.xml.rels')?.async('string')
    if (!wbRels) {
      log('extractEmbeddedImagesFromXlsx 无 workbook.xml.rels')
      return map
    }
    const wbRelsMap = parseRelsXml(wbRels)
    const sheetEntry = Array.from(wbRelsMap.entries()).find(
      ([, t]) => /worksheets\/sheet\d*\.xml$/i.test(t)
    )
    const sheetRelTarget = sheetEntry?.[1]
    if (!sheetRelTarget) {
      log('extractEmbeddedImagesFromXlsx 未找到 sheet 引用')
      return map
    }
    const sheetPath = 'xl/' + sheetRelTarget.replace(/^\.\.\//, '')
    const sheetXml = await zip.file(sheetPath)?.async('string')
    if (!sheetXml) {
      log('extractEmbeddedImagesFromXlsx 无法读取 sheet XML')
      return map
    }
    log('extractEmbeddedImagesFromXlsx sheet 读取完成', { sheetPath, sheetLen: sheetXml.length })

    const drawIdMatch = sheetXml.match(/<drawing\s[^>]*r:id=["']([^"']+)["']/i)
    const drawingRId = drawIdMatch?.[1]
    log('extractEmbeddedImagesFromXlsx drawing 引用', { drawingRId: !!drawingRId })

    if (drawingRId) {
      const sheetDir = sheetPath.replace(/[^/]+$/, '')
      const sheetName = sheetPath.split('/').pop()!.replace('.xml', '')
      const sheetRelsPath = sheetDir + '_rels/' + sheetName + '.xml.rels'
      const sheetRels = await zip.file(sheetRelsPath)?.async('string')
      if (sheetRels) {
        const sheetRelsMap = parseRelsXml(sheetRels)
        const drawingRelTarget = sheetRelsMap.get(drawingRId)
        if (drawingRelTarget) {
          log('extractEmbeddedImagesFromXlsx 开始读取 drawing XML')
          const drawingPath = 'xl/drawings/' + drawingRelTarget.replace(/^\.\.\/drawings\//, '').replace(/^\.\.\//, '')
          let drawingXmlText: string | undefined = await zip.file(drawingPath)?.async('string')
          if (!drawingXmlText) drawingXmlText = await zip.file('xl/' + drawingRelTarget.replace(/^\.\.\//, ''))?.async('string') ?? undefined
          if (!drawingXmlText) {
            const first = Object.keys(zip.files).find((p) => p.includes('drawings/') && p.endsWith('.xml') && !p.includes('_rels'))
            if (first) drawingXmlText = (await zip.file(first)?.async('string')) ?? undefined
          }
          if (drawingXmlText) {
            log('extractEmbeddedImagesFromXlsx drawing XML 读取完成', { len: drawingXmlText.length })
            const xmlText = drawingXmlText
            const anchors = parseDrawingAnchors(xmlText)
            log('extractEmbeddedImagesFromXlsx 主 drawing 锚点数', anchors.length)
            if (anchors.length === 0) {
              log('extractEmbeddedImagesFromXlsx 主 drawing 无锚点，尝试 tryAllDrawingFilesIntoMap')
              await tryAllDrawingFilesIntoMap(zip, map)
            } else {
              log('extractEmbeddedImagesFromXlsx 开始读取 drawing rels')
              const drawingDir = drawingPath.replace(/[^/]+\.xml$/, '')
              const drawingRelsPath = drawingDir + '_rels/' + (drawingPath.split('/').pop() ?? 'drawing1.xml').replace('.xml', '.xml.rels')
              let drawingRelsText: string | undefined = (await zip.file(drawingRelsPath)?.async('string')) ?? (await zip.file('xl/drawings/_rels/drawing1.xml.rels')?.async('string')) ?? undefined
              if (!drawingRelsText) {
                const relsFiles = Object.keys(zip.files).filter((p) => p.includes('drawings/_rels') && p.endsWith('.xml.rels'))
                if (relsFiles[0]) drawingRelsText = (await zip.file(relsFiles[0])?.async('string')) ?? undefined
              }
              if (drawingRelsText) {
                const relsText = drawingRelsText
                const drawingRelsMap = parseRelsXml(relsText)
                const mediaFiles = Object.keys(zip.files).filter((p) => p.startsWith('xl/media/') && !p.includes('_rels'))
                const anchorTasks: Array<{ row: number; col: number; mediaPath: string }> = []
                for (const { row, col, rId } of anchors) {
                  const relTarget = drawingRelsMap.get(rId)
                  if (!relTarget) continue
                  const mediaName = relTarget.replace(/^\.\.\/media\//, '').split('/').pop()!
                  let mediaPath = 'xl/media/' + mediaName
                  if (!zip.file(mediaPath)) {
                    const found = mediaFiles.find((p) => p.endsWith(mediaName) || p.includes(mediaName))
                    if (found) mediaPath = found
                    else continue
                  }
                  if (zip.file(mediaPath)) anchorTasks.push({ row, col, mediaPath })
                }
                log('extractEmbeddedImagesFromXlsx 开始并行读取媒体 Blob', { count: anchorTasks.length })
                const blobs = await Promise.all(
                  anchorTasks.map(async ({ mediaPath }) => {
                    const file = zip.file(mediaPath)
                    if (!file) return null
                    const buf = await file.async('arraybuffer')
                    const ext = (mediaPath.split('.').pop() || 'png').toLowerCase()
                    const mime = ext === 'jpg' || ext === 'jpeg' ? 'image/jpeg' : ext === 'gif' ? 'image/gif' : 'image/png'
                    return new Blob([buf], { type: mime })
                  })
                )
                for (let i = 0; i < anchorTasks.length; i++) {
                  const blob = blobs[i]
                  const meta = anchorTasks[i]
                  if (!blob || !meta) continue
                  const { row, col } = meta
                  const dataRowIndex = Math.max(0, row - 1)
                  const arr = map.get(dataRowIndex) ?? []
                  arr.push({ blob, col, row })
                  map.set(dataRowIndex, arr)
                }
                log('extractEmbeddedImagesFromXlsx 主 drawing 写入 map 完成', { total: map.size })
              }
            }
          }
        }
      }
    }

    // 始终执行 WPS DISPIMG 路径以合并嵌入单元格图片；超大 sheet 时由 parseSheetForDispimgFormulas 内部分用「先找 DISPIMG」方式避免卡死
    log('extractEmbeddedImagesFromXlsx 开始 extractDispImgImagesIntoMap (WPS)')
    await extractDispImgImagesIntoMap(zip, sheetXml, map)
    for (const arr of map.values()) arr.sort((a, b) => a.col - b.col)
    log('extractEmbeddedImagesFromXlsx 结束', { rowsWithImages: map.size })
  } catch (e) {
    console.warn(LOG_PREFIX, '提取Excel嵌入图片失败:', e)
  }
  return map
}

/**
 * 从 xlsx 的 xl/media 按文件名顺序取出所有图片 Blob（兜底用）。
 * 当按 drawing 无法关联到行时，可用「有 DISPIMG 的行」与该数组顺序一一对应。
 */
export async function getMediaBlobsInOrder(arrayBuffer: ArrayBuffer): Promise<Blob[]> {
  const blobs: Blob[] = []
  try {
    const zip = await JSZip.loadAsync(arrayBuffer)
    const mediaPaths = Object.keys(zip.files).filter(
      (p) => p.startsWith('xl/media/') && !p.includes('_rels') && /\.(png|jpe?g|gif|webp|bmp)$/i.test(p)
    )
    mediaPaths.sort()
    const results = await Promise.all(
      mediaPaths.map(async (path) => {
        const f = zip.file(path)
        if (!f) return null
        const buf = await f.async('arraybuffer')
        const ext = (path.split('.').pop() || 'png').toLowerCase()
        const mime =
          ext === 'jpg' || ext === 'jpeg' ? 'image/jpeg' : ext === 'gif' ? 'image/gif' : ext === 'webp' ? 'image/webp' : ext === 'bmp' ? 'image/bmp' : 'image/png'
        return new Blob([buf], { type: mime })
      })
    )
    for (const b of results) if (b) blobs.push(b)
  } catch (e) {
    console.warn('读取 xl/media 图片失败:', e)
  }
  return blobs
}

/** 图片来源：drawing=浮动图，dispimg=WPS 嵌入单元格。同行同图时优先保留 drawing。 */
export type OrderedImageSource = 'drawing' | 'dispimg'

/** 按 (dataRowIndex, col) 顺序的锚点+Blob，用于兜底时按表内出现顺序挂到对应行 */
export interface OrderedImageItem {
  dataRowIndex: number
  col: number
  blob: Blob
  /** 来源，用于同行多图时优先保留浮动图、去重同图 */
  source?: OrderedImageSource
}

/**
 * 从 xlsx 中按「表内出现顺序」(row→col) 解析所有嵌入图，返回带 dataRowIndex 的列表。
 * 兜底时用此顺序把 blob 挂到 result[dataRowIndex]，避免用 media 文件名顺序导致错位。
 * dataRowIndex = row - 1（xdr:row 为 0-based：row 1=首行数据→0）。
 */
export async function getOrderedAnchorsWithBlobs(
  arrayBuffer: ArrayBuffer
): Promise<OrderedImageItem[]> {
  log('getOrderedAnchorsWithBlobs 开始')
  const out: OrderedImageItem[] = []
  let zip: JSZip
  try {
    zip = await JSZip.loadAsync(arrayBuffer)
    log('getOrderedAnchorsWithBlobs zip 加载完成')
  } catch {
    return out
  }
  if (!zip.folder('xl')) return out

  const mediaFiles = Object.keys(zip.files).filter(
    (p) => p.startsWith('xl/media/') && !p.includes('_rels')
  )

  async function collectFromDrawing(drawingXmlText: string, drawingRelsMap: Map<string, string>) {
    const anchors = parseDrawingAnchors(drawingXmlText)
    const tasks: Array<{ row: number; col: number; mediaPath: string }> = []
    for (const { row, col, rId } of anchors) {
      const relTarget = drawingRelsMap.get(rId)
      if (!relTarget) continue
      const mediaName = relTarget.replace(/^\.\.\/media\//, '').split('/').pop()!
      let mediaPath = 'xl/media/' + mediaName
      if (!zip!.file(mediaPath)) {
        const found = mediaFiles.find((p) => p.endsWith(mediaName) || p.includes(mediaName))
        if (found) mediaPath = found
        else continue
      }
      if (zip!.file(mediaPath)) tasks.push({ row, col, mediaPath })
    }
    const blobs = await Promise.all(
      tasks.map(async ({ mediaPath }) => {
        const file = zip!.file(mediaPath)
        if (!file) return null
        const buf = await file.async('arraybuffer')
        const ext = (mediaPath.split('.').pop() || 'png').toLowerCase()
        const mime =
          ext === 'jpg' || ext === 'jpeg' ? 'image/jpeg' : ext === 'gif' ? 'image/gif' : 'image/png'
        return new Blob([buf], { type: mime })
      })
    )
    for (let i = 0; i < tasks.length; i++) {
      const blob = blobs[i]
      const meta = tasks[i]
      if (!blob || !meta) continue
      const { row, col } = meta
      const dataRowIndex = Math.max(0, row - 1)
      out.push({ dataRowIndex, col, blob, source: 'drawing' })
    }
  }

  try {
    const wbRels = await zip.file('xl/_rels/workbook.xml.rels')?.async('string')
    if (!wbRels) {
      log('getOrderedAnchorsWithBlobs 无 workbook.xml.rels，走 tryAllDrawingFiles')
      await tryAllDrawingFiles(zip, mediaFiles, collectFromDrawing)
      log('getOrderedAnchorsWithBlobs 结束 (无 wbRels)', { ordered: out.length })
      return out.sort((a, b) => a.dataRowIndex - b.dataRowIndex || a.col - b.col)
    }
    const wbRelsMap = parseRelsXml(wbRels)
    const sheetEntry = Array.from(wbRelsMap.entries()).find(
      ([, t]) => /worksheets\/sheet\d*\.xml$/i.test(t)
    )
    const sheetRelTarget = sheetEntry?.[1]
    const sheetPath = sheetRelTarget ? 'xl/' + sheetRelTarget.replace(/^\.\.\//, '') : null
    let drawingXmlText: string | null = null
    let drawingRelsMap: Map<string, string> | null = null

    if (sheetPath) {
      log('getOrderedAnchorsWithBlobs 读取 sheet', sheetPath)
      const sheetXml = await zip.file(sheetPath)?.async('string')
      log('getOrderedAnchorsWithBlobs sheet 读取完成', { len: sheetXml?.length })
      const drawIdMatch = sheetXml?.match(/<drawing\s[^>]*r:id=["']([^"']+)["']/i)
      const drawingRId = drawIdMatch?.[1]
      if (drawingRId) {
        log('getOrderedAnchorsWithBlobs 有 drawing，读取 drawing XML')
        const sheetDir = sheetPath.replace(/[^/]+$/, '')
        const sheetName = sheetPath.split('/').pop()!.replace('.xml', '')
        const sheetRelsPath = sheetDir + '_rels/' + sheetName + '.xml.rels'
        const sheetRels = await zip.file(sheetRelsPath)?.async('string')
        const sheetRelsMap = parseRelsXml(sheetRels || '')
        const drawingRelTarget = sheetRelsMap.get(drawingRId)
        if (drawingRelTarget) {
          const drawingPath =
            'xl/drawings/' +
            drawingRelTarget.replace(/^\.\.\/drawings\//, '').replace(/^\.\.\//, '')
          drawingXmlText =
            (await zip.file(drawingPath)?.async('string')) ??
            (await zip.file('xl/' + drawingRelTarget.replace(/^\.\.\//, ''))?.async('string')) ??
            null
          if (!drawingXmlText) {
            const first = Object.keys(zip.files).find(
              (p) => p.includes('drawings/') && p.endsWith('.xml') && !p.includes('_rels')
            )
            if (first) drawingXmlText = (await zip.file(first)?.async('string')) ?? null
          }
          const drawingDir = drawingPath.replace(/[^/]+\.xml$/, '')
          const drawingRelsPath =
            drawingDir + '_rels/' + drawingPath.split('/').pop()!.replace('.xml', '.xml.rels')
          const drawingRelsText =
            (await zip.file(drawingRelsPath)?.async('string')) ??
            (await zip.file('xl/drawings/_rels/drawing1.xml.rels')?.async('string')) ??
            null
          if (drawingRelsText) drawingRelsMap = parseRelsXml(drawingRelsText)
        }
      }
    }

    if (drawingXmlText && drawingRelsMap) {
      log('getOrderedAnchorsWithBlobs collectFromDrawing 开始')
      await collectFromDrawing(drawingXmlText, drawingRelsMap)
      log('getOrderedAnchorsWithBlobs collectFromDrawing 结束', { out: out.length })
    }
    if (out.length === 0) {
      log('getOrderedAnchorsWithBlobs out 为空，尝试 tryAllDrawingFiles')
      await tryAllDrawingFiles(zip, mediaFiles, collectFromDrawing)
      log('getOrderedAnchorsWithBlobs tryAllDrawingFiles 结束', { out: out.length })
    }
    // 始终检查 WPS DISPIMG 以合并嵌入单元格图片；超大 sheet 时 parseSheetForDispimgFormulas 内用「先找 DISPIMG」方式，不会卡死
    log('getOrderedAnchorsWithBlobs 检查 WPS DISPIMG')
    const sheetXml: string | null = sheetPath ? (await zip.file(sheetPath)?.async('string')) ?? null : null
    if (sheetXml != null && sheetXml !== '') {
      const idToBlob = await getWpsCellImageBlobs(zip)
      if (idToBlob.size > 0) {
        const dispimgCells = await parseSheetForDispimgFormulas(sheetXml)
        for (const { dataRowIndex, col, imageId } of dispimgCells) {
          const blob = idToBlob.get(imageId)
          if (blob) out.push({ dataRowIndex, col, blob, source: 'dispimg' })
        }
      }
    }
  } catch (e) {
    console.warn(LOG_PREFIX, 'getOrderedAnchorsWithBlobs 失败:', e)
  }
  log('getOrderedAnchorsWithBlobs 结束', { total: out.length })
  return out.sort((a, b) => a.dataRowIndex - b.dataRowIndex || a.col - b.col)
}

/**
 * 从同一行的多项中选出最多 2 张「不同」的图：先按 col 再按 source（drawing 优先），再按 blob 去重（同 size+type 视为同图），
 * 保证实物图片1、实物图片2 不重复且浮动图优先。
 */
export function pickTwoDistinctBlobsPerRow(
  items: Array<{ col: number; blob: Blob; source?: OrderedImageSource }>
): [Blob | null, Blob | null] {
  if (items.length === 0) return [null, null]
  const byColThenSource = [...items].sort((a, b) => {
    if (a.col !== b.col) return a.col - b.col
    return (a.source === 'drawing' ? 0 : 1) - (b.source === 'drawing' ? 0 : 1)
  })
  const firstItem = byColThenSource[0]
  if (!firstItem) return [null, null]
  const first = firstItem.blob
  const second = byColThenSource.find(
    (x) => x.blob !== first && (x.blob.size !== first.size || x.blob.type !== first.type)
  )?.blob ?? null
  return [first, second]
}

/** 当主路径解析到 0 个锚点时，尝试所有 drawing 文件并合并到 map，以缓解「只识别到部分」 */
async function tryAllDrawingFilesIntoMap(
  zip: JSZip,
  map: Map<number, EmbeddedImage[]>,
  _mediaFiles?: string[]
) {
  log('tryAllDrawingFilesIntoMap 开始')
  const mediaFiles =
    _mediaFiles ??
    Object.keys(zip.files).filter((p) => p.startsWith('xl/media/') && !p.includes('_rels'))
  const drawingPaths = Object.keys(zip.files).filter(
    (p) => p.includes('drawings/') && p.endsWith('.xml') && !p.includes('_rels')
  )
  log('tryAllDrawingFilesIntoMap drawing 文件数', drawingPaths.length)
  for (const dp of drawingPaths) {
    log('tryAllDrawingFilesIntoMap 读取 drawing', dp)
    const xml = await zip.file(dp)?.async('string')
    if (!xml) continue
    log('tryAllDrawingFilesIntoMap drawing 读取完成', { path: dp, xmlLen: xml.length })
    const drawingDir = dp.replace(/[^/]+\.xml$/, '')
    const relsPath = drawingDir + '_rels/' + (dp.split('/').pop() ?? 'drawing1.xml').replace('.xml', '.xml.rels')
    let relsText =
      (await zip.file(relsPath)?.async('string')) ??
      (await zip.file('xl/drawings/_rels/drawing1.xml.rels')?.async('string')) ??
      null
    if (!relsText) {
      const anyRels = Object.keys(zip.files).find(
        (p) => p.includes('drawings/_rels') && p.endsWith('.xml.rels')
      )
      if (anyRels) relsText = (await zip.file(anyRels)?.async('string')) ?? null
    }
    if (!relsText) continue
    const drawingRelsMap = parseRelsXml(relsText)
    const anchors = parseDrawingAnchors(xml)
    log('tryAllDrawingFilesIntoMap 锚点数', { path: dp, anchors: anchors.length })
    const anchorTasks: Array<{ row: number; col: number; mediaPath: string }> = []
    for (const { row, col, rId } of anchors) {
      const relTarget = drawingRelsMap.get(rId)
      if (!relTarget) continue
      const mediaName = relTarget.replace(/^\.\.\/media\//, '').split('/').pop()!
      let mediaPath = 'xl/media/' + mediaName
      if (!zip.file(mediaPath)) {
        const found = mediaFiles.find((p) => p.endsWith(mediaName) || p.includes(mediaName))
        if (found) mediaPath = found
        else continue
      }
      if (zip.file(mediaPath)) anchorTasks.push({ row, col, mediaPath })
    }
    const blobs = await Promise.all(
      anchorTasks.map(async ({ mediaPath }) => {
        const file = zip.file(mediaPath)
        if (!file) return null
        const buf = await file.async('arraybuffer')
        const ext = (mediaPath.split('.').pop() || 'png').toLowerCase()
        const mime =
          ext === 'jpg' || ext === 'jpeg' ? 'image/jpeg' : ext === 'gif' ? 'image/gif' : 'image/png'
        return new Blob([buf], { type: mime })
      })
    )
    for (let i = 0; i < anchorTasks.length; i++) {
      const blob = blobs[i]
      const meta = anchorTasks[i]
      if (!blob || !meta) continue
      const { row, col } = meta
      const dataRowIndex = Math.max(0, row - 1)
      const arr = map.get(dataRowIndex) ?? []
      arr.push({ blob, col, row })
      map.set(dataRowIndex, arr)
    }
  }
  for (const arr of map.values()) arr.sort((a, b) => a.col - b.col)
  log('tryAllDrawingFilesIntoMap 结束', { rowsWithImages: map.size })
}

async function tryAllDrawingFiles(
  zip: JSZip,
  mediaFiles: string[],
  collectFromDrawing: (xml: string, rels: Map<string, string>) => Promise<void>
) {
  const drawingPaths = Object.keys(zip.files).filter(
    (p) => p.includes('drawings/') && p.endsWith('.xml') && !p.includes('_rels')
  )
  for (const dp of drawingPaths) {
    const xml = await zip.file(dp)?.async('string')
    if (!xml) continue
    const drawingDir = dp.replace(/[^/]+\.xml$/, '')
    const relsPath = drawingDir + '_rels/' + (dp.split('/').pop() ?? 'drawing1.xml').replace('.xml', '.xml.rels')
    let relsText =
      (await zip.file(relsPath)?.async('string')) ??
      (await zip.file('xl/drawings/_rels/drawing1.xml.rels')?.async('string')) ??
      null
    if (!relsText) {
      const anyRels = Object.keys(zip.files).find(
        (p) => p.includes('drawings/_rels') && p.endsWith('.xml.rels')
      )
      if (anyRels) relsText = (await zip.file(anyRels)?.async('string')) ?? null
    }
    if (relsText) await collectFromDrawing(xml, parseRelsXml(relsText))
  }
}

/**
 * 从 xlsx 按表内出现顺序提取所有嵌入图，打包为 ZIP，文件名为 图片_001.png、图片_002.png ...
 * 用于「从 Excel 按顺序提取图片到文件夹」：前端下载 ZIP 后解压即得到按顺序命名的图片。
 */
export async function exportOrderedImagesAsZip(arrayBuffer: ArrayBuffer): Promise<Blob> {
  const ordered = await getOrderedAnchorsWithBlobs(arrayBuffer)
  const zip = new JSZip()
  ordered.forEach((item, idx) => {
    const ext = item.blob.type?.includes('jpeg') || item.blob.type?.includes('jpg') ? 'jpg' : 'png'
    const name = `图片_${String(idx + 1).padStart(3, '0')}.${ext}`
    zip.file(name, item.blob)
  })
  return zip.generateAsync({ type: 'blob' })
}
