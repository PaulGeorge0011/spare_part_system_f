import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { defaultPathForUser } from '@/utils/defaultPath'
import { navLog, navLogStart } from '@/utils/navLog'
import type { ModulePermLevel } from '@/utils/modules'

// 静态导入所有页面组件，取消懒加载以提升页面流转速度（数据量不大）
import Login from '@/views/Login.vue'
import Register from '@/views/Register.vue'
import SsoCallback from '@/views/sso-callback.vue'
import WechatLoginEntry from '@/views/WechatLoginEntry.vue'
import HomeView from '@/views/HomeView.vue'
import ElectricalLayout from '@/views/layouts/ElectricalLayout.vue'
import MechanicalLayout from '@/views/layouts/MechanicalLayout.vue'
import SparePartList from '@/views/SparePartList.vue'
import MechanicalSparePartList from '@/views/MechanicalSparePartList.vue'
import SparePartRequisition from '@/views/SparePartRequisition.vue'
import MechanicalSparePartRequisition from '@/views/MechanicalSparePartRequisition.vue'
import InventoryView from '@/views/InventoryView.vue'
import OperationLogView from '@/views/OperationLogView.vue'
import UserManage from '@/views/UserManage.vue'
import ReportsView from '@/views/ReportsView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  scrollBehavior(_to, _from, savedPosition) {
    if (savedPosition) return savedPosition
    return { top: 0, left: 0, behavior: 'auto' as ScrollBehavior }
  },
  routes: [
    { path: '/login',        name: 'Login',       component: Login,       meta: { public: true } },
    { path: '/register',     name: 'Register',    component: Register,    meta: { public: true } },
    { path: '/sso/callback', name: 'SsoCallback', component: SsoCallback, meta: { public: true } },
    { path: '/wechat-login', name: 'WechatLoginEntry', component: WechatLoginEntry, meta: { public: true } },
    { path: '/home',         name: 'Home',        component: HomeView },
    { path: '/', redirect: () => ({ path: '/home' }) },

    // 电气备件管理
    {
      path: '/electrical',
      component: ElectricalLayout,
      meta: { moduleId: 'electrical', minLevel: 'viewer' as ModulePermLevel },
      children: [
        { path: '', redirect: (to) => ({ path: '/electrical/parts', query: to.query }) },
        {
          path: 'parts',
          name: 'SparePartList',
          component: SparePartList,
          meta: { moduleId: 'electrical', minLevel: 'viewer' as ModulePermLevel, noClerk: true },
        },
        {
          path: 'requisition',
          name: 'SparePartRequisition',
          component: SparePartRequisition,
          meta: { moduleId: 'electrical', minLevel: 'viewer' as ModulePermLevel },
        },
        {
          path: 'inventory',
          name: 'Inventory',
          component: InventoryView,
          meta: { moduleId: 'electrical', minLevel: 'viewer' as ModulePermLevel },
        },
        {
          path: 'operation-logs',
          name: 'OperationLogs',
          component: OperationLogView,
          meta: { moduleId: 'electrical', minLevel: 'viewer' as ModulePermLevel, noClerk: true },
        },
        {
          path: 'users',
          name: 'UserManage',
          component: UserManage,
          meta: { moduleId: 'electrical', minLevel: 'admin' as ModulePermLevel },
        },
        {
          path: 'reports',
          name: 'Reports',
          component: ReportsView,
          meta: { moduleId: 'electrical', minLevel: 'viewer' as ModulePermLevel },
        },
      ],
    },

    // 机械备件管理
    {
      path: '/mechanical',
      component: MechanicalLayout,
      meta: { moduleId: 'mechanical', minLevel: 'viewer' as ModulePermLevel },
      children: [
        { path: '', redirect: (to) => ({ path: '/mechanical/parts', query: to.query }) },
        {
          path: 'parts',
          name: 'MechanicalSparePartList',
          component: MechanicalSparePartList,
          meta: { moduleId: 'mechanical', minLevel: 'viewer' as ModulePermLevel, noClerk: true },
        },
        {
          path: 'requisition',
          name: 'MechanicalSparePartRequisition',
          component: MechanicalSparePartRequisition,
          meta: { moduleId: 'mechanical', minLevel: 'viewer' as ModulePermLevel },
        },
        {
          path: 'inventory',
          name: 'MechanicalInventory',
          component: InventoryView,
          meta: { moduleId: 'mechanical', minLevel: 'viewer' as ModulePermLevel },
        },
        {
          path: 'operation-logs',
          name: 'MechanicalOperationLogs',
          component: OperationLogView,
          meta: { moduleId: 'mechanical', minLevel: 'viewer' as ModulePermLevel, noClerk: true },
        },
        {
          path: 'users',
          name: 'MechanicalUserManage',
          component: UserManage,
          meta: { moduleId: 'mechanical', minLevel: 'admin' as ModulePermLevel },
        },
        {
          path: 'reports',
          name: 'MechanicalReports',
          component: ReportsView,
          meta: { moduleId: 'mechanical', minLevel: 'viewer' as ModulePermLevel },
        },
      ],
    },

    // 兼容旧路径重定向
    { path: '/spare-parts',            redirect: '/electrical/parts'        },
    { path: '/requisition',            redirect: '/electrical/requisition'  },
    { path: '/mechanical-spare-parts', redirect: '/mechanical/parts'        },
    { path: '/mechanical-requisition', redirect: '/mechanical/requisition'  },
    { path: '/inventory',              redirect: '/electrical/inventory'     },
    { path: '/operation-logs',         redirect: '/electrical/operation-logs' },
    { path: '/users',                  redirect: '/electrical/users'         },
    { path: '/reports',                redirect: '/electrical/reports'       },
  ],
})

// 用户信息加载状态
let userFetchPromise: Promise<any> | null = null
let navStartTime = 0

/**
 * 路由守卫：
 * - 所有受保护页面均通过 meta.moduleId + meta.minLevel 控制权限
 * - 统一调用 auth.canAccessModule() 做判断，无需按路径前缀分叉
 */
router.beforeEach(async (to, from, next) => {
  navStartTime = navLogStart()
  navLog('beforeEach start', { from: from.path, to: to.path })

  const auth = useAuthStore()
  const token = auth.token ?? localStorage.getItem('access_token')

  // 公开页面直接放行
  if (to.meta.public) {
    if (to.name === 'SsoCallback') { next(); return }
    if (token && auth.user) { next(defaultPathForUser(auth)); return }
    next()
    return
  }

  // 无 token 直接跳转登录
  if (!token) {
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }

  // 优先使用缓存用户信息，后台静默刷新
  if (auth.user) {
    if (!userFetchPromise) {
      userFetchPromise = auth.fetchUser().catch(() => null).finally(() => { userFetchPromise = null })
    }
  } else {
    if (!userFetchPromise) {
      userFetchPromise = auth.fetchUser().catch(() => { auth.clearAuth(); return null }).finally(() => { userFetchPromise = null })
    }
    try { await userFetchPromise } catch { /* ignore */ }
    if (!auth.user) {
      next({ path: '/login', query: { redirect: to.fullPath } })
      return
    }
  }

  const path = to.path

  // 进入电气/机械系统根时，重定向到备件列表（只读用户也可访问）
  if (path === '/electrical' || path === '/electrical/') {
    if (auth.canAccessModule('electrical', 'viewer')) {
      next({ path: auth.isElectricalClerk ? '/electrical/requisition' : '/electrical/parts', query: to.query, replace: true })
      return
    }
  }
  if (path === '/mechanical' || path === '/mechanical/') {
    if (auth.canAccessModule('mechanical', 'viewer')) {
      next({ path: auth.isMechanicalClerk ? '/mechanical/requisition' : '/mechanical/parts', query: to.query, replace: true })
      return
    }
  }

  // 领用员不能访问备件列表、操作记录（库存管理已对领用员开放）
  if (to.meta.noClerk) {
    if (auth.isElectricalClerk && (to.meta.moduleId as string) === 'electrical') {
      next({ path: '/electrical/requisition', replace: true })
      return
    }
    if (auth.isMechanicalClerk && (to.meta.moduleId as string) === 'mechanical') {
      next({ path: '/mechanical/requisition', replace: true })
      return
    }
  }

  // 统一模块权限校验（所有带 moduleId meta 的路由）
  if (to.meta.moduleId) {
    const moduleId = to.meta.moduleId as string
    const minLevel = (to.meta.minLevel as ModulePermLevel) ?? 'viewer'
    if (!auth.canAccessModule(moduleId, minLevel)) {
      next({ path: '/home', replace: true })
      return
    }
  }

  navLog('beforeEach next', { to: to.path }, navStartTime)
  next()
})

router.afterEach((to) => {
  navLog('afterEach', { to: to.path, name: to.name }, navStartTime)
})

export default router
