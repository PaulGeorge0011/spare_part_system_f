<template>
  <div class="sidebar-container">
    <div class="sidebar-logo" @click="$router.push('/home')">
      <div class="logo-icon">备</div>
      <span v-show="!collapsed" class="logo-title">制丝二设备管理</span>
    </div>

    <div class="sidebar-menu">
      <el-menu
        :default-active="activeMenu"
        :collapse="collapsed"
        :collapse-transition="false"
        :router="true"
        @select="$emit('select')"
      >
        <el-menu-item index="/home">
          <el-icon><HomeFilled /></el-icon>
          <template #title>首页</template>
        </el-menu-item>

        <template v-if="authStore.hasElectricalScope">
          <div v-show="!collapsed" class="menu-group-title">电气模块</div>
          <el-menu-item v-if="!authStore.isElectricalClerk" index="/electrical/parts">
            <el-icon><Box /></el-icon>
            <template #title>电气设备</template>
          </el-menu-item>
          <el-menu-item index="/electrical/requisition">
            <el-icon><ShoppingCart /></el-icon>
            <template #title>电气领用</template>
          </el-menu-item>
          <el-menu-item
            v-if="authStore.canManageElectrical || authStore.isElectricalClerk"
            index="/electrical/inventory"
          >
            <el-icon><Files /></el-icon>
            <template #title>库存管理</template>
          </el-menu-item>
          <el-menu-item v-if="!authStore.isElectricalClerk" index="/electrical/operation-logs">
            <el-icon><Document /></el-icon>
            <template #title>记录查询</template>
          </el-menu-item>
          <el-menu-item v-if="authStore.canManageElectrical" index="/electrical/users">
            <el-icon><User /></el-icon>
            <template #title>用户管理</template>
          </el-menu-item>
          <el-menu-item index="/electrical/reports">
            <el-icon><DataAnalysis /></el-icon>
            <template #title>报表统计</template>
          </el-menu-item>
        </template>

        <template v-if="authStore.hasMechanicalScope">
          <div v-show="!collapsed" class="menu-group-title">机械模块</div>
          <el-menu-item v-if="!authStore.isMechanicalClerk" index="/mechanical/parts">
            <el-icon><Box /></el-icon>
            <template #title>机械设备</template>
          </el-menu-item>
          <el-menu-item index="/mechanical/requisition">
            <el-icon><ShoppingCart /></el-icon>
            <template #title>机械领用</template>
          </el-menu-item>
          <el-menu-item
            v-if="authStore.canManageMechanical || authStore.isMechanicalClerk"
            index="/mechanical/inventory"
          >
            <el-icon><Files /></el-icon>
            <template #title>库存管理</template>
          </el-menu-item>
          <el-menu-item v-if="!authStore.isMechanicalClerk" index="/mechanical/operation-logs">
            <el-icon><Document /></el-icon>
            <template #title>记录查询</template>
          </el-menu-item>
          <el-menu-item v-if="authStore.canManageMechanical" index="/mechanical/users">
            <el-icon><User /></el-icon>
            <template #title>用户管理</template>
          </el-menu-item>
          <el-menu-item index="/mechanical/reports">
            <el-icon><DataAnalysis /></el-icon>
            <template #title>报表统计</template>
          </el-menu-item>
        </template>
      </el-menu>
    </div>

    <div class="sidebar-footer">
      <div class="collapse-btn" @click="$emit('toggle-collapse')">
        <el-icon :size="18">
          <Fold v-if="!collapsed" />
          <Expand v-else />
        </el-icon>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  HomeFilled, Box, ShoppingCart, Files, Document,
  User, DataAnalysis, Fold, Expand,
} from '@element-plus/icons-vue'

defineProps<{ collapsed: boolean }>()
defineEmits<{
  'toggle-collapse': []
  'select': []
}>()

const route = useRoute()
const authStore = useAuthStore()

const activeMenu = computed(() => route.path)
</script>
