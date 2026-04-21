import request from '@/utils/request'

export interface WechatAuthUrlResult {
  url: string
  message?: string
}

export const wechatApi = {
  /** 获取企业微信 OAuth2 扫码授权链接（登录/注册）。未配置时 url 为空。 */
  getAuthUrl() {
    return request.get<WechatAuthUrlResult>('/wechat/auth-url')
  },

  /** 获取企业微信 OAuth2 扫码授权链接（绑定当前账号）。需登录后调用。401 时不弹窗、不跳转登录。 */
  getBindAuthUrl() {
    return request.get<WechatAuthUrlResult>('/wechat/bind-auth-url', {
      skipAuthError: true,
    } as any)
  },
}
