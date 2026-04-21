<template>
  <div :class="['app-wrapper', { 'sidebar-collapsed': collapsed, 'mobile-sidebar': isMobile }]">
    <!-- Mobile overlay -->
    <div
      v-if="isMobile && sidebarVisible"
      class="sidebar-overlay"
      @click="sidebarVisible = false"
    />

    <!-- Sidebar (PC: always visible; Mobile: toggle) -->
    <Sidebar
      v-show="!isMobile || sidebarVisible"
      :collapsed="isMobile ? false : collapsed"
      @toggle-collapse="collapsed = !collapsed"
      @select="sidebarVisible = false"
    />

    <!-- Main container -->
    <div class="main-container">
      <Navbar @toggle-sidebar="sidebarVisible = !sidebarVisible" />
      <div class="app-main">
        <router-view v-slot="{ Component, route: viewRoute }">
          <transition name="page-fade" mode="out-in">
            <keep-alive :include="cachedViews" :max="10">
              <component :is="Component" :key="viewRoute.name" />
            </keep-alive>
          </transition>
        </router-view>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useIsMobile } from '@/composables/useIsMobile'
import Sidebar from './components/Sidebar.vue'
import Navbar from './components/Navbar.vue'

const route = useRoute()
const { isMobile } = useIsMobile()
const collapsed = ref(false)
const sidebarVisible = ref(false)

const cachedViews = [
  'HomeView',
  'SparePartList',
  'SparePartRequisition',
  'MechanicalSparePartList',
  'MechanicalSparePartRequisition',
  'Inventory',
  'MechanicalInventory',
  'OperationLogs',
  'MechanicalOperationLogs',
  'UserManage',
  'MechanicalUserManage',
  'Reports',
  'MechanicalReports',
]

watch(() => route.path, () => {
  sidebarVisible.value = false
})
</script>
