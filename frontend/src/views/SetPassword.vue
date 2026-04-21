<template>
  <div class="set-password-page">
    <div class="set-password-card">
      <h1 class="title">设置登录密码</h1>
      <p class="subtitle">请设置您的新密码，设置成功后请使用新密码登录</p>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="0"
        class="form"
        @submit.prevent="handleSubmit"
      >
        <el-form-item prop="newPassword">
          <el-input
            v-model="form.newPassword"
            type="password"
            placeholder="新密码（至少 6 位）"
            size="large"
            show-password
            maxlength="72"
            @keyup.enter="handleSubmit"
          />
        </el-form-item>
        <el-form-item prop="confirmPassword">
          <el-input
            v-model="form.confirmPassword"
            type="password"
            placeholder="再次输入新密码"
            size="large"
            show-password
            maxlength="72"
            @keyup.enter="handleSubmit"
          />
        </el-form-item>
        <el-form-item class="submit-item">
          <el-button type="primary" size="large" :loading="loading" class="submit-btn" @click="handleSubmit">
            确认设置
          </el-button>
        </el-form-item>
      </el-form>
      <p v-if="errorMsg" class="error-msg">{{ errorMsg }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { authApi } from '@/api/auth'

const route = useRoute()
const router = useRouter()

const token = ref('')
const formRef = ref<FormInstance>()
const loading = ref(false)
const errorMsg = ref('')

const form = reactive({
  newPassword: '',
  confirmPassword: '',
})

const validateConfirm = (_rule: unknown, value: string, callback: (e?: Error) => void) => {
  if (value !== form.newPassword) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules: FormRules = {
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码至少 6 位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    { validator: validateConfirm, trigger: 'blur' },
  ],
}

onMounted(() => {
  const t = route.query.token
  token.value = typeof t === 'string' ? t : ''
  if (!token.value) {
    errorMsg.value = '缺少设置密码链接参数，请向管理员获取正确链接'
  }
})

async function handleSubmit() {
  if (!token.value) return
  await formRef.value?.validate().catch(() => {})
  loading.value = true
  errorMsg.value = ''
  try {
    await authApi.setPasswordByToken(token.value, form.newPassword)
    ElMessage.success('密码设置成功，请使用新密码登录')
    router.replace({ path: '/login' })
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    errorMsg.value = typeof detail === 'string' ? detail : '设置失败，链接可能已过期'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped lang="scss">
.set-password-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
}

.set-password-card {
  width: 100%;
  max-width: 400px;
  padding: 32px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

.title {
  margin: 0 0 8px;
  font-size: 22px;
  color: #303133;
  text-align: center;
}

.subtitle {
  margin: 0 0 24px;
  font-size: 14px;
  color: #909399;
  text-align: center;
}

.form :deep(.el-input) {
  width: 100%;
}

.submit-item {
  margin-bottom: 0;
  margin-top: 8px;
}

.submit-btn {
  width: 100%;
}

.error-msg {
  margin: 16px 0 0;
  font-size: 14px;
  color: var(--el-color-danger);
  text-align: center;
}
</style>
