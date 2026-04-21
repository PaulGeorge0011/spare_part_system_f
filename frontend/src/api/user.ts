import request from '@/utils/request'

export type UserRole =
  | 'admin'
  | 'electrical_requisition_clerk'
  | 'mechanical_requisition_clerk'
  | 'electrical_admin'
  | 'mechanical_admin'
  | 'general_staff'
  | 'requisition_clerk'

export const ROLE_LABELS: Record<string, string> = {
  admin: '超级管理员',
  electrical_requisition_clerk: '电气领用员',
  mechanical_requisition_clerk: '机械领用员',
  electrical_admin: '电气管理员',
  mechanical_admin: '机械管理员',
  general_staff: '通用人员',
  requisition_clerk: '修复件领用员',
}

export interface UserListItem {
  id: number
  username: string
  real_name: string | null
  role: string
  status: string
  wechat_userid: string | null
  wechat_name: string | null
  created_at: string | null
  material_scopes?: string[]
  permissions?: Record<string, string> | null
}

export interface BatchUserItem {
  username: string
  real_name: string | null
  token: string
}

export interface BatchCreateUsersResult {
  created: number
  failed: number
  items: BatchUserItem[]
  errors: { row: number; username: string; error: string }[]
}

/** 管理员新建用户（单用户）返回：含设置密码链接用 token */
export interface AdminCreateUserResult {
  username: string
  real_name: string | null
  token: string
}

export const userApi = {
  list() {
    return request.get<UserListItem[]>('/users')
  },

  updateRole(userId: number, role: UserRole) {
    return request.patch<UserListItem>(`/users/${userId}`, { role })
  },

  approve(userId: number, role: UserRole, permissions?: Record<string, string>) {
    return request.post<UserListItem>(`/users/${userId}/approve`, { role, permissions })
  },

  reject(userId: number) {
    return request.post<{ message: string }>(`/users/${userId}/reject`)
  },

  delete(userId: number) {
    return request.delete<{ message: string }>(`/users/${userId}`)
  },

  /** 批量新增用户：上传 Excel（账号、姓名、角色），返回设置密码链接用 token */
  batchCreateUsers(file: File) {
    const form = new FormData()
    form.append('file', file)
    return request.post<BatchCreateUsersResult>('/users/batch', form)
  },

  /** 更新用户新模块权限（仅超级管理员，传空对象清空所有新模块权限） */
  updatePermissions(userId: number, permissions: Record<string, string>) {
    return request.patch<UserListItem>(`/users/${userId}/permissions`, { permissions })
  },

  /** 管理员新建用户（授权分级：超级管理员任意角色与权限，模块管理员仅能建本模块领用员或通用人员）。返回设置密码链接用 token。 */
  createUser(data: { username: string; real_name?: string | null; role: UserRole; permissions?: Record<string, string> }) {
    return request.post<AdminCreateUserResult>('/users', data)
  },
}
