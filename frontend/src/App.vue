<template>
  <div id="app">
    <template v-if="isAuthPage">
      <router-view />
    </template>
    <template v-else>
      <Layout />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, watch, provide } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import Layout from '@/layout/index.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const openMobileSearch = ref(false)
provide('openMobileSearch', openMobileSearch)

const isAuthPage = computed(
  () =>
    route.path === '/login' ||
    route.path === '/register' ||
    route.path === '/set-password' ||
    route.path === '/sso/callback' ||
    route.path === '/wechat-login',
)

function checkWechatBindQuery() {
  const q = route.query as Record<string, string>
  const bind = q.wechat_bind
  if (bind === 'success') {
    ElMessage.success('企业微信绑定成功')
    router.replace({ path: route.path, query: {} })
  } else if (bind === 'already_used') {
    ElMessage.warning('该企业微信已绑定其他账号，无法重复绑定')
    router.replace({ path: route.path, query: {} })
  } else if (bind === 'expired') {
    ElMessage.warning('绑定链接已过期，请重新点击「绑定企业微信」')
    router.replace({ path: route.path, query: {} })
  }
}

onMounted(() => checkWechatBindQuery())
watch(() => route.query, () => checkWechatBindQuery(), { deep: true })
</script>

<style>
#app {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
    'Helvetica Neue', Arial, 'Noto Sans', sans-serif;
  height: 100vh;
  overflow: hidden;
}

/* 移动端搜索抽屉统一样式 */
.mobile-search-drawer-unified .el-drawer__body {
  padding: 20px;
  padding-left: calc(20px + env(safe-area-inset-left, 0));
  padding-right: calc(20px + env(safe-area-inset-right, 0));
  padding-bottom: calc(28px + env(safe-area-inset-bottom, 0));
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  font-size: 15px;
  line-height: 1.5;
  color: #334155;
}
.mobile-search-drawer-unified .el-drawer__header {
  padding: 16px 20px 12px;
  margin-bottom: 4px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.mobile-search-drawer-unified .el-drawer__header .el-drawer__title {
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
}
.mobile-search-drawer-unified .filter-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 20px;
}
.mobile-search-drawer-unified .filter-label {
  font-size: 15px;
  font-weight: 600;
  color: #334155;
}
.mobile-search-drawer-unified .filter-actions {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--el-border-color-lighter);
  gap: 12px;
}
.mobile-search-drawer-unified .el-input__wrapper,
.mobile-search-drawer-unified .el-select .el-select__wrapper {
  min-height: 44px;
  padding: 8px 14px;
  font-size: 16px;
  border-radius: 10px;
}
</style>
