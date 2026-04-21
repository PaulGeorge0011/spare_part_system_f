import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, type UserInfo, type LoginResult } from '@/api/auth'
import { ssoApi } from '@/api/sso.ts'
import { ALL_MODULES, hasLevel, type ModulePermLevel } from '@/utils/modules'

const TOKEN_KEY = 'access_token'
const USER_KEY = 'user_info'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const user = ref<UserInfo | null>(null)

  const raw = localStorage.getItem(USER_KEY)
  if (raw) {
    try {
      user.value = JSON.parse(raw) as UserInfo
    } catch {
      localStorage.removeItem(USER_KEY)
    }
  }

  const role = computed(() => user.value?.role ?? '')
  const isAdmin = computed(() => role.value === 'admin')
  const isRequisitionClerk = computed(() =>
    ['requisition_clerk', 'electrical_requisition_clerk', 'mechanical_requisition_clerk'].includes(role.value)
  )
  /** 电气领用员（只能访问电气领用页和报表，能领用和归还） */
  const isElectricalClerk = computed(() =>
    role.value === 'electrical_requisition_clerk' || role.value === 'requisition_clerk'
  )
  /** 机械领用员（只能访问机械领用页和报表，能领用和归还） */
  const isMechanicalClerk = computed(() => role.value === 'mechanical_requisition_clerk')
  const isLoggedIn = computed(() => !!token.value)

  /** 新模块权限字典（来自 User.permissions 列，包含 electrical / mechanical 的 general_staff 配置） */
  const modulePermissions = computed<Record<string, string>>(() => {
    return (user.value?.permissions as Record<string, string>) ?? {}
  })

  /**
   * 角色推导的电气模块等效级别（仅用于角色用户，general_staff 走 permissions JSON）
   * - admin / electrical_admin → 'admin'
   * - electrical_requisition_clerk / requisition_clerk → 'viewer'
   * - 其他 → null
   */
  const _electricalRoleLevel = computed((): ModulePermLevel | null => {
    const r = role.value
    if (r === 'admin' || r === 'electrical_admin') return 'admin'
    if (r === 'electrical_requisition_clerk' || r === 'requisition_clerk') return 'viewer'
    return null
  })

  /** 角色推导的机械模块等效级别 */
  const _mechanicalRoleLevel = computed((): ModulePermLevel | null => {
    const r = role.value
    if (r === 'admin' || r === 'mechanical_admin') return 'admin'
    if (r === 'mechanical_requisition_clerk') return 'viewer'
    return null
  })

  /**
   * 统一模块访问权限检查（Phase 2 核心）。
   * - admin：始终有所有权限。
   * - electrical / mechanical：先按角色推导等效级别，再按 permissions JSON（general_staff 走此路径）。
   * - 新模块（process / safety 等）：仅按 permissions JSON。
   */
  function canAccessModule(moduleId: string, level: ModulePermLevel = 'viewer'): boolean {
    if (role.value === 'admin') return true

    if (moduleId === 'electrical') {
      const roleLevel = _electricalRoleLevel.value
      if (roleLevel && hasLevel(roleLevel, level)) return true
      return hasLevel(modulePermissions.value['electrical'], level)
    }
    if (moduleId === 'mechanical') {
      const roleLevel = _mechanicalRoleLevel.value
      if (roleLevel && hasLevel(roleLevel, level)) return true
      return hasLevel(modulePermissions.value['mechanical'], level)
    }
    // 新模块：纯 permissions 控制
    return hasLevel(modulePermissions.value[moduleId], level)
  }

  /** 用户物资范围：从 canAccessModule 派生，保持向后兼容 */
  const materialScopes = computed(() => {
    const scopes: string[] = []
    if (canAccessModule('electrical', 'viewer')) scopes.push('electrical')
    if (canAccessModule('mechanical', 'viewer')) scopes.push('mechanical')
    return scopes
  })
  const hasElectricalScope = computed(() => materialScopes.value.includes('electrical'))
  const hasMechanicalScope = computed(() => materialScopes.value.includes('mechanical'))

  /** 可见电气备件列表（editor 级别，即旧版 electrical_admin 等效） */
  const canSeeElectricalParts = computed(() => canAccessModule('electrical', 'editor'))
  /** 可见机械备件列表（editor 级别） */
  const canSeeMechanicalParts = computed(() => canAccessModule('mechanical', 'editor'))

  /** 电气模块管理权（admin 级别：库存/日志/报表/用户管理） */
  const canManageElectrical = computed(() => canAccessModule('electrical', 'admin'))
  /** 机械模块管理权（admin 级别） */
  const canManageMechanical = computed(() => canAccessModule('mechanical', 'admin'))
  /** 可管理任一模块（用于通用判断） */
  const canManageSystem = computed(() => canManageElectrical.value || canManageMechanical.value)

  /** 是否超级管理员（可删除用户、可审批为任意角色、可设任意模块 admin 权限） */
  const isSuperAdmin = computed(() => user.value?.username === 'admin')
  /** 电气管理员（可管理电气模块用户、可为 general_staff 设 electrical 权限至 editor） */
  const isElectricalAdmin = computed(() => role.value === 'electrical_admin')
  /** 机械管理员 */
  const isMechanicalAdmin = computed(() => role.value === 'mechanical_admin')

  /** 当前用户可访问的所有模块 ID 列表（按 ALL_MODULES 顺序） */
  const accessibleModuleIds = computed(() =>
    ALL_MODULES.filter((m) => canAccessModule(m.id)).map((m) => m.id),
  )

  function setAuth(t: string, u: UserInfo) {
    token.value = t
    user.value = u
    localStorage.setItem(TOKEN_KEY, t)
    localStorage.setItem(USER_KEY, JSON.stringify(u))
  }

  function clearAuth() {
    token.value = null
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  async function login(username: string, password: string) {
    const res = (await authApi.login(username, password)) as unknown as LoginResult
    const u = res.user
    setAuth(res.access_token, u)
    return u
  }

  /** SSO 单点登录：用 code 换取本系统 JWT */
  async function ssoLogin(code: string, sessionState: string = '') {
    const res = (await ssoApi.ssoLogin(code, sessionState)) as unknown as LoginResult
    const u = res.user
    setAuth(res.access_token, u)
    return u
  }

  /** 使用 token 登录（如企业微信回调）。存 token 后拉取用户信息。 */
  async function loginWithToken(accessToken: string) {
    token.value = accessToken
    localStorage.setItem(TOKEN_KEY, accessToken)
    const u = (await authApi.getMe()) as unknown as UserInfo
    user.value = u
    localStorage.setItem(USER_KEY, JSON.stringify(u))
    return u
  }

  function logout() {
    clearAuth()
  }

  async function fetchUser() {
    if (!token.value) return null
    const u = (await authApi.getMe()) as unknown as UserInfo
    user.value = u
    localStorage.setItem(USER_KEY, JSON.stringify(u))
    return user.value
  }

  return {
    token,
    user,
    role,
    isAdmin,
    isRequisitionClerk,
    isElectricalClerk,
    isMechanicalClerk,
    isLoggedIn,
    modulePermissions,
    materialScopes,
    hasElectricalScope,
    hasMechanicalScope,
    canSeeElectricalParts,
    canSeeMechanicalParts,
    canManageElectrical,
    canManageMechanical,
    canManageSystem,
    isSuperAdmin,
    isElectricalAdmin,
    isMechanicalAdmin,
    canAccessModule,
    accessibleModuleIds,
    login,
    ssoLogin,
    loginWithToken,
    logout,
    fetchUser,
    setAuth,
    clearAuth,
  }
})
