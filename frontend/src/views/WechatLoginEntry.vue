<template>
  <div class="wechat-entry-page">
    <div class="wechat-entry-card">
      <div v-if="error" class="wechat-entry-error">
        <el-icon :size="48" color="#e53e3e"><CircleCloseFilled /></el-icon>
        <h2>无法跳转</h2>
        <p class="error-msg">{{ error }}</p>
        <el-button type="primary" @click="goLogin">前往登录页</el-button>
      </div>
      <div v-else class="wechat-entry-loading">
        <el-icon :size="48" color="#07c160" class="spin-icon"><Loading /></el-icon>
        <h2>正在跳转到企业微信授权</h2>
        <p>请稍候，即将进入统一认证...</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Loading, CircleCloseFilled } from '@element-plus/icons-vue'
import { ssoApi } from '@/api/sso'
import { useAuthStore } from '@/stores/auth'
import { defaultPathForUser } from '@/utils/defaultPath'

const router = useRouter()
const authStore = useAuthStore()
const error = ref('')

function goLogin() {
  router.replace('/login')
}

onMounted(async () => {
  // 已登录用户直接进入系统
  const token = authStore.token ?? localStorage.getItem('access_token')
  if (token && authStore.user) {
    router.replace(defaultPathForUser(authStore))
    return
  }
  if (token && !authStore.user) {
    try {
      await authStore.fetchUser()
      if (authStore.user) {
        router.replace(defaultPathForUser(authStore))
        return
      }
    } catch {
      // token 无效，继续走 SSO 流程
    }
  }

  try {
    const statusRes = await ssoApi.getStatus()
    if (!statusRes?.sso_enabled) {
      error.value = '当前未启用企业微信登录，请使用账号密码登录。'
      return
    }
    const urlRes = await ssoApi.getSsoUrl(true)
    if (urlRes?.url) {
      window.location.href = urlRes.url
      return
    }
    error.value = '获取授权链接失败，请稍后重试或前往登录页。'
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    error.value = typeof detail === 'string' ? detail : '网络异常，请检查配置后重试或前往登录页。'
  }
})
</script>

<style scoped>
.wechat-entry-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(145deg, #0f2744 0%, #1a3d5c 35%, #256391 100%);
}

.wechat-entry-card {
  width: 100%;
  max-width: 420px;
  padding: 48px 40px;
  background: rgba(255, 255, 255, 0.98);
  border-radius: 20px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.35);
  text-align: center;
}

.wechat-entry-loading h2,
.wechat-entry-error h2 {
  margin: 20px 0 8px;
  font-size: 20px;
  color: #1a2d42;
}

.wechat-entry-loading p,
.wechat-entry-error p {
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
