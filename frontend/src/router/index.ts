import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { defaultPathForUser } from '@/utils/defaultPath'
import { navLog, navLogStart } from '@/utils/navLog'
import type { ModulePermLevel } from '@/utils/modules'

import Login from '@/views/Login.vue'
import Register from '@/views/Register.vue'
import SetPassword from '@/views/SetPassword.vue'
import SsoCallback from '@/views/sso-callback.vue'
import WechatLoginEntry from '@/views/WechatLoginEntry.vue'
import HomeView from '@/views/HomeView.vue'
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
    // Public pages (no layout)
    { path: '/login',        name: 'Login',       component: Login,       meta: { public: true } },
    { path: '/register',     name: 'Register',    component: Register,    meta: { public: true } },
    { path: '/set-password', name: 'SetPassword', component: SetPassword, meta: { public: true } },
    { path: '/sso/callback', name: 'SsoCallback', component: SsoCallback, meta: { public: true } },
    { path: '/wechat-login', name: 'WechatLoginEntry', component: WechatLoginEntry, meta: { public: true } },

    // Home
    { path: '/home', name: 'Home', component: HomeView },
    { path: '/', redirect: () => ({ path: '/home' }) },

    // Electrical module
    { path: '/electrical', redirect: '/electrical/parts' },
    {
      path: '/electrical/parts',
      name: 'SparePartList',
      component: SparePartList,
      meta: { moduleId: 'electrical', minLevel: 'viewer' as ModulePermLevel, noClerk: true },
    },
    {
      path: '/electrical/requisition',
      name: 'SparePartRequisition',
      component: SparePartRequisition,
      meta: { moduleId: 'electrical', minLevel: 'viewer' as ModulePermLevel },
    },
    {
      path: '/electrical/inventory',
      name: 'Inventory',
      component: InventoryView,
      meta: { moduleId: 'electrical', minLevel: 'viewer' as ModulePermLevel },
    },
    {
      path: '/electrical/operation-logs',
      name: 'OperationLogs',
      component: OperationLogView,
      meta: { moduleId: 'electrical', minLevel: 'viewer' as ModulePermLevel, noClerk: true },
    },
    {
      path: '/electrical/users',
      name: 'UserManage',
      component: UserManage,
      meta: { moduleId: 'electrical', minLevel: 'admin' as ModulePermLevel },
    },
    {
      path: '/electrical/reports',
      name: 'Reports',
      component: ReportsView,
      meta: { moduleId: 'electrical', minLevel: 'viewer' as ModulePermLevel },
    },

    // Mechanical module
    { path: '/mechanical', redirect: '/mechanical/parts' },
    {
      path: '/mechanical/parts',
      name: 'MechanicalSparePartList',
      component: MechanicalSparePartList,
      meta: { moduleId: 'mechanical', minLevel: 'viewer' as ModulePermLevel, noClerk: true },
    },
    {
      path: '/mechanical/requisition',
      name: 'MechanicalSparePartRequisition',
      component: MechanicalSparePartRequisition,
      meta: { moduleId: 'mechanical', minLevel: 'viewer' as ModulePermLevel },
    },
    {
      path: '/mechanical/inventory',
      name: 'MechanicalInventory',
      component: InventoryView,
      meta: { moduleId: 'mechanical', minLevel: 'viewer' as ModulePermLevel },
    },
    {
      path: '/mechanical/operation-logs',
      name: 'MechanicalOperationLogs',
      component: OperationLogView,
      meta: { moduleId: 'mechanical', minLevel: 'viewer' as ModulePermLevel, noClerk: true },
    },
    {
      path: '/mechanical/users',
      name: 'MechanicalUserManage',
      component: UserManage,
      meta: { moduleId: 'mechanical', minLevel: 'admin' as ModulePermLevel },
    },
    {
      path: '/mechanical/reports',
      name: 'MechanicalReports',
      component: ReportsView,
      meta: { moduleId: 'mechanical', minLevel: 'viewer' as ModulePermLevel },
    },

    // Legacy redirects
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

let userFetchPromise: Promise<any> | null = null
let navStartTime = 0

router.beforeEach(async (to, from, next) => {
  navStartTime = navLogStart()
  navLog('beforeEach start', { from: from.path, to: to.path })

  const auth = useAuthStore()
  const token = auth.token ?? localStorage.getItem('access_token')

  if (to.meta.public) {
    if (to.name === 'SsoCallback') { next(); return }
    if (token && auth.user) { next(defaultPathForUser(auth)); return }
    next()
    return
  }

  if (!token) {
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }

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
