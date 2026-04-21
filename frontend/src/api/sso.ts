import request from '@/utils/request'
import type { LoginResult } from './auth'

export interface SsoStatusResult {
  sso_enabled: boolean
}

export interface SsoUrlResult {
  url: string
  sso_enabled: boolean
}

export const ssoApi = {
  /** 获取 SSO 是否启用 */
  getStatus() {
    return request.get<SsoStatusResult>('/auth/sso-status')
  },

  /** 获取 SSO 授权链接 */
  getSsoUrl(wechat: boolean = false) {
    return request.get<SsoUrlResult>('/auth/sso-url', { params: { wechat } })
  },

  /** 用 SSO code 换取本系统 JWT */
  ssoLogin(code: string, sessionState: string = '') {
    return request.post<LoginResult>('/auth/sso-login', { code, session_state: sessionState })
  },
}
