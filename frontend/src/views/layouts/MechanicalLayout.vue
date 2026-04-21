<template>
  <div class="mechanical-layout">
    <!-- 移动端子导航已移至 App 左上角抽屉，此处仅 PC 显示 -->
    <div v-if="!isMobile" class="sub-nav">
      <el-menu
        mode="horizontal"
        :router="true"
        :default-active="activeMenu"
        class="sub-menu"
      >
        <el-menu-item v-if="authStore.hasMechanicalScope && !authStore.isMechanicalClerk" index="/mechanical/parts">机械设备</el-menu-item>
        <el-menu-item v-if="authStore.hasMechanicalScope" index="/mechanical/requisition">机械领用</el-menu-item>
        <el-menu-item v-if="authStore.hasMechanicalScope && (authStore.canManageMechanical || authStore.isMechanicalClerk)" index="/mechanical/inventory">库存管理</el-menu-item>
        <el-menu-item v-if="authStore.hasMechanicalScope && !authStore.isMechanicalClerk" index="/mechanical/operation-logs">记录查询</el-menu-item>
        <el-menu-item v-if="authStore.canManageMechanical" index="/mechanical/users">用户管理</el-menu-item>
        <el-menu-item v-if="authStore.hasMechanicalScope" index="/mechanical/reports">报表统计</el-menu-item>
      </el-menu>
    </div>
    <div class="sub-content">
      <router-view v-slot="{ Component, route }">
        <Transition name="page-slide" mode="out-in">
          <keep-alive :max="8" :include="cachedViews">
            <component :is="Component" :key="route.name" class="page-view" />
          </keep-alive>
        </Transition>
      </router-view>
    </div>
  </div>
</template>

<script setup lang="ts">
// 定义组件名称，用于 App.vue 层级的 keep-alive 缓存
defineOptions({
  name: 'MechanicalLayout'
})

import { computed, onMounted, onActivated, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useIsMobile } from '@/composables/useIsMobile'
import { navLog } from '@/utils/navLog'

const route = useRoute()
const authStore = useAuthStore()
const { isMobile } = useIsMobile()

const activeMenu = computed(() => route.path || '/mechanical/parts')

onMounted(() => {
  navLog('MechanicalLayout mounted', { path: route.path })
})
watch(() => route.path, (path) => {
  navLog('MechanicalLayout route change', { path })
}, { immediate: false })

// 扩大缓存范围：缓存所有常用页面，提升切换速度
// 注意：Inventory、OperationLogs、UserManage、Reports 是共享组件，使用统一名称
const cachedViews = [
  'MechanicalSparePartList',
  'MechanicalSparePartRequisition',
  'Inventory',
  'OperationLogs',
  'UserManage',
  'Reports'
]

onActivated(() => {
  navLog('MechanicalLayout activated', { path: route.path })
})
</script>

<style scoped>
.mechanical-layout {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.sub-nav {
  flex-shrink: 0;
  margin-bottom: 12px;
}

.sub-nav .sub-menu {
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.sub-nav :deep(.el-menu--horizontal > .el-menu-item) {
  padding: 0 16px;
}

.sub-content {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

/* 子页面切换：淡入 + 轻微上移 */
.page-slide-enter-active,
.page-slide-leave-active {
  transition: opacity 0.1s ease, transform 0.1s ease;
}
.page-slide-enter-from {
  opacity: 0;
  transform: translateY(6px);
}
.page-slide-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
.page-view {
  transform: translateZ(0);
}

@media (max-width: 767px) {
  .sub-nav {
    margin-bottom: 10px;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    padding-bottom: 2px;
  }
  .sub-nav .sub-menu {
    flex-wrap: nowrap;
    min-width: max-content;
  }
  .sub-nav :deep(.el-menu--horizontal > .el-menu-item) {
    padding: 0 12px;
    font-size: 14px;
    white-space: nowrap;
  }
}
</style>
