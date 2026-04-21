<template>
  <div class="navbar">
    <div class="navbar-left">
      <el-icon
        v-if="isMobile"
        class="hamburger"
        :size="20"
        @click="$emit('toggle-sidebar')"
      >
        <Menu />
      </el-icon>
      <el-breadcrumb separator="/">
        <el-breadcrumb-item
          v-for="item in breadcrumbs"
          :key="item.path"
          :class="{ 'is-active': item.active }"
          class="breadcrumb-item"
        >
          {{ item.title }}
        </el-breadcrumb-item>
      </el-breadcrumb>
    </div>
    <div class="navbar-right">
      <el-button
        v-if="isMobile && showSearch"
        :icon="Search"
        circle
        size="small"
        @click="openMobileSearch = true"
      />
      <el-dropdown trigger="click" @command="handleCommand">
        <div class="user-dropdown">
          <div class="user-avatar">{{ avatarText }}</div>
          <span v-if="!isMobile" class="user-name">{{ displayName }}</span>
          <el-icon><ArrowDown /></el-icon>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item disabled>
              {{ displayName }}（{{ roleLabel }}）
            </el-dropdown-item>
            <el-dropdown-item divided v-if="wechatBindAvailable" command="bind-wechat">
              绑定企业微信
            </el-dropdown-item>
            <el-dropdown-item divided command="logout">
              <el-icon><SwitchButton /></el-icon>退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, inject } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Menu, Search, ArrowDown, SwitchButton } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { useIsMobile } from '@/composables/useIsMobile'
import { ROLE_LABELS } from '@/api/user'
import { wechatApi } from '@/api/wechat'

defineEmits<{ 'toggle-sidebar': [] }>()

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const { isMobile } = useIsMobile()
const wechatBindAvailable = ref(false)
const openMobileSearch = inject<import('vue').Ref<boolean>>('openMobileSearch', ref(false))

const SEARCH_ROUTES = [
  '/electrical/requisition', '/electrical/parts', '/electrical/inventory', '/electrical/operation-logs',
  '/mechanical/requisition', '/mechanical/parts', '/mechanical/inventory', '/mechanical/operation-logs',
]
const showSearch = computed(() => isMobile.value && SEARCH_ROUTES.some(p => route.path === p))

const displayName = computed(() => authStore.user?.real_name || authStore.user?.username || '')
const avatarText = computed(() => displayName.value.charAt(0).toUpperCase())
const roleLabel = computed(() => ROLE_LABELS[authStore.user?.role ?? ''] ?? authStore.user?.role ?? '')

const TITLE_MAP: Record<string, string> = {
  '/home': '首页',
  '/electrical/parts': '电气设备',
  '/electrical/requisition': '电气领用',
  '/electrical/inventory': '库存管理',
  '/electrical/operation-logs': '记录查询',
  '/electrical/users': '用户管理',
  '/electrical/reports': '报表统计',
  '/mechanical/parts': '机械设备',
  '/mechanical/requisition': '机械领用',
  '/mechanical/inventory': '库存管理',
  '/mechanical/operation-logs': '记录查询',
  '/mechanical/users': '用户管理',
  '/mechanical/reports': '报表统计',
}

const MODULE_MAP: Record<string, string> = {
  electrical: '电气模块',
  mechanical: '机械模块',
}

const breadcrumbs = computed(() => {
  const path = route.path
  const items: Array<{ path: string; title: string; active: boolean }> = []

  if (path === '/home') {
    items.push({ path: '/home', title: '首页', active: true })
    return items
  }

  items.push({ path: '/home', title: '首页', active: false })

  const segments = path.split('/').filter(Boolean)
  if (segments.length >= 1 && MODULE_MAP[segments[0]]) {
    items.push({ path: `/${segments[0]}`, title: MODULE_MAP[segments[0]], active: false })
  }

  const pageTitle = TITLE_MAP[path]
  if (pageTitle) {
    items.push({ path, title: pageTitle, active: true })
  }

  return items
})

async function handleCommand(command: string) {
  if (command === 'logout') {
    try {
      await ElMessageBox.confirm('确定退出登录吗？', '提示', {
        type: 'warning',
        confirmButtonText: '确定',
        cancelButtonText: '取消',
      })
      authStore.logout()
      router.replace('/login')
    } catch {
      // cancelled
    }
  } else if (command === 'bind-wechat') {
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
}

onMounted(async () => {
  try {
    const res = await wechatApi.getBindAuthUrl()
    wechatBindAvailable.value = !!(res?.url && res.url.trim())
  } catch {
    wechatBindAvailable.value = false
  }
})
</script>

<style scoped>
.hamburger {
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: background 0.2s;
}
.hamburger:hover {
  background: var(--el-fill-color-light);
}
</style>
