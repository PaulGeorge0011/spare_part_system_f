<template>
  <div class="register-page">
    <div class="register-card">
      <h1>用户注册</h1>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="0"
        class="register-form"
        @submit.prevent="handleSubmit"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="用户名（2-64 字符）"
            size="large"
            prefix-icon="User"
          />
        </el-form-item>
        <el-form-item prop="realName">
          <el-input
            v-model="form.realName"
            placeholder="真实姓名（必填）"
            size="large"
            prefix-icon="User"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码（至少 6 位）"
            size="large"
            show-password
            prefix-icon="Lock"
          />
        </el-form-item>
        <el-form-item prop="confirmPassword">
          <el-input
            v-model="form.confirmPassword"
            type="password"
            placeholder="确认密码"
            size="large"
            show-password
            prefix-icon="Lock"
            @keyup.enter="handleSubmit"
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            class="submit-btn"
            @click="handleSubmit"
          >
            注册
          </el-button>
        </el-form-item>
        <el-form-item class="link-row">
          <router-link to="/login">已有账号？去登录</router-link>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { authApi } from '@/api/auth'

const router = useRouter()
const formRef = ref<FormInstance>()
const loading = ref(false)
const form = reactive({
  username: '',
  realName: '',
  password: '',
  confirmPassword: '',
})

const validateConfirm = (_rule: unknown, value: string, callback: (e?: Error) => void) => {
  if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 2, max: 64, message: '用户名 2-64 字符', trigger: 'blur' },
  ],
  realName: [
    { required: true, message: '请输入真实姓名', trigger: 'blur' },
    { min: 1, max: 100, message: '真实姓名 1-100 字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, max: 72, message: '密码至少 6 位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    { validator: validateConfirm, trigger: 'blur' },
  ],
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
    await authApi.register(form.username.trim(), form.realName.trim(), form.password)
    ElMessage.success('注册成功，请等待管理员审核通过后再登录')
    router.replace('/login')
  } catch (e: any) {
    const msg = e?.response?.data?.detail || '注册失败'
    ElMessage.error(typeof msg === 'string' ? msg : '注册失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.register-page {
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
  box-sizing: border-box;
}

.register-card {
  width: 380px;
  max-width: 100%;
  padding: 40px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
  box-sizing: border-box;
}

.register-card h1 {
  margin: 0 0 28px;
  font-size: 22px;
  text-align: center;
  color: #1e3a5f;
}

.register-form :deep(.el-form-item) {
  margin-bottom: 20px;
}

.submit-btn {
  width: 100%;
}

.link-row {
  margin-bottom: 0;
  text-align: center;
}

.link-row a {
  color: var(--el-color-primary);
  text-decoration: none;
}

.link-row a:hover {
  text-decoration: underline;
}

@media (max-width: 767px) {
  .register-page {
    padding: 20px 16px 32px;
    align-items: flex-start;
    justify-content: flex-start;
    min-height: 100%;
  }
  .register-card {
    width: 100%;
    max-width: 100%;
    padding: 28px 20px;
    box-sizing: border-box;
    margin: 0 auto;
  }
}
</style>
