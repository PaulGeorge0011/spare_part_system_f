<template>
  <div class="sso-callback-page">
    <div class="sso-callback-card">
      <div v-if="error" class="sso-error">
        <el-icon :size="48" color="#e53e3e"><CircleCloseFilled /></el-icon>
        <h2>登录失败</h2>
        <p class="error-msg">{{ error }}</p>
        <el-button type="primary" size="large" @click="goLogin">返回登录</el-button>
      </div>
      <div v-else class="sso-loading">
        <el-icon :size="48" color="#2d7ab8" class="spin-icon"><Loading /></el-icon>
        <h2>正在登录...</h2>
        <p>正在通过单点登录系统验证身份，请稍候</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Loading, CircleCloseFilled } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { defaultPathForUser } from '@/utils/defaultPath'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const error = ref('')

function goLogin() {
  // 带上 no_auto_sso=1，防止在企业微信内再次自动触发 SSO 造成死循环
  router.replace('/login?no_auto_sso=1')
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
  const code = route.query.code as string
  const sessionState = route.query.session_state as string

  if (!code) {
    error.value = 'SSO 授权未返回 code 参数'
    return
  }

  try {
    await authStore.ssoLogin(code, sessionState || '')
    const redirectPath = route.query.redirect as string
    const defaultPath = defaultPathForUser(authStore)
    ElMessage.success({ message: '登录成功', duration: 1500 })
    navigateAfterLogin(
      redirectPath && redirectPath.startsWith('/') && !redirectPath.startsWith('/login') && !redirectPath.startsWith('/sso')
        ? redirectPath
        : defaultPath
    )
  } catch (e: any) {
    const data = e?.response?.data
    let msg = 'SSO 登录失败'
    if (data?.detail != null) {
      msg = Array.isArray(data.detail) ? (data.detail[0]?.msg || String(data.detail)) : String(data.detail)
    } else if (e?.message) {
      msg = e.message
    }
    error.value = msg
    ElMessage.error(msg)
  }
})
</script>

<style scoped>
.sso-callback-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(145deg, #0f2744 0%, #1a3d5c 35%, #256391 100%);
}

.sso-callback-card {
  width: 100%;
  max-width: 420px;
  padding: 48px 40px;
  background: rgba(255, 255, 255, 0.98);
  border-radius: 20px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.35);
  text-align: center;
}

.sso-loading h2,
.sso-error h2 {
  margin: 20px 0 8px;
  font-size: 20px;
  color: #1a2d42;
}

.sso-loading p,
.sso-error p {
  margin: 0 0 24px;
  font-size: 14px;
  color: #6b7c8f;
}

.error-msg {
  color: #e53e3e !important;
  font-weight: 500;
}

.spin-icon {
  animation: spin 1.2s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
