/**
 * 页面流转日志：用于排查切换/加载卡顿。
 * 控制台筛选 [Nav] 即可只看流转相关输出。
 * 如需关闭：将 NAV_LOG_ENABLED 设为 false 或注释掉 navLog 内 console 调用。
 */
const NAV_LOG_ENABLED = true
const PREFIX = '[Nav]'

function ts(): string {
  const d = new Date()
  return d.toISOString().slice(11, 23) // HH:mm:ss.SSS
}

function elapsed(ms: number): string {
  if (ms >= 1000) return `${(ms / 1000).toFixed(2)}s`
  return `${ms}ms`
}

export function navLog(phase: string, detail?: Record<string, unknown> | string, startTime?: number) {
  if (!NAV_LOG_ENABLED) return
  const msg = detail === undefined
    ? `${PREFIX} ${ts()} ${phase}`
    : typeof detail === 'string'
      ? `${PREFIX} ${ts()} ${phase} ${detail}`
      : `${PREFIX} ${ts()} ${phase}`
  if (typeof detail === 'object' && detail !== null) {
    const extra: Record<string, unknown> = { ...detail }
    if (startTime !== undefined) extra.elapsed = elapsed(Date.now() - startTime)
    console.log(msg, extra)
  } else {
    console.log(msg)
  }
}

/** 返回一个用于计时的开始时间，配合 navLog(phase, { ... }, startTime) 可打印 elapsed */
export function navLogStart(): number {
  return Date.now()
}
