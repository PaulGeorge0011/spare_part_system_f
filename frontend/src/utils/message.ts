import { ElMessage } from 'element-plus'

const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini|Mobile|mobile/i.test(
  navigator.userAgent || '',
)
const DEFAULT_DURATION = isMobile ? 1500 : 2000

type MsgOpts = Parameters<typeof ElMessage>[0]
function normalize(opts: MsgOpts): Exclude<MsgOpts, string> {
  const base = typeof opts === 'string' ? { message: opts } : { ...opts }
  if ((base as any).duration === undefined) (base as any).duration = DEFAULT_DURATION
  return base as any
}

export const msg = Object.assign(
  (opts: MsgOpts) => ElMessage(normalize(opts)),
  {
    success: (o: MsgOpts) => ElMessage.success(normalize(o)),
    warning: (o: MsgOpts) => ElMessage.warning(normalize(o)),
    info: (o: MsgOpts) => ElMessage.info(normalize(o)),
    error: (o: MsgOpts) => ElMessage.error(normalize(o)),
    closeAll: ElMessage.closeAll,
  },
)
