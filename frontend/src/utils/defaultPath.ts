import { useAuthStore } from '@/stores/auth'

/** 根据当前用户权限返回默认首页路径（电气/机械系统入口及子页） */
export function defaultPathForUser(auth: ReturnType<typeof useAuthStore>): string {
  if (auth.hasElectricalScope) return '/electrical/parts'
  if (auth.hasMechanicalScope) return '/mechanical/parts'
  return '/home'
}
