<template>
  <div id="app" :class="{ 'app-logged-in': !isLoginPage }">
    <template v-if="!isLoginPage">
      <el-container class="app-container">
        <el-header>
          <div class="header-content">
            <div class="header-left">
              <el-button
                v-if="isMobile"
                class="menu-btn"
                :icon="Menu"
                circle
                @click="drawerVisible = true"
              />
              <h1>制丝二设备管理系统</h1>
            </div>
            <!-- PC 端：横向菜单 + 用户区 -->
            <div v-show="!isMobile" class="header-nav">
              <el-menu mode="horizontal" :router="true" :ellipsis="false" :default-active="currentSystem">
                <el-menu-item index="/home">首页</el-menu-item>
                <el-menu-item v-if="authStore.hasElectricalScope" index="/electrical">电气制丝二设备管理系统</el-menu-item>
                <el-menu-item v-if="authStore.hasMechanicalScope" index="/mechanical">机械制丝二设备管理系统</el-menu-item>
              </el-menu>
              <div class="user-area">
                <span class="user-name">{{ authStore.user?.username }}（{{ roleLabel }}）</span>
                <el-button v-if="wechatBindAvailable" type="success" link @click="handleBindWechat">绑定企业微信</el-button>
                <el-button type="danger" link @click="handleLogout">退出登录</el-button>
              </div>
            </div>
            <!-- 移动端：搜索按钮（与菜单同级）+ 用户快捷，搜索在用户名左侧 -->
            <div v-if="isMobile" class="header-right-mobile">
              <el-button
                v-if="showMobileSearch"
                class="search-btn"
                :icon="Search"
                circle
                aria-label="打开搜索"
                @click="openMobileSearch = true"
              />
              <div class="user-area-mobile">
                <span class="user-name">{{ authStore.user?.username }}</span>
                <el-button type="danger" link size="small" @click="handleLogout">退出</el-button>
              </div>
            </div>
          </div>
        </el-header>
        <el-main class="app-main">
          <router-view v-slot="{ Component, route }">
            <Transition name="layout-fade" mode="out-in">
              <keep-alive :include="cachedLayouts" :max="3">
                <component :is="Component" :key="route.matched[0]?.path || route.path" class="main-view" />
              </keep-alive>
            </Transition>
          </router-view>
        </el-main>
      </el-container>

      <!-- 移动端侧边菜单抽屉：收纳所有页面流转入口，扩大内容区；append-to-body 便于 iframe 内不随 zoom 放大、遮罩可点关闭 -->
      <el-drawer
        v-model="drawerVisible"
        title="菜单"
        direction="ltr"
        size="280px"
        :with-header="true"
        append-to-body
        modal-class="app-menu-drawer-overlay"
        @close="drawerVisible = false"
      >
        <div class="drawer-body">
        <el-menu
          mode="vertical"
          :router="true"
          :default-active="route.path"
          class="drawer-menu"
          @select="drawerVisible = false"
        >
          <el-menu-item index="/home">🏠 首页</el-menu-item>
          <template v-if="authStore.hasElectricalScope">
            <el-menu-item disabled index="__electrical__" class="drawer-menu-group">电气</el-menu-item>
            <el-menu-item v-if="!authStore.isElectricalClerk" index="/electrical/parts">电气设备</el-menu-item>
            <el-menu-item index="/electrical/requisition">电气领用</el-menu-item>
            <el-menu-item v-if="authStore.canManageElectrical || authStore.isElectricalClerk" index="/electrical/inventory">库存管理</el-menu-item>
            <el-menu-item v-if="!authStore.isElectricalClerk" index="/electrical/operation-logs">记录查询</el-menu-item>
            <el-menu-item v-if="authStore.canManageElectrical" index="/electrical/users">用户管理</el-menu-item>
            <el-menu-item index="/electrical/reports">报表统计</el-menu-item>
          </template>
          <template v-if="authStore.hasMechanicalScope">
            <el-menu-item disabled index="__mechanical__" class="drawer-menu-group">机械</el-menu-item>
            <el-menu-item v-if="!authStore.isMechanicalClerk" index="/mechanical/parts">机械设备</el-menu-item>
            <el-menu-item index="/mechanical/requisition">机械领用</el-menu-item>
            <el-menu-item v-if="authStore.canManageMechanical || authStore.isMechanicalClerk" index="/mechanical/inventory">库存管理</el-menu-item>
            <el-menu-item v-if="!authStore.isMechanicalClerk" index="/mechanical/operation-logs">记录查询</el-menu-item>
            <el-menu-item v-if="authStore.canManageMechanical" index="/mechanical/users">用户管理</el-menu-item>
            <el-menu-item index="/mechanical/reports">报表统计</el-menu-item>
          </template>
        </el-menu>
        <div class="drawer-user">
          <p class="drawer-user-name">{{ authStore.user?.username }}（{{ roleLabel }}）</p>
          <el-button v-if="wechatBindAvailable" type="success" plain size="small" block @click="handleBindWechat">绑定企业微信</el-button>
        </div>
        </div>
      </el-drawer>
    </template>
    <template v-else>
      <router-view />
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, watch } from 'vue'
import { Menu, Search } from '@element-plus/icons-vue'
import { provide } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { ROLE_LABELS } from '@/api/user'
import { wechatApi } from '@/api/wechat'
import { useIsMobile } from '@/composables/useIsMobile'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const wechatBindAvailable = ref(false)
const { isMobile } = useIsMobile()
const drawerVisible = ref(false)
/** 移动端顶栏点击搜索时置为 true，由当前页 inject 后打开抽屉并置回 false */
const openMobileSearch = ref(false)
provide('openMobileSearch', openMobileSearch)

/** 带搜索/筛选抽屉的页面：在顶栏显示搜索按钮 */
const SEARCH_ROUTES = [
  '/electrical/requisition', '/electrical/parts', '/electrical/inventory', '/electrical/operation-logs',
  '/mechanical/requisition', '/mechanical/parts', '/mechanical/inventory', '/mechanical/operation-logs'
]
const showMobileSearch = computed(() => isMobile.value && SEARCH_ROUTES.some(p => route.path === p))

const isLoginPage = computed(
  () =>
    route.path === '/login' ||
    route.path === '/register' ||
    route.path === '/set-password' ||
    route.path === '/sso/callback',
)

// 缓存的布局组件名称，实现电气/机械系统间秒切
const cachedLayouts = ['ElectricalLayout', 'MechanicalLayout']

// 当前所在系统，用于高亮顶部菜单
const currentSystem = computed(() => {
  if (route.path.startsWith('/electrical')) return '/electrical'
  if (route.path.startsWith('/mechanical')) return '/mechanical'
  if (route.path === '/home' || route.path === '/') return '/home'
  return '/home'
})

const roleLabel = computed(() => ROLE_LABELS[authStore.user?.role ?? ''] ?? authStore.user?.role ?? '')

async function fetchWechatBindAvailable() {
  try {
    const res = await wechatApi.getBindAuthUrl()
    wechatBindAvailable.value = !!(res?.url && res.url.trim())
  } catch {
    wechatBindAvailable.value = false
  }
}

async function handleBindWechat() {
  drawerVisible.value = false
  try {
    const res = await wechatApi.getBindAuthUrl()
    const url = (res?.url || '').trim()
    if (url) {
      window.location.href = url
      return
    }
    ElMessage.warning('企业微信未配置或不可用')
  } catch (e: any) {
    if (e?.response?.status === 401) {
      authStore.clearAuth()
      router.replace('/login')
      return
    }
    ElMessage.error('获取绑定链接失败')
  }
}

function handleLogout() {
  ElMessageBox.confirm('确定退出登录吗？', '提示', {
    type: 'warning',
    confirmButtonText: '确定',
    cancelButtonText: '取消',
  })
    .then(() => {
      authStore.logout()
      router.replace('/login')
    })
    .catch(() => {})
}

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

onMounted(() => {
  if (!isLoginPage.value) fetchWechatBindAvailable()
  checkWechatBindQuery()
})

watch(() => route.query, () => checkWechatBindQuery(), { deep: true })

// 页面切换时关闭菜单抽屉，避免抽屉内容与当前页不一致
watch(() => route.path, () => {
  drawerVisible.value = false
})
</script>

<style scoped>
#app {
  font-family: Arial, sans-serif;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  height: 56px;
  gap: 12px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.menu-btn {
  flex-shrink: 0;
}

.header-content h1 {
  margin: 0;
  font-size: 18px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header-nav {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 1;
  justify-content: flex-end;
  min-width: 0;
}

.header-nav .el-menu {
  border-bottom: none;
}

.header-nav .el-menu--horizontal > .el-menu-item {
  padding: 0 12px;
}

.user-area {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-right-mobile {
  display: flex;
  align-items: center;
  gap: 8px;
}

.search-btn {
  flex-shrink: 0;
}

.user-area-mobile {
  display: flex;
  align-items: center;
  gap: 8px;
}

.user-name {
  font-size: 14px;
  color: var(--el-text-color-regular);
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.drawer-body {
  display: flex;
  flex-direction: column;
  min-height: 100%;
}

.drawer-user {
  padding: 16px;
  border-top: 1px solid var(--el-border-color-lighter);
  margin-top: auto;
}

.drawer-user-name {
  margin: 0 0 12px;
  font-size: 14px;
  color: var(--el-text-color-regular);
}

.drawer-menu-group {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  cursor: default;
  height: 36px;
  line-height: 36px;
}
.drawer-menu-group:not(.is-disabled) {
  opacity: 1;
}
:deep(.drawer-menu .drawer-menu-group.is-disabled) {
  opacity: 0.85;
  color: var(--el-text-color-secondary);
}

@media (max-width: 767px) {
  .header-content h1 {
    font-size: 16px;
    max-width: 50vw;
  }
  .user-area-mobile .user-name {
    max-width: 80px;
  }
  .el-drawer__header {
    padding-left: calc(16px + env(safe-area-inset-left, 0));
  }
}

/* 登录后主布局：固定视口高度，主内容区内滚动，避免移动端被挤出 */
#app.app-logged-in {
  height: 100vh;
  max-height: 100dvh;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

#app.app-logged-in .app-container {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

#app.app-logged-in .el-main {
  flex: 1;
  min-height: 0;
  overflow: auto;
  -webkit-overflow-scrolling: touch;
}

/* 电气/机械布局切换：淡入淡出 */
.layout-fade-enter-active,
.layout-fade-leave-active {
  transition: opacity 0.1s ease;
}
.layout-fade-enter-from,
.layout-fade-leave-to {
  opacity: 0;
}

</style>

<!-- 移动端搜索抽屉统一样式（非 scoped：抽屉 append-to-body 挂到 body 下） -->
<style>
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
  letter-spacing: 0.01em;
}
.mobile-search-drawer-unified .filter-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 20px;
}
.mobile-search-drawer-unified .filter-group:last-of-type {
  margin-bottom: 0;
}
.mobile-search-drawer-unified .filter-label {
  font-size: 15px;
  font-weight: 600;
  color: #334155;
  line-height: 1.4;
  flex-shrink: 0;
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
