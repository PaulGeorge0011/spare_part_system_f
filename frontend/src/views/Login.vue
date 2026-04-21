<template>
  <div class="login-page">
    <div class="login-bg">
      <div class="login-bg-shape shape-1" />
      <div class="login-bg-shape shape-2" />
      <div class="login-bg-shape shape-3" />
    </div>
    <div class="login-card">
      <div class="login-header">
        <div class="login-logo">
          <span class="logo-icon">◆</span>
        </div>
        <h1 class="login-title">制丝二设备管理系统</h1>
        <p class="login-subtitle">Spare Parts Management</p>
      </div>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="0"
        class="login-form"
        @submit.prevent="handleSubmit"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="用户名（字母、数字、下划线或中文）"
            size="large"
            prefix-icon="User"
            maxlength="64"
            show-word-limit
            class="login-input"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            size="large"
            show-password
            prefix-icon="Lock"
            maxlength="72"
            class="login-input"
            @keyup.enter="handleSubmit"
          />
        </el-form-item>
        <el-form-item class="submit-item">
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="submit-btn"
            @click="handleSubmit"
          >
            登 录
          </el-button>
        </el-form-item>
        <!-- SSO 单点登录（企业微信） -->
        <el-form-item v-if="ssoEnabled" class="wechat-row">
          <div class="login-divider">
            <span>或</span>
          </div>
          <div class="wechat-section">
            <p class="wechat-scan-tip">
              点击下方按钮将<strong>跳转到企业统一认证</strong>，在企业微信内可<strong>免登录</strong>，PC 浏览器可使用<strong>企业微信扫码</strong>登录。
            </p>
            <el-button
              type="success"
              size="large"
              :loading="ssoLoading"
              class="wechat-btn"
              @click="handleSsoLogin(true)"
            >
              企业微信登录
            </el-button>
            <el-button
              type="info"
              size="large"
              :loading="ssoLoading"
              plain
              class="sso-account-btn"
              @click="handleSsoLogin(false)"
            >
              统一认证账号登录
            </el-button>
            <p class="wechat-hint">首次登录将自动注册，需管理员审批通过后方可使用。</p>
          </div>
        </el-form-item>
        <!-- 旧版企业微信直连（非 SSO 模式） -->
        <el-form-item v-else-if="wechatAuthUrl" class="wechat-row">
          <div class="login-divider">
            <span>或</span>
          </div>
          <div class="wechat-section">
            <p class="wechat-scan-tip">
              点击下方按钮将<strong>跳转到企业微信授权页面</strong>，在跳转后的页面使用<strong>手机企业微信</strong>扫描二维码或确认授权即可登录。
            </p>
            <el-button
              type="success"
              size="large"
              :loading="wechatLoading"
              class="wechat-btn"
              @click="handleWechatLogin"
            >
              企业微信扫码登录
            </el-button>
            <p class="wechat-hint">新用户扫码将自动提交注册申请，需管理员审批通过后可登录。</p>
            <div class="wechat-register-link">
              <span class="wechat-register-text">首次使用？</span>
              <a href="javascript:void(0)" class="wechat-register-a" @click="handleWechatLogin">企业微信扫码注册</a>
            </div>
          </div>
        </el-form-item>
        <el-form-item v-else class="wechat-row wechat-unconfigured">
          <p class="wechat-unconfigured-tip">
            企业微信登录：需管理员在系统后台配置企业微信应用（WECHAT_CORP_ID、应用密钥、回调地址等）后，此处才会显示「企业微信扫码登录」入口；扫码在跳转后的企业微信页面进行。
          </p>
        </el-form-item>
        <el-form-item class="link-row">
          <a href="javascript:void(0)" class="register-link" @click="showChangePasswordDialog = true">修改密码</a>
          <span class="link-sep">|</span>
          <router-link to="/register" class="register-link">没有账号？账号密码注册</router-link>
        </el-form-item>
        <!-- iframe 移动端：用全屏面板替代 el-dialog，与页面同缩放、可滚动、关闭可靠 -->
        <div
          v-if="isIframeMobile && showChangePasswordDialog"
          class="change-password-mobile-panel"
          role="dialog"
          aria-label="修改密码"
        >
          <header class="change-password-mobile-header">
            <h2 class="change-password-mobile-title">修改密码</h2>
            <button
              type="button"
              class="change-password-mobile-close"
              aria-label="关闭"
              @click="closeChangePasswordPanel"
            >
              关闭
            </button>
          </header>
          <div class="change-password-mobile-body">
            <el-form
              ref="changePwdFormRef"
              :model="changePwdForm"
              :rules="changePwdRules"
              label-width="80px"
              class="change-password-mobile-form"
              @submit.prevent="handleChangePasswordSubmit"
            >
              <el-form-item label="账号" prop="username">
                <el-input
                  v-model="changePwdForm.username"
                  placeholder="请输入账号"
                  maxlength="64"
                  show-word-limit
                  clearable
                />
              </el-form-item>
              <el-form-item label="旧密码" prop="old_password">
                <el-input
                  v-model="changePwdForm.old_password"
                  type="password"
                  placeholder="请输入旧密码"
                  maxlength="72"
                  show-password
                  clearable
                />
              </el-form-item>
              <el-form-item label="新密码" prop="new_password">
                <el-input
                  v-model="changePwdForm.new_password"
                  type="password"
                  placeholder="至少 6 位"
                  maxlength="72"
                  show-password
                  clearable
                />
              </el-form-item>
              <el-form-item label="确认新密码" prop="confirm_password">
                <el-input
                  v-model="changePwdForm.confirm_password"
                  type="password"
                  placeholder="请再次输入新密码"
                  maxlength="72"
                  show-password
                  clearable
                />
              </el-form-item>
            </el-form>
          </div>
          <footer class="change-password-mobile-footer">
            <el-button type="button" class="change-password-mobile-btn-cancel" @click="closeChangePasswordPanel">
              取消
            </el-button>
            <el-button
              type="primary"
              :loading="changePwdLoading"
              class="change-password-mobile-btn-submit"
              @click="handleChangePasswordSubmit"
            >
              确认修改
            </el-button>
          </footer>
        </div>
        <!-- PC：使用 el-dialog -->
        <el-dialog
          v-if="!isIframeMobile"
          v-model="showChangePasswordDialog"
          title="修改密码"
          width="400px"
          :close-on-click-modal="false"
          class="change-password-dialog login-page-dialog"
          @closed="onChangePasswordDialogClosed"
        >
          <el-form
            ref="changePwdFormRef"
            :model="changePwdForm"
            :rules="changePwdRules"
            label-width="80px"
            @submit.prevent="handleChangePasswordSubmit"
          >
            <el-form-item label="账号" prop="username">
              <el-input
                v-model="changePwdForm.username"
                placeholder="请输入账号"
                maxlength="64"
                show-word-limit
                clearable
              />
            </el-form-item>
            <el-form-item label="旧密码" prop="old_password">
              <el-input
                v-model="changePwdForm.old_password"
                type="password"
                placeholder="请输入旧密码"
                maxlength="72"
                show-password
                clearable
              />
            </el-form-item>
            <el-form-item label="新密码" prop="new_password">
              <el-input
                v-model="changePwdForm.new_password"
                type="password"
                placeholder="至少 6 位"
                maxlength="72"
                show-password
                clearable
              />
            </el-form-item>
            <el-form-item label="确认新密码" prop="confirm_password">
              <el-input
                v-model="changePwdForm.confirm_password"
                type="password"
                placeholder="请再次输入新密码"
                maxlength="72"
                show-password
                clearable
              />
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button type="button" @click="showChangePasswordDialog = false">取消</el-button>
            <el-button type="primary" :loading="changePwdLoading" @click="handleChangePasswordSubmit">
              确认修改
            </el-button>
          </template>
        </el-dialog>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { defaultPathForUser } from '@/utils/defaultPath'
import { wechatApi } from '@/api/wechat'
import { ssoApi } from '@/api/sso.ts'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const formRef = ref<FormInstance>()
const changePwdFormRef = ref<FormInstance>()
const loading = ref(false)
const wechatLoading = ref(false)
const wechatAuthUrl = ref('')
const ssoEnabled = ref(false)
const ssoLoading = ref(false)
const showChangePasswordDialog = ref(false)
const changePwdLoading = ref(false)
const isIframeMobile = ref(false)
const form = reactive({ username: '', password: '' })
const changePwdForm = reactive({
  username: '',
  old_password: '',
  new_password: '',
  confirm_password: '',
})

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { max: 64, message: '用户名不能超过 64 个字符', trigger: 'blur' },
    {
      pattern: /^[a-zA-Z0-9_\u4e00-\u9fa5]+$/,
      message: '用户名仅允许字母、数字、下划线或中文',
      trigger: 'blur',
    },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { max: 72, message: '密码不能超过 72 个字符', trigger: 'blur' },
  ],
}

const validateConfirmPassword = (_rule: unknown, value: string, callback: (err?: Error) => void) => {
  if (value !== changePwdForm.new_password) {
    callback(new Error('两次输入的新密码不一致'))
  } else {
    callback()
  }
}
const changePwdRules: FormRules = {
  username: [
    { required: true, message: '请输入账号', trigger: 'blur' },
    { max: 64, message: '账号不能超过 64 个字符', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_\u4e00-\u9fa5]+$/, message: '账号仅允许字母、数字、下划线或中文', trigger: 'blur' },
  ],
  old_password: [{ required: true, message: '请输入旧密码', trigger: 'blur' }, { max: 72, message: '密码不能超过 72 个字符', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '新密码至少 6 位', trigger: 'blur' },
    { max: 72, message: '密码不能超过 72 个字符', trigger: 'blur' },
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' },
  ],
}

const wechatErrorMessages: Record<string, string> = {
  not_configured: '企业微信未配置，无法扫码登录',
  no_code: '企业微信授权未返回 code',
  token_fail: '获取企业微信 access_token 失败',
  userinfo_fail: '获取企业微信用户信息失败',
  no_userid: '企业微信未返回用户标识',
  exception: '企业微信登录异常，请稍后重试',
}

async function fetchSsoStatus() {
  try {
    const res = await ssoApi.getStatus()
    ssoEnabled.value = res?.sso_enabled === true
  } catch {
    ssoEnabled.value = false
  }
}

async function handleSsoLogin(wechat: boolean) {
  ssoLoading.value = true
  try {
    const res = await ssoApi.getSsoUrl(wechat)
    const url = (res?.url || '').trim()
    if (url) {
      window.location.href = url
      return
    }
    ElMessage.warning('SSO 未配置或不可用')
  } catch {
    ElMessage.error('获取 SSO 登录链接失败')
  } finally {
    ssoLoading.value = false
  }
}

async function fetchWechatAuthUrl() {
  try {
    const res = await wechatApi.getAuthUrl()
    wechatAuthUrl.value = (res?.url || '').trim()
  } catch {
    wechatAuthUrl.value = ''
  }
}

async function handleWechatLogin() {
  if (!wechatAuthUrl.value) {
    ElMessage.warning('企业微信未配置或不可用')
    return
  }
  wechatLoading.value = true
  try {
    const res = await wechatApi.getAuthUrl()
    const url = (res?.url || '').trim()
    if (url) {
      window.location.href = url
      return
    }
    ElMessage.warning(res?.message || '企业微信未配置或不可用')
  } catch {
    ElMessage.error('获取企业微信登录链接失败')
  } finally {
    wechatLoading.value = false
  }
}

async function handleSubmit() {
  if (!formRef.value) return
  try {
    await formRef.value.validate()
  } catch {
    return
  }
  loading.value = true
  try {
    const username = String(form.username ?? '').trim()
    const password = String(form.password ?? '')
    await authStore.login(username, password)
    const redirectPath = route.query.redirect as string
    const defaultPath = defaultPathForUser(authStore)
    ElMessage.success({ message: '登录成功', duration: 1500 })
    navigateAfterLogin(redirectPath && redirectPath.startsWith('/') && !redirectPath.startsWith('/login') ? redirectPath : defaultPath)
  } catch (e: any) {
    const data = e?.response?.data
    let msg = '登录失败'
    if (data?.detail != null) {
      msg = Array.isArray(data.detail) ? (data.detail[0]?.msg || String(data.detail)) : String(data.detail)
    } else if (e?.message) {
      msg = e.message
    }
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

function onChangePasswordDialogClosed() {
  changePwdForm.username = ''
  changePwdForm.old_password = ''
  changePwdForm.new_password = ''
  changePwdForm.confirm_password = ''
  changePwdFormRef.value?.resetFields()
}

function closeChangePasswordPanel() {
  showChangePasswordDialog.value = false
  onChangePasswordDialogClosed()
}

async function handleChangePasswordSubmit() {
  if (!changePwdFormRef.value) return
  try {
    await changePwdFormRef.value.validate()
  } catch {
    return
  }
  changePwdLoading.value = true
  try {
    const { authApi } = await import('@/api/auth')
    await authApi.changePasswordFromLogin(
      changePwdForm.username.trim(),
      changePwdForm.old_password,
      changePwdForm.new_password
    )
    ElMessage.success('密码已修改，请使用新密码登录')
    showChangePasswordDialog.value = false
    onChangePasswordDialogClosed()
  } catch (e: any) {
    const data = e?.response?.data
    const msg = data?.detail != null
      ? (Array.isArray(data.detail) ? (data.detail[0]?.msg || String(data.detail)) : String(data.detail))
      : (e?.message || '修改失败')
    ElMessage.error(msg)
  } finally {
    changePwdLoading.value = false
  }
}

/** 判断是否在企业微信内置浏览器中（含 PC 端扫码场景） */
function isWechatWorkBrowser(): boolean {
  const ua = navigator.userAgent.toLowerCase()
  return ua.includes('wxwork')
}

function navigateAfterLogin(targetPath: string) {
  const path = String(targetPath || '').trim()
  if (!path.startsWith('/')) {
    router.replace('/home')
    return
  }
  // 企业微信新媒体 iframe 场景下，整页跳转更稳定，可避免偶发空白页
  if (typeof window !== 'undefined' && window.self !== window.top) {
    const base = (import.meta.env.BASE_URL || '/').replace(/\/+$/, '')
    window.location.replace(`${base}${path}`)
    return
  }
  router.replace(path)
}

onMounted(async () => {
  if (typeof document !== 'undefined' && document.documentElement.classList.contains('iframe-mobile-viewport')) {
    isIframeMobile.value = true
  }
  await Promise.all([fetchSsoStatus(), fetchWechatAuthUrl()])

  const q = route.query as Record<string, string>
  const token = q.token
  const pending = q.pending
  const wechatError = q.wechat_error

  // 企业微信内自动 SSO：无 token、SSO 已启用、未被标记为"返回登录（禁止自动跳转）"
  if (
    !token &&
    !pending &&
    !wechatError &&
    !q.no_auto_sso &&
    ssoEnabled.value &&
    isWechatWorkBrowser() &&
    !localStorage.getItem('access_token')
  ) {
    handleSsoLogin(true)
    return
  }

  if (token) {
    loading.value = true
    try {
      await authStore.loginWithToken(token)
      const redirectPath = route.query.redirect as string
      const defaultPath = defaultPathForUser(authStore)
      ElMessage.success({ message: '登录成功', duration: 1500 })
      navigateAfterLogin(redirectPath && redirectPath.startsWith('/') && !redirectPath.startsWith('/login') ? redirectPath : defaultPath)
    } catch (e: any) {
      ElMessage.error(e?.message || e?.response?.data?.detail || '登录失败')
      router.replace('/login')
    } finally {
      loading.value = false
    }
    return
  }

  if (pending) {
    ElMessage.info('您的注册申请待管理员审批，请等待审批通过后再登录。')
    router.replace('/login')
    return
  }

  if (wechatError) {
    const msg = wechatErrorMessages[wechatError] || `企业微信登录失败：${wechatError}`
    ElMessage.error(msg)
    router.replace('/login')
  }
})
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  background: linear-gradient(145deg, #0f2744 0%, #1a3d5c 35%, #256391 100%);
}

.login-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.login-bg-shape {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.25;
}

.login-bg-shape.shape-1 {
  width: 400px;
  height: 400px;
  background: linear-gradient(135deg, #4a9fd4, #2d7ab8);
  top: -120px;
  right: -80px;
}

.login-bg-shape.shape-2 {
  width: 320px;
  height: 320px;
  background: linear-gradient(135deg, #5eb8a8, #2d8a7a);
  bottom: -60px;
  left: -100px;
}

.login-bg-shape.shape-3 {
  width: 200px;
  height: 200px;
  background: linear-gradient(135deg, #7b68c4, #5a4a9a);
  top: 50%;
  left: 15%;
  opacity: 0.15;
}

.login-card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 420px;
  padding: 44px 40px 36px;
  background: rgba(255, 255, 255, 0.98);
  border-radius: 20px;
  box-shadow:
    0 25px 50px -12px rgba(0, 0, 0, 0.35),
    0 0 0 1px rgba(255, 255, 255, 0.1) inset;
  backdrop-filter: blur(12px);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-logo {
  width: 56px;
  height: 56px;
  margin: 0 auto 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1e5f8a 0%, #2d7ab8 100%);
  border-radius: 14px;
  box-shadow: 0 8px 20px rgba(30, 95, 138, 0.4);
}

.logo-icon {
  font-size: 26px;
  color: #fff;
  font-weight: 300;
  letter-spacing: -1px;
}

.login-title {
  margin: 0 0 6px;
  font-size: 24px;
  font-weight: 600;
  color: #1a2d42;
  letter-spacing: 0.5px;
}

.login-subtitle {
  margin: 0;
  font-size: 13px;
  color: #6b7c8f;
  font-weight: 400;
  letter-spacing: 0.5px;
}

.login-form :deep(.el-form-item) {
  margin-bottom: 20px;
}

.login-form :deep(.login-input .el-input__wrapper) {
  border-radius: 12px;
  padding: 4px 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  transition: box-shadow 0.2s, border-color 0.2s;
}

.login-form :deep(.login-input .el-input__wrapper:hover),
.login-form :deep(.login-input:focus-within .el-input__wrapper) {
  box-shadow: 0 0 0 2px rgba(45, 122, 184, 0.25);
}

.submit-item {
  margin-top: 28px;
  margin-bottom: 24px;
}

.submit-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
  font-weight: 500;
  letter-spacing: 2px;
  border-radius: 12px;
  box-shadow: 0 4px 14px rgba(30, 95, 138, 0.35);
  transition: transform 0.15s, box-shadow 0.2s;
}

.submit-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(30, 95, 138, 0.4);
}

.submit-btn:active {
  transform: translateY(0);
}

.login-divider {
  width: 100%;
  display: flex;
  align-items: center;
  margin: 8px 0 20px;
  color: #a0aec0;
  font-size: 13px;
}

.login-divider::before,
.login-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, transparent, #e2e8f0, transparent);
}

.login-divider span {
  padding: 0 14px;
}

.wechat-row {
  margin-bottom: 0;
}

.wechat-section {
  width: 100%;
}

.wechat-scan-tip {
  margin: 0 0 14px;
  padding: 12px 14px;
  font-size: 13px;
  color: #4a5568;
  line-height: 1.55;
  background: linear-gradient(135deg, #f0fdf4 0%, #ecfdf5 100%);
  border-radius: 12px;
  border: 1px solid rgba(34, 197, 94, 0.2);
}

.wechat-scan-tip strong {
  color: #166534;
}

.wechat-btn {
  width: 100%;
  height: 44px;
  border-radius: 12px;
  font-weight: 500;
  transition: transform 0.15s, box-shadow 0.2s;
}

.wechat-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(34, 197, 94, 0.3);
}

.sso-account-btn {
  width: 100%;
  height: 44px;
  border-radius: 12px;
  font-weight: 500;
  margin-top: 10px;
  margin-left: 0 !important;
  transition: transform 0.15s, box-shadow 0.2s;
}

.sso-account-btn:hover {
  transform: translateY(-1px);
}

.wechat-hint {
  margin: 10px 0 6px;
  font-size: 12px;
  color: #718096;
  line-height: 1.45;
}

.wechat-unconfigured-tip {
  margin: 0;
  padding: 12px 14px;
  font-size: 12px;
  color: #718096;
  line-height: 1.55;
  background: #f7fafc;
  border-radius: 12px;
  border: 1px dashed #cbd5e0;
}

.wechat-register-link {
  font-size: 13px;
  color: #4a5568;
}

.wechat-register-a {
  color: #2d7ab8;
  text-decoration: none;
  margin-left: 6px;
  font-weight: 500;
}

.wechat-register-a:hover {
  text-decoration: underline;
  color: #1e5f8a;
}

.link-row {
  margin-bottom: 0;
  margin-top: 20px;
  text-align: center;
}

.link-row .register-link {
  color: #2d7ab8;
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: color 0.2s;
}

.link-row .register-link:hover {
  color: #1e5f8a;
  text-decoration: underline;
}

.link-sep {
  margin: 0 10px;
  color: #cbd5e0;
  font-size: 13px;
}

/* iframe 移动端：修改密码全屏面板（与页面同缩放，可滚动，关闭可靠） */
.change-password-mobile-panel {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  flex-direction: column;
  background: #fff;
  box-sizing: border-box;
  width: 100%;
  max-width: 100%;
  overflow: hidden;
}

.change-password-mobile-header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid #e5e7eb;
  background: #f9fafb;
}

.change-password-mobile-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1a2d42;
}

.change-password-mobile-close {
  padding: 8px 14px;
  font-size: 15px;
  color: #2d7ab8;
  background: transparent;
  border: 1px solid #2d7ab8;
  border-radius: 8px;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  min-height: 44px;
  box-sizing: border-box;
}

.change-password-mobile-close:active {
  background: rgba(45, 122, 184, 0.1);
}

.change-password-mobile-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  padding: 20px 16px;
}

.change-password-mobile-form :deep(.el-form-item) {
  margin-bottom: 18px;
}

.change-password-mobile-form :deep(.el-input) {
  max-width: 100%;
}

.change-password-mobile-footer {
  flex-shrink: 0;
  display: flex;
  gap: 12px;
  padding: 16px;
  border-top: 1px solid #e5e7eb;
  background: #fff;
}

.change-password-mobile-btn-cancel {
  flex: 1;
  min-height: 44px;
  font-size: 16px;
}

.change-password-mobile-btn-submit {
  flex: 1;
  min-height: 44px;
  font-size: 16px;
}
</style>
