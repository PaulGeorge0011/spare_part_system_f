import request from '@/utils/request'

export interface UserInfo {
  id: number
  username: string
  real_name?: string | null
  role: 'admin' | 'requisition_clerk'
  /** 物资范围：electrical / mechanical，空则视为全部 */
  material_scopes?: string[]
  /** 新模块权限：{"process": "admin", "safety": "viewer"}，旧版模块由 role 控制 */
  permissions?: Record<string, string> | null
}

export interface LoginResult {
  access_token: string
  token_type: string
  user: UserInfo
}

export interface RegisterResult {
  message: string
}

export const authApi = {
  login(username: string, password: string) {
    return request.post<LoginResult>('/auth/login', { username, password })
  },

  register(username: string, realName: string, password: string) {
    return request.post<RegisterResult>('/auth/register', { username, real_name: realName, password })
  },

  getMe() {
    return request.get<UserInfo>('/auth/me')
  },

  /** 通过设置密码链接 token 设置新密码（无需登录） */
  setPasswordByToken(token: string, newPassword: string) {
    return request.post<{ message: string }>('/auth/set-password-by-token', { token, new_password: newPassword })
  },

  /** 已登录用户修改自己的密码 */
  changePassword(currentPassword: string, newPassword: string) {
    return request.patch<{ message: string }>('/auth/me/password', {
      current_password: currentPassword,
      new_password: newPassword,
    })
  },

  /** 登录页修改密码：凭账号与旧密码设置新密码（无需登录） */
  changePasswordFromLogin(username: string, oldPassword: string, newPassword: string) {
    return request.post<{ message: string }>('/auth/change-password', {
      username,
      old_password: oldPassword,
      new_password: newPassword,
    })
  },
}
